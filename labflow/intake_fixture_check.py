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
    with target.open('xb') as stream:
        stream.write(raw)


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


def _compile_conducted_mock(output, compiler):
    _conducted_write(output, 'm/authored-mock.cs', _CONDUCTED_MOCK_CS)
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
        'source_sha256': sha256(_CONDUCTED_MOCK_CS.encode('utf-8')).hexdigest(),
        'executable_sha256': sha256(executable.read_bytes()).hexdigest(),
        'policy': ['dut.start', 'advance:1', 'sensor.acquire', 'advance:1', 'stop:completed']})
    return executable


def _scripted_pdf_analysis(context):
    """Author the declared mock response from this new PDF's exact citations."""
    facts = []
    for document in context['documents']:
        for page in document['pages']:
            for index, line in enumerate(page['text'].splitlines(), 1):
                if line == _CONDUCTED_RF_QUOTE:
                    field, value = 'features', line
                elif any(line.startswith(key + ': ') for key in ('product_type', 'model', 'market', 'purpose')):
                    field, value = line.split(': ', 1)
                else:
                    continue
                evidence = {'kind': 'pdf_page', 'extraction_id': document['extraction_id'],
                    'page_number': page['page_number'], 'text_sha256': page['text_sha256'],
                    'path': document['path'], 'sha256': document['sha256'],
                    'line_start': index, 'line_end': index, 'quote': line, 'role': 'request'}
                facts.append({'field': field, 'value': value, 'status': 'explicit', 'evidence': [evidence]})
    return {'schema_version': 2, 'context_id': context['analysis_context_id'],
        'producer': {'kind': 'model', 'name': _CONDUCTED_MOCK_NAME},
        'identity': 'single', 'facts': facts, 'missing_fields': []}


def run_conducted_flow(output_dir, *, document_kind='pdf', measurement_ref=None, mock_model=None):
    """Opt-in authored PDF -> current C1 -> genuine plan/execution/result/DRAFT."""
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Output directory already exists')
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema_version': 1, 'kind': 'conducted_intake_workflow_demo',
        'synthetic': True, 'provider': 'authored_scripted_mock', 'ai_model_called': False,
        'hardware_verified': False, 'physical_verified': False, 'resumable': False,
        'fixture_acceptance': 'fail', 'runtime_calls': 0, 'document_kind': document_kind,
        'task_outcome': 'not_assessed', 'conformity': 'not_assessed'}
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
        from .intake_jobs import claim_job, complete_job
        from .intake_model_boundary import build_analysis_prompt, decode_analysis_response
        from .intake_facts_to_conducted_plan import build_conducted_plan_from_intake_facts
        from .intake_plan_virtual_execution import run_intake_plan_virtual_execution
        from .conducted_execution_result_finalizer import finalize_conducted_execution_result
        from .ui_read_model import IntakeReadModel

        run_uuid = uuid.uuid4().hex
        product = ['product_type: smartphone', 'model: SM-A176U', 'market: US',
                   'purpose: Wi-Fi 2.4 GHz conducted engineering simulation']
        condition = ['Condition SYN-WIFI24-CH1; authored synthetic engineering condition.', _CONDUCTED_RF_QUOTE]
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
        respond(store, 'CW-PROCEED-' + run_uuid, 'proceed', intake_id=intake_id)
        phase = 'strict_scripted_analysis'
        job = claim_job(store, 'conducted-MOCK-' + run_uuid, synthetic_only=True)
        if job is None or job['intake_id'] != intake_id:
            raise ValueError('conducted_workflow_claim_mismatch')
        context = {key: job[key] for key in ('job_id', 'intake_id', 'revision', 'synthetic',
                   'documents', 'analysis_context_id', 'analysis_contract', 'instructions')}
        prompt = build_analysis_prompt(context, producer_name=_CONDUCTED_MOCK_NAME)
        raw = canonical(_scripted_pdf_analysis(context)).encode('utf-8')
        _conducted_json(output, 'analysis-context-original.json', context)
        _conducted_json(output, 'analysis-prompt.json', prompt)
        _conducted_write(output, 'analysis-MOCK-original.json', raw)
        analysis = decode_analysis_response(raw, context, producer_name=_CONDUCTED_MOCK_NAME)
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
        summary.update(intake_id=intake_id, revision=context['revision'], context_sha256=context_pin,
                       source6_assembly='genuine_cited_intake_facts', mock_model=mock_model)
        if assembled['status'] != 'ready_for_simulation':
            summary.update(status='blocked', reason='conducted_workflow_plan_blocked')
            _conducted_json(output, 'public-summary.json', summary)
            return {'summary': summary, 'workspace': store.root, 'output': output}

        phase = 'compile_authored_mock'
        executable = _compile_conducted_mock(output, compiler)
        project = Path(__file__).resolve().parents[1]
        contract = json.loads((project / 'docs/fcc/codex_first_decision_contract.json').read_bytes())
        schema = contract['response_schema']['literal_utf8'].encode('utf-8')
        if len(schema) != 3052 or sha256(schema).hexdigest() != _CONDUCTED_SCHEMA_SHA:
            raise ValueError('conducted_workflow_schema_unsupported')
        catalog = project / 'virtual_profiles/sm_a176u_unlicensed.json'
        plan = assembled['plan_input']
        phase = 'execute_same_plan'
        execution = run_intake_plan_virtual_execution(context, analysis, plan,
            expected_revision=context['revision'], expected_context_sha256=context_pin,
            expected_plan_input_sha256=sha256(canonical(plan).encode('utf-8')).hexdigest(),
            catalog_path=catalog, catalog_sha256=sha256(catalog.read_bytes()).hexdigest(),
            response_schema_bytes=schema, executable=executable, requested_model=mock_model,
            scenario='normal', evidence_dir=output / 'x', execution_origin='mock_subprocess',
            quantity={'metric': 'on', 'reference_plane': 'sensor_input',
                      'loss_compensation_applied': False, 'loss_compensation_sign': 1})
        _conducted_json(output, 'execution-original.json', execution)
        phase = 'finalize_explicit_measurement'
        finalized = finalize_conducted_execution_result(execution,
            expected_execution_sha256=sha256(canonical(execution).encode('utf-8')).hexdigest(),
            evidence_dir=output / 'x', measurement_ref=measurement_ref,
            workspace_root=output, artifact_name='draft-' + run_uuid[:12])
        _conducted_json(output, 'finalizer-original.json', finalized)
        result, artifact = finalized['result'], finalized['artifact']
        current_after = IntakeReadModel(store.root).current_conducted_plan_context(intake_id)
        current_matches = canonical(current_after) == canonical(current)
        _conducted_json(output, 'current-readonly-after.json', current_after)
        phase = 'bind_readonly_server'
        server_options = {'conducted_plan_preview_inputs': {'intake_id': intake_id,
            'revision': context['revision'], 'source_settings': plan['plan']['source_settings'],
            'basis': plan['plan']['basis_refs'], 'method': method},
            'conducted_result_snapshot': {'intake_id': intake_id, 'revision': context['revision'],
                'expected_current_binding': plan['binding'], 'result': result}}
        _conducted_json(output, 'server-startup-original.json', server_options)
        stored = bool(finalized['status'] == 'stored' and artifact and artifact['storage']['status'] == 'complete')
        recorded = bool(result and result['status'] == 'recorded')
        summary.update(status='stored' if stored else 'held', runtime_calls=1,
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
            if code is None and isinstance(error, ValueError) and str(error).startswith('conducted_workflow_'):
                code = str(error)
            _conducted_json(output, 'failure.json', {'code': code or 'conducted_workflow_incomplete',
                'phase': phase, 'synthetic': True, 'actual_model_calls': 0, 'hardware_verified': False})
        except Exception:
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
    parser.add_argument('--document-kind', choices=['text', 'pdf'], default='text')
    parser.add_argument('--port', type=int, help='After execution, serve the existing intake store on loopback')
    args = parser.parse_args(argv)
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    output = args.output or Path('.local/cw' if args.conducted_workflow else '.local/intake-fixture-check') / uuid.uuid4().hex[:12 if args.conducted_workflow else 32]
    try:
        result = (run_conducted_flow(output, document_kind=args.document_kind,
                  measurement_ref=args.measurement_ref, mock_model=args.mock_model) if args.conducted_workflow
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
