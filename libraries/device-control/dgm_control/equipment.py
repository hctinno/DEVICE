"""Bounded JSON operations on reviewed native drivers, with durable evidence.

No arbitrary SCPI, Python, transport discovery, retries or regulatory judgment.
"""
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import uuid
import time

from .catalog import devices, describe, profile_template, UnsupportedDevice
from .profiles import require_profile
from .session import open_device
from .errors import error_details


def equipment_catalog():
    from importlib.resources import files
    extensions=json.loads(files('dgm_lab').joinpath('data/model-expansion.json').read_text(encoding='utf-8'))
    return dict(devices=[r for r in devices() if r['backend'] == 'dgm_lab'], physical_verified=False,
                extensions=extensions,extension_role_model_count=len(extensions),extension_distinct_model_names=len({r['model'] for r in extensions}),
                scope='Per-model capabilities and site limits; simulator support is separate from physical commissioning')


def equipment_template(device_id, model=None, *, mode='simulation'):
    profile = deepcopy(profile_template(device_id, mode))
    row = describe(device_id)
    known = {m['model'] for m in row.get('models',[])}
    if model is not None:
        if model not in known: raise ValueError('Model is not in the reviewed device-role catalog')
        profile['config']['parameters']['model'] = model
    model = profile['config']['parameters'].get('model')
    p = profile['config']['parameters']
    if mode == 'simulation' and device_id == 'PowerSupply' and model == '6674A': p.update(max_voltage=5,max_current=.1)
    setup, active = [], {}
    step = lambda op, **args: dict(operation=op,arguments=args)
    if device_id == 'SpectrumAnalyzer':
        steps = [step('acquire', config=dict(start_hz=100e6,stop_hz=101e6,rbw_hz=100000,vbw_hz=300000,
                      reference_dbm=0,attenuation_db=20,points=101,detector='POS',sweep_seconds=.1))]
    elif device_id == 'EmiReceiver':
        steps = [step('read_verified_level',frequency_hz=100e6,rbw_hz=120000,detector='QP',dwell_seconds=1,attenuation_db=20)]
        if model=='EPL1000': steps[0]['arguments'].update(frequency_hz=13.56e6,rbw_hz=9000)
    elif device_id == 'SignalGenerator':
        setup = [step('configure_cw',frequency_hz=100e6,power_dbm=-30)]
        steps = []  # start and verified stop are owned by active(), never a raw command
    elif device_id == 'PowerSupply':
        from dgm_lab.model_scope import SUPPLY_RANGES
        args = dict(voltage=1,current_limit=.05)
        if model in SUPPLY_RANGES: args['range_name'] = next(iter(SUPPLY_RANGES[model]))
        elif model == 'E3632A': args['range_name'] = 'P15V'
        setup = [step('configure',**args)]
        steps = [step('read_voltage'), step('read_current')]
    elif device_id == 'UsbPowerSensor':
        setup = [step('configure_average',frequency_hz=100e6)]
        steps = [step('read_power')]
    elif device_id == 'DigitalMultimeter':
        setup = [step('configure',function='DCV',range_value=10)]
        steps = [step('read')]
    else:
        raise UnsupportedDevice('No generic recipe template; use the documented native API or radio/motion workflow for ' + device_id)
    return dict(schema_version=1,profile=profile,setup=setup,active=active,steps=steps,settle_seconds=0,
                notes='Template requires site review. Synthetic values are not a regulatory method or equipment commissioning.')


def _arguments(device_id, operation, args):
    args = deepcopy(args)
    if device_id == 'SpectrumAnalyzer' and operation == 'acquire':
        from dgm_lab import Sweep
        args['config'] = Sweep(**args['config'])
    elif device_id == 'CmwLte' and operation == 'configure':
        from dgm_rf.cmw_lte import LteRmcConfig
        args['config'] = LteRmcConfig(**args['config'])
    return args


def check_equipment(job):
    from dgm_lab.registry import DRIVERS
    from .session import LIFECYCLES
    if not isinstance(job,dict) or set(job) != {'schema_version','profile','setup','active','steps','notes','settle_seconds'}:
        raise ValueError('Invalid equipment job fields')
    if type(job['schema_version']) is not int or job['schema_version'] != 1: raise ValueError('Equipment schema 1 required')
    from dgm_lab.core import number
    number(job['settle_seconds'],'settle_seconds',0,60)
    row = require_profile(job['profile'])
    if row['backend'] != 'dgm_lab': raise UnsupportedDevice('Use radio-run for smartphone workflows')
    if not isinstance(job['active'],dict) or not isinstance(job['notes'],str): raise ValueError('Invalid equipment scope or notes')
    driver = DRIVERS[row['id']](None, **job['profile']['config']['parameters'])
    lifecycle = getattr(driver, LIFECYCLES[row['id']]) if row['id'] in LIFECYCLES else None
    if lifecycle: inspect.signature(lifecycle).bind(**job['active'])
    elif job['active']: raise ValueError('This driver active scope takes no arguments')
    total = 0
    for phase in ('setup','steps'):
        if not isinstance(job[phase],list): raise ValueError('Equipment phases must be lists')
        for step in job[phase]:
            if not isinstance(step,dict) or set(step) != {'operation','arguments'} or not isinstance(step['arguments'],dict):
                raise ValueError('Each step requires operation and arguments')
            op = step['operation']
            if op not in row['operations'] or op in {'start','stop','stop_all','select'}:
                raise ValueError('Operation must be exposed and lifecycle-owned: ' + str(op))
            if phase == 'setup' and op not in {'configure','configure_cw','configure_average','setpoint'}:
                raise ValueError('Only configuration operations are allowed before active scope')
            inspect.signature(getattr(driver,op)).bind(**_arguments(row['id'],op,step['arguments']))
            total += 1
    if not 1 <= total <= 100: raise ValueError('Equipment job requires 1..100 operations')
    return dict(valid=True,device_id=row['id'],operations=total,connection_attempted=False,physical_verified=False)


def _save(path, value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2)
        f.write('\n')


def _plain(value):
    if is_dataclass(value): return _plain(asdict(value))
    if isinstance(value,complex): return dict(real=value.real,imag=value.imag)
    if isinstance(value,dict): return {k:_plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [_plain(v) for v in value]
    return value


def _traffic_sink(path):
    # Logging errors must fail the run without preventing the next cleanup command.
    from dgm_lab.transport import JsonlLog
    log = JsonlLog(path)
    failures = []
    def emit(record):
        if not failures:
            try: log(record)
            except Exception as exc: failures.append(error_details(exc))
    return log,emit,failures


def run_equipment(job, output_dir, *, cancelled=None, cancel_file=None):
    from dgm_lab.transport import JsonlLog
    job = deepcopy(job)
    check = check_equipment(job)
    target = Path(output_dir)
    target.mkdir(parents=True,exist_ok=False)
    result = dict(run_id=str(uuid.uuid4()),utc=datetime.now(timezone.utc).isoformat(),status='running',
                  device_id=check['device_id'],simulated=job['profile']['mode']=='simulation',physical_verified=False,
                  physical_shutdown_verified=False,fcc_verdict=None,cleanup_scope_succeeded=False,operations_completed=0)
    serialized = json.dumps(job,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')
    result['input_sha256'] = hashlib.sha256(serialized).hexdigest()
    _save(target/'inputs.json',job)
    traffic, sink, log_errors = _traffic_sink(target/'traffic.jsonl')
    def checkpoint():
        if log_errors: raise OSError('Equipment traffic logging failed; see traffic_log_errors')
        if cancelled is not None and cancelled.is_set() or cancel_file and Path(cancel_file).exists():
            raise InterruptedError('Equipment run cancelled at checkpoint')
    def execute(session, phase):
        checkpoint()
        for index, step in enumerate(job[phase]):
            checkpoint()
            value = session.call(step['operation'], **_arguments(check['device_id'],step['operation'],step['arguments']))
            record = dict(phase=phase,index=index,operation=step['operation'],arguments=step['arguments'],
                          utc=datetime.now(timezone.utc).isoformat(),result=_plain(value))
            with (target/'operations.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
            result['operations_completed'] += 1
            checkpoint()
    try:
        checkpoint()
        with open_device(job['profile'],log=sink) as session:
            result['identity'] = session.info
            _save(target/'identity.json',session.info)
            active_attempted = False
            try:
                execute(session,'setup')
                checkpoint()
                active_attempted = True
                with session.active(**job['active']):
                    deadline = time.monotonic()+job['settle_seconds']
                    while time.monotonic()<deadline:
                        checkpoint()
                        time.sleep(min(.05,max(0,deadline-time.monotonic())))
                    execute(session,'steps')
                result['cleanup_scope_succeeded'] = True
                checkpoint()
            except BaseException as primary:
                if not active_attempted:
                    try:
                        session.call('stop_all' if check['device_id']=='Co3000' else 'stop')
                        result['cleanup_scope_succeeded'] = True
                    except BaseException as cleanup:
                        raise BaseExceptionGroup('Equipment operation and cleanup failed',[primary,cleanup]) from None
                raise
        result['status'] = 'completed'
        _save(target/'result.json',result)
    except BaseException as exc:
        result.update(status='cancelled' if isinstance(exc,(InterruptedError,KeyboardInterrupt)) else 'failed',error=error_details(exc))
        if log_errors: result['traffic_log_errors'] = log_errors
        _save(target/'failure.json',result)
    finally:
        traffic.close()
    return result


def probe_equipment(profile, output_dir):
    """IDN and documented option query only. No reset/error-queue drain/stop/test."""
    from dgm_lab.core import Scpi
    from dgm_lab.registry import DRIVERS
    from dgm_lab.transport import JsonlLog
    from dgm_lab.extended_detectors import required_option
    profile = deepcopy(profile)
    row = require_profile(profile)
    if row['backend'] != 'dgm_lab' or DRIVERS[row['id']].identify is not Scpi.identify:
        raise UnsupportedDevice('Read-only probe excludes custom identity/remote-entry protocols; use native commissioning procedure')
    target = Path(output_dir)
    target.mkdir(parents=True,exist_ok=False)
    result = dict(status='running',physical_verified=False,commissioned=False,simulated=profile['mode']=='simulation',
                  query_scope='IDN and final-detector required option only; no RF/input/overload/calibration commissioning')
    _save(target/'inputs.json',profile)
    traffic, sink, log_errors = _traffic_sink(target/'traffic.jsonl')
    try:
        with open_device(profile,log=sink) as session:
            result['identity'] = session.info
            if row['id']=='EmiReceiver':
                option = required_option(profile['config']['parameters']['model'])
                result['required_option'] = option
                if option:
                    raw = session._driver.io.query('*OPT?')
                    result['options_raw'] = raw
                    tokens = {t.strip().strip('"').upper() for t in raw.strip('"').split(',')}
                    result['required_option_present'] = option in tokens
                    if option not in tokens: raise UnsupportedDevice('Required option not confirmed: ' + option)
        if log_errors: raise OSError('Equipment probe traffic logging failed')
        result['status'] = 'identified'
        _save(target/'probe.json',result)
    except BaseException as exc:
        result.update(status='failed',error=error_details(exc))
        if log_errors: result['traffic_log_errors'] = log_errors
        _save(target/'failure.json',result)
    finally:
        traffic.close()
    return result
