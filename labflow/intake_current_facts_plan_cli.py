"""One bounded local readonly current-facts plan; no execution or approval."""
import hashlib
from pathlib import Path
import re
import sys

from . import control_packet_prepare as _native
from . import fcc_report_cases as _json
from .intake_current_facts_plan import read_current_conducted_plan_from_facts
from .store import canonical
from .ui_read_model import ReadModelError
from .virtual_fleet.rf_signal_waveform_observation_cli import _write as _write_text,_quiet


__all__=['main']
_PREFIX='intake_current_facts_plan_cli_'
_METHOD_BYTES=65536
_FRAME_BYTES=16*1024*1024
_CONTROL=(KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError)
_OPTIONS={'--workspace','--intake-id','--method-json','--expected-revision','--expected-context-sha256'}
_REQUIRED={'--workspace','--intake-id','--method-json'}
_PARENT_CODES={'store_missing','store_unavailable','intake_not_found','intake_conducted_preview_invalid_request',
    'intake_conducted_preview_synthetic_required','intake_conducted_preview_analysis_unavailable',
    'intake_conducted_preview_source_invalid','intake_conducted_preview_v2_pdf_required'}
_SUFFIXES={'invalid_arguments','method_invalid','method_unavailable','method_changed','parent_unavailable',
    'output_invalid','output_limit','output_failed','internal_error','interrupted'}
_HELP=('Read one current synthetic text/PDF plan, without execution or approval.\n'
    'Usage: python -B -m labflow.intake_current_facts_plan_cli '
    '--workspace ABS_LOCAL_DIR --intake-id ID --method-json ABS_LOCAL_JSON '
    '[--expected-revision N] [--expected-context-sha256 SHA]\n'
    'Each flag once, separate values; method <=65536 bytes, depth8/nodes2048.\n'
    'stdout: original exact3 UTF8 JSON plus LF, whole frame <=16777216 bytes.\n'
    'Exit ready0, blocked2, parent unavailable3, invalid/I-O1, first process KI130.\n'
    'No profile/environment selection, defaults for RF values, AI, network or writes.\n')


class _Failure(ValueError):
    pass


def _fail(suffix):raise _Failure(suffix)


def _help(argv):return type(argv) in (list,tuple) and len(argv)==1 and type(argv[0]) is str and argv[0]=='--help'


def _arguments(argv):
    if (type(argv) not in (list,tuple) or len(argv) not in (6,8,10)
            or any(type(value) is not str for value in argv)):_fail('invalid_arguments')
    values={}
    for flag,value in zip(argv[::2],argv[1::2]):
        if flag not in _OPTIONS or flag in values:_fail('invalid_arguments')
        if not value or len(value.encode('utf-8'))>16384:_fail('invalid_arguments')
        values[flag]=value
    if not _REQUIRED<=set(values):_fail('invalid_arguments')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}',values['--intake-id'],re.ASCII):
        _fail('invalid_arguments')
    for key in ('--workspace','--method-json'):
        if not Path(values[key]).is_absolute():_fail('invalid_arguments')
        try:values[key]=_native._local_path(values[key])
        except _native.ControlPacketPrepareError:_fail('invalid_arguments')
    if values['--method-json'].suffix.lower()!='.json':_fail('invalid_arguments')
    revision=values.get('--expected-revision')
    if revision is not None:
        if not re.fullmatch(r'[1-9][0-9]{0,18}',revision,re.ASCII):_fail('invalid_arguments')
        revision=int(revision)
        if revision>2**63-1:_fail('invalid_arguments')
    sha=values.get('--expected-context-sha256')
    if sha is not None and not re.fullmatch(r'[0-9a-f]{64}',sha,re.ASCII):_fail('invalid_arguments')
    return values['--workspace'],values['--intake-id'],values['--method-json'],revision,sha


def _method(backend,path):
    tree=_native._Tree(path.parent,backend);before=tree.file_stat(path)
    if before.st_nlink!=1 or before.st_size>_METHOD_BYTES:_fail('method_invalid')
    stamp=_native._stamp(before);fd=backend.open_read(path,pin=True)
    info=backend.info(fd,directory=False)
    if info.st_nlink!=1 or _native._stamp(info)!=stamp:_fail('method_changed')
    raw=_native._read_descriptor(fd,_METHOD_BYTES,'packet_prepare_source_changed')
    if len(raw)!=before.st_size:_fail('method_changed')
    value=_json._plain(_json._decode(raw,byte_limit=_METHOD_BYTES),byte_limit=_METHOD_BYTES,
        depth_limit=8,node_limit=2048,string_limit=_METHOD_BYTES)
    if type(value) is not dict:_fail('method_invalid')
    record=(tree,path,fd,stamp,hashlib.sha256(raw).hexdigest())
    _method_unchanged(backend,record)
    return value,record


def _method_unchanged(backend,record):
    tree,path,fd,stamp,sha=record;info=backend.info(fd,directory=False);current=tree.file_stat(path)
    if (info.st_nlink!=1 or current.st_nlink!=1 or _native._stamp(info)!=stamp
            or _native._stamp(current)!=stamp):_fail('method_changed')
    raw=_native._read_descriptor(fd,_METHOD_BYTES,'packet_prepare_source_changed')
    if hashlib.sha256(raw).hexdigest()!=sha:_fail('method_changed')


def _frame(value):
    value=_json._plain(value,byte_limit=_FRAME_BYTES-1,depth_limit=48,node_limit=400000,
        string_limit=_FRAME_BYTES-1)
    if type(value) is not dict or set(value)!={'context','analysis','facts_plan'}:_fail('output_invalid')
    wrapper=value['facts_plan']
    if (type(value['context']) is not dict or type(value['analysis']) is not dict or type(wrapper) is not dict
            or type(wrapper.get('status')) is not str or wrapper['status'] not in ('ready_for_simulation','blocked')):
        _fail('output_invalid')
    plan=wrapper.get('plan_input')
    if (type(plan) is not dict or plan.get('status')!=wrapper['status'] or type(plan.get('verification')) is not dict
            or plan['verification'].get('execution_authority') is not False):_fail('output_invalid')
    text=canonical(value)+'\n'
    if len(text.encode('utf-8'))>_FRAME_BYTES:_fail('output_limit')
    return text,0 if wrapper['status']=='ready_for_simulation' else 2


def _diagnose(code):
    try:_write_text(sys.stderr,canonical({'error':{'code':code}})+'\n')
    except BaseException:pass  # A diagnostic fault cannot replace the first failure.


def _classified(error,phase):
    if isinstance(error,_CONTROL) or not isinstance(error,Exception):raise error
    if type(error) is _Failure:
        suffix=error.args[0] if error.args and type(error.args[0]) is str and error.args[0] in _SUFFIXES else 'internal_error'
        return _PREFIX+suffix,1
    if type(error) is ReadModelError:
        code=_PREFIX+'parent_unavailable'
        try:
            value=error.code
            if type(value) is str and value in _PARENT_CODES:code=value
        except BaseException:pass
        return code,3
    if phase=='arguments':return _PREFIX+'invalid_arguments',1
    if phase=='help':return _PREFIX+'output_failed',1
    if phase=='method':
        return _PREFIX+('method_invalid' if isinstance(error,_json.FccReportCaseError) else 'method_unavailable'),1
    if phase=='result':
        suffix='output_invalid'
        try:
            if type(error) is _json.FccReportCaseError and error.code=='fcc_case_limit_exceeded':suffix='output_limit'
        except BaseException:pass
        return _PREFIX+suffix,1
    return _PREFIX+'internal_error',1


def main(argv=None) -> int:
    """Borrow streams; preserve controls, original result and first native failure."""
    backend=None;first=None;phase='arguments';text=None;status=1
    try:
        arguments=sys.argv[1:] if argv is None else argv
        if _help(arguments):
            phase='help'
            _write_text(sys.stderr,_HELP);return 0
        workspace,intake_id,path,revision,sha=_arguments(arguments)
        phase='method';backend=_native._WindowsIO();method,record=_method(backend,path)
        phase='read'
        value=read_current_conducted_plan_from_facts(workspace,intake_id,method=method,
            expected_revision=revision,expected_context_sha256=sha)
        phase='result';text,status=_frame(value)
        phase='method';_method_unchanged(backend,record)
    except BaseException as error:first=error
    finally:
        if backend is not None:
            try:backend.close()
            except BaseException as error:
                if first is None:first=error
    if first is not None:
        code,status=_classified(first,phase);_diagnose(code);return status
    try:_write_text(sys.stdout,text)
    except _CONTROL:raise
    except Exception:
        _diagnose(_PREFIX+'output_failed');return 1
    return status


def _process_main() -> int:
    """Only this process configures UTF8/LF and quiets failed shutdown streams."""
    streams=(sys.stdout,sys.stderr);first=None;status=1
    try:arguments=list(sys.argv[1:])
    except BaseException as error:first=error
    for stream in streams:
        try:stream.reconfigure(encoding='utf-8',errors='strict',newline='\n')
        except BaseException as error:
            if first is None:first=error
    if first is None:
        try:
            status=main(arguments)
            if type(status) is not int or status not in (0,1,2,3,130):raise ValueError()
        except BaseException as error:first=error
    if first is not None:
        status=130 if isinstance(first,KeyboardInterrupt) else 1
        _diagnose(_PREFIX+('interrupted' if status==130 else 'output_failed'))
    for stream in streams:
        try:stream.flush()
        except BaseException as error:
            if first is None and status in (0,2):
                first=error;status=130 if isinstance(error,KeyboardInterrupt) else 1
                _diagnose(_PREFIX+('interrupted' if status==130 else 'output_failed'))
            _quiet(stream,status)
    return status


if __name__=='__main__':raise SystemExit(_process_main())
