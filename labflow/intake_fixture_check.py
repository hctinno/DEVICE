"""A new-only synthetic intake-to-fixture flow, optionally served in the intake UI."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid

from .active_intake import register_source, scan_source
from .intake_fixture_jobs import fixture_readiness, request_fixture_job
from .intake_jobs import respond
from .intake_worker import SyntheticTextProvider, run_worker
from .store import Store, canonical


_PAGE_ONE = ['product_type: smartphone', 'manufacturer: Samsung', 'model: SM-A176U']
_PAGE_TWO = ['market: US', 'purpose: synthetic fixture acceptance']


class _SnapshotStore:
    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connection(self):
        yield self._connection


def _write_request(folder, document_kind):
    folder.mkdir(parents=True, exist_ok=False)
    if document_kind == 'text':
        (folder / 'request.txt').write_text('\n'.join(_PAGE_ONE + _PAGE_TWO) + '\n', encoding='utf-8')
    else:
        from reportlab.pdfgen import canvas
        output = canvas.Canvas(str(folder / 'request.pdf'))
        for lines in (_PAGE_ONE, _PAGE_TWO):
            text = output.beginText(48, 790)
            for line in lines:
                text.textLine(line)
            output.drawText(text)
            output.showPage()
        output.save()


def _write_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8'))


def run_fixture_flow(output_dir, *, power_dbm=12.5, document_kind='text'):
    """Create explicit fixture inputs; never accept or label user originals here."""
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Output directory already exists')
    if (document_kind not in {'text', 'pdf'} or type(power_dbm) not in (int, float)
            or not math.isfinite(power_dbm) or not -30 <= power_dbm <= 20):
        raise ValueError('Invalid fixture configuration')
    from .intake_fixture_bridge import run_fixture_worker
    output.mkdir(parents=True, exist_ok=False)
    phase = 'prepare_intake'
    try:
        inbox, workspace = output / 'inbox', output / 'state'
        _write_request(inbox / 'fixture-request', document_kind)
        store = Store(workspace)
        register_source(store, 'FLOW-INBOX', inbox, synthetic=True, settle_seconds=0.001)
        started = time.time()
        scan_source(store, 'FLOW-INBOX', now=started)
        accepted = scan_source(store, 'FLOW-INBOX', now=started + 0.002)['accepted']
        if len(accepted) != 1:
            raise ValueError('fixture_intake_not_accepted')
        intake_id = accepted[0]['intake_id']
        # This is a simulated trusted proceed event for a sealed synthetic demo.
        respond(store, 'FLOW-DELEGATION', 'proceed', intake_id=intake_id)
        phase = 'analyze_fixture'
        analysis = run_worker(store, SyntheticTextProvider(), worker_id='flow-analysis', max_jobs=1)
        if len(analysis['results']) != 1 or analysis['results'][0]['status'] != 'completed':
            raise ValueError('fixture_analysis_incomplete')
        ready = fixture_readiness(store, intake_id)
        if not ready['ready']:
            raise ValueError('fixture_intake_not_ready')
        phase = 'run_single_fixture'
        request_fixture_job(store, 'FLOW-REQUEST', intake_id, expected_revision=ready['revision'],
            expected_readiness_fingerprint=ready['readiness_fingerprint'],
            recipe_id='conducted_sensor_fixture_v1', settings={'power_dbm': power_dbm})
        run_fixture_worker(store, worker_id='flow-execution', output_root=output / 'artifacts', max_jobs=1)
        with store.connection() as con:
            con.execute('BEGIN')
            row = con.execute('SELECT * FROM intake_fixture_jobs WHERE request_id=?', ('FLOW-REQUEST',)).fetchone()
            records = con.execute('SELECT COUNT(*) FROM intake_fixture_jobs').fetchone()[0]
            current = fixture_readiness(_SnapshotStore(con), intake_id)
        source_current = bool(current['revision'] == row['revision']
            and current['readiness_fingerprint'] == row['readiness_fingerprint'])
        report = json.loads(row['result_json'])['report'] if row['result_json'] else None
        observed = bool(row['state'] == 'completed' and report
            and report['termination'] == {'reason': 'policy_stop', 'policy_claim': 'completed'}
            and report['assessment']['status'] == 'completed' and report['assessment']['verdict'] == 'pass'
            and report['evidence']['measurement_refs'] and not report['unresolved_request_ids'])
        summary = {'schema_version': 1, 'kind': 'intake_fixture_flow_check',
            'synthetic': True, 'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
            'document_kind': document_kind, 'intake_id': intake_id, 'revision': row['revision'],
            'current_revision': current['revision'], 'source_current': source_current,
            'historical': not source_current, 'intake_ready': current['ready'],
            'source_synthetic': bool(row['source_synthetic']),
            'request_id': row['request_id'], 'run_id': row['run_id'], 'records': records,
            'execution_state': row['state'], 'fixture_measurement_observed': observed,
            'fixture_acceptance': 'pass' if observed and source_current and current['ready'] else 'fail',
            'task_outcome': report['task_outcome'] if report else 'not_assessed',
            'cleanup_status': report['cleanup']['status'] if report else 'not_assessed',
            'validation_scope': 'synthetic intake and single sensor fixture; no model or hardware validation'}
        _write_json(output / 'public-summary.json', summary)
        return {'summary': summary, 'workspace': workspace, 'output': output}
    except Exception:
        _write_json(output / 'failure.json', {'schema_version': 1, 'synthetic': True,
            'hardware_verified': False, 'ai_model_called': False, 'resumable': False,
            'code': 'intake_fixture_flow_incomplete', 'phase': phase})
        raise


_CONDUCTED_RF_QUOTE = ('frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; '
                       'duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB')
_CONDUCTED_MOCK_NAME = 'DGM-AUTHORED-SCRIPTED-MOCK-PDF'
_CONDUCTED_SCHEMA_SHA = 'aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb'
_CONDUCTED_SCENARIOS = ('normal', 'missing-duty-unit', 'invalid-citation',
                        'measurement-invalid', 'restored-disconnect', 'transport-error', 'recovery-failure')

# A new, local mock binary, never the installed CLI. It implements only the
# public producer envelope and an explicitly authored five-action policy.
_CONDUCTED_MOCK_CS = r'''
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;
class AuthoredSyntheticMock {
  static Dictionary<string,object> D(params object[] pairs) {
    var result=new Dictionary<string,object>();
    for(int i=0;i<pairs.Length;i+=2) result.Add((string)pairs[i],pairs[i+1]);
    return result;
  }
  static int Main(string[] args) {
    Console.OutputEncoding=new UTF8Encoding(false); Console.Out.NewLine="\n";
    if(args.Length==1 && args[0]=="--version") {
      Console.Write("codex-cli 0.163.0-alpha.11.2\n"); return 0;
    }
    try {
      var buffer=new char[262145]; int size=0,got;
      while(size<buffer.Length && (got=Console.In.Read(buffer,size,buffer.Length-size))>0) size+=got;
      if(size>262144) return 21;
      var json=new JavaScriptSerializer(); json.MaxJsonLength=262144;
      var prompt=json.Deserialize<Dictionary<string,object>>(new string(buffer,0,size));
      var binding=(Dictionary<string,object>)prompt["binding"];
      var producer=(Dictionary<string,object>)prompt["expected_producer"];
      string home=AppDomain.CurrentDomain.BaseDirectory;
      int step=1; while(step<=8 && File.Exists(Path.Combine(home,"step-"+step+".json"))) step++;
      if(step>5) return 22;
      object proposal;
      if(step==1) proposal=D("kind","execute","device_id","dut","action","start","parameters",D());
      else if(step==2 || step==4) proposal=D("kind","advance","ticks",1);
      else if(step==3) proposal=D("kind","execute","device_id","sensor","action","acquire","parameters",D());
      else proposal=D("kind","stop","claim","completed","reason","Authored MOCK policy stopped; task and conformity remain not assessed.");
      string wire=json.Serialize(D("schema_version",1,"kind","virtual_operator_response",
        "request_sha256",binding["request_sha256"],"producer",producer,"proposal",proposal));
      int last=Array.IndexOf(args,"--output-last-message");
      if(last<0 || last+1>=args.Length) return 23;
      using(var marker=new FileStream(Path.Combine(home,"step-"+step+".json"),FileMode.CreateNew)) {
        byte[] raw=Encoding.UTF8.GetBytes(wire); marker.Write(raw,0,raw.Length);
      }
      File.WriteAllText(args[last+1],wire,new UTF8Encoding(false));
      Console.WriteLine(json.Serialize(D("type","thread.started","thread_id","authored-mock-thread")));
      Console.WriteLine(json.Serialize(D("type","turn.started")));
      Console.WriteLine(json.Serialize(D("type","item.completed","item",D("id","mock-answer","type","agent_message","text",wire))));
      Console.WriteLine(json.Serialize(D("type","turn.completed")));
      return 0;
    } catch { return 24; }
  }
}
'''


def _conducted_write(output, relative, raw):
    """Bound own evidence writes; native producers keep their existing limits."""
    raw = raw.encode('utf-8') if isinstance(raw, str) else raw
    target = output / relative
    target.resolve().relative_to(output)
    files = [item for item in output.rglob('*') if item.is_file()]
    if len(files) + 1 > 512 or sum(item.stat().st_size for item in files) + len(raw) > 32 * 1024 * 1024:
        raise ValueError('conducted_workflow_evidence_limit')
    target.parent.mkdir(parents=True, exist_ok=True)
    first = None
    try:
        with target.open('xb') as stream:
            try:
                stream.write(raw)
            except BaseException as error:
                first = error
    except BaseException:
        if first is None:
            raise
    if first is not None:
        raise first


def _conducted_json(output, relative, value):
    _conducted_write(output, relative, canonical(value) + '\n')


def _conducted_mock_compiler():
    if os.name != 'nt':
        return None
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    for framework in ('Framework64', 'Framework'):
        compiler = windows / 'Microsoft.NET' / framework / 'v4.0.30319/csc.exe'
        if compiler.is_file():
            return compiler
    return None


def _compile_conducted_mock(output, compiler, *, scenario='normal'):
    source = _CONDUCTED_MOCK_CS
    policy = ['dut.start', 'advance:1', 'sensor.acquire', 'advance:1', 'stop:completed']
    if scenario == 'measurement-invalid':
        # Author this new fixture before compilation; never edit retained responses.
        original = ('else if(step==2 || step==4) proposal=D("kind","advance","ticks",1);\n'
                    '      else if(step==3) proposal=D("kind","execute","device_id","sensor","action","acquire","parameters",D());')
        replacement = ('else if(step==2) proposal=D("kind","execute","device_id","sensor","action","acquire","parameters",D());\n'
                       '      else if(step==3) proposal=D("kind","advance","ticks",1);\n'
                       '      else if(step==4) proposal=D("kind","execute","device_id","sensor","action","read","parameters",D());')
        if source.count(original) != 1:
            raise ValueError('conducted_workflow_mock_policy_invalid')
        source = source.replace(original, replacement)
        policy = ['dut.start', 'sensor.acquire', 'advance:1', 'sensor.read', 'stop:completed']
    elif scenario == 'transport-error':
        source = source.replace('"claim","completed"', '"claim","blocked"')
        policy = ['dut.start', 'advance:1', 'sensor.acquire', 'advance:1', 'stop:blocked']
    elif scenario == 'recovery-failure':
        original = ('if(step==1) proposal=D("kind","execute","device_id","dut","action","start","parameters",D());\n'
                    '      else if(step==2 || step==4) proposal=D("kind","advance","ticks",1);\n'
                    '      else if(step==3) proposal=D("kind","execute","device_id","sensor","action","acquire","parameters",D());')
        replacement = ('if(step==1 || step==5) proposal=D("kind","execute","device_id","dut","action","start","parameters",D());\n'
                       '      else if(step==2 || step==4 || step==7) proposal=D("kind","advance","ticks",1);\n'
                       '      else if(step==3 || step==6) proposal=D("kind","execute","device_id","sensor","action","acquire","parameters",D());')
        if source.count(original) != 1 or source.count('if(step>5)') != 1:
            raise ValueError('conducted_workflow_mock_policy_invalid')
        source = source.replace(original, replacement).replace('if(step>5)', 'if(step>8)')
        source = source.replace('"claim","completed"', '"claim","blocked"')
        policy = ['dut.start', 'advance:1', 'sensor.acquire', 'advance:1',
                  'dut.start', 'sensor.acquire', 'advance:1', 'stop:blocked']
    _conducted_write(output, 'm/authored-mock.cs', source)
    executable = output / 'm/codex.exe'
    compiled = subprocess.run([str(compiler), '/nologo', '/target:exe',
        '/r:System.Web.Extensions.dll', '/out:' + str(executable), str(output / 'm/authored-mock.cs')],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW)
    _conducted_write(output, 'm/compiler.log', compiled.stdout)
    if compiled.returncode or not executable.is_file():
        raise ValueError('conducted_workflow_mock_compile_failed')
    _conducted_json(output, 'm/mock-origin.json', {'kind': 'authored_scripted_mock',
        'installed_cli_used': False, 'actual_model_calls': 0,
        'source_sha256': sha256(source.encode('utf-8')).hexdigest(),
        'executable_sha256': sha256(executable.read_bytes()).hexdigest(),
        'scenario': scenario, 'policy': policy})
    return executable


def _scripted_pdf_analysis(context, *, rf_quote=_CONDUCTED_RF_QUOTE, invalid_citation=False):
    """Author the declared mock response from this new PDF's exact citations."""
    facts = []
    for document in context['documents']:
        for page in document['pages']:
            for index, line in enumerate(page['text'].splitlines(), 1):
                if line == rf_quote:
                    field, value = 'features', line
                elif any(line.startswith(key + ': ') for key in ('product_type', 'model', 'market', 'purpose')):
                    field, value = line.split(': ', 1)
                else:
                    continue
                evidence = {'kind': 'pdf_page', 'extraction_id': document['extraction_id'],
                    'page_number': page['page_number'], 'text_sha256': page['text_sha256'],
                    'path': document['path'], 'sha256': document['sha256'],
                    'line_start': index, 'line_end': index, 'quote': line, 'role': 'request'}
                if invalid_citation and field == 'features':
                    evidence['quote'] = line + '; AUTHORED MOCK citation mismatch'
                facts.append({'field': field, 'value': value, 'status': 'explicit', 'evidence': [evidence]})
    return {'schema_version': 2, 'context_id': context['analysis_context_id'],
        'producer': {'kind': 'model', 'name': _CONDUCTED_MOCK_NAME},
        'identity': 'single', 'facts': facts, 'missing_fields': []}


def _conducted_artifact_startup(plan, method, finalized, artifact_root):
    """Compose read selection from original current pins and committed artifact."""
    failed=False;selection=None
    try:
        if type(plan) is not dict or type(finalized) is not dict:raise ValueError()
        if plan.get('status')!='ready_for_simulation' or finalized.get('status')!='stored':return None
        result,artifact=finalized.get('result'),finalized.get('artifact')
        if result is None or artifact is None:return None
        if type(artifact) is not dict or type(artifact.get('storage')) is not dict:raise ValueError()
        if artifact['storage'].get('status')!='complete':return None
        if (type(result) is not dict or type(result.get('schema_version')) is not int or result['schema_version']!=1
                or result.get('kind')!='conducted_twin_result' or result.get('status') not in ('recorded','incomplete','invalid')
                or type(artifact.get('schema_version')) is not int or artifact['schema_version']!=1
                or artifact.get('kind')!='conducted_result_artifact' or artifact.get('result_status')!=result['status']
                or artifact.get('execution_authority') is not False):raise ValueError()
        from .virtual_fleet.conducted_result_artifact import _verification,MAX_MANIFEST_BYTES
        if canonical(artifact.get('verification'))!=canonical(_verification('full_bound')):raise ValueError()
        if type(artifact_root) not in (str,type(Path())) or not Path(artifact_root).is_absolute():raise ValueError()
        root=Path(artifact_root);binding=plan['binding']
        from .ui_server import _conducted_artifact_readback_selection
        selection=json.loads(_conducted_artifact_readback_selection(dict(
            intake_id=binding['intake_id'],method=method,expected_revision=binding['revision'],
            expected_context_sha256=binding['context_sha256'],artifact_workspace_root=str(root),
            artifact_name=artifact['artifact_name'],expected_manifest_sha256=artifact['storage']['sha256'],
            expected_result_sha256=sha256(canonical(result).encode('utf-8')).hexdigest(),
            run_id=artifact['run_id'],runtime_instance_id=artifact['runtime_instance_id'])))
        if selection['artifact_workspace_root']!=str(root):raise ValueError()
        marker='.local/conducted-result-artifacts/'+selection['artifact_name']+'/manifest.json'
        if (type(artifact['storage'].get('commit_marker')) is not str or artifact['storage']['commit_marker']!=marker
                or type(artifact['storage'].get('bytes')) is not int
                or not 1<=artifact['storage']['bytes']<=MAX_MANIFEST_BYTES):raise ValueError()
    except (KeyboardInterrupt,SystemExit,GeneratorExit,MemoryError):raise
    except Exception:failed=True
    if failed:raise ValueError('conducted_workflow_artifact_startup_invalid') from None
    return selection


def _conducted_readback_inputs(output, selection):
    """Save already validated startup pins for the optional readonly CLI."""
    if selection is not None:
        _conducted_json(output,'readback-inputs.json',{key:value for key,value in selection.items() if key!='intake_id'})


def _conducted_export_need(condition):
    if not condition:
        raise ValueError('conducted_workflow_readback_export_invalid')


def _conducted_export_frame(value, cap):
    """Detach provided native data; this does not open or authenticate its source."""
    from . import intake_conducted_artifact_readback as readback
    try:
        raw = readback._raw(value, cap)
    except readback.IntakeConductedArtifactReadbackError:
        raise ValueError('conducted_workflow_readback_export_invalid') from None
    return json.loads(raw), raw


def _conducted_export_pin(value, raw):
    _conducted_export_need(type(value) is dict and set(value) == {'bytes', 'sha256'}
        and type(value['bytes']) is int and value['bytes'] == len(raw)
        and type(value['sha256']) is str and value['sha256'] == sha256(raw).hexdigest())


def export_conducted_workflow_readback_inputs(output_dir, workflow_summary, finalizer_receipt, *,
        current_facts_plan, method, artifact_workspace_root):
    """Export provided pin consistency only; never complete a job or repair current binding."""
    from . import intake_conducted_artifact_readback as readback
    from . import control_packet_prepare as native
    from .virtual_fleet import conducted_twin_result as result_api
    from .virtual_fleet import rf_signal_waveform_observation_read as cleanup
    need = _conducted_export_need
    host, _ = _conducted_export_frame(workflow_summary, 69632)
    need(type(host) is dict and set(host) == set('schema_version kind status phase scenario_id requested_model history reservation execution finalization errors verification'.split())
        and type(host['schema_version']) is int and host['schema_version'] == 1
        and host['kind'] == 'codex_registered_conducted_workflow_host_receipt'
        and type(host['status']) is str and host['status'] in ('completed', 'not_run', 'failed', 'unknown')
        and type(host['verification']) is dict and all(host['verification'].get(key) is False
            for key in ('hardware_verified', 'origin_authenticated', 'remote_model_identity_verified'))
        and host['verification'].get('measurement') == 'not_assessed')
    if current_facts_plan is None or finalizer_receipt is None or host['finalization'] is None:
        return None
    current, _ = _conducted_export_frame(current_facts_plan, 8 * 1024 * 1024)
    need(type(current) is dict and type(current.get('context')) is dict
        and type(current['context'].get('intake_id')) is str)
    try:
        readback._current_value(current, current['context']['intake_id'])
    except readback.IntakeConductedArtifactReadbackError:
        raise ValueError('conducted_workflow_readback_export_invalid') from None
    if current['facts_plan']['status'] == 'blocked':
        return None
    method, _ = _conducted_export_frame(method, 65536)
    need(type(method) is dict and set(method) == set('method_id method_version metric reference_plane'.split()))
    plan = current['facts_plan']['plan_input']
    need(canonical(method) == canonical({key: plan['plan'][key] for key in method}))
    final, final_raw = _conducted_export_frame(finalizer_receipt, 2 * 1024 * 1024)
    final_keys = set('schema_version kind status execution_receipt input_files result artifact failure secondary_errors verification execution_authority'.split())
    need(type(final) is dict and set(final) in (final_keys, final_keys | {'measurement_selection'})
        and type(final['schema_version']) is int and final['schema_version'] == 1
        and final['kind'] == 'conducted_execution_result_finalizer'
        and final['status'] in ('held', 'stored') and final['execution_authority'] is False
        and type(final['verification']) is dict
        and all(final['verification'].get(key) is False for key in ('hardware_verified', 'physical_verified', 'full_task_verified', 'execution_rerun'))
        and final['verification'].get('method_approval') == 'not_assessed')
    projected = host['finalization']
    need(type(projected) is dict and set(projected) == set('status result_status artifact failure receipt'.split()))
    _conducted_export_pin(projected['receipt'], final_raw)
    need(canonical(projected['status']) == canonical(final['status'])
        and canonical(projected['artifact']) == canonical(final['artifact'])
        and canonical(projected['failure']) == canonical(final['failure']))
    result, artifact = final['result'], final['artifact']
    need(result is None or type(result) is dict)
    need(canonical(projected['result_status']) == canonical(None if result is None else result.get('status')))
    if final['status'] != 'stored' or result is None or artifact is None:
        return None
    need(type(artifact) is dict and type(artifact.get('storage')) is dict)
    if artifact['storage'].get('status') != 'complete':
        return None
    result, result_raw = _conducted_export_frame(result, result_api.MAX_OUTPUT_BYTES)
    need(type(result) is dict and set(result) == set(result_api._base())
        and type(result['schema_version']) is int and result['schema_version'] == 1
        and result['kind'] == 'conducted_twin_result' and result['status'] in ('recorded', 'invalid', 'incomplete')
        and type(result['binding']) is dict and type(result['verification']) is dict
        and all(result['verification'].get(key) is False for key in ('hardware_verified', 'physical_verified', 'execution_authority'))
        and result['verification'].get('method_approval') == 'not_assessed')
    execution, execution_raw = _conducted_export_frame(final['execution_receipt'], 262144)
    need(type(execution) is dict and type(execution.get('binding')) is dict
        and type(execution.get('schema_version')) is int and execution['schema_version'] == 1
        and execution.get('kind') == 'intake_plan_virtual_execution_result')
    observed = host['execution']
    need(type(observed) is dict and set(observed) == set('run_id runtime_instance_id status failure receipt producer_receipts'.split()))
    _conducted_export_pin(observed['receipt'], execution_raw)
    need(canonical(observed['status']) == canonical(execution.get('status'))
        and canonical(observed['failure']) == canonical(execution.get('failure')))
    need(set(artifact) == set('schema_version kind artifact_name run_id runtime_instance_id result_status storage files verification execution_authority'.split())
        and artifact['result_status'] == result['status'] and type(artifact['artifact_name']) is str and bool(artifact['artifact_name']))
    for key in ('run_id', 'runtime_instance_id'):
        need(type(artifact[key]) is str and bool(artifact[key])
            and canonical(artifact[key]) == canonical(observed[key]) == canonical(execution['binding'].get(key)) == canonical(result['binding'].get(key)))
    prefix = '.local/conducted-result-artifacts/' + artifact['artifact_name'] + '/'
    files = artifact['files']
    need(type(files) is list and len(files) == 2)
    for row, name, media, cap in zip(files, ('result.json', 'draft.md'), ('application/json', 'text/markdown'), (1024 * 1024 + 1, 256 * 1024)):
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256', 'media_type'}
            and row['path'] == prefix + name and row['media_type'] == media
            and type(row['bytes']) is int and 1 <= row['bytes'] <= cap
            and type(row['sha256']) is str and len(row['sha256']) == 64
            and all(c in '0123456789abcdef' for c in row['sha256']))
    need(files[0]['bytes'] == len(result_raw) + 1 and files[0]['sha256'] == sha256(result_raw + b'\n').hexdigest())
    selection = _conducted_artifact_startup(plan, method, final, artifact_workspace_root)
    if selection is None:
        return None
    _conducted_export_frame(selection, 65536)
    file_raw = (canonical({key: value for key, value in selection.items() if key != 'intake_id'}) + '\n').encode('utf-8')
    need(len(file_raw) <= 65536)
    need(type(output_dir) in (str, type(Path())))
    output = Path(output_dir)
    need(output.is_absolute() and not str(output_dir).startswith(('\\\\', '//'))
        and all(native._valid_segment(part) for part in output.parts[1:]))
    output = native._local_path(output_dir)
    backend = primary = None
    try:
        backend = native._WindowsIO()
        native._Tree(output, backend)
        _conducted_readback_inputs(output, selection)
    except BaseException as error:
        primary = error
    finally:
        if backend is not None:
            try:
                closing = cleanup._close(backend)
            except BaseException as error:
                closing = error
            if primary is None and closing is not None:
                primary = closing
    if primary is not None:
        raise primary
    return selection


def run_conducted_flow(output_dir, *, document_kind='pdf', measurement_ref=None, mock_model=None, scenario='normal',
        uncertainty_inputs=None):
    """Opt-in authored PDF -> current C1 -> genuine plan/execution/result/DRAFT."""
    if scenario not in _CONDUCTED_SCENARIOS:
        raise ValueError('conducted_workflow_scenario_unsupported')
    if uncertainty_inputs is not None:
        uncertainty_inputs = _conducted_export_frame(uncertainty_inputs, 262144)[0]
        _conducted_export_need(type(uncertainty_inputs) is dict
            and set(uncertainty_inputs) == {'components', 'policy'})
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Output directory already exists')
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema_version': 1, 'kind': 'conducted_intake_workflow_demo',
        'synthetic': True, 'provider': 'authored_scripted_mock', 'ai_model_called': False,
        'hardware_verified': False, 'physical_verified': False, 'resumable': False,
        'fixture_acceptance': 'fail', 'runtime_calls': 0, 'document_kind': document_kind,
        'task_outcome': 'not_assessed', 'conformity': 'not_assessed', 'scenario': scenario,
        'result_status': None, 'storage_status': None, 'draft_status': 'not_run',
        'raw_measurement': None, 'corrected': None, 'files': None}
    compiler = _conducted_mock_compiler()
    reason = ('conducted_workflow_pdf_required' if document_kind != 'pdf' else
              'conducted_workflow_measurement_ref_required' if not isinstance(measurement_ref, str) or not measurement_ref else
              'conducted_workflow_mock_model_required' if mock_model not in ('gpt-6.1-sol', 'gpt-6-astra') else
              'conducted_workflow_windows_mock_compiler_required' if compiler is None else None)
    if reason:
        summary.update(status='unsupported', reason=reason)
        _conducted_json(output, 'public-summary.json', summary)
        return {'summary': summary, 'workspace': None, 'output': output}
    phase = 'prepare_intake'
    try:
        from reportlab.pdfgen import canvas
        from .intake_jobs import claim_job, complete_job, fail_job
        from .intake_model_boundary import build_analysis_prompt, decode_analysis_response
        from .intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
        from .intake_plan_virtual_execution import run_intake_plan_virtual_execution
        from .conducted_execution_result_finalizer import finalize_conducted_execution_result
        from .ui_read_model import IntakeReadModel

        run_uuid = uuid.uuid4().hex
        product = ['product_type: smartphone', 'model: SM-A176U', 'market: US',
                   'purpose: Wi-Fi 2.4 GHz conducted engineering simulation']
        rf_quote = (_CONDUCTED_RF_QUOTE.replace('duty_cycle: 50 %', 'duty_cycle: 50')
                    if scenario == 'missing-duty-unit' else _CONDUCTED_RF_QUOTE)
        condition = ['Condition SYN-WIFI24-CH1; authored synthetic engineering condition.', rf_quote]
        _conducted_write(output, 'authored-request.txt', '\n'.join(product + condition) + '\n')
        folder = output / 'i/r'
        folder.mkdir(parents=True)
        pdf = canvas.Canvas(str(folder / 'request.pdf'))
        for lines in (product, condition):
            text = pdf.beginText(48, 790)
            text.setFont('Helvetica', 7)
            for line in lines:
                text.textLine(line)
            pdf.drawText(text)
            pdf.showPage()
        pdf.save()
        store = Store(output / 's')
        source_id = 'CW-' + run_uuid
        register_source(store, source_id, output / 'i', synthetic=True, settle_seconds=0.001)
        now = time.time()
        scan_source(store, source_id, now=now)
        scanned = scan_source(store, source_id, now=now + 0.002)
        _conducted_json(output, 'scan.json', scanned)
        if len(scanned['accepted']) != 1:
            raise ValueError('conducted_workflow_intake_not_accepted')
        intake_id = scanned['accepted'][0]['intake_id']
        summary.update(intake_id=intake_id, revision=scanned['accepted'][0]['revision'])
        respond(store, 'CW-PROCEED-' + run_uuid, 'proceed', intake_id=intake_id)
        phase = 'strict_scripted_analysis'
        job = claim_job(store, 'conducted-MOCK-' + run_uuid, synthetic_only=True)
        if job is None or job['intake_id'] != intake_id:
            raise ValueError('conducted_workflow_claim_mismatch')
        context = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'synthetic',
                   'documents', 'analysis_context_id', 'analysis_contract', 'instructions')}
        prompt = build_analysis_prompt(context, producer_name=_CONDUCTED_MOCK_NAME)
        raw = canonical(_scripted_pdf_analysis(context, rf_quote=rf_quote,
                        invalid_citation=scenario == 'invalid-citation')).encode('utf-8')
        _conducted_json(output, 'analysis-context-original.json', context)
        _conducted_json(output, 'analysis-prompt.json', prompt)
        _conducted_write(output, 'analysis-MOCK-original.json', raw)
        try:
            analysis = decode_analysis_response(raw, context, producer_name=_CONDUCTED_MOCK_NAME)
        except ValueError as error:
            if scenario != 'invalid-citation' or str(error) != 'analysis_response_invalid':
                raise
            # Expected negative scenario: keep the genuine rejection and raw prefix,
            # fail this owned claim, and expose only the incomplete Store for reading.
            failure = {'code': str(error), 'phase': phase, 'synthetic': True,
                       'actual_model_calls': 0, 'hardware_verified': False}
            _conducted_json(output, 'failure.json', failure)
            try:
                fail_job(store, job['job_id'], job['token'])
            except Exception:
                _conducted_json(output, 'failure-secondary.json', {
                    'code': 'conducted_workflow_failure_projection_unconfirmed', 'phase': 'fail_owned_claim'})
            summary.update(status='rejected', reason=failure['code'], failure=failure)
            _conducted_json(output, 'public-summary.json', summary)
            return {'summary': summary, 'workspace': store.root, 'output': output}
        _conducted_json(output, 'analysis-strict.json', analysis)
        complete_job(store, job['job_id'], job['token'], analysis)

        phase = 'current_readonly_plan'
        current = IntakeReadModel(store.root).current_conducted_plan_context(intake_id)
        context, analysis = current['context'], current['analysis']
        _conducted_json(output, 'current-readonly-context-analysis.json', current)
        context_pin = sha256(canonical(context).encode('utf-8')).hexdigest()
        method = {'method_id': 'conducted_synthetic', 'method_version': 1,
                  'metric': 'on', 'reference_plane': 'source_output'}
        assembled = build_conducted_plan_from_intake_facts(context, analysis,
            expected_revision=context['revision'], expected_context_sha256=context_pin, method=method)
        _conducted_json(output, 'facts-plan-original.json', assembled)
        plan = assembled['plan_input']
        server_options = {'conducted_plan_preview_inputs': {'intake_id': intake_id,
            'revision': context['revision'], 'source_settings': plan['plan']['source_settings'],
            'basis': plan['plan']['basis_refs'], 'method': method}}
        summary.update(intake_id=intake_id, revision=context['revision'], context_sha256=context_pin,
                       source6_assembly='genuine_cited_intake_facts', mock_model=mock_model)
        if assembled['status'] != 'ready_for_simulation':
            summary.update(status='blocked', reason='conducted_workflow_plan_blocked')
            _conducted_json(output, 'server-startup-original.json', server_options)
            _conducted_json(output, 'public-summary.json', summary)
            return {'summary': summary, 'workspace': store.root, 'output': output, 'server_options': server_options}

        phase = 'compile_authored_mock'
        executable = _compile_conducted_mock(output, compiler, scenario=scenario)
        project = Path(__file__).resolve().parents[1]
        contract = json.loads((project / 'docs/fcc/codex_first_decision_contract.json').read_bytes())
        schema = contract['response_schema']['literal_utf8'].encode('utf-8')
        if len(schema) != 3052 or sha256(schema).hexdigest() != _CONDUCTED_SCHEMA_SHA:
            raise ValueError('conducted_workflow_schema_unsupported')
        catalog = project / 'virtual_profiles/sm_a176u_unlicensed.json'
        phase = 'execute_same_plan'
        runtime_scenario = {'restored-disconnect': 'restored_disconnect',
            'transport-error': 'persistent_disconnect', 'recovery-failure': 'persistent_disconnect'}.get(scenario, 'normal')
        execution = run_intake_plan_virtual_execution(context, analysis, plan,
            expected_revision=context['revision'], expected_context_sha256=context_pin,
            expected_plan_input_sha256=sha256(canonical(plan).encode('utf-8')).hexdigest(),
            catalog_path=catalog, catalog_sha256=sha256(catalog.read_bytes()).hexdigest(),
            response_schema_bytes=schema, executable=executable, requested_model=mock_model,
            scenario=runtime_scenario,
            evidence_dir=output / 'x', execution_origin='mock_subprocess',
            quantity={'metric': 'on', 'reference_plane': 'sensor_input',
                      'loss_compensation_applied': False, 'loss_compensation_sign': 1})
        _conducted_json(output, 'execution-original.json', execution)
        phase = 'finalize_explicit_measurement'
        artifact_root=output
        uncertainty_options = {} if uncertainty_inputs is None else {'uncertainty_inputs': uncertainty_inputs}
        finalized = finalize_conducted_execution_result(execution,
            expected_execution_sha256=sha256(canonical(execution).encode('utf-8')).hexdigest(),
            evidence_dir=output / 'x', measurement_ref=measurement_ref,
            workspace_root=artifact_root, artifact_name='draft-' + run_uuid[:12], **uncertainty_options)
        _conducted_json(output, 'finalizer-original.json', finalized)
        result, artifact = finalized['result'], finalized['artifact']
        current_after = IntakeReadModel(store.root).current_conducted_plan_context(intake_id)
        current_matches = canonical(current_after) == canonical(current)
        _conducted_json(output, 'current-readonly-after.json', current_after)
        phase = 'bind_readonly_server'
        server_options['conducted_result_snapshot'] = {'intake_id': intake_id, 'revision': context['revision'],
            'expected_current_binding': plan['binding'], 'result': result}
        selection=_conducted_artifact_startup(plan,method,finalized,artifact_root)
        if selection is not None:server_options['conducted_artifact_readback_inputs']=selection
        _conducted_json(output, 'server-startup-original.json', server_options)
        _conducted_readback_inputs(output,selection)
        stored = bool(finalized['status'] == 'stored' and artifact and artifact['storage']['status'] == 'complete')
        recorded = bool(result and result['status'] == 'recorded')
        summary.update(status='stored' if stored else 'held', runtime_calls=execution['execution']['trial_factory_calls'],
            producer_calls=execution['execution']['producer_calls_started'],
            runtime_scenario=runtime_scenario,
            failure=finalized['failure'], gaps=result['gaps'] if result else None,
            draft_status=artifact['verification']['report_status'] if artifact else 'not_run',
            source_current=current_matches, result_status=result['status'] if result else None,
            storage_status=artifact['storage']['status'] if artifact else None,
            run_id=result['binding'].get('run_id') if result else None,
            runtime_instance_id=result['binding'].get('runtime_instance_id') if result else None,
            measurement_ref=measurement_ref, raw_measurement=result['raw_measurement'] if result else None,
            corrected=result['calculation']['corrected'] if result else None,
            files=artifact['files'] if artifact else None, storage=artifact['storage'] if artifact else None,
            fixture_acceptance='pass' if stored and recorded and current_matches else 'fail')
        _conducted_json(output, 'public-summary.json', summary)
        return {'summary': summary, 'workspace': store.root, 'output': output, 'server_options': server_options}
    except BaseException as error:
        # Preserve native first-error receipt and control identity. No retry/repair.
        try:
            receipt = getattr(error, 'receipt', None)
            if receipt is not None:
                _conducted_json(output, 'failure-original-receipt.json', receipt)
            code = getattr(error, 'code', None)
            if code is None and isinstance(error, ValueError) and (str(error).startswith('conducted_workflow_')
                    or str(error) in {'analysis_context_invalid', 'analysis_context_limit', 'analysis_producer_invalid',
                                      'analysis_response_invalid', 'analysis_response_limit'}):
                code = str(error)
            _conducted_json(output, 'failure.json', {'code': code or 'conducted_workflow_incomplete',
                'phase': phase, 'synthetic': True, 'actual_model_calls': 0, 'hardware_verified': False})
        except BaseException:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--power-dbm', type=float, default=12.5)
    mode.add_argument('--conducted-workflow', action='store_true', help='Authored PDF plan/execution/result/DRAFT mock demo')
    parser.add_argument('--measurement-ref', help='Explicit same-journal reference for the opt-in workflow')
    parser.add_argument('--mock-model', choices=['gpt-6.1-sol', 'gpt-6-astra'], help='Logical model label for the generated mock executable only')
    parser.add_argument('--conducted-scenario', choices=_CONDUCTED_SCENARIOS,
                        help='New authored input/mock/runtime scenario; requires --conducted-workflow')
    parser.add_argument('--document-kind', choices=['text', 'pdf'], default='text')
    parser.add_argument('--port', type=int, help='After execution, serve the existing intake store on loopback')
    args = parser.parse_args(argv)
    if args.conducted_scenario is not None and not args.conducted_workflow:
        parser.error('--conducted-scenario requires --conducted-workflow')
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    output = args.output or Path('.local/cw' if args.conducted_workflow else '.local/intake-fixture-check') / uuid.uuid4().hex[:12 if args.conducted_workflow else 32]
    try:
        result = (run_conducted_flow(output, document_kind=args.document_kind,
                  measurement_ref=args.measurement_ref, mock_model=args.mock_model,
                  scenario=args.conducted_scenario or 'normal') if args.conducted_workflow
                  else run_fixture_flow(output, power_dbm=args.power_dbm, document_kind=args.document_kind))
        print(json.dumps(result['summary'], ensure_ascii=False, allow_nan=False), flush=True)
        if args.port is not None and result['workspace'] is not None:
            from .ui_server import create_server
            with create_server(result['workspace'], port=args.port, **result.get('server_options', {})) as server:
                print(f"DGM synthetic intake fixture: http://127.0.0.1:{server.server_port}/#{result['summary']['intake_id']}", flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
        return 0 if result['summary']['fixture_acceptance'] == 'pass' else 1
    except Exception:
        print(json.dumps({'error': 'intake_fixture_flow_failed', 'synthetic': True,
                          'hardware_verified': False, 'ai_model_called': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
