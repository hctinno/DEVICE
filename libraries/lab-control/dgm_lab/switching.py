"""First-generation R&S OSP120/130 with explicit B101/B102 module maps.

OSP150 is a CAN extension, not a directly addressable LAN instrument.
Source: OSP manual 1505.3896.12-17 pp.157-165. No implicit reset/path creation.
"""
import csv
import re
from .core import Scpi, InstrumentError, UnsupportedInstrument, integer, managed_run
from .analyzers import RS


class OspSwitch(Scpi):
    source_id='rs-osp'
    def __init__(self, transport, *, model, modules, paths, safe_path, switching_enabled=False):
        if model not in ('OSP120','OSP130'):
            raise UnsupportedInstrument('Connect to OSP120/130 host; OSP150 is a CAN extension')
        super().__init__(transport,model=model,manufacturers=RS)
        if type(switching_enabled) is not bool:
            raise ValueError('switching_enabled must be bool')
        self.switching_enabled=switching_enabled
        if not isinstance(modules,dict) or not modules:
            raise ValueError('Explicit installed modules required')
        self.modules=dict(modules)
        for name,kind in self.modules.items():
            if not re.fullmatch(r'F0[1-9]A1[123]',name) or kind not in ('OSP-B101','OSP-B102'):
                raise ValueError('Only reviewed B101 SPDT / B102 SP6T modules supported')
        if not isinstance(paths,dict) or safe_path not in paths or not paths:
            raise ValueError('Explicit paths including safe_path required')
        self.paths={}
        for name,settings in paths.items():
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,49}',name):
                raise ValueError('Invalid local path name')
            seen=set();parts=[]
            for entry in settings:
                module=entry['module'];relay=entry['relay'];state=entry['state']
                if module not in self.modules:
                    raise ValueError('Path references unconfigured module')
                kind=self.modules[module]
                integer(relay,'relay',1,6 if kind=='OSP-B101' else 2)
                integer(state,'state',0 if kind=='OSP-B101' else 1,1 if kind=='OSP-B101' else 6)
                if (module,relay) in seen:
                    raise ValueError('Duplicate relay in path')
                seen.add((module,relay));parts.append(f'{module}({state:02d}{relay:02d})')
            if not parts:
                raise ValueError('Empty path')
            self.paths[name]=('(@'+','.join(parts)+')',len(parts),seen)
        self.safe_path=safe_path
        safety_relays=self.paths[safe_path][2]
        # Every named path defines the whole managed relay set, avoiding stale routes.
        if any(value[2]!=safety_relays for value in self.paths.values()):
            raise ValueError('Every path, including safe_path, must define the same relay set')

    def identify(self):
        identity=super().identify()
        try:
            raw=self.io.query('ROUT:MOD:CAT?')
            found=set(next(csv.reader([raw],skipinitialspace=True)))
            for name,kind in self.modules.items():
                if f'{kind}-{name}' not in found:
                    raise UnsupportedInstrument(f'Module missing or wrong type: {kind}-{name}')
        except BaseException:
            self.identity=None
            raise
        return identity

    def _path(self,name):
        if name not in self.paths:
            raise ValueError('Path outside site profile')
        return self.paths[name]

    def matches(self,name):
        self.ready()
        channels,count,_=self._path(name)
        raw=self.io.query(f'ROUT:CLOS? {channels}')
        values=[x.strip() for x in raw.split(',')]
        if len(values)!=count or any(x not in ('0','1') for x in values):
            raise InstrumentError(f'Invalid OSP relay state: {raw!r}')
        return all(x=='1' for x in values)

    def select(self,name):
        channels,_,_=self._path(name)
        self.ready()
        if not self.switching_enabled:
            raise InstrumentError('Site profile has switching_enabled=false')
        with self.io.transaction():
            self.apply([f'ROUT:CLOS {channels}'])
            if not self.matches(name):
                raise InstrumentError(f'OSP relay readback mismatch: {name}')
            self.errors()

    def stop(self):
        """Route to the site's declared safe path. Does not imply RF OFF."""
        self.ready()
        if not self.switching_enabled:
            raise InstrumentError('Site profile has switching_enabled=false')
        channels,_,_=self._path(self.safe_path)
        with self.io.transaction():
            # Attempt cleanup before consulting an already populated error queue.
            self.io.write(f'ROUT:CLOS {channels}')
            self.opc()
            if not self.matches(self.safe_path):
                raise InstrumentError('OSP safe path not confirmed')
            self.errors()

    def routed(self,name):
        self._path(name)
        return managed_run(lambda:self.select(name),self.stop)
