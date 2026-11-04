import json
from pathlib import Path
import socketserver
import threading
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from test_control import Scripted, fixture
from dgm_lab import Co3000, OspSwitch, SocketTransport, InstrumentError, UnsupportedInstrument, scan_positions, PowerSupply
from dgm_lab.transport import Transport, CommunicationError

AXES={'MA1':{'unit':'CM','min':100,'max':400},'DT1':{'unit':'DG','min':0,'max':360}}


class MotionFixture(Transport):
    def __init__(self):
        super().__init__('fixture://co3000',2)
        self.events=[];self.selected=0;self.pos=[100.,0.];self.target=0;self.pol='PH';self.pending=0;self.error=None
    def _write(self,command):
        self.events.append(command);self.command=command
    def _read(self):
        c=self.command
        if self.error==c: return 'E - V'
        if c=='*IDN?': return 'inncoCO3000/SIMULATED/v1.02.60'
        if c=='*OPT?': return 'MA1,DT1,'+','.join(['0']*14)
        if c.startswith('STATUS '):
            i=0 if 'MA1' in c else 1
            if self.pending:
                self.pending-=1
                if self.pending==0: self.pos[self.selected]=self.target
            return f'{"MA1" if i==0 else "DT1"},{int(self.pending>0)},{self.pos[i]} {"CM" if i==0 else "DG"}'+(','+self.pol if i==0 else '')
        if c.startswith('LD ') and c.endswith(' DV'):
            self.selected=int(c.split()[1]);return str(self.selected)
        if c=='LL': return '100'
        if c=='UL': return '400'
        if c=='CL': return '0'
        if c=='WL': return '360'
        if c.startswith('LD ') and c.endswith(' NP'):
            self.target=float(c.split()[1]);return '1'
        if c=='GO': self.pending=3;return '1'
        if c in ('PH','PV'): self.pol=c;return '1'
        if c=='ES': self.pending=0;return '1'
        raise AssertionError('Unmodeled command '+c)
    def _close(self): pass


def controller(io=None,enabled=True):
    io=io or MotionFixture()
    d=Co3000(io,axes=AXES,motion_enabled=enabled,poll_seconds=.01)
    d.identify()
    return io,d


class MotionTests(unittest.TestCase):
    def test_identify_does_not_select_or_move(self):
        io,d=controller()
        self.assertEqual(io.events,['*IDN?','*OPT?'])
    def test_profile_and_precision_reject_before_commands(self):
        io,d=controller();io.events.clear()
        for axis,value in [('DT1',361),('DT1',True),('DT1',10.01),('MA1',99),('MA2',200)]:
            with self.assertRaises(ValueError): d.move(axis,value)
        self.assertEqual(io.events,[])
    def test_disabled_profile_cannot_move(self):
        io,d=controller(enabled=False);io.events.clear()
        with self.assertRaises(InstrumentError): d.move('DT1',90)
        self.assertEqual(io.events,[])
    def test_move_waits_for_actual_target_and_stops(self):
        io,d=controller();state=d.move('DT1',90,timeout=2)
        self.assertEqual(state.value,90)
        self.assertIn('LD 90.0 DG NP',io.events)
        self.assertEqual(io.events[-1],'ES')
    def test_polarization(self):
        io,d=controller();state=d.polarize('MA1','V',timeout=2)
        self.assertEqual(state.polarization,'PV')
        self.assertEqual(io.events[-1],'ES')
    def test_timeout_when_idle_but_not_at_target(self):
        io,d=controller()
        with self.assertRaises(TimeoutError): d.move('DT1',90,timeout=.02)
        self.assertEqual(io.events[-1],'ES')
    def test_cancel_attempts_stop(self):
        io,d=controller()
        with self.assertRaises(InterruptedError): d.move('DT1',90,cancelled=lambda:True)
        self.assertEqual(io.events[-1],'ES')
    def test_start_error_attempts_stop(self):
        io,d=controller();io.error='GO'
        with self.assertRaisesRegex(InstrumentError,'E - V'): d.move('DT1',90)
        self.assertEqual(io.events[-1],'ES')
    def test_readback_wrong_axis_or_unit_rejected(self):
        for reply in ('DT1,0,100 CM','MA1,0,0 DG','DT1,2,0 DG','DT1,0,nan DG'):
            io,d=controller();d.io=Scripted({'STATUS DT1 ?':reply})
            with self.assertRaises(InstrumentError): d.position('DT1')
    def test_old_firmware_or_missing_axis_rejected(self):
        for raw in ('OTHER/S/1.02.60','inncoCO3000/S/1.02.20'):
            d=Co3000(Scripted({'*IDN?':raw}),axes=AXES)
            with self.assertRaises(UnsupportedInstrument): d.identify()
        d=Co3000(Scripted({'*IDN?':'inncoCO3000/S/1.02.60','*OPT?':','.join(['0']*16)}),axes=AXES)
        with self.assertRaises(UnsupportedInstrument): d.identify()
    def test_scan_records_measured_positions_and_returns_peak(self):
        io,d=controller()
        result=scan_positions(d,'DT1',[0,90,180],lambda:10-abs(io.pos[1]-90),timeout=2)
        self.assertEqual(result['peak']['actual'],90)
        self.assertEqual(io.pos[1],90)
        self.assertEqual(len(result['samples']),3)
    def test_scan_bad_measurement_stops_without_result(self):
        io,d=controller()
        with self.assertRaises(InstrumentError): scan_positions(d,'DT1',[0],lambda:float('nan'))
        self.assertEqual(io.events[-1],'ES')
    def test_stop_and_original_error_both_preserved(self):
        io,d=controller();d.io=Scripted({'LD 1 DV':'1','CL':'0','WL':'360','STATUS DT1 ?':'DT1,0,0 DG','LD 90.0 DG NP':'1','GO':'E - D','ES':'E - P'})
        with self.assertRaises(ExceptionGroup) as found: d.move('DT1',90)
        self.assertEqual(len(found.exception.exceptions),2)


@contextmanager
def motion_server(*,bad_ack=False):
    emulator=MotionFixture()
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            while line:=self.rfile.readline():
                command=line.decode('ascii').rstrip('\n')
                emulator._write(command);answer=emulator._read()
                if bad_ack and command=='GO': answer='E - D'
                data=(answer+'\n').encode('ascii')
                self.wfile.write(data[:2]);self.wfile.flush()
                self.wfile.write(data[2:]);self.wfile.flush()
    server=socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield server.server_address,emulator
    finally: server.shutdown();server.server_close();thread.join()


class LocalhostMotionTests(unittest.TestCase):
    def test_tcp_position_move_and_stop(self):
        with motion_server() as (address,emulator):
            with SocketTransport(address[0],address[1],timeout=2) as io:
                _,d=controller(io);result=d.move('DT1',90,timeout=2)
                self.assertEqual(result.value,90)
            self.assertEqual(emulator.events[-1],'ES')
    def test_tcp_device_error_then_stop(self):
        with motion_server(bad_ack=True) as (address,emulator):
            with SocketTransport(address[0],address[1],timeout=2) as io:
                _,d=controller(io)
                with self.assertRaises(InstrumentError): d.move('DT1',90)
            self.assertEqual(emulator.events[-1],'ES')


class SwitchingTests(unittest.TestCase):
    def device(self,reply='1'):
        io=fixture('OSP120','Rohde&Schwarz',**{'ROUT:MOD:CAT?':'"OSP-B101-F01A11"','ROUT:CLOS? (@F01A11(0101))':reply,'ROUT:CLOS? (@F01A11(0001))':'1'})
        d=OspSwitch(io,model='OSP120',modules={'F01A11':'OSP-B101'},paths={'measure':[{'module':'F01A11','relay':1,'state':1}],'safe':[{'module':'F01A11','relay':1,'state':0}]},safe_path='safe',switching_enabled=True)
        d.identify();return io,d
    def test_route_then_safe_state(self):
        io,d=self.device()
        with d.routed('measure'): self.assertTrue(d.matches('measure'))
        self.assertIn('ROUT:CLOS (@F01A11(0001))',io.events)
    def test_mismatch_still_returns_safe_state(self):
        io,d=self.device('0')
        with self.assertRaises(InstrumentError):
            with d.routed('measure'): pass
        self.assertIn('ROUT:CLOS (@F01A11(0001))',io.events)
    def test_osp150_direct_connection_rejected(self):
        with self.assertRaises(UnsupportedInstrument): OspSwitch(None,model='OSP150',modules={},paths={},safe_path='safe')
    def test_unknown_path_no_command(self):
        io,d=self.device();io.events.clear()
        with self.assertRaises(ValueError): d.select('unknown')
        self.assertEqual(io.events,[])


class HctInventoryTests(unittest.TestCase):
    def test_no_date_or_table_column_shift(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'dgm_lab/data/report-2026-instruments.json').read_text(encoding='utf-8'))
        self.assertTrue(all(o['issue_date'].endswith('2026') for r in data for o in r['occurrences']))
        self.assertFalse(any('DUE DATE' in r['model'] for r in data))
        co=next(r for r in data if r['model']=='CO3000')
        self.assertEqual(co['driver'],'Co3000')
        self.assertTrue(any(o['report']=='HCT-RF-2609-FC006' and o['pdf_page']==137 for o in co['occurrences']))
        self.assertTrue(all(not r['physical_verified'] for r in data))
    def test_e3632a_rejects_wrong_range_and_limits(self):
        d=PowerSupply(None,model='E3632A',max_voltage=30,max_current=7)
        for settings in ({'voltage':16,'current_limit':1,'range_name':'P15V'},{'voltage':10,'current_limit':5,'range_name':'P30V'},{'voltage':1,'current_limit':1,'range_name':'P8V'}):
            with self.assertRaises(ValueError): d.configure(**settings)


if __name__=='__main__': unittest.main()
