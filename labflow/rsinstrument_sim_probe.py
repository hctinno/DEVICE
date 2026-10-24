"""Pinned, isolated vendor Simulation probe; no operational instrument authority."""
from contextlib import AbstractContextManager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import subprocess
import sys
import time


_APPROVED_RECEIPT_SHA256 = 'b6f3575d2a50b99abf73a351daed2c4662ace102df265eaef8c7d152cb1c4798'
_APPROVED_FILES_SHA256 = '3e31c3ee59e4ad47f1160fecea2e381ac0796643b1e62b03a92952cbb80aa7f1'
_DISTRIBUTION_PINS = {
    'RsInstrument':('1.131.0','2a2088b5feb9533621bb1282eee284b1713848513830c235e205133d022fcc14'),
    'PyVISA':('1.15.0','e3ac8d9e863fbdbbe7e6d4d91401bceb7914d1c4a558a89b2cc755789f1e8309'),
    'typing_extensions':('4.12.2','04e5ca0351e0f3f85c6853954072df659d0d13fac324d0072316b67d7794700d'),
    'defusedxml':('0.7.1','a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61')}
_PYTHON_CORE_PINS = {
    'python.exe':'fd5c46d73d29ba21b04c844bbaf9096066136526911230645a2a040d23fb612b',
    'python312.dll':'21700f0bad5769a1b61ea408dc0a140ffd0a356a774c6eb0cc70e574b929d2e2',
    'python3.dll':'5146005c36455e7ede4b8ecc0dc6f6fa8ea6b4a99fedbabc1994ae27dfab9d1b',
    'vcruntime140.dll':'4d292623516f65c80482081e62d5dadb759dc16e851de5db24c3cbb57b87db83',
    'vcruntime140_1.dll':'a113f192195f245f17389e6ecbed8005990bcb2476ddad33f7c4c6c86327afe5'}
_PYTHON_PATHS = {'Scripts/'+name for name in _PYTHON_CORE_PINS}|{'pyvenv.cfg','PYTHON-LICENSE.txt'}
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_VERSION = re.compile(r'[0-9][0-9A-Za-z.+-]{0,63}\Z')
_LOCK_LIMIT, _JOURNAL_LIMIT, _RECEIPT_LIMIT = 2*1024*1024, 64*1024, 32*1024
_NAMES = set(_DISTRIBUTION_PINS)
_FILES = ('dependency-lock.json', 'control.json', 'journal.jsonl', 'child-receipt.json', 'result.json', 'manifest.json')
_CHILD_CODES = {'validated','import_contamination','runtime_pin_mismatch','sdk_unavailable',
                'sdk_version_mismatch','sdk_operation_failed','forbidden_io','output_limit_exceeded'}
_OPERATIONS = (('open_simulation',None),('query_str','*IDN?'),('query_str','DGM:UNVERIFIED:VALUE?'),
    ('write_str','SOURce:FREQuency 123456789'),('query_str','SOURce:FREQuency?'),('query_opc',None),
    ('query_all_errors',None),('reconnect',None),('query_str','SOURce:FREQuency?'),('close',None))
_EXPECTED = ('VisaSessionSim','Rohde&Schwarz,SimulationDevice,100001,1.131.0.128','Simulating',
             None,'123456789',True,None,True,'Simulating',None)


class _ProbeFailure(Exception):
    pass


class _ForbiddenIO(_ProbeFailure):
    pass


class _OutputLimit(_ProbeFailure):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _plain(value):
    path = Path(value).absolute()
    if str(path).startswith(('\\\\','//')):
        raise ValueError()
    for item in (path,*path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
            raise ValueError()
    return path.resolve()


def _relative(value):
    if type(value) is not str or not value or len(value)>512 or '\\' in value or ':' in value:
        raise ValueError()
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {'','.', '..'} or part.endswith((' ','.')) for part in value.split('/')):
        raise ValueError()
    return path


def _configuration(python_executable, dependency_manifest, timeout):
    try:
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=60:
            raise ValueError()
        if type(python_executable) not in (str,type(Path())):
            raise ValueError()
        python = Path(python_executable)
        if (not python.is_absolute() or python.name.lower()!='python.exe' or python.parent.name.lower()!='scripts'
                or str(python).startswith(('\\\\','//')) or any(part in {'.','..'} for part in re.split(r'[\\/]',str(python_executable)))):
            raise ValueError()
    except (ValueError,TypeError,OverflowError):
        raise ValueError('simulation_configuration_invalid') from None
    try:
        def strict(value):
            if type(value) is dict:
                if any(type(key) is not str for key in value): raise ValueError()
                for item in value.values(): strict(item)
            elif type(value) is list:
                for item in value: strict(item)
            elif value is not None and type(value) not in (str,int,bool,float):
                raise ValueError()
        strict(dependency_manifest)
        data = _json(dependency_manifest)
        if len(data)>_LOCK_LIMIT: raise ValueError()
        lock = json.loads(data)
        if (type(lock) is not dict or set(lock)!={'schema_version','kind','receipt_sha256','python_version',
                'python_sha256','python_runtime','sdk_version','distributions','files'} or type(lock['schema_version']) is not int
                or lock['schema_version']!=1 or lock['kind']!='rsinstrument_simulation_dependency_lock'):
            raise ValueError()
        for key in ('receipt_sha256','python_sha256'):
            if type(lock[key]) is not str or not _SHA.fullmatch(lock[key]): raise ValueError()
        for key in ('python_version','sdk_version'):
            if type(lock[key]) is not str or not _VERSION.fullmatch(lock[key]): raise ValueError()
        if type(lock['python_runtime']) is not list or len(lock['python_runtime'])!=len(_PYTHON_PATHS): raise ValueError()
        runtime_paths = set()
        for item in lock['python_runtime']:
            if (type(item) is not dict or set(item)!={'path','bytes','sha256'} or type(item['path']) is not str
                    or item['path'] not in _PYTHON_PATHS or item['path'] in runtime_paths
                    or type(item['bytes']) is not int or not 0<=item['bytes']<=16*1024*1024
                    or type(item['sha256']) is not str or not _SHA.fullmatch(item['sha256'])):
                raise ValueError()
            runtime_paths.add(item['path'])
        if type(lock['distributions']) is not list or len(lock['distributions'])!=4: raise ValueError()
        names, roots, licenses = set(), {'RsInstrument','pyvisa','defusedxml','typing_extensions.py'}, []
        for item in lock['distributions']:
            if type(item) is not dict or set(item)!={'name','version','wheel_sha256','license_path','license_sha256'}:
                raise ValueError()
            name = item['name']
            if type(name) is not str or name not in _NAMES or name in names: raise ValueError()
            names.add(name)
            if type(item['version']) is not str or not _VERSION.fullmatch(item['version']): raise ValueError()
            if name=='RsInstrument' and item['version']!=lock['sdk_version']: raise ValueError()
            for key in ('wheel_sha256','license_sha256'):
                if type(item[key]) is not str or not _SHA.fullmatch(item[key]): raise ValueError()
            license_path = _relative(item['license_path'])
            metadata_root = name+'-'+item['version']+'.dist-info'
            if license_path.parts[0].casefold()!=metadata_root.casefold(): raise ValueError()
            roots.add(license_path.parts[0])
            licenses.append((str(license_path),item['license_sha256']))
            if name=='typing_extensions': roots.add('typing_extensions.py')
        if names!=_NAMES: raise ValueError()
        if type(lock['files']) is not list or not 1<=len(lock['files'])<=4096: raise ValueError()
        files, total, folded = {}, 0, set()
        for item in lock['files']:
            if type(item) is not dict or set(item)!={'path','bytes','sha256'}: raise ValueError()
            path = _relative(item['path'])
            if (path.parts[0] not in roots or str(path).casefold() in folded or path.suffix in {'.pyc','.pth'}
                    or '__pycache__' in path.parts or type(item['bytes']) is not int or not 0<=item['bytes']<=8*1024*1024
                    or type(item['sha256']) is not str or not _SHA.fullmatch(item['sha256'])):
                raise ValueError()
            files[str(path)], total = item, total+item['bytes']
            folded.add(str(path).casefold())
        if total>64*1024*1024 or not {'RsInstrument/__init__.py','pyvisa/__init__.py'}<=set(files): raise ValueError()
        if any(path not in files or files[path]['sha256']!=digest for path,digest in licenses): raise ValueError()
    except (ValueError,TypeError,KeyError,RecursionError,OverflowError):
        raise ValueError('simulation_manifest_invalid') from None
    return {'python':str(python),'lock':lock,'lock_bytes':data,'timeout':timeout}


def _reserve(value):
    try:
        if type(value) not in (str,type(Path())): raise ValueError()
        if any(part in {'.','..'} for part in re.split(r'[\\/]',str(value))): raise ValueError()
        raw = Path(value)
        if raw.drive and not raw.is_absolute(): raise ValueError()
        if any(part.endswith((' ','.')) or ':' in part for part in raw.parts if part!=raw.anchor): raise ValueError()
        path = _plain(raw)
        if path.exists() or not path.parent.is_dir(): raise ValueError()
        if os.name=='nt' and any(len(str(path/name).encode('utf-16-le'))//2>=260 for name in _FILES): raise ValueError()
        path.mkdir(mode=0o700,exist_ok=False)
        return _plain(path)
    except (OSError,TypeError,ValueError):
        raise ValueError('simulation_output_invalid') from None


def _stream(path):
    _plain(path.parent)
    return os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0),0o600),'wb')


def _write_new(path,data):
    with _stream(path) as stream:
        if stream.write(data)!=len(data): raise OSError()
        stream.flush()
        os.fsync(stream.fileno())


def _read(path,limit):
    path = _plain(path)
    if not path.exists(): return None
    if not path.is_file(): raise ValueError()
    with path.open('rb') as stream: data = stream.read(limit+1)
    if len(data)>limit: raise _OutputLimit()
    return data


class _Journal:
    def __init__(self,path):
        self.stream, self.bytes = _stream(path), 0

    def append(self,record):
        data = _json(record)+b'\n'
        if len(data)+self.bytes>_JOURNAL_LIMIT: raise _OutputLimit()
        if self.stream.write(data)!=len(data): raise OSError()
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.bytes += len(data)

    def close(self):
        self.stream.close()


class _Sentinels(AbstractContextManager):
    def __init__(self):
        self.attempts, self.originals = [], []

    def _guard(self,owner,name,code):
        if not hasattr(owner,name): return
        original = getattr(owner,name)
        def deny(*args,**kwargs):
            if len(self.attempts)<32: self.attempts.append(code)
            raise _ForbiddenIO(code)
        self.originals.append((owner,name,original))
        setattr(owner,name,deny)

    def __enter__(self):
        import _socket
        for owner in (socket,_socket):
            for name in ('socket','create_connection','socketpair','fromfd'):
                self._guard(owner,name,'socket')
            for name in ('getaddrinfo','gethostbyname','gethostbyname_ex','gethostbyaddr','getnameinfo'):
                self._guard(owner,name,'dns')
        self._guard(subprocess,'Popen','process')
        self._guard(os,'system','process')
        return self

    def guard_visa(self,visa):
        self._guard(visa,'ResourceManager','visa_resource_manager')
        if hasattr(visa,'highlevel'): self._guard(visa.highlevel,'ResourceManager','visa_resource_manager')

    def guard_real_session(self,session_class):
        self._guard(session_class,'__init__','visa_session')

    def __exit__(self,*args):
        for owner,name,value in reversed(self.originals): setattr(owner,name,value)
        return False


def _verify_runtime(configuration):
    try:
        python = _plain(configuration['python'])
        if not python.is_file(): raise _ProbeFailure('runtime_unavailable')
        site = _plain(python.parent.parent/'Lib/site-packages')
        if not site.is_dir() or not (python.parent.parent/'pyvenv.cfg').is_file(): raise _ProbeFailure('runtime_unavailable')
        if _sha(_read(python,64*1024*1024))!=configuration['lock']['python_sha256']:
            raise _ProbeFailure('runtime_pin_mismatch')
        lock = configuration['lock']
        if (lock['python_version']!='3.12.4' or lock['python_sha256']!=_PYTHON_CORE_PINS['python.exe']
                or _sha(_json(sorted(lock['files'],key=lambda item:item['path'])))!=_APPROVED_FILES_SHA256
                or {item['name']:(item['version'],item['wheel_sha256']) for item in lock['distributions']}!=_DISTRIBUTION_PINS):
            raise _ProbeFailure('runtime_pin_mismatch')
        for name,digest in _PYTHON_CORE_PINS.items():
            if _sha(_read(python.parent/name,16*1024*1024))!=digest:
                raise _ProbeFailure('runtime_pin_mismatch')
        for item in lock['python_runtime']:
            data = _read(python.parent.parent/item['path'],16*1024*1024)
            if data is None or len(data)!=item['bytes'] or _sha(data)!=item['sha256']:
                raise _ProbeFailure('runtime_pin_mismatch')
        expected = {item['path']:item for item in configuration['lock']['files']}
        actual, pending = set(), [site]
        while pending:
            directory = pending.pop()
            for path in directory.iterdir():
                _plain(path)
                if path.is_dir():
                    if len(path.relative_to(site).parts)>16: raise _ProbeFailure('import_contamination')
                    pending.append(path)
                elif path.is_file():
                    relative = path.relative_to(site).as_posix()
                    if relative not in expected: raise _ProbeFailure('import_contamination')
                    data = _read(path,8*1024*1024)
                    item = expected[relative]
                    if len(data)!=item['bytes'] or _sha(data)!=item['sha256']: raise _ProbeFailure('runtime_pin_mismatch')
                    actual.add(relative)
                else:
                    raise _ProbeFailure('import_contamination')
        if actual!=set(expected): raise _ProbeFailure('runtime_pin_mismatch')
        return {'site_packages':str(site),'python':str(python)}
    except _OutputLimit:
        raise _ProbeFailure('runtime_pin_mismatch') from None
    except _ProbeFailure:
        raise
    except (ValueError,OSError,TypeError):
        raise _ProbeFailure('runtime_pin_mismatch') from None


def _stop(child):
    try:
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=.25)
            except subprocess.TimeoutExpired: pass
        if child.poll() is None:
            child.kill()
            try: child.wait(timeout=.25)
            except subprocess.TimeoutExpired: pass
        return child.poll() is not None
    except BaseException:
        return False


def _launch_child(configuration,folder):
    return subprocess.Popen([configuration['python'],'-I','-S','-B','-X','utf8',str(Path(__file__).resolve()),'--child',str(folder)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,
        env={key:os.environ[key] for key in ('SystemRoot','WINDIR') if key in os.environ},
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def _base_result():
    return {'schema_version':1,'kind':'rsinstrument_simulation_probe','execution_mode':'vendor_sdk_simulation',
        'synthetic':True,'actual_vendor_simulation_executed':False,'hardware_verified':False,
        'model_execution_verified':False,'physical_model_verified':False,'support_status':'not_assessed',
        'status':'unavailable','reason_code':'dependency_receipt_unapproved','sdk':None,'observations':[],
        'cleanup':{'child_pid':None,'child_stopped':True,'session_closed':None,'forbidden_io_attempts':[]}}


def _publish(folder,result,configuration,consumed):
    try:
        for name,data in consumed.items():
            if _read(folder/name,_LOCK_LIMIT if name=='dependency-lock.json' else _JOURNAL_LIMIT)!=data: raise ValueError()
        result_bytes = _json(result)
        records = [{'path':name,'bytes':len(data),'sha256':_sha(data)} for name,data in consumed.items() if data is not None]
        records.append({'path':'result.json','bytes':len(result_bytes),'sha256':_sha(result_bytes)})
        manifest = {'schema_version':1,'kind':'private_rsinstrument_simulation_evidence',
            'actual_vendor_simulation_executed':result['actual_vendor_simulation_executed'],
            'hardware_verified':False,'physical_model_verified':False,'model_execution_verified':False,
            'receipt_sha256':configuration['lock']['receipt_sha256'],
            'dependency_lock_sha256':_sha(configuration['lock_bytes']),
            'implementation_sha256':_sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
            'python_version':configuration['lock']['python_version'],'python_sha256':configuration['lock']['python_sha256'],
            'unverified_child_evidence':[name for name in ('journal.jsonl','child-receipt.json') if consumed.get(name) is None],
            'files':records}
        _write_new(folder/'result.json',result_bytes)
        _write_new(folder/'manifest.json',_json(manifest))
    except Exception:
        raise ValueError('simulation_evidence_error') from None
    return result


def probe_rsinstrument_simulation(*,python_executable,dependency_manifest,output_dir,timeout_seconds=10):
    configuration = _configuration(python_executable,dependency_manifest,timeout_seconds)
    folder = _reserve(output_dir)
    try:
        _write_new(folder/'dependency-lock.json',configuration['lock_bytes'])
    except Exception:
        raise ValueError('simulation_evidence_error') from None
    consumed = {'dependency-lock.json':configuration['lock_bytes']}
    result = _base_result()
    if _APPROVED_RECEIPT_SHA256 is None or configuration['lock']['receipt_sha256']!=_APPROVED_RECEIPT_SHA256:
        return _publish(folder,result,configuration,consumed)
    try:
        runtime = _verify_runtime(configuration)
    except _ProbeFailure as error:
        code = str(error) if str(error) in {'runtime_unavailable','runtime_pin_mismatch','import_contamination'} else 'runtime_pin_mismatch'
        result.update(status='unavailable' if code=='runtime_unavailable' else 'rejected',reason_code=code)
        return _publish(folder,result,configuration,consumed)
    control = {'schema_version':1,'runtime':runtime,'dependency_lock_sha256':_sha(configuration['lock_bytes']),
        'implementation_sha256':_sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))}
    try:
        consumed['control.json'] = _json(control)
        _write_new(folder/'control.json',consumed['control.json'])
    except Exception:
        raise ValueError('simulation_evidence_error') from None
    child, stopped, timed_out = None, True, False
    deadline = time.monotonic()+timeout_seconds
    try:
        child = _launch_child(configuration,folder)
        result['cleanup']['child_pid'] = child.pid
        while child.poll() is None:
            remaining = deadline-time.monotonic()
            if remaining<=0:
                timed_out = True
                break
            try: child.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
                break
        timed_out = timed_out or time.monotonic()>=deadline
        result.update(status='rejected',reason_code='child_failed')
    except BaseException:
        result.update(status='rejected',reason_code='child_start_failed')
    finally:
        if child is not None: stopped = _stop(child)
    result['cleanup']['child_stopped'] = stopped
    if not stopped:
        result.update(status='rejected',reason_code='termination_failed')
        try: _write_new(folder/'result.json',_json(result))
        except Exception: raise ValueError('simulation_evidence_error') from None
        return result
    try:
        consumed['journal.jsonl'] = _read(folder/'journal.jsonl',_JOURNAL_LIMIT)
        consumed['child-receipt.json'] = _read(folder/'child-receipt.json',_RECEIPT_LIMIT)
        if timed_out:
            result.update(status='timeout',reason_code='deadline_exceeded')
        elif child is not None and child.returncode==0:
            receipt = _decode_receipt(consumed['child-receipt.json'],consumed['journal.jsonl'],configuration,child.pid)
            for key in ('actual_vendor_simulation_executed','status','reason_code','sdk','observations'):
                result[key] = receipt[key]
            result['cleanup'].update(session_closed=receipt['session_closed'],forbidden_io_attempts=receipt['forbidden_io_attempts'])
        if time.monotonic()>=deadline:
            result.update(status='timeout',reason_code='deadline_exceeded',actual_vendor_simulation_executed=False,sdk=None,observations=[])
    except _OutputLimit:
        result.update(status='rejected',reason_code='output_limit_exceeded')
    except Exception:
        result.update(status='rejected',reason_code='evidence_error',actual_vendor_simulation_executed=False,sdk=None,observations=[])
    return _publish(folder,result,configuration,consumed)


def _pairs(items):
    result = {}
    for key,value in items:
        if key in result: raise ValueError()
        result[key] = value
    return result


def _load(data,limit):
    if type(data) is not bytes or len(data)>limit: raise ValueError()
    value = json.loads(data.decode('utf-8'),object_pairs_hook=_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    _json(value)  # Reject escaped lone surrogates before trusting any receipt.
    return value


def _implementation_sha256():
    return _sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))


def _decode_receipt(data,journal,configuration,pid):
    value = _load(data,_RECEIPT_LIMIT)
    keys = {'schema_version','kind','pid','dependency_lock_sha256','implementation_sha256','python_version',
        'actual_vendor_simulation_executed','status','reason_code','sdk','observations','session_closed',
        'forbidden_io_attempts','journal_sha256'}
    if (type(value) is not dict or set(value)!=keys or type(value['schema_version']) is not int
            or value['schema_version']!=1 or value['kind']!='rsinstrument_simulation_child_receipt'
            or type(value['pid']) is not int or value['pid']!=pid
            or value['dependency_lock_sha256']!=_sha(configuration['lock_bytes'])
            or value['implementation_sha256']!=_implementation_sha256()
            or value['python_version']!=configuration['lock']['python_version']
            or type(value['actual_vendor_simulation_executed']) is not bool
            or type(value['status']) is not str or value['status'] not in {'passed','unavailable','rejected'}
            or type(value['reason_code']) is not str or value['reason_code'] not in _CHILD_CODES
            or value['session_closed'] is not None and type(value['session_closed']) is not bool):
        raise ValueError()
    if type(journal) is not bytes or len(journal)>_JOURNAL_LIMIT or value['journal_sha256']!=_sha(journal): raise ValueError()
    attempts = value['forbidden_io_attempts']
    if (type(attempts) is not list or len(attempts)>32 or any(type(item) is not str or item not in
            {'socket','dns','process','visa_resource_manager','visa_session'} for item in attempts)):
        raise ValueError()
    if attempts and (value['status']!='rejected' or value['reason_code']!='forbidden_io'): raise ValueError()
    observations = value['observations']
    if type(observations) is not list or len(observations)>len(_OPERATIONS): raise ValueError()
    lines = [_load(line,_RECEIPT_LIMIT) for line in journal.splitlines()]
    if journal and not journal.endswith(b'\n') or len(lines)!=2*len(observations): raise ValueError()
    for index,record in enumerate(observations):
        if (type(record) is not dict or set(record)!={'sequence','api','command','state','response','error_code'}
                or type(record['sequence']) is not int or record['sequence']!=index
                or (record['api'],record['command'])!=_OPERATIONS[index]
                or type(record['state']) is not str or record['state'] not in {'returned','raised'}
                or type(record['response']) not in (str,int,bool,type(None))
                or type(record['response']) is str and len(record['response'].encode('utf-8'))>1024
                or record['error_code'] is not None and (type(record['error_code']) is not str or
                    record['error_code'] not in {'sdk_operation_failed','forbidden_io','output_limit_exceeded'})):
            raise ValueError()
        if record['state']=='returned' and record['error_code'] is not None: raise ValueError()
        intent = {'event':'intent','sequence':index,'api':record['api'],'command':record['command']}
        if _json(lines[2*index])!=_json(intent) or _json(lines[2*index+1])!=_json({'event':'observation','observation':record}):
            raise ValueError()
    sdk = value['sdk']
    if value['actual_vendor_simulation_executed']:
        expected_hash = next(item['sha256'] for item in configuration['lock']['files'] if item['path']=='RsInstrument/__init__.py')
        if (type(sdk) is not dict or type(sdk.get('simulation_selected')) is not bool or
                sdk!={'name':'RsInstrument','version':'1.131.0','driver_build':'1.131.0.128',
                'module_path':'RsInstrument/__init__.py','module_sha256':expected_hash,'simulation_selected':True,
                'session_class':'RsInstrument.Internal.VisaSessionSim.VisaSessionSim'}):
            raise ValueError()
    elif sdk is not None:
        raise ValueError()
    if value['status']=='passed':
        if (not value['actual_vendor_simulation_executed'] or value['reason_code']!='validated'
                or value['session_closed'] is not True or attempts or len(observations)!=len(_OPERATIONS)
                or any(record['state']!='returned' or type(record['response']) is not type(expected)
                       or record['response']!=expected for record,expected in zip(observations,_EXPECTED))):
            raise ValueError()
    elif value['reason_code']=='validated':
        raise ValueError()
    return value


def _imports_clean(site,lock):
    expected = {item['path']:item['sha256'] for item in lock['files']}
    for name,module in tuple(sys.modules.items()):
        if name.split('.')[0] in {'pyvisa_py','pyvisa_sim','zeroconf','fastmcp'} or name.startswith('RsInstrument.mcp'):
            raise _ProbeFailure('import_contamination')
        if name.split('.')[0] not in {'RsInstrument','pyvisa','typing_extensions','defusedxml'}: continue
        file = getattr(module,'__file__',None)
        if type(file) is not str: raise _ProbeFailure('import_contamination')
        try:
            path = _plain(file)
            relative = path.relative_to(site).as_posix()
        except (ValueError,OSError):
            raise _ProbeFailure('import_contamination') from None
        if relative not in expected or _sha(_read(path,8*1024*1024))!=expected[relative]:
            raise _ProbeFailure('import_contamination')


def _run_vendor(configuration,runtime,journal):
    import importlib.metadata
    site, lock = _plain(runtime['site_packages']), configuration['lock']
    outcome = {'actual_vendor_simulation_executed':False,'status':'unavailable','reason_code':'sdk_unavailable',
               'sdk':None,'observations':[],'session_closed':None,'forbidden_io_attempts':[]}
    session, handles = None, []
    guard = _Sentinels()
    def operation(index,call):
        api, command = _OPERATIONS[index]
        journal.append({'event':'intent','sequence':index,'api':api,'command':command})
        record = {'sequence':index,'api':api,'command':command,'state':'returned','response':None,'error_code':None}
        try:
            response = call()
            if type(response) not in (str,int,bool,type(None)): raise _OutputLimit()
            if type(response) is str and (len(response)>1024 or len(response.encode('utf-8'))>1024): raise _OutputLimit()
            record['response'] = response
        except Exception as error:
            record.update(state='raised',error_code='forbidden_io' if isinstance(error,_ForbiddenIO) else
                          'output_limit_exceeded' if isinstance(error,_OutputLimit) else 'sdk_operation_failed')
            journal.append({'event':'observation','observation':record})
            outcome['observations'].append(record)
            raise
        journal.append({'event':'observation','observation':record})
        outcome['observations'].append(record)
        return response
    with guard:
        try:
            versions = {}
            for distribution in importlib.metadata.distributions(path=[str(site)]):
                name = distribution.metadata['Name'].replace('-','_').casefold()
                if name in versions: raise _ProbeFailure('import_contamination')
                versions[name] = distribution.version
            if versions!={item['name'].replace('-','_').casefold():item['version'] for item in lock['distributions']}:
                raise _ProbeFailure('sdk_version_mismatch')
            sys.path.insert(0,str(site))
            import pyvisa
            guard.guard_visa(pyvisa)
            import RsInstrument
            from RsInstrument.Internal.VisaSession import VisaSession
            from RsInstrument.Internal.VisaSessionSim import VisaSessionSim
            guard.guard_real_session(VisaSession)
            _imports_clean(site,lock)
            if RsInstrument.__version__!='1.131.0': raise _ProbeFailure('sdk_version_mismatch')
            def open_simulation():
                nonlocal session
                session = RsInstrument.RsInstrument('DGM-SIMULATION-ONLY',id_query=False,reset=False,
                    options='Simulate=True,LoggingMode=Off,LoggingToConsole=False,LoggingToUdp=False,Encoding=utf-8')
                if (session._core.simulating is not True or session._core.io._simulating is not True
                        or type(session._core.io._session) is not VisaSessionSim):
                    raise _ProbeFailure('sdk_operation_failed')
                handles.append(session._core.io._session)
                outcome['actual_vendor_simulation_executed'] = True
                outcome['sdk'] = {'name':'RsInstrument','version':RsInstrument.__version__,
                    'driver_build':RsInstrument.RsInstrument._driver_version_const,
                    'module_path':'RsInstrument/__init__.py','module_sha256':_sha(_read(site/'RsInstrument/__init__.py',8*1024*1024)),
                    'simulation_selected':True,'session_class':'RsInstrument.Internal.VisaSessionSim.VisaSessionSim'}
                return 'VisaSessionSim'
            operation(0,open_simulation)
            operation(1,lambda:session.query_str('*IDN?'))
            operation(2,lambda:session.query_str('DGM:UNVERIFIED:VALUE?'))
            operation(3,lambda:session.write_str('SOURce:FREQuency 123456789'))
            operation(4,lambda:session.query_str('SOURce:FREQuency?'))
            operation(5,lambda:session.query_opc())
            operation(6,lambda:session.query_all_errors())
            operation(7,lambda:session.reconnect(force_close=True))
            if type(session._core.io._session) is not VisaSessionSim: raise _ProbeFailure('sdk_operation_failed')
            handles.append(session._core.io._session)
            operation(8,lambda:session.query_str('SOURce:FREQuency?'))
            operation(9,lambda:session.close())
            if any(type(record['response']) is not type(expected) or record['response']!=expected
                   for record,expected in zip(outcome['observations'],_EXPECTED)):
                raise _ProbeFailure('sdk_operation_failed')
            _imports_clean(site,lock)
            _verify_runtime(configuration)
            outcome.update(status='passed',reason_code='validated')
        except _ForbiddenIO:
            outcome.update(status='rejected',reason_code='forbidden_io')
        except _OutputLimit:
            outcome.update(status='rejected',reason_code='output_limit_exceeded')
        except _ProbeFailure as error:
            outcome.update(status='rejected',reason_code=str(error) if str(error) in _CHILD_CODES else 'sdk_operation_failed')
        except ImportError:
            outcome.update(status='unavailable',reason_code='sdk_unavailable')
        except BaseException:
            outcome.update(status='rejected',reason_code='sdk_operation_failed')
        finally:
            try:
                if session is not None and session._core.io is not None: session.close()
                if handles: outcome['session_closed'] = all(handle.is_connection_active() is False for handle in handles)
            except BaseException:
                outcome.update(status='rejected',reason_code='sdk_operation_failed',session_closed=False)
            if handles and outcome['session_closed'] is not True:
                outcome.update(status='rejected',reason_code='sdk_operation_failed')
            outcome['forbidden_io_attempts'] = list(guard.attempts)
            if guard.attempts: outcome.update(status='rejected',reason_code='forbidden_io')
    return outcome


def _child_main(folder):
    journal = None
    try:
        folder = _plain(folder)
        lock_bytes = _read(folder/'dependency-lock.json',_LOCK_LIMIT)
        lock = _load(lock_bytes,_LOCK_LIMIT)
        control = _load(_read(folder/'control.json',_RECEIPT_LIMIT),_RECEIPT_LIMIT)
        if (type(control) is not dict or set(control)!={'schema_version','runtime','dependency_lock_sha256','implementation_sha256'}
                or type(control['schema_version']) is not int or control['schema_version']!=1
                or control['dependency_lock_sha256']!=_sha(lock_bytes) or control['implementation_sha256']!=_implementation_sha256()
                or type(control['runtime']) is not dict or set(control['runtime'])!={'python','site_packages'}):
            return 2
        configuration = _configuration(control['runtime']['python'],lock,1)
        if configuration['lock_bytes']!=lock_bytes or lock['receipt_sha256']!=_APPROVED_RECEIPT_SHA256: return 2
        journal = _Journal(folder/'journal.jsonl')
        outcome = {'actual_vendor_simulation_executed':False,'status':'rejected','reason_code':'runtime_pin_mismatch',
            'sdk':None,'observations':[],'session_closed':None,'forbidden_io_attempts':[]}
        try:
            runtime = _verify_runtime(configuration)
            if runtime!=control['runtime'] or '.'.join(map(str,sys.version_info[:3]))!=lock['python_version']:
                raise _ProbeFailure('runtime_pin_mismatch')
            if _plain(sys.executable)!=_plain(configuration['python']): raise _ProbeFailure('runtime_pin_mismatch')
            outcome = _run_vendor(configuration,runtime,journal)
        except _ProbeFailure as error:
            outcome['reason_code'] = str(error) if str(error) in _CHILD_CODES else 'runtime_pin_mismatch'
        journal.close()
        journal = None
        receipt = {'schema_version':1,'kind':'rsinstrument_simulation_child_receipt','pid':os.getpid(),
            'dependency_lock_sha256':_sha(lock_bytes),'implementation_sha256':_implementation_sha256(),
            'python_version':'.'.join(map(str,sys.version_info[:3])),
            'journal_sha256':_sha(_read(folder/'journal.jsonl',_JOURNAL_LIMIT)),**outcome}
        data = _json(receipt)
        if len(data)>_RECEIPT_LIMIT: return 3
        _write_new(folder/'child-receipt.json',data)
        return 0
    except BaseException:
        return 2
    finally:
        if journal is not None:
            try: journal.close()
            except BaseException: pass


if __name__=='__main__':
    raise SystemExit(_child_main(Path(sys.argv[2])) if len(sys.argv)==3 and sys.argv[1]=='--child' else 2)
