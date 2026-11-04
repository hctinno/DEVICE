"""Explicit receiver frequency grids, shared by all five radio/facility workflows."""
from dataclasses import asdict
from importlib.resources import files
import json
import math

from dgm_lab.analyzers import EmiReceiver, SpectrumAnalyzer
from dgm_lab.core import number, normalized, scalar
from dgm_lab.detectors import DETECTORS, RECEIVER_RANGES, validate_receiver, verify_readbacks

CONVERSION = 90 + 10 * math.log10(50)
CONFIG_KEYS = {'schema_version', 'device_id', 'model', 'simulation_only', 'site_verified', 'evidence_notes',
               'frequencies_hz', 'detector', 'rbw_hz', 'dwell_seconds', 'attenuation_db', 'filter_type',
               'path_frequency_limits_hz'}


def detector_catalog():
    rows = []
    for model, source in EmiReceiver.MODELS.items():
        ready = model in RECEIVER_RANGES
        rows.append(dict(device_id='EmiReceiver', manufacturer='Rohde & Schwarz', model=model,
                         status='implemented-uncommissioned' if ready else 'reference-only',
                         detectors=list(DETECTORS) if ready else [], source_id=source,
                         physical_verified=False, acquisition='receiver_grid' if ready else None,
                         maximum_hz=RECEIVER_RANGES.get(model), qp_workflow_maximum_hz=1e9 if ready else None,
                         reason='Single bargraph with settings readback; site commissioning required' if ready else
                                'Detector commands documented; verified-grid integration not implemented'))
    for model, (source, _) in SpectrumAnalyzer.MODELS.items():
        documented = model in {'FSW50', 'FSW67', 'ESU8', 'ESU40', 'N9030B', 'N9040B'}
        rows.append(dict(device_id='SpectrumAnalyzer', model=model, source_id=source,
                         manufacturer='Keysight/Agilent' if source.startswith('keysight') else 'Rohde & Schwarz',
                         status='reference-only' if documented else 'unconfirmed', physical_verified=False,
                         detectors=['POS'], acquisition='swept_spectrum',
                         reason='QP/EMI-average options or final measurement documented; not integrated into this swept workflow'
                         if documented else 'QP/average final-measurement dialect/options not reviewed for this workflow',
                         legacy_average='AVER/RMS is not eligible for QP or voltage-average judgment'))
    sources = json.loads(files('dgm_control').joinpath('data/detector-sources.json').read_text(encoding='utf-8'))
    return {'models': rows, 'detectors': dict(DETECTORS), 'physical_verified': False, 'sources': sources,
            'unsupported_by_workflow': ['QP above 1 GHz', 'ambiguous AVER or RMS as voltage-average criterion',
                                        'EPL/FSW/ESU/X-Series verified receiver-grid execution', 'automatic FCC certification'],
            'scope': 'Wrapper support is distinct from physical instrument capability; unknown models are rejected'}


def measurement_template(plan, detector):
    from .evaluation import context
    sweep, paths, _ = context(plan)
    lo, hi = sweep['start_hz'], sweep['stop_hz']
    if detector == 'QP' and hi > 1e9:
        # Explicit low-frequency synthetic fixture; no claim that this is a real emission.
        lo, hi = 30e6, 31e6
    rbw = 200 if hi < 150e3 else 9000 if hi < 30e6 else 120000 if hi <= 1e9 else 1000000
    result = dict(schema_version=1, device_id='EmiReceiver', model='ESW44', simulation_only=True,
                  site_verified=False, evidence_notes='Synthetic frequency grid, not a test standard or site profile',
                  frequencies_hz=[lo, (lo+hi)/2, hi], detector=detector, rbw_hz=rbw,
                  dwell_seconds=1, attenuation_db=20, filter_type='CISPR',
                  path_frequency_limits_hz={p: [9000, 44e9] for p in paths})
    validate_measurement(result, plan, simulated=True)
    return result


def validate_measurement(config, plan, *, simulated, profile=None):
    from .evaluation import context
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS: raise ValueError('Invalid receiver measurement fields')
    if type(config['schema_version']) is not int or config['schema_version'] != 1 or config['device_id'] != 'EmiReceiver':
        raise ValueError('Receiver measurement schema 1 / EmiReceiver required')
    if type(config['simulation_only']) is not bool or config['simulation_only'] != simulated:
        raise ValueError('Receiver measurement execution mode mismatch')
    if type(config['site_verified']) is not bool or (not simulated and not config['site_verified']):
        raise ValueError('Hardware receiver requires commissioned path/setup evidence')
    if not isinstance(config['evidence_notes'], str) or not config['evidence_notes'].strip():
        raise ValueError('Receiver evidence_notes required')
    if config['filter_type'] != 'CISPR': raise ValueError('Only explicit CISPR 6 dB receiver filter implemented')
    frequencies = config['frequencies_hz']
    if not isinstance(frequencies, list) or not 2 <= len(frequencies) <= 101:
        raise ValueError('Receiver grid requires 2..101 explicit frequencies; native API also supports a single frequency')
    maximum = RECEIVER_RANGES.get(config['model'], 0)
    previous = 0
    for hz in frequencies:
        validate_receiver(config['model'], maximum, frequency_hz=hz, **point_arguments(config))
        if hz <= previous: raise ValueError('Receiver frequency grid must strictly increase')
        previous = hz
    _, paths, _ = context(plan)
    limits = config['path_frequency_limits_hz']
    if not isinstance(limits, dict) or set(limits) != set(paths): raise ValueError('Receiver RF path limits must match scan paths')
    for path, bounds in limits.items():
        if not isinstance(bounds, list) or len(bounds) != 2: raise ValueError('Receiver path requires [min,max] Hz')
        low, high = (number(n, 'RF path limit', 0, 1e12) for n in bounds)
        if not low <= frequencies[0] < frequencies[-1] <= high: raise ValueError('Receiver grid outside RF path limits')
        if isinstance(plan, dict):
            base_low, base_high = plan['scan']['path_frequency_limits_hz'][path]
            if not base_low <= frequencies[0] < frequencies[-1] <= base_high:
                raise ValueError('Receiver grid outside commissioned scan RF path')
    if profile is not None:
        from .profiles import require_profile
        require_profile(profile)
        if profile['device_id'] != 'EmiReceiver' or profile['mode'] != 'hardware': raise ValueError('Matching hardware receiver profile required')
        p = profile['config']['parameters']
        if p['model'] != config['model'] or frequencies[-1] > p['max_frequency_hz']:
            raise ValueError('Receiver model/range differs from site profile')
        if config['dwell_seconds'] >= profile['config']['transport'].get('timeout', 10):
            raise ValueError('Receiver transport timeout must exceed dwell duration plus settling margin')
    return {'valid': True, 'model': config['model'], 'detector': config['detector'], 'points': len(frequencies),
            'minimum_acquisition_seconds_per_pose': len(frequencies)*config['dwell_seconds'],
            'physical_verified': False, 'connection_attempted': False}


def point_arguments(config):
    return {k: config[k] for k in ('rbw_hz', 'detector', 'dwell_seconds', 'attenuation_db')}


def measurement_settings(config):
    return {**point_arguments(config), 'acquisition': 'receiver_grid', 'model': config['model'],
            'filter_type': config['filter_type'], 'frequencies_hz': list(config['frequencies_hz']),
            'start_hz': config['frequencies_hz'][0], 'stop_hz': config['frequencies_hz'][-1],
            'points': len(config['frequencies_hz']), 'vbw_hz': None}


def acquire_grid(receiver, config, checkpoint, observation=None):
    points = []
    for index, hz in enumerate(config['frequencies_hz']):
        checkpoint()
        point = asdict(receiver.call('read_verified_level', frequency_hz=hz, **point_arguments(config)))
        if observation is not None: observation({'phase': 'receiver-point', 'frequency_index': index, 'receiver': point})
        points.append(point)
        checkpoint()
    trace = {'frequencies_hz': list(config['frequencies_hz']), 'values_dbm': [p['value']-CONVERSION for p in points],
             'values_dbuv': [p['value'] for p in points], 'utc': points[-1]['utc'], 'identity': points[-1]['identity'],
             'settings': measurement_settings(config), 'raw': [p['raw'] for p in points], 'receiver_points': points}
    validate_trace(trace, config)
    return trace


def validate_trace(trace, config):
    points = trace.get('receiver_points', [])
    if trace['settings'] != measurement_settings(config) or len(points) != len(config['frequencies_hz']):
        raise ValueError('Receiver trace settings/proof count mismatch')
    if list(trace['frequencies_hz']) != config['frequencies_hz'] or len(trace['values_dbm']) != len(points) or len(trace.get('values_dbuv', [])) != len(points):
        raise ValueError('Receiver grid/data length mismatch')
    if trace['identity'] != points[-1]['identity'] or trace['utc'] != points[-1]['utc']:
        raise ValueError('Receiver trace identity/time differs from point evidence')
    for index, (hz, point) in enumerate(zip(config['frequencies_hz'], points)):
        expected = dict(frequency_hz=hz, **point_arguments(config), filter_type='CISPR')
        if point['settings'] != expected or point['unit'] != 'dBuV' or normalized(point['identity']['model']) != normalized(config['model']):
            raise ValueError('Receiver settings/identity/unit proof mismatch')
        for phase in ('before', 'after'): verify_readbacks(point['readbacks'][phase], expected)
        value = scalar(point['raw'])
        if value != point['value'] or value != trace['values_dbuv'][index] or not math.isclose(value-CONVERSION, trace['values_dbm'][index], abs_tol=1e-9):
            raise ValueError('Receiver raw/normalized value mismatch')
