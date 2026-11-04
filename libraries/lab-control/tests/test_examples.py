import importlib.util
import json
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_control import ROOT, fixture
from dgm_lab import SpectrumAnalyzer, Sweep
from dgm_rf import Controller, Profile, ScriptedTransport, WlanTxConfig


class ExampleTests(unittest.TestCase):
    def test_phone_example_exports_success_and_failed_tx_cleanup_log(self):
        spec=importlib.util.spec_from_file_location('phone_spectrum_example',ROOT/'examples/phone_spectrum.py')
        example=importlib.util.module_from_spec(spec);spec.loader.exec_module(example)
        for failed in (False,True):
            with self.subTest(failed=failed),tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)
                profile=Profile.load(ROOT.parent/'samsung-rf/profiles/simulation.json')
                phone=Controller(ScriptedTransport(),profile)
                io=fixture('N9030B',**{'FREQ:STAR?':'1e9','FREQ:STOP?':'2e9','BAND:RES?':'1e6',
                    'BAND:VID?':'3e6','SWE:POIN?':'101','SWE:TIME?':'1','POW:ATT?':'10',
                    'DISP:WIND:TRAC:Y:RLEV?':'-10','UNIT:POW?':'DBM',
                    'TRAC:DATA? TRACE1':'NaN' if failed else ','.join(['-40']*101)})
                analyzer=SpectrumAnalyzer(io,model='N9030B',max_frequency_hz=3e9);analyzer.identify()
                wlan=WlanTxConfig(band=3,bandwidth=9,channel_argument=17,rate=15,antenna=1,gi=5,encoding=1,power='0.0',burst=1000,payload=1000)
                for name,value in [('analyzer',{'parameters':{'max_frequency_hz':3e9}}),
                                   ('wlan',asdict(wlan)),('sweep',asdict(Sweep(1e9,2e9,1e6,3e6,-10,10,101)))]:
                    (path/(name+'.json')).write_text(json.dumps(value),encoding='utf-8')
                @contextmanager
                def analyzer_context(*a,**kw): yield analyzer
                @contextmanager
                def phone_context(*a,**kw): yield phone
                output=path/'result.json'
                args=['example','--analyzer-profile',str(path/'analyzer.json'),'--phone-profile','fixture.json',
                      '--phone-port','COM_FIXTURE','--baudrate','115200','--wlan-config',str(path/'wlan.json'),
                      '--sweep-config',str(path/'sweep.json'),'--output',str(output)]
                with patch.object(example,'connect',analyzer_context),patch.object(example,'samsung_serial',phone_context),patch('sys.argv',args):
                    if failed:
                        with self.assertRaises(Exception): example.main()
                    else: example.main()
                log=json.loads(Path(str(output)+'.phone.json').read_text(encoding='utf-8'))
                self.assertTrue(log)
                self.assertEqual(output.exists(),not failed)
                self.assertIn('ABOR',io.events)
                if not failed:
                    result=json.loads(output.read_text(encoding='utf-8'))
                    self.assertEqual(len(result['trace']['values_dbm']),101)
                    self.assertEqual(result['phone_events'],log)


if __name__=='__main__': unittest.main()
