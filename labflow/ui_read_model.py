"""Read the existing intake contract without initializing or migrating a store."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import hashlib
import re
import sqlite3

from .active_intake import intake_status
from .intake_jobs import notifications
from .virtual_fleet_server import _harness_payload

try:
    from .intake_fixture_jobs import fixture_readiness
except ModuleNotFoundError as exc:
    if exc.name != __package__ + '.intake_fixture_jobs':
        raise
    fixture_readiness = None

_HASH = re.compile(r'[a-f0-9]{64}\Z')
_CODE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')
_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z')


def _text(value, maximum=128):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError('invalid_fixture_text')
    value.encode('utf-8')
    return value


def _hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ValueError('invalid_fixture_hash')
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_fixture_key')
        result[key] = value
    return result


def _public_fixture_record(row, revisions, current_revision, readiness_fingerprint):
    revision = row['revision']
    if type(revision) is not int or revision not in revisions or revision > current_revision:
        raise ValueError('invalid_fixture_revision')
    source = revisions[revision]
    if (row['revision_fingerprint'] != source['fingerprint']
            or row['source_synthetic'] not in (0, 1)
            or row['source_synthetic'] != source['synthetic']):
        raise ValueError('invalid_fixture_source')
    _text(row['request_id'], 150)
    if not _IDENTIFIER.fullmatch(row['request_id']):
        raise ValueError('invalid_fixture_request_id')
    _text(row['recipe_id'])
    _hash(row['readiness_fingerprint'])
    if row['state'] not in {'queued', 'running', 'completed', 'failed', 'uncertain', 'superseded'}:
        raise ValueError('invalid_fixture_state')
    run_id, instance_id = row['run_id'], row['runtime_instance_id']
    if (run_id is None) != (instance_id is None):
        raise ValueError('invalid_fixture_identity')
    if run_id is not None:
        _text(run_id)
        _text(instance_id)
    if row['state'] in {'running', 'completed', 'uncertain'} and run_id is None:
        raise ValueError('missing_fixture_identity')
    if row['error_code'] is not None and (type(row['error_code']) is not str or not _CODE.fullmatch(row['error_code'])):
        raise ValueError('invalid_fixture_error')
    report = None
    if row['result_json'] is not None:
        raw = row['result_json']
        if type(raw) is not str or len(raw.encode('utf-8')) > 280 * 1024:
            raise ValueError('fixture_result_too_large')
        result = json.loads(raw, object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_fixture_json')))
        if type(result) is not dict or set(result) != {'report', 'artifacts'}:
            raise ValueError('invalid_fixture_result')
        report = json.loads(_harness_payload(result['report']))['report']
        if (report is None or report['run_id'] != run_id or report['runtime_instance_id'] != instance_id
                or row['state'] in {'queued', 'running'}):
            raise ValueError('invalid_fixture_report_binding')
        artifacts = result['artifacts']
        if type(artifacts) is not list or len(artifacts) != 2:
            raise ValueError('invalid_fixture_artifacts')
        kinds = set()
        for artifact in artifacts:
            if type(artifact) is not dict or set(artifact) != {'kind', 'artifact_id', 'sha256', 'bytes'}:
                raise ValueError('invalid_fixture_artifact')
            kind = artifact['kind']
            if type(kind) is not str or kind not in {'result', 'operator_journal'} or kind in kinds:
                raise ValueError('invalid_fixture_artifact_kind')
            kinds.add(kind)
            if artifact['artifact_id'] != 'blob:' + _hash(artifact['sha256']):
                raise ValueError('invalid_fixture_artifact_identity')
            if type(artifact['bytes']) is not int or not 0 <= artifact['bytes'] <= 9007199254740991:
                raise ValueError('invalid_fixture_artifact_size')
    if row['state'] == 'completed' and report is None:
        raise ValueError('missing_fixture_report')
    return dict(request_id=row['request_id'], intake_id=row['intake_id'], revision=revision,
                readiness_fingerprint=row['readiness_fingerprint'], recipe_id=row['recipe_id'],
                run_id=run_id, runtime_instance_id=instance_id, state=row['state'],
                source_current=revision == current_revision and row['readiness_fingerprint'] == readiness_fingerprint,
                source_synthetic=bool(row['source_synthetic']), synthetic=True, hardware_verified=False,
                ai_model_called=False, resumable=False, case_id=None, plan_id=None,
                error_code=row['error_code'], report=report)


class ReadModelError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code



_RESULT_INVALID = set('acquisition_invalid evidence_context_missing input_limit invalid_evidence journal_header_invalid journal_integrity_invalid journal_invalid journal_limit journal_state_invalid measurement_invalid measurement_path_conflict measurement_stale native_input_invalid observation_clock_regression observation_invalid output_limit plan_basis_invalid plan_binding_invalid plan_binding_mismatch plan_hash_mismatch plan_intake_invalid plan_invalid plan_limit plan_method_invalid plan_verification_invalid receipt_advance_clock receipt_identity_or_clock receipt_invalid report_invalid run_binding_mismatch setup_advance_invalid setup_clock_mismatch setup_duplicate_request setup_hash_mismatch setup_identity_invalid setup_invalid setup_limit setup_receipt_invalid source_metadata_mismatch source_settings_mismatch topology_hash_mismatch topology_invalid'.split())
_RESULT_INCOMPLETE = set('correction_overflow execution_incomplete journal_incomplete measurement_missing measurement_not_referenced measurement_reference_missing path_ambiguous path_configuration_invalid path_configuration_missing path_selection_missing plan_blocked post_setup_configuration setup_failed setup_missing setup_partial unit_conversion_failed unsupported_path_device'.split())
_RESULT_GAP_ONLY = set('correction_basis_invalid correction_basis_missing metric_mismatch'.split())
_RESULT_D1_GAPS = set('native_input_invalid analysis_invalid context_invalid expected_revision_changed_or_invalid expected_context_changed_or_invalid analysis_evidence_invalid conflicting_intake_fact missing_intake_field follow_up_missing_field product_identity unread_documents uncertain_intake_fact intent_value_not_in_request_quote invalid_source_settings unknown_source_field missing_setting unsupported_modulation invalid_setting invalid_rf_domain invalid_method unknown_method_field unsupported_method_field missing_method_field invalid_basis unknown_basis_field missing_or_invalid_basis unsupported_or_invalid_basis basis_value_mismatch basis_quote_value_mismatch basis_evidence_invalid'.split())
_RESULT_FIELD = re.compile(r'^(?:input|output|plan_input(?:\.(?:binding|gaps|status|verification|intake|plan(?:\.basis_refs)?))?|journal_read(?:\.(?:events|header|integrity))?|setup_snapshot(?:\.[0-9]+)?|topology|run_report|measurement_ref|calculation|observation\.[\s\S]+)$')
_RESULT_REASON = set('provided_revision_changed expected_current_binding_missing expected_intake_mismatch expected_revision_mismatch expected_context_mismatch expected_analysis_context_mismatch expected_analysis_mismatch result_plan_binding_unavailable result_plan_binding_mismatch result_plan_hash_mismatch result_plan_input_hash_mismatch result_report_hash_mismatch result_run_binding_mismatch'.split())


def _result_need(value):
    if not value: raise ReadModelError('intake_conducted_result_invalid')


def _result_keys(value, fields):
    _result_need(type(value) is dict and set(value)==set(fields.split()))


def _result_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def _result_binding(value):
    _result_keys(value,'intake_id revision analysis_context_id context_sha256 analysis_sha256 plan_sha256')
    _result_need(type(value['intake_id']) is str and _IDENTIFIER.fullmatch(value['intake_id']) and type(value['revision']) is int and value['revision']>0)
    for field in ('analysis_context_id','context_sha256','analysis_sha256','plan_sha256'):
        _result_need(type(value[field]) is str and _HASH.fullmatch(value[field]))


def validate_conducted_result_report(value):
    """Shape only, from public412c usage; never import or execute the D3 builder.

    Invalid input copies are deliberately opaque JSON, not normal packet casts.
    Native JSON byte/depth/node limits are enforced at the server boundary.
    """
    need=_result_need;keys=_result_keys
    number=lambda x:type(x) is int or type(x) is float and math.isfinite(x)
    integer=lambda x:type(x) is int and x>=0
    text=lambda x:type(x) is str and bool(x.strip())
    sha=lambda x:type(x) is str and bool(_HASH.fullmatch(x))
    keys(value,'schema_version kind status binding raw_measurement setup_provenance calculation gaps failure verification')
    need(type(value['schema_version']) is int and value['schema_version']==1 and value['kind']=='conducted_twin_result' and value['status'] in ('recorded','incomplete','invalid'))
    status=value['status'];binding=value['binding']
    need(type(binding) is dict and (set(binding) in (set(),{'plan_input','run_report'},set('plan_input run_report plan_input_sha256 setup_sha256 journal_file_sha256 journal_head_sha256 report_sha256 topology_sha256 run_id runtime_instance_id measurement_ref'.split()))))
    if len(binding)==11:
        for key in ('plan_input_sha256','setup_sha256','journal_file_sha256','journal_head_sha256','report_sha256','topology_sha256'):need(sha(binding[key]))
        for key in ('run_id','runtime_instance_id','measurement_ref'):need(text(binding[key]))
    if status!='invalid' and binding:
        plan=binding['plan_input'];keys(plan,'schema_version kind status binding intake plan gaps verification')
        need(type(plan['schema_version']) is int and plan['schema_version']==1 and plan['kind']=='intake_conducted_twin_plan_input' and plan['status'] in ('ready_for_simulation','blocked'))
        keys(plan['verification'],'evidence current_version source_bytes regulatory measurement_prediction execution_authority')
        pv=plan['verification'];need(pv['execution_authority'] is False and pv['current_version']=='caller_snapshot_only' and pv['source_bytes']=='not_reopened' and pv['regulatory']=='not_assessed' and pv['measurement_prediction']=='not_assessed' and pv['evidence']==('validated_in_memory' if plan['status']=='ready_for_simulation' else 'not_validated'))
        if status=='recorded':need(plan['status']=='ready_for_simulation')
    raw=value['raw_measurement']
    if raw is not None:
        keys(raw,'packet event_id sequence device_id tick setup_revision quantity reference_plane');need(type(raw['packet']) is dict and raw['device_id']=='sensor')
    setup=value['setup_provenance'];keys(setup,'records topology path');need(type(setup['path']) is list)
    for edge in setup['path']:
        need(type(edge) is dict and {'source','target','kind'}<=set(edge) and edge['kind']=='rf')
        for side in ('source','target'):
            endpoint=edge[side];need(type(endpoint) is dict and {'device_id','port'}<=set(endpoint) and text(endpoint['device_id']) and text(endpoint['port']))
    calc=value['calculation'];keys(calc,'raw_power_w raw_reference_plane correction_ledger target_reference_plane corrected conformity')
    need(calc['target_reference_plane'] in (None,'source_output'))
    if calc['raw_power_w'] is not None:
        keys(calc['raw_power_w'],'value unit');need(number(calc['raw_power_w']['value']) and calc['raw_power_w']['value']>0 and calc['raw_power_w']['unit']=='W')
    need(type(calc['correction_ledger']) is list)
    for row in calc['correction_ledger']:
        keys(row,'device_id output_port setting loss_db record_index request_id tick setup_revision propagation_db already_applied compensation_db')
        for key in ('device_id','output_port','request_id'):need(text(row[key]))
        need(row['setting'] in ('attenuation_db','loss_db','coupling_db','through_loss_db') and row['already_applied'] is False)
        for key in ('loss_db','propagation_db','compensation_db'):need(number(row[key]))
        for key in ('record_index','tick','setup_revision'):need(integer(row[key]))
    if calc['corrected'] is not None:
        keys(calc['corrected'],'value unit power_w');need(number(calc['corrected']['value']) and calc['corrected']['unit']=='dBm' and number(calc['corrected']['power_w']) and calc['corrected']['power_w']>0)
    keys(calc['conformity'],'status verdict numeric_limit_dbm uncertainty_db')
    need(calc['conformity']==dict(status='not_assessed',verdict=None,numeric_limit_dbm=None,uncertainty_db=None))
    need(type(value['gaps']) is list)
    if status!='invalid':
        for gap in value['gaps']:
            keys(gap,'code field provided blocking');need(type(gap['code']) is str and gap['code'] in (_RESULT_D1_GAPS|_RESULT_INVALID|_RESULT_INCOMPLETE|_RESULT_GAP_ONLY) and text(gap['field']) and type(gap['blocking']) is bool)
            if gap['code'] in _RESULT_D1_GAPS:need(re.fullmatch(r'(?:input|context|analysis|(?:binding|intake)\.[\s\S]+|(?:source_settings|method|basis)(?:\.[\s\S]+)?)',gap['field']))
            else:need(_RESULT_FIELD.fullmatch(gap['field']) or gap['field'] in ('quantity','quantity.metric'))
    failure=value['failure']
    if failure is not None:
        keys(failure,'code field');need(text(failure['field']) and _RESULT_FIELD.fullmatch(failure['field']) and type(failure['code']) is str and failure['code'] in (_RESULT_INVALID if status=='invalid' else _RESULT_INCOMPLETE if status=='incomplete' else set()))
    elif status=='invalid':need(False)
    if status=='recorded':
        need(failure is None and len(binding)==11 and raw is not None and calc['corrected'] is not None)
        need(type(binding['run_report']) is dict and len(binding['run_report'])==15)
        packet=raw['packet'];need(set('status valid value unit frequency_hz power_dbm duty_cycle crest_factor_db acquisition_tick acquisition_setup_revision source_id'.split())<=set(packet))
        need(packet['status']=='ok' and packet['valid'] is True and packet['unit']=='dBm' and packet['source_id']=='sensor')
        for key in ('value','frequency_hz','power_dbm','duty_cycle','crest_factor_db'):need(number(packet[key]))
        for key in ('acquisition_tick','acquisition_setup_revision'):need(integer(packet[key]))
        need(packet['value']==packet['power_dbm'] and text(raw['event_id']) and integer(raw['sequence']) and raw['sequence']>0 and integer(raw['tick']) and integer(raw['setup_revision']))
        keys(raw['quantity'],'metric reference_plane loss_compensation_applied loss_compensation_sign')
        need(raw['quantity']['metric']=='on' and raw['quantity']['reference_plane']=='sensor_input' and raw['quantity']['loss_compensation_applied'] is False and type(raw['quantity']['loss_compensation_sign']) is int and raw['quantity']['loss_compensation_sign']==1)
        need(type(setup['records']) is list and len(setup['records'])<=32 and type(setup['topology']) is dict)
        topology=setup['topology'];need({'devices','connections'}<=set(topology) and type(topology['devices']) is list and type(topology['connections']) is list)
        for node in topology['devices']:need(type(node) is dict and {'id','profile_id'}<=set(node) and text(node['id']) and text(node['profile_id']))
        for edge in topology['connections']:
            need(type(edge) is dict and {'source','target','kind'}<=set(edge) and text(edge['kind']))
            for side in ('source','target'):need(type(edge[side]) is dict and {'device_id','port'}<=set(edge[side]) and text(edge[side]['device_id']) and text(edge[side]['port']))
        need(raw['reference_plane']=='sensor_input' and calc['target_reference_plane']=='source_output')
        for record in setup['records']:
            keys(record,'request_id operation device_id action parameters receipt tick setup_revision')
            need(text(record['request_id']) and record['operation'] in ('execute','advance'))
            for key in ('device_id','action'):need(record[key] is None or text(record[key]))
            for key in ('parameters','receipt'):need(record[key] is None or type(record[key]) is dict)
            for key in ('tick','setup_revision'):need(record[key] is None or integer(record[key]))
    keys(value['verification'],'synthetic hardware_verified physical_verified source_bytes method_approval trust_scope execution_authority')
    need(value['verification']==dict(synthetic=True,hardware_verified=False,physical_verified=False,source_bytes='not_reopened',method_approval='not_assessed',trust_scope='provided_host_snapshots_and_hash_consistency',execution_authority=False))
    # Equality alone would accept 1/0 in place of bool. Check their native types.
    for key in ('synthetic','hardware_verified','physical_verified','execution_authority'):need(type(value['verification'][key]) is bool)
    return value


class _SnapshotStore:
    """Only the connection interface required by the pure service readers."""
    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connection(self):
        yield self._connection


def _current_text_manifest(store,con,row,analysis,current_profile):
    """One deterministic locator, verified against an already retained text graph.

    Schema1 remains unbound to an original provider prompt. Only this current
    read gets the actual retained manifest hash; no preparation/retention runs.
    """
    from pathlib import PurePosixPath
    from . import intake_documents as documents
    from . import intake_generation as generation
    from . import intake_reference_snapshot as retained
    from .intake_analysis import FIELDS,validate_analysis,project_analysis
    from .active_intake import MAX_FILES
    from .store import _open_native
    invalid='intake_conducted_preview_source_invalid'
    unavailable='intake_conducted_preview_analysis_unavailable'
    if row['intake_status']=='upload_incomplete':raise ReadModelError(unavailable)
    if (type(analysis) is not dict or type(analysis.get('schema_version')) is not int
            or analysis['schema_version']!=1):raise ReadModelError(unavailable)
    files=generation._files(row)
    if not files or len(files)>MAX_FILES:raise ReadModelError(unavailable)
    profile=documents._profile();profile_id=retained._hash(profile)
    generation._profile(profile,profile_id)
    if profile_id!=current_profile:raise ReadModelError(invalid)
    binding=documents._binding(files,row['source_id'],row['intake_id'],row['revision'],row['fingerprint'])
    owner=store._existing_binding;held={};graph={}
    def read(sha,limit):
        retained._sha(sha,'source_integrity_invalid')
        if sha not in held:
            path=store.blob_path(sha);before=owner.tree.file_stat(path)
            if before.st_size>limit or before.st_nlink!=1:raise ReadModelError(invalid)
            fd=owner.backend.open_read(path,pin=True)
            info=owner.backend.info(fd,directory=False)
            if _open_native._stamp(info)!=_open_native._stamp(before) or info.st_nlink!=1:
                raise ReadModelError(invalid)
            held[sha]=(path,fd,_open_native._stamp(info))
            graph[sha]=(info.st_size,info.st_mtime_ns,info.st_mode,info.st_dev,info.st_ino)
        path,fd,stamp=held[sha]
        raw=_open_native._read_descriptor(fd,limit,'packet_prepare_source_changed')
        if hashlib.sha256(raw).hexdigest()!=sha:raise ReadModelError(invalid)
        return raw
    remaining=profile['max_total_text_bytes'];expected_documents=[]
    for item in files:
        if (PurePosixPath(item['path']).suffix.lower() not in documents.TEXT_SUFFIXES
                or item['bytes']>min(profile['max_text_bytes'],remaining)):
            raise ReadModelError(unavailable)
        raw=read(item['sha256'],item['bytes'])
        if len(raw)!=item['bytes']:raise ReadModelError(invalid)
        try:text=raw.decode('utf-8-sig')
        except UnicodeError as error:raise ReadModelError(unavailable) from error
        remaining-=len(raw)
        expected_documents.append(dict(item,format='text',text=text,parse_status='text',
            extraction_status='ok' if text.strip() else 'empty',issues=[]))
    candidate=dict(schema_version=1,binding=binding,profile=profile,extraction_profile_id=profile_id,
        documents=expected_documents)
    encoded=retained._encoded(candidate)
    if len(encoded)>profile['max_context_bytes']:raise ReadModelError(unavailable)
    context_id=hashlib.sha256(encoded).hexdigest()
    raw=read(context_id,profile['max_context_bytes'])
    if raw!=encoded:raise ReadModelError(invalid)
    manifest=retained._json(raw.decode('utf-8'),profile['max_context_bytes'],'source_integrity_invalid')
    # The returned documents are decoded from the actual stored blob, never the
    # candidate. Existing validators recheck original bytes without parsing.
    if generation._documents(store,files,manifest['documents'],profile,profile_id)!=0:
        raise ReadModelError(invalid)
    provenance,confirmed=retained._provenance(con,row,graph)
    if not confirmed:raise ReadModelError('intake_conducted_preview_synthetic_required')
    if next(record for record in provenance['blobs'] if record['sha256']==context_id)['kind']!='analysis_context':
        raise ReadModelError(invalid)
    answers=retained._rows(con,'intake_answers',['field','intake_id','value','basis_json','event_id'],
        'intake_id=?',(row['intake_id'],),len(FIELDS),'delegation_invalid')
    questions=retained._rows(con,'intake_questions',['question_key','intake_id','question_json','state','last_revision'],
        'intake_id=?',(row['intake_id'],),10000,'projection_inconsistent')
    for question in questions:
        if type(question['question_key']) is not str or question['state'] not in ('open','resolved'):
            raise ReadModelError(invalid)
        parsed=retained._json(question['question_json'],8*1024**2,'projection_inconsistent')
        if type(parsed) is not dict or parsed.get('key')!=question['question_key']:raise ReadModelError(invalid)
        retained._positive(question['last_revision'],'projection_inconsistent')
        if question['last_revision']>row['revision']:raise ReadModelError(invalid)
    retained._events(con,row['intake_id'],row,answers)
    unread=validate_analysis(analysis,manifest['documents'],True,context_id=context_id)
    projection=project_analysis(analysis,unread,{a['field']:a for a in answers},delegated=bool(row['delegated']),
        deferred=bool(row['deferred']),required_fields=[q['question_key'][8:] for q in questions if q['question_key'].startswith('missing_')])
    projection.update(intake_id=row['intake_id'],revision=row['revision'])
    live=retained._json(row['analysis_json'],8*1024**2,'projection_inconsistent')
    if not retained._same(live,projection):raise ReadModelError(invalid)
    for sha,(path,fd,stamp) in held.items():
        info=owner.backend.info(fd,directory=False);current=owner.tree.file_stat(path)
        if (info.st_nlink!=1 or current.st_nlink!=1 or _open_native._stamp(info)!=stamp
                or _open_native._stamp(current)!=stamp):raise ReadModelError(invalid)
        if hashlib.sha256(_open_native._read_descriptor(fd,graph[sha][0],'packet_prepare_source_changed')).hexdigest()!=sha:
            raise ReadModelError(invalid)
    if documents.current_extraction_profile_id()!=profile_id:raise ReadModelError(invalid)
    owner.check_owner(store);owner.check_identity()
    return manifest,context_id


class IntakeReadModel:
    def __init__(self, workspace):
        self.database = Path(workspace).resolve() / 'lab.sqlite3'

    def current_conducted_plan_context(self, intake_id):
        """Current provided context, never a restored original provider prompt.

        Reuse the existing retained-source/read-transaction validation. No Store
        initializer, claim, parsing preparation, retention or queue mutation runs.
        """
        if type(intake_id) is not str or not _IDENTIFIER.fullmatch(intake_id):
            raise ReadModelError('intake_conducted_preview_invalid_request')
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        from .store import Store
        from . import intake_reference_snapshot as retained
        from .intake_jobs import _analysis_contract
        from .intake_model_boundary import build_analysis_prompt
        first_error=None;native=None
        try:
            try:
                with Store.open_existing(str(self.database.parent)) as store:
                    con=None
                    try:
                        con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
                        con.row_factory = sqlite3.Row
                        con.execute('PRAGMA query_only=ON'); con.execute('BEGIN')
                        eligibility = con.execute('''SELECT i.revision,r.synthetic,s.synthetic AS source_synthetic,j.state
                            FROM intakes i LEFT JOIN intake_revisions r ON r.intake_id=i.intake_id AND r.revision=i.revision
                            LEFT JOIN intake_sources s ON s.source_id=i.source_id
                            LEFT JOIN intake_jobs j ON j.intake_id=i.intake_id AND j.revision=i.revision
                            WHERE i.intake_id=?''', (intake_id,)).fetchone()
                        if eligibility is None:
                            raise ReadModelError('intake_not_found')
                        if eligibility['synthetic'] != 1 or eligibility['source_synthetic'] != 1:
                            raise ReadModelError('intake_conducted_preview_synthetic_required')
                        if eligibility['state'] != 'completed':
                            raise ReadModelError('intake_conducted_preview_analysis_unavailable')
                        capture = retained.capture_intake_reference_snapshot_in_transaction(store,con,intake_id)
                        row = retained._origin(con,intake_id)
                        result = retained._json(row['result_json'],8*1024**2,'source_integrity_invalid')
                        analysis = result['submission']
                        if capture['status'] == 'unavailable':
                            if capture['reason_codes']==['legacy_analysis']:
                                manifest,context_id=_current_text_manifest(store,con,row,analysis,capture['profile']['current_profile_id'])
                            else:
                                reason = ('v2_pdf_required' if 'no_pdf_context' in capture['reason_codes'] else 'analysis_unavailable')
                                raise ReadModelError('intake_conducted_preview_' + reason)
                        else:
                            if 'source_provenance_unconfirmed' in capture['readiness']['reason_codes']:
                                raise ReadModelError('intake_conducted_preview_synthetic_required')
                            if not capture['profile']['matches']:
                                raise ReadModelError('intake_conducted_preview_source_invalid')
                            # Keep the PDF capture and retained graph validation.
                            files, manifest, _, _ = retained._graph(store,row,analysis)
                            context_id=analysis['context_id']
                        context = dict(job_id=row['job_id'],intake_id=intake_id,revision=row['revision'],synthetic=True,
                            documents=manifest['documents'],analysis_context_id=context_id,
                            analysis_contract=_analysis_contract({'documents':manifest['documents'],'context_id':context_id}),
                            instructions='Current provided read-only synthetic planning context. This is not an original model prompt and grants no execution authority.')
                        prompt = build_analysis_prompt(context,producer_name='current-readonly-plan')
                        native={'context':json.loads(prompt['messages'][1]['content']),'analysis':analysis}
                    except BaseException as error:
                        first_error=error
                    finally:
                        if con is not None:
                            try:con.close()
                            except BaseException as error:
                                if first_error is None:first_error=error
            except BaseException as error:
                if first_error is None:first_error=error
            if first_error is not None:raise first_error
            return native
        except ReadModelError:
            raise
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except (OSError,ValueError,TypeError,KeyError,IndexError,UnicodeError,RecursionError,OverflowError) as exc:
            raise ReadModelError('intake_conducted_preview_source_invalid') from exc

    def conducted_plan_preview(self, intake_id, selection=None):
        native = self.current_conducted_plan_context(intake_id)
        context, analysis = native['context'], native['analysis']
        raw = json.dumps(context,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
        import hashlib
        context_sha = hashlib.sha256(raw).hexdigest()
        status = ('not_provided' if selection is None else 'other_intake' if selection['intake_id'] != intake_id
                  else 'revision_changed' if selection['revision'] != context['revision'] else 'matched')
        provided = selection if status == 'matched' else {}
        from .intake_conducted_twin_plan import build_conducted_twin_plan_input
        report = build_conducted_twin_plan_input(context,analysis,expected_revision=context['revision'],
            expected_context_sha256=context_sha,source_settings=provided.get('source_settings',{}),
            basis=provided.get('basis',{}),method=provided.get('method',{}))
        return dict(schema_version=1,kind='intake_conducted_plan_preview',intake_id=intake_id,revision=context['revision'],
            context_sha256=context_sha,context_scope='current_provided_context',selection_status=status,plan_input=report)


    def conducted_result_view(self, intake_id, snapshot=None):
        if snapshot is None: raise ReadModelError('intake_conducted_result_missing')
        if snapshot['intake_id']!=intake_id: raise ReadModelError('intake_conducted_result_unavailable')
        report=validate_conducted_result_report(snapshot['result'])
        native=self.current_conducted_plan_context(intake_id);context=native['context'];context_sha=_result_hash(context)
        expected=snapshot['expected_current_binding'];reasons=[]
        if snapshot['revision']!=context['revision']:reasons.append('provided_revision_changed')
        if expected is None:reasons.append('expected_current_binding_missing')
        else:
            _result_binding(expected)
            checks={'intake_id':('expected_intake_mismatch',intake_id),'revision':('expected_revision_mismatch',context['revision']),'context_sha256':('expected_context_mismatch',context_sha),'analysis_context_id':('expected_analysis_context_mismatch',context['analysis_context_id']),'analysis_sha256':('expected_analysis_mismatch',_result_hash(native['analysis']))}
            for key,(reason,current) in checks.items():
                if expected[key]!=current:reasons.append(reason)
        binding=report['binding'];plan=binding.get('plan_input');plan_binding=plan.get('binding') if type(plan) is dict else None
        try:_result_binding(plan_binding)
        except ReadModelError:reasons.append('result_plan_binding_unavailable')
        else:
            if expected is not None and plan_binding!=expected:reasons.append('result_plan_binding_mismatch')
            if type(plan.get('plan')) is not dict or _result_hash(plan['plan'])!=plan_binding['plan_sha256']:reasons.append('result_plan_hash_mismatch')
        if len(binding)==11:
            if _result_hash(plan)!=binding['plan_input_sha256']:reasons.append('result_plan_input_hash_mismatch')
            if _result_hash(binding['run_report'])!=binding['report_sha256']:reasons.append('result_report_hash_mismatch')
            run=binding['run_report']
            if type(run) is not dict or run.get('run_id')!=binding['run_id'] or run.get('runtime_instance_id')!=binding['runtime_instance_id']:reasons.append('result_run_binding_mismatch')
        return json.loads(json.dumps(dict(schema_version=1,kind='intake_conducted_result_view',intake_id=intake_id,revision=context['revision'],context_sha256=context_sha,source_kind='provided_snapshot',expected_current_binding=expected,relation=dict(status='blocked' if reasons else 'matched',reasons=reasons,provided_revision=snapshot['revision']),result=report),ensure_ascii=False,allow_nan=False))

    def fixture_runs(self, intake_id):
        """One pure read transaction; no queue claim, blob resolver or evaluator."""
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        con = None
        try:
            con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            intake = con.execute('SELECT revision FROM intakes WHERE intake_id=?', (intake_id,)).fetchone()
            if intake is None:
                raise ReadModelError('intake_not_found')
            revision = intake['revision']
            if type(revision) is not int or revision < 1:
                raise ValueError('invalid_current_revision')
            payload = dict(schema_version=1, intake_id=intake_id, current_revision=revision,
                           storage_available=False, records=[], more_available=False)
            table = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intake_fixture_jobs'").fetchone()
            if table is None or fixture_readiness is None:
                return payload
            readiness = fixture_readiness(_SnapshotStore(con), intake_id)
            if readiness['intake_id'] != intake_id or readiness['revision'] != revision:
                raise ValueError('invalid_current_readiness')
            fingerprint = _hash(readiness['readiness_fingerprint'])
            revisions = {r['revision']: r for r in con.execute(
                'SELECT revision,fingerprint,synthetic FROM intake_revisions WHERE intake_id=?', (intake_id,))}
            rows = con.execute('''SELECT request_id,intake_id,revision,readiness_fingerprint,
                revision_fingerprint,recipe_id,run_id,runtime_instance_id,state,source_synthetic,
                error_code,result_json FROM intake_fixture_jobs WHERE intake_id=?
                ORDER BY created_at DESC,request_id DESC LIMIT 21''', (intake_id,)).fetchall()
            payload.update(storage_available=True, more_available=len(rows) > 20,
                           records=[_public_fixture_record(row, revisions, revision, fingerprint) for row in rows[:20]])
            return payload
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError, OverflowError) as exc:
            raise ReadModelError('state_invalid') from exc
        finally:
            if con is not None:
                con.close()

    def snapshot(self, intake_id=None):
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        con = None
        try:
            con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            store = _SnapshotStore(con)
            records = intake_status(store, intake_id)
            notices = notifications(store)
            result = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat()}
            if intake_id is None:
                result['intakes'] = records
            else:
                result['intake'] = records
                notices = [n for n in notices if n['intake_id'] == intake_id]
            result['notifications'] = notices
            return result
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except ValueError as exc:
            # Service readers distinguish a missing ID before decoding its state.
            code = 'intake_not_found' if str(exc) == 'Unknown intake' else 'state_invalid'
            raise ReadModelError(code) from exc
        except (TypeError, KeyError, IndexError) as exc:
            raise ReadModelError('state_invalid') from exc
        finally:
            if con is not None:
                con.close()
