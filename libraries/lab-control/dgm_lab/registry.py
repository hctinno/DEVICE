from contextlib import contextmanager
from importlib.resources import files
import json
from . import (SpectrumAnalyzer, EmiReceiver, SignalGenerator, PowerSupply, PSeriesPowerMeter,
               UsbPowerSensor, VectorNetworkAnalyzer, CmwLte, Thermotron8800, EspecController, Hp437B, Co3000, OspSwitch, EpmPowerMeter, OdaEx, Cmu200Cw)
from .transport import SocketTransport, VisaTransport, SerialTransport
from .core import UnsupportedInstrument

DRIVERS = {c.__name__: c for c in (SpectrumAnalyzer, EmiReceiver, SignalGenerator, PowerSupply,
           PSeriesPowerMeter, UsbPowerSensor, VectorNetworkAnalyzer, CmwLte, Thermotron8800, EspecController, Hp437B, Co3000, OspSwitch, EpmPowerMeter, OdaEx, Cmu200Cw)}


def inventory(query='', *, scope='legacy'):
    if scope not in ('legacy','hct-2026'):
        raise ValueError('scope must be legacy or hct-2026')
    filename='hct-2026-instruments.json' if scope=='hct-2026' else 'instruments.json'
    data=json.loads(files('dgm_lab').joinpath('data/'+filename).read_text(encoding='utf-8'))
    key=query.casefold()
    return [r for r in data if key in (r['manufacturer']+' '+r['model']+' '+r['status']+' '+r['driver']).casefold()]


def open_transport(config, log=None):
    options=dict(config)
    kind=options.pop('kind')
    for key in ('termination',):
        if key in options and kind in ('tcp','serial'):
            options[key]=options[key].encode('ascii')
    cls={'tcp':SocketTransport,'visa':VisaTransport,'serial':SerialTransport}.get(kind)
    if cls is None:
        raise ValueError('transport.kind must be tcp, visa, or serial')
    return cls(**options, log=log)


@contextmanager
def connect(profile, *, log=None):
    """Connect + identify. Remote entry may affect state (notably CMU200).

    Use device.emitting()/powering()/connected() for owned outputs.
    Closing the transport alone never promises output shutdown.
    """
    from .capabilities import validate_profile
    validate_profile(profile)
    name=profile.get('driver')
    if name not in DRIVERS:
        raise UnsupportedInstrument(f'No implemented driver {name!r}; review equipment-coverage.csv')
    # Validate constructor/model/limits before opening a resource.
    driver=DRIVERS[name](None, **profile.get('parameters',{}))
    with open_transport(profile['transport'], log) as transport:
        driver.io=transport
        driver.identify()
        yield driver
