"""E4419B average power, explicit input and installed 8480-series calibration table."""
import re
from .core import Scpi, InstrumentError, integer, number, fmt, scalar, close_enough, switch
from .analyzers import KEYSIGHT


class EpmPowerMeter(Scpi):
    source_id='keysight-e4419b'
    def __init__(self, transport, *, model='E4419B'):
        if model!='E4419B':
            raise ValueError('Only E4419B reviewed')
        super().__init__(transport,model=model,manufacturers=KEYSIGHT)
        self.configured_channel=None

    def configure_average(self, *, frequency_hz, calibration_table, channel=1):
        number(frequency_hz,'frequency_hz',1,1e12)
        integer(channel,'channel',1,2)
        if not isinstance(calibration_table,str) or not re.fullmatch(r'[A-Za-z0-9 _.-]{1,12}',calibration_table):
            raise ValueError('Existing calibration table name required (1..12 ASCII characters)')
        self.configured_channel=None
        with self.io.transaction():
            self.apply(['ABOR1','INIT1:CONT OFF',f'CONF1:POW:AC DEF,DEF,(@{channel})',
                f'SENS{channel}:CORR:CSET1:SEL "{calibration_table}"',f'SENS{channel}:CORR:CSET1:STAT ON',
                f'SENS{channel}:FREQ {fmt(frequency_hz)}','UNIT1:POW DBM','TRIG1:SOUR IMM'])
            selected=self.io.query(f'SENS{channel}:CORR:CSET1:SEL?').strip().strip('"')
            if selected!=calibration_table or not switch(self.io.query(f'SENS{channel}:CORR:CSET1:STAT?')):
                raise InstrumentError('Installed sensor calibration table not confirmed')
            close_enough(scalar(self.io.query(f'SENS{channel}:FREQ?')),frequency_hz,abs_tol=.1)
            if self.io.query('UNIT1:POW?').strip().upper()!='DBM':
                raise InstrumentError('E4419B power unit is not dBm')
            self.errors();self.configured_channel=channel

    def read_power(self):
        if self.configured_channel is None:
            raise InstrumentError('configure_average() must succeed first')
        return self.measure('READ1?','dBm')

    def stop(self):
        self.ready()
        with self.io.transaction():
            for command in ('ABOR1','ABOR2','INIT1:CONT OFF','INIT2:CONT OFF'):
                self.io.write(command)
            self.opc();self.errors()
