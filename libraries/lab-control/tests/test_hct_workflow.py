import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from test_control import ROOT, fixture
from test_motion import controller
from dgm_lab import (EmiReceiver, EpmPowerMeter, InstrumentError, PowerSupply,
                     SignalGenerator, scan_radiated_grid)


def grid():
    return dict(mast_axis='MA1',table_axis='DT1',heights_cm=[100,200],
                angles_deg=[0,90],polarizations=['H','V'],timeout=2)


class GridTests(unittest.TestCase):
    def test_two_axes_polarization_peak_return(self):
        io,d=controller()
        def measure(): return io.pos[0]+io.pos[1]+(1000 if io.pol=='PV' else 0)
        result=scan_radiated_grid(d,measure=measure,unit='dBuV',**grid())
        self.assertEqual(len(result['samples']),8)
        self.assertEqual(result['peak'],dict(height_cm=200.,angle_deg=90.,polarization='V',reading=1290.,unit='dBuV'))
        self.assertEqual(io.pos,[200.,90.]);self.assertEqual(io.pol,'PV')
        self.assertEqual(io.events[-1],'ES')

    def test_cancel_before_start_does_not_move(self):
        io,d=controller();io.events.clear()
        with self.assertRaises(InterruptedError):
            scan_radiated_grid(d,measure=lambda:1,unit='dBuV',cancelled=lambda:True,**grid())
        self.assertEqual(set(io.events),{'ES'})

    def test_measurement_motion_or_nan_invalidates_run(self):
        for wrong_position in (False,True):
            io,d=controller()
            def bad_reading():
                if wrong_position: io.pos[0]=300;return 1
                return float('nan')
            with self.assertRaises(InstrumentError):
                scan_radiated_grid(d,measure=bad_reading,unit='dBuV',**grid())
            self.assertEqual(io.events[-1],'ES')

    def test_bad_grid_has_zero_io(self):
        io,d=controller();io.events.clear()
        for bad in (dict(heights_cm=[99]),dict(polarizations=['Z']),dict(angles_deg=[])):
            with self.assertRaises(ValueError):
                scan_radiated_grid(d,measure=lambda:1,unit='dBuV',**(grid()|bad))
        self.assertEqual(io.events,[])


class HctInstrumentTests(unittest.TestCase):
    def test_epm_input_b_table_power_and_stop(self):
        io=fixture('E4419B',**{'SENS2:CORR:CSET1:SEL?':'"8481A_SITE"',
            'SENS2:CORR:CSET1:STAT?':'1','SENS2:FREQ?':'1e9','UNIT1:POW?':'DBM','READ1?':'-20.5'})
        d=EpmPowerMeter(io);d.identify()
        d.configure_average(frequency_hz=1e9,calibration_table='8481A_SITE',channel=2)
        self.assertEqual(d.read_power().value,-20.5)
        self.assertIn('CONF1:POW:AC DEF,DEF,(@2)',io.events)
        d.stop();self.assertIn('ABOR2',io.events)
        io.responses['SENS2:CORR:CSET1:SEL?']='"OTHER"'
        with self.assertRaises(InstrumentError):
            d.configure_average(frequency_hz=1e9,calibration_table='8481A_SITE',channel=2)
        with self.assertRaises(InstrumentError): d.read_power()

    def test_hct_supplies_on_off_and_ranges(self):
        for model,range_name in (('E3632A','P15V'),('E3632A','P30V'),('6674A',None)):
            io=fixture(model,**{'OUTP?':['0','1','0'],'VOLT?':'5','CURR?':'1'})
            d=PowerSupply(io,model=model,max_voltage=30,max_current=4);d.identify()
            d.configure(voltage=5,current_limit=1,range_name=range_name)
            with d.powering(): pass
            self.assertEqual(io.events.count('OUTP OFF'),2)
            if range_name: self.assertIn('VOLT:RANG '+range_name,io.events)
        with self.assertRaises(ValueError): PowerSupply(None,model='6674A',max_voltage=61,max_current=1)
        with self.assertRaises(ValueError): PowerSupply(None,model='6674A',max_voltage=30,max_current=36)

    def test_sar_generators_native_cw_and_off(self):
        for model in ('E8267D','E4421B','E4433B'):
            io=fixture(model,'Hewlett-Packard',**{'OUTP?':['0','1','0'],
                'SOUR:FREQ:CW?':'1e9','SOUR:POW?':'-30'})
            d=SignalGenerator(io,model=model,max_frequency_hz=2e9,max_power_dbm=-20);d.identify()
            d.configure_cw(frequency_hz=1e9,power_dbm=-30)
            with d.emitting(): pass
            self.assertIn('OUTP:MOD OFF',io.events)
            self.assertEqual(io.events.count('OUTP OFF'),2)

    def test_qualified_reports_sources_and_nr_continuity(self):
        reports=json.loads((ROOT/'research/hct-report-review.json').read_text(encoding='utf-8'))
        accepted=[r for r in reports if r['included']]
        self.assertEqual(len(accepted),16)
        self.assertEqual(len({r['report_candidate'] for r in accepted}),12)
        self.assertTrue(all(r['issue_date_verified'] and r['issue_date'].endswith('2026') for r in accepted))
        self.assertTrue(any(not r['included'] and '2025' in (r['issue_date'] or '') for r in reports))
        pages=[p[0] for r in accepted if r['report_candidate']=='HCT-RF-2604-FC051' for p in r['printed_page_numbers']]
        self.assertEqual(sorted(pages),list(range(1,372)))
        sources=json.loads((ROOT/'research/source-review.json').read_text(encoding='utf-8'))
        rows=json.loads((ROOT/'dgm_lab/data/hct-2026-instruments.json').read_text(encoding='utf-8'))
        for row in rows:
            if row['status']=='implemented_uncommissioned':
                self.assertIn(row['source_id'],sources)
            for occurrence in row['occurrences']:
                source=next(r for r in accepted if r['id']==occurrence['source_id'])
                self.assertEqual(source['sha256'],occurrence['source_sha256'])
                self.assertLessEqual(occurrence['pdf_page'],source['pages'])


class ExampleTests(unittest.TestCase):
    def test_success_and_stop_failure_exports(self):
        spec=importlib.util.spec_from_file_location('hct_radiated_example',ROOT/'examples/hct_radiated.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for stop_fails in (False,True):
            io,motion=controller()
            receiver_io=fixture('EPL1000','Rohde&Schwarz')
            receiver=EmiReceiver(receiver_io,model='EPL1000',max_frequency_hz=3e9);receiver.identify()
            if stop_fails: receiver.stop=lambda:(_ for _ in ()).throw(InstrumentError('stop fixture failed'))
            @contextmanager
            def fake_connect(profile,log):
                log(dict(fixture=True,profile=profile))
                yield motion if profile=='motion' else receiver
            with tempfile.TemporaryDirectory() as temp:
                job=Path(temp)/'job.json';output=Path(temp)/'result.json'
                job.write_text(json.dumps(dict(motion='motion',receiver='receiver',grid={},measurement={},
                    external_dut_tx_and_shutdown_owner_confirmed=True)),encoding='utf-8')
                with patch.object(sys,'argv',['hct_radiated.py',str(job),str(output),'--execute']), \
                        patch.object(module,'connect',fake_connect), \
                        patch.object(module,'scan_radiated_grid',return_value={'fixture':True}):
                    if stop_fails:
                        with self.assertRaisesRegex(InstrumentError,'stop fixture failed'): module.main()
                    else: module.main()
                self.assertEqual(output.exists(),not stop_fails)
                saved=Path(str(output)+'.failure.json') if stop_fails else output
                result=json.loads(saved.read_text(encoding='utf-8'))
                self.assertEqual('result' in result,not stop_fails)
                self.assertTrue(Path(str(output)+'.traffic.jsonl').read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
