"""Offline agent discovery. No address scanning, imports of vendor SDKs or device I/O."""
from importlib.resources import files
import inspect
import json
import re
from .registry import DRIVERS
from .transport import SocketTransport, SerialTransport, VisaTransport, positive_timeout
from .core import UnsupportedInstrument


def capabilities(driver=None):
    rows = json.loads(files('dgm_lab').joinpath('data/capabilities.json').read_text(encoding='utf-8'))
    if driver is not None:
        rows = [r for r in rows if r['driver'] == driver]
        if not rows:
            raise UnsupportedInstrument(f'Unknown driver {driver!r}')
    return rows


def validate_profile(profile):
    """Validate constructor/transport fields only; does NOT commission or identify hardware."""
    if not isinstance(profile, dict): raise ValueError('Profile must be a JSON object')
    name = profile.get('driver')
    if name not in DRIVERS: raise UnsupportedInstrument(f'Unknown driver {name!r}')
    parameters = profile.get('parameters', {})
    if not isinstance(parameters, dict): raise ValueError('parameters must be an object')
    DRIVERS[name](None, **parameters)  # constructors validate without opening a connection
    transport = profile.get('transport')
    if not isinstance(transport, dict): raise ValueError('transport must be an object')
    options = dict(transport)
    kind = options.pop('kind', None)
    cls = {'tcp':SocketTransport, 'serial':SerialTransport, 'visa':VisaTransport}.get(kind)
    if cls is None: raise ValueError('transport.kind must be tcp, serial or visa')
    if 'log' in options: raise ValueError('log is owned by the application, not JSON transport')
    inspect.signature(cls).bind(**options)
    positive_timeout(options.get('timeout', 10))
    address_key = {'tcp':'host', 'serial':'port', 'visa':'resource'}[kind]
    address = options.get(address_key)
    if not isinstance(address, str) or not address.strip() or 'REPLACE' in address.upper():
        raise ValueError('Explicit commissioned ' + address_key + ' required')
    if kind == 'tcp' and (type(options['port']) is not int or not 1 <= options['port'] <= 65535):
        raise ValueError('TCP port must be 1..65535')
    if options.get('termination', '\n') not in ('\n','\r','\r\n'):
        raise ValueError('termination must be LF, CR or CRLF')
    if kind == 'visa' and '::' not in address:
        raise ValueError('Explicit VISA resource required')
    if kind == 'serial':
        if type(options['baudrate']) is not int or options['baudrate'] <= 0:
            raise ValueError('baudrate must be a positive integer')
        if options['parity'] not in ('N','E','O','M','S') or options['bytesize'] not in (5,6,7,8) or options['stopbits'] not in (1,1.5,2):
            raise ValueError('Invalid serial framing')
    if name == 'Cmu200Cw' and (kind == 'tcp' or kind == 'visa' and not address.upper().startswith('GPIB')):
        raise ValueError('CMU profile supports reviewed GPIB/RS232 only; LAN socket is not established')
    if name == 'Cmu200Cw' and kind == 'visa':
        match = re.fullmatch(r'GPIB\d*::(\d{1,2})::INSTR', address.upper())
        if not match or int(match[1]) > 30:
            raise ValueError('Use CMU primary GPIB address only; do not combine hardware and logical secondary addresses')
    return dict(driver=name, offline_valid=True, connection_attempted=False, physical_verified=False,
                remaining=capabilities(name)[0]['site_requirements'])
