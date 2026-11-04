from contextlib import contextmanager
from importlib.resources import files
import json
from . import (SpectrumAnalyzer, EmiReceiver, SignalGenerator, PowerSupply, PSeriesPowerMeter,
               UsbPowerSensor, VectorNetworkAnalyzer, CmwLte, Thermotron8800, EspecController, Hp437B)
from .transport import SocketTransport, VisaTransport, SerialTransport
from .core import UnsupportedInstrument

DRIVERS = {c.__name__: c for c in (SpectrumAnalyzer, EmiReceiver, SignalGenerator, PowerSupply,
           PSeriesPowerMeter, UsbPowerSensor, VectorNetworkAnalyzer, CmwLte, Thermotron8800, EspecController, Hp437B)}


def inventory(query=''):
    data=json.loads(files('dgm_lab').joinpath('data/instruments.json').read_text(encoding='utf-8'))
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
    """Connect + identify only. Use device.emitting()/powering()/connected() for outputs."""
    name=profile.get('driver')
    if name not in DRIVERS:
        raise UnsupportedInstrument(f'No implemented driver {name!r}; review equipment-coverage.csv')
    # Validate constructor/model/limits before opening a resource.
    driver=DRIVERS[name](None, **profile.get('parameters',{}))
    with open_transport(profile['transport'], log) as transport:
        driver.io=transport
        driver.identify()
        yield driver
