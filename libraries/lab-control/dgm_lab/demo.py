"""Hardware-free executable integration example. All values explicitly simulated.

Uses production OdaEx lifecycle and measurement parsing with a small in-memory
protocol peer. Never opens a socket, VISA resource or serial port.
"""
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from .core import InstrumentError
from .oda import OdaEx
from .transport import Transport, JsonlLog


class DemoPowerSupply(Transport):
    def __init__(self, *, log=None, inject_failure=False):
        super().__init__('simulation://oda-ex-no-hardware', log=log)
        self.output = False
        self.voltage = 0.0
        self.current = 0.0
        self.reply = None
        self.inject_failure = inject_failure

    def _write(self, command):
        fixed = {'*IDN?':'ODA Technologies,EX-Series,SIMULATION', '*SN?':'SIMULATION-ONLY',
                 'SYST:ERR?':'0,"No error"', 'VOLT:OVP:TRIP?':'0', 'CURR:OCP:TRIP?':'0',
                 'VOLT:UVL?':'0', 'VOLT:OVL?':'60', 'CURR:UCL?':'0', 'CURR:OCL?':'40'}
        self.reply = None
        if command in fixed: self.reply = fixed[command]
        elif command == 'OUTP?': self.reply = str(int(self.output))
        elif command == 'VOLT?': self.reply = str(self.voltage)
        elif command == 'CURR?': self.reply = str(self.current)
        elif command == 'OUTP ON': self.output = True
        elif command == 'OUTP OFF': self.output = False
        elif command.startswith('APPL '):
            if self.output: raise InstrumentError('Demo peer refuses live reconfiguration')
            self.voltage, self.current = map(float, command[5:].split(','))
        elif command == 'MEAS:VOLT?':
            self.reply = 'NaN' if self.inject_failure else str(self.voltage - 0.01 if self.output else 0)
        elif command == 'MEAS:CURR?': self.reply = str(self.current * 0.8 if self.output else 0)
        else: raise InstrumentError(f'Unsupported demo command: {command!r}')

    def _read(self):
        if self.reply is None: raise InstrumentError('Demo query had no response')
        return self.reply

    def _close(self):
        pass  # deliberately does NOT turn off the simulated output


def run_demo(output_dir, *, inject_failure=False):
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=False)  # preserve previous evidence
    run_id = str(uuid.uuid4())
    result = dict(schema_version=1, run_id=run_id, simulated=True, physical_verified=False,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  requested=dict(voltage=5.0,current=1.0), measurements=[])
    with closing(JsonlLog(target/'traffic.jsonl')) as log:
        with DemoPowerSupply(log=log, inject_failure=inject_failure) as io:
            device = OdaEx(io, expected_serial='SIMULATION-ONLY', expected_firmware='SIMULATION',
                           max_voltage=5, max_current=1, installed_model_confirmed=True)
            try:
                result['identity'] = asdict(device.identify())
                device.configure(**result['requested'])
                with device.powering():
                    result['measurements'] = [asdict(device.read_voltage()),asdict(device.read_current())]
                result['status'] = 'completed'
            except BaseException as exc:
                result['status'] = 'failed'
                result['error'] = f'{type(exc).__name__}: {exc}'
                result['measurements'] = []
                raise
            finally:
                result['simulated_output_off'] = not io.output
                result['finished_utc'] = datetime.now(timezone.utc).isoformat()
                filename = 'result.json' if result.get('status') == 'completed' else 'failure.json'
                (target/filename).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
