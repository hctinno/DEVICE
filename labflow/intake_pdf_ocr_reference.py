"""Local, revision-bound OCR observations; never original text or execution authority."""
import sys
from pathlib import Path

if __name__=='__main__' and __package__ is None:
    # -I -S: use only this trusted checkout and the existing interpreter's venv
    # packages, without PYTHONPATH/user site/.pth/sitecustomize execution.
    sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(sys.executable).parent.parent/'Lib/site-packages')]
    __package__='labflow'

import ctypes
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import threading
import time

from . import intake_docx_reference as _source
from .android_emulator_check import _WindowsJob
from .development_paths import load_layout
from .document_extract import ExtractionLimits, extract_document
from .store import Store, StoreOpenError, _ExistingBinding, canonical, identifier

_PREFIX='intake_pdf_ocr_reference_'
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_SHA=re.compile(r'[a-f0-9]{64}\Z',re.ASCII)
_PDF_BYTES=2097152;_TEXT_BYTES=16384;_RASTER_BYTES=8388608;_WORK_BYTES=16777216
_WORKER_SECONDS=15;_CLEANUP_SECONDS=3;_WORKER_MEMORY_MIB=512
_REQUEST_BYTES=16384;_REPLY_BYTES=2097152;_FRAME=b'DGM-OCR-WORKER/1 '


class IntakePdfOcrReferenceError(ValueError):
    def __init__(self,code):
        self.code=code if code.startswith(_PREFIX) else _PREFIX+code
        super().__init__(self.code)


def _fail(code):raise IntakePdfOcrReferenceError(code)
def _hash(raw):return hashlib.sha256(raw).hexdigest()
def _bytes(value):return canonical(value).encode('utf-8')
def _save(path,raw):
    with path.open('xb') as target:target.write(raw)


@dataclass(frozen=True)
class LocalOcrTools:
    """Explicit trusted installation pins; no PATH search, installation, or fallback."""
    tesseract_executable: str
    renderer_executable: str
    tesseract_sha256: str
    renderer_sha256: str
    dll_sha256: str
    language_sha256: str
    expected_tesseract_version: str
    expected_renderer_version: str


def _file_pin(path,expected,cap=134217728):
    if type(expected) is not str or _SHA.fullmatch(expected) is None:_fail('tools_unavailable')
    before=path.lstat()
    if (not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode)
            or getattr(before,'st_file_attributes',0)&0x400 or before.st_size>cap):_fail('tools_unavailable')
    digest=hashlib.sha256();count=0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            count+=len(block)
            if count>cap:_fail('tools_unavailable')
            digest.update(block)
    after=path.lstat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        _fail('tool_pin_mismatch')
    if digest.hexdigest()!=expected:_fail('tool_pin_mismatch')
    return dict(path=str(path),bytes=count,sha256=expected)


def _tools(config):
    if type(config) is not LocalOcrTools or os.name!='nt':_fail('tools_unavailable')
    tesseract,renderer=Path(config.tesseract_executable),Path(config.renderer_executable)
    for path,name in ((tesseract,'tesseract.exe'),(renderer,'pdftoppm.exe')):
        if (not path.is_absolute() or re.fullmatch(r'[A-Za-z]:',path.drive) is None
                or '..' in path.parts or path.name.lower()!=name):_fail('tools_unavailable')
    dll=tesseract.parent/'libtesseract-5.dll';language=tesseract.parent/'tessdata/eng.traineddata'
    pins=dict(tesseract=_file_pin(tesseract,config.tesseract_sha256),renderer=_file_pin(renderer,config.renderer_sha256),
        dll=_file_pin(dll,config.dll_sha256),language_data=_file_pin(language,config.language_sha256))
    with os.add_dll_directory(str(tesseract.parent)):
        library=ctypes.CDLL(str(dll));library.TessVersion.argtypes=[];library.TessVersion.restype=ctypes.c_char_p
        version=library.TessVersion().decode('ascii')
    if len(version)>100 or version!=config.expected_tesseract_version:_fail('tool_version_mismatch')
    pins.update(tesseract_version=version,tesseract_version_source='installed_dll_TessVersion',
        CLI_version_evidence='not_claimed; installed --version may return no bytes',language='eng')
    return pins


def _run(command,work,label,*,seconds,stdout_cap):
    """Run one known local child with bounded pipe prefixes and deterministic cleanup."""
    if not 0<seconds<=5 or type(stdout_cap) is not int or not 0<stdout_cap<=_TEXT_BYTES:_fail('invalid_argument')
    buffers=[bytearray(),bytearray()];caps=[stdout_cap,8192];overflow=threading.Event();reader_errors=[]
    process=job=None;readers=[];primary=None;reaped=joined=closed=False;deadline=time.monotonic()+seconds
    assigned=False;job_closed=os.name!='nt'
    def read(pipe,index):
        try:
            while True:
                block=pipe.read(4096)
                if not block:break
                remaining=caps[index]-len(buffers[index]);buffers[index].extend(block[:remaining])
                if len(block)>remaining:overflow.set();break
        except BaseException as error:reader_errors.append(error);overflow.set()
    try:
        environment=dict(os.environ,TMP=str(work),TEMP=str(work))
        # Reuse only the common Win32 Job primitive, never its SDK/boot paths.
        # Suspending before assignment also owns venv redirector descendants.
        if os.name=='nt':job=_WindowsJob(256)
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)|(0x4 if job else 0)
        process=subprocess.Popen(command,cwd=work,env=environment,stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,creationflags=flags)
        if job:job.assign_resume(process);assigned=True
        for index,pipe in enumerate((process.stdout,process.stderr)):
            reader=threading.Thread(target=read,args=(pipe,index),daemon=True);readers.append(reader);reader.start()
        while process.poll() is None:
            if overflow.is_set():break
            if time.monotonic()>=deadline:_fail('process_timeout')
            overflow.wait(min(0.01,max(0,deadline-time.monotonic())))
        if reader_errors:raise reader_errors[0]
        if overflow.is_set():_fail('output_limit')
    except BaseException as error:primary=error
    finally:
        def cleanup(action):
            nonlocal primary
            try:action()
            except BaseException as error:
                if primary is None:primary=error
        if job is not None:
            def close_job():
                if job.handle:
                    if not job.kernel.CloseHandle(job.handle):_fail('cleanup_unknown')
                    job.handle=None
            cleanup(close_job);job_closed=job.handle is None
        if process is not None:
            if process.poll() is None:cleanup(process.kill)
            cleanup(lambda:process.wait(timeout=1));reaped=process.poll() is not None
            for reader in readers:cleanup(lambda reader=reader:reader.join(timeout=1))
            joined=all(not reader.is_alive() for reader in readers)
            # Never wait indefinitely on BufferedReader's lock after uncertain
            # reader cleanup. The incomplete record remains a failure.
            for index,pipe in enumerate((process.stdout,process.stderr)):
                if index>=len(readers) or not readers[index].is_alive():cleanup(pipe.close)
            closed=all(pipe.closed for pipe in (process.stdout,process.stderr))
        else:reaped=joined=closed=True
        if primary is None and reader_errors:primary=reader_errors[0]
        if primary is None and overflow.is_set():primary=IntakePdfOcrReferenceError('output_limit')
        if primary is None and not (reaped and joined and closed and job_closed):primary=IntakePdfOcrReferenceError('cleanup_unknown')
        if primary is None and process.returncode!=0:primary=IntakePdfOcrReferenceError('process_failed')
        record=dict(argv=[os.fspath(part) for part in command],returncode=process.returncode if process else None,
            child_reaped=reaped,readers_joined=joined,pipes_closed=closed,overflow=overflow.is_set(),
            job_assigned_before_resume=assigned,job_closed=job_closed,job_memory_limit_mib=256 if job else None,
            stdout_bytes=len(buffers[0]),stderr_bytes=len(buffers[1]),
            failure=primary.code if isinstance(primary,IntakePdfOcrReferenceError) else 'control_or_storage_error' if primary else None)
        for suffix,raw in (('stdout.bin',bytes(buffers[0])),('stderr.bin',bytes(buffers[1])),('process.json',_bytes(record))):
            cleanup(lambda suffix=suffix,raw=raw:_save(work/(label+'-'+suffix),raw))
    if primary is not None:raise primary
    return bytes(buffers[0]),bytes(buffers[1])


def _work(path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts:_fail('invalid_argument')
    layout=load_layout();path=layout.reference(str(path));runs=layout.directory('runs');control=layout.control_root()
    if path==runs or not path.is_relative_to(runs) or path==control or path.is_relative_to(control):_fail('run_unavailable')
    try:path.mkdir(parents=True,exist_ok=False)
    except OSError:_fail('run_unavailable')
    return path


def _budget(work,deadline):
    if time.monotonic()>=deadline:_fail('total_wall_exhausted')
    total=0
    for path in work.iterdir():
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:_fail('input_limit')
        total+=info.st_size
    if total>_WORK_BYTES:_fail('output_limit')
    return min(5,deadline-time.monotonic())


def _eligible(baseline):
    return (baseline['status']=='image_only' and baseline['complete'] is False
        and baseline['total_pages']==baseline['processed_pages']==len(baseline['pages'])==1
        and baseline['pages'][0]['status']=='image_only' and baseline['pages'][0]['text']==''
        and baseline['issues'] and all(row['code']=='ocr_required' for row in baseline['issues']))


def _observe(payload,work,config,baseline,binding,deadline,source_check):
    result=dict(schema_version=1,kind='intake_pdf_ocr_reference',status='ocr_required',binding=binding,
        baseline=baseline,ocr=None,tools=None,errors=[],complete=False,native_once_eligible=False,
        provenance=dict(original_text=False,image_text_equivalence='not_verified',execution_authority=False,
            origin_authenticated=False,same_account_arbitrary_code_defense=False),
        limits=dict(pdf_input_bytes=_PDF_BYTES,pages=1,raster_long_side=1600,raster_pixels=2560000,
            raster_bytes=_RASTER_BYTES,OCR_UTF8_bytes=_TEXT_BYTES,stderr_bytes=8192,
            per_process_seconds=5,total_wall_seconds=15,work_bytes=_WORK_BYTES,automatic_retries=0))
    primary=None
    try:
        if not _eligible(baseline):_fail('unsupported_scope')
        tools=_tools(config);result['tools']=tools
        stdout,stderr=_run([config.renderer_executable,'-v'],work,'renderer-version',seconds=_budget(work,deadline),stdout_cap=8192)
        version=(stdout+stderr).decode('utf-8',errors='strict')
        if not version.startswith('pdftoppm version '+config.expected_renderer_version+'\r\n') and not version.startswith('pdftoppm version '+config.expected_renderer_version+'\n'):
            _fail('tool_version_mismatch')
        tools['renderer_version']=config.expected_renderer_version;tools['renderer_version_source']='actual_version_child'
        _save(work/'source.pdf',payload)
        _run([config.renderer_executable,'-f','1','-l','1','-singlefile','-scale-to','1600','-gray','-png',
            str(work/'source.pdf'),str(work/'page')],work,'render',seconds=_budget(work,deadline),stdout_cap=8192)
        image=work/'page.png'
        if image.stat().st_size>_RASTER_BYTES:_fail('output_limit')
        from PIL import Image
        with Image.open(image) as bitmap:
            width,height=bitmap.size
            if bitmap.format!='PNG' or not 0<width<=1600 or not 0<height<=1600 or width*height>2560000:_fail('output_limit')
            bitmap.verify()
        raw,_=_run([config.tesseract_executable,str(image),'stdout','--tessdata-dir',str(Path(config.tesseract_executable).parent/'tessdata'),
            '-l','eng','--psm','6'],work,'ocr',seconds=_budget(work,deadline),stdout_cap=_TEXT_BYTES)
        text=raw.decode('utf-8',errors='strict')
        if not text.strip():_fail('empty_ocr')
        # Recheck source and installation pins after the actual local processes.
        source_check();after=_tools(config)
        if any(after[key]!=tools[key] for key in after):_fail('tool_pin_mismatch')
        _budget(work,deadline)
        result['ocr']=dict(page_number=1,method='tesseract_local',text=text,text_sha256=_hash(raw),
            raster_sha256=_hash(image.read_bytes()),raster_width=width,raster_height=height,
            image_text_equivalence='not_verified',original_text=False)
        result['status']='ocr_observed'
    except _CONTROL as error:primary=error;result['errors']=[_PREFIX+'control_interrupted']
    except IntakePdfOcrReferenceError as error:result['errors']=[error.code]
    except _source.IntakeDocxReferenceError as error:result['errors']=[_PREFIX+error.code.removeprefix('intake_docx_reference_')]
    except (OSError,ValueError,StoreOpenError):result['errors']=[_PREFIX+'tools_unavailable']
    except Exception:result['errors']=[_PREFIX+'storage_error']
    if result['status']!='ocr_observed':result['ocr']=None
    result['reference_id']=_hash(_bytes(result))
    try:_save(work/'inner-reference.json',_bytes(result))
    except BaseException as error:
        if primary is None:primary=error
    if primary is not None:raise primary
    return result


def _synthetic(store,selected,sha):
    with store.connection() as con:
        con.execute('PRAGMA query_only=ON')
        row=con.execute('SELECT synthetic FROM intake_sources WHERE source_id=?',(selected['source_id'],)).fetchone()
    if row is None or row['synthetic']!=1 or not store.evidence_is_synthetic(sha):_fail('synthetic_required')


def _read_inner_reference(store,intake_id,document_path,*,expected_revision,expected_sha256,tools=None,run_root):
    """Observe one selected synthetic image PDF; never mutate its intake or default context."""
    started=time.monotonic();binding=store.__dict__.get('_existing_binding') if type(store) is Store else None
    if type(binding) is not _ExistingBinding or binding.state!='open':_fail('store_invalid')
    try:
        if (type(intake_id) is not str or not _source._path(document_path) or not document_path.lower().endswith('.pdf')
                or len(document_path.encode('utf-8'))>1024 or type(expected_revision) is not int or expected_revision<1
                or type(expected_sha256) is not str or _SHA.fullmatch(expected_sha256) is None
                or not isinstance(run_root,(str,Path)) or not Path(run_root).is_absolute()
                or '..' in Path(run_root).parts or len(os.fspath(run_root).encode('utf-8'))>4096
                or any(ord(char)<32 for char in os.fspath(run_root))):_fail('invalid_argument')
        identifier(intake_id)
    except (UnicodeError,TypeError,ValueError) as error:
        if isinstance(error,IntakePdfOcrReferenceError):raise
        _fail('invalid_argument')
    try:
        selected=_source._selection(store,intake_id,document_path,expected_revision,expected_sha256);item=selected['document']
        if item['bytes']>_PDF_BYTES:_fail('input_limit')
        _synthetic(store,selected,expected_sha256)
        path=store.blob_path(expected_sha256)
        with ExitStack() as owned:
            descriptor,before=owned.enter_context(_source._source(binding,path,item['bytes'],pin=True))
            def current():
                if (_source._read(descriptor,item['bytes'],retain=False)[0]!=expected_sha256
                        or _source._info(binding,path,descriptor)!=before or _source._info(binding,path)!=before
                        or _source._selection(store,intake_id,document_path,expected_revision,expected_sha256)!=selected):
                    _fail('source_integrity_invalid')
                _synthetic(store,selected,expected_sha256)
            actual,payload=_source._read(descriptor,item['bytes'],retain=True)
            if actual!=expected_sha256:_fail('source_integrity_invalid')
            # Keep unsupported input bounded too. Only an eligible image page
            # proceeds to the unchanged default extractor (which has no text
            # output for that page), retaining its exact original baseline.
            current();baseline=extract_document(payload,document_path,limits=ExtractionLimits(
                max_input_bytes=_PDF_BYTES,max_pages=1,max_output_chars=_TEXT_BYTES))
            if _eligible(baseline):baseline=extract_document(payload,document_path)
            work=_work(run_root)
            def finish_source():
                current()
                # A successful observation is persisted only after the held
                # native source descriptor has closed without a late failure.
                owned.close()
            return _observe(payload,work,tools,baseline,selected,started+15,finish_source)
    except _source.IntakeDocxReferenceError as error:
        _fail(error.code.removeprefix('intake_docx_reference_'))


def ocr_page_citation(reference,line_start,line_end):
    """Check internal derived-text consistency; does not authenticate OCR accuracy or origin."""
    try:
        unsigned={key:value for key,value in reference.items() if key!='reference_id'}
        if (_hash(_bytes(unsigned))!=reference['reference_id'] or reference['kind']!='intake_pdf_ocr_reference'
                or reference['status']!='ocr_observed' or reference['complete'] is not False
                or reference['native_once_eligible'] is not False
                or ('isolation' in reference and reference['isolation']['outcome']!='completed')):_fail('invalid_reference')
        ocr=reference['ocr'];text=ocr['text'];lines=text.splitlines()
        if (type(line_start) is not int or type(line_end) is not int or not 1<=line_start<=line_end<=len(lines)
                or ocr['page_number']!=1 or ocr['method']!='tesseract_local' or ocr['original_text'] is not False
                or _hash(text.encode('utf-8'))!=ocr['text_sha256']):_fail('invalid_reference')
        return dict(schema_version=1,kind='pdf_ocr_page',reference_id=reference['reference_id'],
            source_sha256=reference['binding']['document']['sha256'],revision_fingerprint=reference['binding']['revision_fingerprint'],
            page_number=1,method='tesseract_local',engine_version=reference['tools']['tesseract_version'],
            text_sha256=ocr['text_sha256'],line_start=line_start,line_end=line_end,quote='\n'.join(lines[line_start-1:line_end]),
            original_text=False,image_text_equivalence='not_verified',native_once_eligible=False)
    except IntakePdfOcrReferenceError:raise
    except (KeyError,TypeError,ValueError,AttributeError):_fail('invalid_reference')


def _strict_json(raw,cap):
    if type(raw) is not bytes or not 0<len(raw)<=cap:_fail('worker_protocol')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:_fail('worker_protocol')
            result[key]=value
        return result
    try:
        result=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
            parse_constant=lambda value:_fail('worker_protocol'))
        pending=[(result,0)];count=0
        while pending:
            value,depth=pending.pop();count+=1
            if depth>32 or count>65536:_fail('worker_protocol')
            if type(value) is dict:pending.extend((item,depth+1) for item in value.values())
            elif type(value) is list:pending.extend((item,depth+1) for item in value)
        if _bytes(result)!=raw:_fail('worker_protocol')
        return result
    except IntakePdfOcrReferenceError:raise
    except (UnicodeError,ValueError,RecursionError,TypeError):_fail('worker_protocol')


def _borrowed(store):
    binding=store.__dict__.get('_existing_binding') if type(store) is Store else None
    if (type(binding) is not _ExistingBinding or binding.state!='open'
            or store.root!=binding.root or store.db!=binding.db):_fail('store_invalid')
    return binding,store.root,store.db


def _worker_command():
    return [sys.executable,'-I','-S','-B',str(Path(__file__).absolute()),'--ocr-worker-v1']


def _validate_request(request):
    fields='schema_version kind request_id store_root intake_id document_path expected_revision expected_sha256 tools run_root'.split()
    try:
        if (type(request) is not dict or set(request)!=set(fields) or type(request['schema_version']) is not int
                or request['schema_version']!=1 or request['kind']!='intake_pdf_ocr_worker_request'
                or type(request['request_id']) is not str or re.fullmatch(r'[a-f0-9]{32}',request['request_id']) is None
                or type(request['intake_id']) is not str or not _source._path(request['document_path'])
                or not request['document_path'].lower().endswith('.pdf') or len(request['document_path'].encode('utf-8'))>1024
                or type(request['expected_revision']) is not int or request['expected_revision']<1
                or type(request['expected_sha256']) is not str or _SHA.fullmatch(request['expected_sha256']) is None):_fail('worker_protocol')
        identifier(request['intake_id'])
        for name in ('store_root','run_root'):
            value=request[name]
            if (type(value) is not str or len(value.encode('utf-8'))>4096 or any(ord(char)<32 for char in value)
                    or not Path(value).is_absolute() or re.fullmatch(r'[A-Za-z]:',Path(value).drive) is None
                    or '..' in Path(value).parts):_fail('worker_protocol')
        config=request['tools']
        if config is not None and (type(config) is not dict or set(config)!=set(LocalOcrTools.__dataclass_fields__)
                or any(type(value) is not str or len(value.encode('utf-8'))>4096 for value in config.values())):_fail('worker_protocol')
    except IntakePdfOcrReferenceError:raise
    except (UnicodeError,ValueError,TypeError,KeyError):_fail('worker_protocol')


def _request(store,intake_id,document_path,revision,sha,tools,run_root):
    loan=_borrowed(store)
    try:
        identifier(intake_id)
        if (type(intake_id) is not str or type(document_path) is not str or len(document_path)>1024
                or not _source._path(document_path) or not document_path.lower().endswith('.pdf')
                or len(document_path.encode('utf-8'))>1024 or type(revision) is not int or revision<1
                or type(sha) is not str or _SHA.fullmatch(sha) is None
                or type(run_root) not in (str,type(Path())) or len(os.fspath(run_root))>4096 or not Path(run_root).is_absolute()
                or '..' in Path(run_root).parts or any(ord(char)<32 for char in os.fspath(run_root))):_fail('invalid_argument')
        if tools is not None and type(tools) is not LocalOcrTools:_fail('invalid_argument')
        # Validate primitive fields before serialization; dataclass asdict would
        # deepcopy an arbitrary non-string value in the parent before admission.
        config={name:getattr(tools,name) for name in LocalOcrTools.__dataclass_fields__} if tools is not None else None
        if config is not None and any(type(value) is not str or len(value)>4096 or len(value.encode('utf-8'))>4096 for value in config.values()):_fail('invalid_argument')
        layout=load_layout();target=layout.reference(str(run_root));runs=layout.directory('runs');control=layout.control_root()
        if (target==runs or not target.is_relative_to(runs) or target==control or target.is_relative_to(control)
                or target.exists()):_fail('run_unavailable')
        request=dict(schema_version=1,kind='intake_pdf_ocr_worker_request',request_id=secrets.token_hex(16),
            store_root=str(loan[1]),intake_id=intake_id,document_path=document_path,expected_revision=revision,
            expected_sha256=sha,tools=config,run_root=str(target))
        _validate_request(request)
        raw=_bytes(request)
        if len(raw)>_REQUEST_BYTES:_fail('invalid_argument')
        evidence=target.parent/('ocr-worker-'+request['request_id'][:16]);evidence.mkdir(parents=True,exist_ok=False)
        return request,raw,evidence,loan
    except IntakePdfOcrReferenceError:raise
    except (UnicodeError,ValueError,TypeError):_fail('invalid_argument')
    except OSError:_fail('run_unavailable')


def _execute_worker(raw,evidence):
    """Only fixed trusted worker code; deadline and one bounded cleanup budget."""
    process=job=None;readers=[];writer=None;buffers=[bytearray(),bytearray()]
    overflow=threading.Event();thread_errors=[];primary=None;assigned=job_closed=False
    started=time.monotonic();deadline=started+_WORKER_SECONDS;peak=None;reaped=joined=written=closed=False
    configured_memory=None;job_flags=None
    def read(pipe,index,cap):
        try:
            while True:
                block=pipe.read(4096)
                if not block:break
                left=cap-len(buffers[index]);buffers[index].extend(block[:left])
                if len(block)>left:overflow.set();break
        except BaseException as error:thread_errors.append(error);overflow.set()
    def write():
        try:
            for offset in range(0,len(raw),4096):process.stdin.write(raw[offset:offset+4096])
            process.stdin.flush()
        except BaseException as error:thread_errors.append(error)
        finally:
            try:process.stdin.close()
            except BaseException as error:thread_errors.append(error)
    try:
        if os.name!='nt':_fail('worker_unavailable')
        job=_WindowsJob(_WORKER_MEMORY_MIB)
        configured=job.extended()
        if not job.kernel.QueryInformationJobObject(job.handle,9,ctypes.byref(configured),ctypes.sizeof(configured),None):_fail('worker_unavailable')
        configured_memory=int(configured.job_memory);job_flags=int(configured.basic.flags)
        if configured_memory!=_WORKER_MEMORY_MIB*1024*1024 or not job_flags&0x200:_fail('worker_unavailable')
        environment=dict(os.environ,TMP=str(evidence),TEMP=str(evidence))
        process=subprocess.Popen(_worker_command(),cwd=evidence,env=environment,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,creationflags=0x4|getattr(subprocess,'CREATE_NO_WINDOW',0))
        job.assign_resume(process);assigned=True
        for index,pipe in enumerate((process.stdout,process.stderr)):
            thread=threading.Thread(target=read,args=(pipe,index,_REPLY_BYTES+64 if index==0 else 8192),daemon=True)
            readers.append(thread);thread.start()
        writer=threading.Thread(target=write,daemon=True);writer.start()
        while process.poll() is None:
            if overflow.is_set():_fail('worker_output_limit')
            if thread_errors:raise thread_errors[0]
            if time.monotonic()>=deadline:_fail('worker_timeout')
            overflow.wait(min(0.01,max(0,deadline-time.monotonic())))
    except BaseException as error:primary=error
    finally:
        cleanup_started=time.monotonic();cleanup_deadline=cleanup_started+_CLEANUP_SECONDS
        def cleanup(action):
            nonlocal primary
            try:action()
            except BaseException as error:
                if primary is None:primary=error
        if job is not None:
            try:peak=job.snapshot()['peak_committed_mib']
            except BaseException as caught:
                if isinstance(caught,_CONTROL) and primary is None:primary=caught
            def close_job():
                if job.handle:
                    if not job.kernel.CloseHandle(job.handle):_fail('cleanup_unknown')
                    job.handle=None
            cleanup(close_job);job_closed=job.handle is None
        if process is not None:
            if process.poll() is None:cleanup(process.kill)
            cleanup(lambda:process.wait(timeout=max(0.001,cleanup_deadline-time.monotonic())))
            reaped=process.poll() is not None
            for thread in [*readers,*([writer] if writer else [])]:
                cleanup(lambda thread=thread:thread.join(timeout=max(0,cleanup_deadline-time.monotonic())))
            joined=all(not thread.is_alive() for thread in readers)
            written=writer is not None and not writer.is_alive()
            for index,pipe in enumerate((process.stdout,process.stderr)):
                if index>=len(readers) or not readers[index].is_alive():cleanup(pipe.close)
            if writer is None or not writer.is_alive():cleanup(process.stdin.close)
            closed=all(pipe.closed for pipe in (process.stdin,process.stdout,process.stderr))
        if primary is None and thread_errors:primary=thread_errors[0]
        if primary is None and overflow.is_set():primary=IntakePdfOcrReferenceError('worker_output_limit')
        if primary is None and not (assigned and job_closed and reaped and joined and written and closed):primary=IntakePdfOcrReferenceError('cleanup_unknown')
        state=dict(job_assigned_before_resume=assigned,job_closed=job_closed,child_reaped=reaped,
            readers_joined=joined,writer_joined=written,pipes_closed=closed,tree_memory_mib=_WORKER_MEMORY_MIB,
            peak_committed_mib=peak,deadline_seconds=_WORKER_SECONDS,cleanup_seconds=_CLEANUP_SECONDS,
            configured_job_memory_bytes=configured_memory,job_limit_flags=job_flags,
            elapsed_seconds=round(time.monotonic()-started,6),cleanup_elapsed_seconds=round(time.monotonic()-cleanup_started,6),
            returncode=process.returncode if process else None,stdout_bytes=len(buffers[0]),stderr_bytes=len(buffers[1]),
            failure=primary.code if isinstance(primary,IntakePdfOcrReferenceError) else 'parent_control_or_storage_error' if primary else None)
        for suffix,data in (('stdout.bin',bytes(buffers[0])),('stderr.bin',bytes(buffers[1])),('process.json',_bytes(state))):
            cleanup(lambda suffix=suffix,data=data:_save(evidence/('worker-'+suffix),data))
    return bytes(buffers[0]),state,primary


def _decode_worker_reply(raw,request):
    try:
        end=raw.index(b'\n')
        if end>63 or not raw.startswith(_FRAME):_fail('worker_protocol')
        length=raw[len(_FRAME):end]
        if not re.fullmatch(rb'[1-9][0-9]{0,6}',length):_fail('worker_protocol')
        size=int(length);payload=raw[end+1:]
        if size!=len(payload) or size>_REPLY_BYTES:_fail('worker_protocol')
        reply=_strict_json(payload,_REPLY_BYTES)
        if (type(reply) is not dict or set(reply)!=set('schema_version kind request_id outcome reference failure inner_receipt'.split())
                or type(reply['schema_version']) is not int or reply['schema_version']!=1
                or reply['kind']!='intake_pdf_ocr_worker_reply' or reply['request_id']!=request['request_id']
                or reply['outcome'] not in ('returned','error','control')):_fail('worker_protocol')
        reference=reply['reference']
        if reference is not None:
            if type(reference) is not dict or set(reference)!=set('schema_version kind status binding baseline ocr tools errors complete native_once_eligible provenance limits reference_id'.split()):_fail('worker_protocol')
            unsigned={key:value for key,value in reference.items() if key!='reference_id'}
            if (reference['reference_id']!=_hash(_bytes(unsigned)) or type(reference['schema_version']) is not int
                    or reference['schema_version']!=1 or reference['kind']!='intake_pdf_ocr_reference'
                    or reference['complete'] is not False or reference['native_once_eligible'] is not False
                    or reference['provenance']['execution_authority'] is not False
                    or reference['status'] not in ('ocr_observed','ocr_required')):_fail('worker_protocol')
            binding=reference['binding'];document=binding['document']
            if (type(binding) is not dict or set(binding)!=set('source_id intake_id revision revision_fingerprint document'.split())
                    or type(document) is not dict or set(document)!=set(('path','sha256','bytes'))
                    or type(binding['revision']) is not int or binding['intake_id']!=request['intake_id'] or binding['revision']!=request['expected_revision']
                    or type(document['bytes']) is not int or not 0<=document['bytes']<=_PDF_BYTES
                    or document['path']!=request['document_path'] or document['sha256']!=request['expected_sha256']):_fail('worker_protocol')
            if reference['status']=='ocr_observed':
                ocr=reference['ocr'];tools=reference['tools'];config=request['tools']
                if (config is None or type(ocr) is not dict or set(ocr)!=set('page_number method text text_sha256 raster_sha256 raster_width raster_height image_text_equivalence original_text'.split())
                        or type(ocr['page_number']) is not int or ocr['page_number']!=1 or ocr['method']!='tesseract_local'
                        or ocr['original_text'] is not False or ocr['image_text_equivalence']!='not_verified'
                        or type(ocr['text']) is not str or not ocr['text'].strip() or len(ocr['text'].encode('utf-8'))>_TEXT_BYTES
                        or _hash(ocr['text'].encode('utf-8'))!=ocr['text_sha256'] or reference['errors']!=[]
                        or not _eligible(reference['baseline']) or tools['language']!='eng'
                        or tools['tesseract_version_source']!='installed_dll_TessVersion'
                        or tools['renderer_version_source']!='actual_version_child'
                        or tools['tesseract_version']!=config['expected_tesseract_version']
                        or tools['renderer_version']!=config['expected_renderer_version']):_fail('worker_protocol')
                for section,key in (('tesseract','tesseract_sha256'),('renderer','renderer_sha256'),('dll','dll_sha256'),('language_data','language_sha256')):
                    if tools[section]['sha256']!=config[key]:_fail('worker_protocol')
                if (Path(tools['tesseract']['path'])!=Path(config['tesseract_executable'])
                        or Path(tools['renderer']['path'])!=Path(config['renderer_executable'])):_fail('worker_protocol')
            elif reference['ocr'] is not None:_fail('worker_protocol')
            expected=dict(filename='inner-reference.json',bytes=len(_bytes(reference)),sha256=_hash(_bytes(reference)))
            if reply['inner_receipt']!=expected:_fail('worker_protocol')
        elif reply['inner_receipt'] is not None:_fail('worker_protocol')
        if reply['outcome']=='returned':
            if reference is None or reply['failure'] is not None:_fail('worker_protocol')
        else:
            failure=reply['failure']
            if (type(failure) is not dict or set(failure)!=set(('code','control'))
                    or type(failure['code']) is not str or not re.fullmatch(_PREFIX+r'[a-z_]{1,80}',failure['code'])
                    or failure['control'] not in (None,'memory_error','keyboard_interrupt','system_exit','generator_exit')):_fail('worker_protocol')
            if (reply['outcome']=='control')!=(failure['control'] is not None):_fail('worker_protocol')
        return reply
    except IntakePdfOcrReferenceError:raise
    except (ValueError,KeyError,TypeError,AttributeError,UnicodeError):_fail('worker_protocol')


def _public_reference(request,reply,state,evidence,outcome,error):
    inner=reply['reference'] if reply else None
    if inner is not None:result=dict(inner)
    else:
        result=dict(schema_version=1,kind='intake_pdf_ocr_reference',status='ocr_required',
            binding=dict(source_id=None,intake_id=request['intake_id'],revision=request['expected_revision'],revision_fingerprint=None,
                document=dict(path=request['document_path'],sha256=request['expected_sha256'],bytes=None)),
            baseline=None,ocr=None,tools=None,errors=[],complete=False,native_once_eligible=False,
            provenance=dict(original_text=False,image_text_equivalence='not_verified',execution_authority=False,
                origin_authenticated=False,same_account_arbitrary_code_defense=False),limits=None)
    result.pop('reference_id',None)
    if outcome!='completed':result.update(status='ocr_required',ocr=None,errors=[error])
    result['isolation']=dict(state,outcome=outcome,request_id=request['request_id'],evidence_root=str(evidence),
        inner_receipt=reply['inner_receipt'] if reply else None,inner_reference_id=inner['reference_id'] if inner else None)
    result['reference_id']=_hash(_bytes(result))
    return result


def read_intake_pdf_ocr_reference(store,intake_id,document_path,*,expected_revision,expected_sha256,tools=None,run_root):
    """Keep the borrowed Store; isolate all synchronous OCR work in an owned worker."""
    request,raw,evidence,loan=_request(store,intake_id,document_path,expected_revision,expected_sha256,tools,run_root)
    _save(evidence/'request.json',raw)
    wire,state,primary=_execute_worker(raw,evidence);reply=None;outcome='unknown';error=_PREFIX+'worker_unknown'
    rejection=None
    try:
        if primary is not None:raise primary
        reply=_decode_worker_reply(wire,request)
        if reply['outcome']=='error':
            error=reply['failure']['code']
            if reply['reference'] is None or reply['reference']['status']!='ocr_observed':
                outcome='failed';rejection=IntakePdfOcrReferenceError(error)
        elif reply['outcome']=='control':error=_PREFIX+'worker_control'
        elif state['returncode']!=0:error=_PREFIX+'worker_exit'
        elif _borrowed(store)!=loan:error=_PREFIX+'store_invalid'
        else:outcome='completed';error=None
    except BaseException as caught:
        if primary is None:primary=caught
        error=caught.code if isinstance(caught,IntakePdfOcrReferenceError) else _PREFIX+'parent_control' if isinstance(caught,_CONTROL) else _PREFIX+'worker_protocol'
    try:result=_public_reference(request,reply,state,evidence,outcome,error)
    except BaseException:
        if isinstance(primary,_CONTROL):raise primary
        raise
    try:
        target=Path(request['run_root'])
        if target.is_dir():_save(target/'reference.json',_bytes(result))
    except BaseException as caught:
        if primary is None:primary=caught;error=_PREFIX+'parent_publish_failed'
        outcome='unknown'
        try:result=_public_reference(request,reply,state,evidence,outcome,error)
        except BaseException:
            if primary is not None:raise primary
            raise
    # The sidecar is the final parent outcome, after public-file publication.
    # A missing/partial sidecar is not a committed completed parent outcome.
    try:_save(evidence/'parent-outcome.json',_bytes(result))
    except BaseException as caught:
        if primary is None:primary=caught
        raise primary
    if isinstance(primary,_CONTROL):raise primary
    if rejection is not None:raise rejection
    return result


def _worker_main():
    """Private strict-data entrypoint; no caller-provided operation or command."""
    request=None;store=None;reference=None;primary=None
    try:
        request=_strict_json(sys.stdin.buffer.read(_REQUEST_BYTES+1),_REQUEST_BYTES)
        _validate_request(request)
        config=request['tools']
        if config is not None:
            if type(config) is not dict or set(config)!=set(LocalOcrTools.__dataclass_fields__):_fail('worker_protocol')
            config=LocalOcrTools(**config)
        target=Path(request['run_root']);allowed=(target,target.parent/('ocr-worker-'+request['request_id'][:16]))
        def local(path):
            value=Path(os.path.abspath(os.fspath(path)))
            return any(value==root or value.is_relative_to(root) for root in allowed)
        def audit(event,args):
            if event in ('socket.connect','socket.getaddrinfo','socket.bind','socket.sendto','os.system') or event.startswith(('os.exec','os.spawn')):
                raise PermissionError('isolated_worker_network_or_shell_forbidden')
            if event=='subprocess.Popen':
                executable,argv,cwd,environment=args;allowed_commands=() if config is None else (config.tesseract_executable,config.renderer_executable)
                actual=str(executable) if executable else argv[0] if type(argv) is list and argv else None
                if actual is None and type(argv) is str:
                    actual=next((path for path in allowed_commands if argv.casefold().startswith(('"'+path+'"').casefold()) or argv.casefold().startswith(path.casefold()+' ')),None)
                if actual is None or all(Path(actual)!=Path(path) for path in allowed_commands):raise PermissionError('isolated_worker_command_forbidden')
            if event=='open' and type(args[0]) is not int:
                path,mode,flags=args
                if os.fspath(path).casefold()!=os.devnull.casefold() and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND) and not local(path):
                    raise PermissionError('isolated_worker_original_write_forbidden')
            if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime') and not local(args[0]):
                raise PermissionError('isolated_worker_original_write_forbidden')
            if event in ('os.rename','os.replace') and (not local(args[0]) or not local(args[1])):raise PermissionError('isolated_worker_original_write_forbidden')
        sys.addaudithook(audit)
        store=Store.open_existing(request['store_root']);connection=store.connection
        @contextmanager
        def readonly():
            with connection() as con:
                con.execute('PRAGMA query_only=ON');yield con
        store.connection=readonly
        reference=_read_inner_reference(store,request['intake_id'],request['document_path'],
            expected_revision=request['expected_revision'],expected_sha256=request['expected_sha256'],tools=config,run_root=request['run_root'])
    except BaseException as caught:primary=caught
    finally:
        if store is not None:
            try:store.close()
            except BaseException as caught:
                if primary is None:primary=caught
    if primary is not None and reference is None and request is not None:
        try:
            inner=Path(request['run_root'])/'inner-reference.json'
            if inner.stat().st_size<=_REPLY_BYTES:reference=_strict_json(inner.read_bytes(),_REPLY_BYTES)
        except BaseException:pass  # Retain the first failure and any partial raw file.
    control={MemoryError:'memory_error',KeyboardInterrupt:'keyboard_interrupt',SystemExit:'system_exit',GeneratorExit:'generator_exit'}
    if isinstance(primary,_CONTROL):outcome='control';failure=dict(code=_PREFIX+'worker_control',control=next(label for kind,label in control.items() if isinstance(primary,kind)))
    elif primary is not None:
        outcome='error';failure=dict(code=primary.code if isinstance(primary,IntakePdfOcrReferenceError) else _PREFIX+'storage_error',control=None)
    else:outcome='returned';failure=None
    pin=dict(filename='inner-reference.json',bytes=len(_bytes(reference)),sha256=_hash(_bytes(reference))) if reference is not None else None
    reply=dict(schema_version=1,kind='intake_pdf_ocr_worker_reply',request_id=request.get('request_id') if type(request) is dict else None,
        outcome=outcome,reference=reference,failure=failure,inner_receipt=pin)
    payload=_bytes(reply)
    if len(payload)>_REPLY_BYTES:return 2
    sys.stdout.buffer.write(_FRAME+str(len(payload)).encode('ascii')+b'\n'+payload);sys.stdout.buffer.flush()
    return 1 if outcome=='control' else 0


if __name__=='__main__':
    if sys.argv[1:]!=['--ocr-worker-v1']:raise SystemExit(2)
    raise SystemExit(_worker_main())
