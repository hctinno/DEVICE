"""Local, revision-bound OCR observations; never original text or execution authority."""
import ctypes
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
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
    try:_save(work/'reference.json',_bytes(result))
    except BaseException as error:
        if primary is None:primary=error
    if primary is not None:raise primary
    return result


def _synthetic(store,selected,sha):
    with store.connection() as con:
        con.execute('PRAGMA query_only=ON')
        row=con.execute('SELECT synthetic FROM intake_sources WHERE source_id=?',(selected['source_id'],)).fetchone()
    if row is None or row['synthetic']!=1 or not store.evidence_is_synthetic(sha):_fail('synthetic_required')


def read_intake_pdf_ocr_reference(store,intake_id,document_path,*,expected_revision,expected_sha256,tools=None,run_root):
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
                or reference['native_once_eligible'] is not False):_fail('invalid_reference')
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
