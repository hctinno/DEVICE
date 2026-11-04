from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from dgm_rf import *


def profile(**kwargs):
    values=dict(model='SM-S918N',build='S918NKSU1AWC8',argument_domains={
        's23_uwb_timing':{'gap':['2000'],'window':['750'],'packets':['1000']},
        's23_uwb_tx':{'value':['0','128']}})
    values.update(kwargs)
    return Profile(**values)


def config():
    return UwbTxConfig(9,0,2000,750,1000,power_code=0)


class UwbTests(unittest.TestCase):
    def test_periodic_tx_sequence_and_stop(self):
        transport=ScriptedTransport()
        with uwb_tx(Controller(transport,profile()),config()):
            self.assertEqual(transport.sent[-1],'AT+UWBDTEST=0,1,1,0')
        self.assertEqual(transport.sent,[
            'AT+UWBDTEST=0,0,0,0','AT+UWBDTEST=0,0,0,1','AT+UWBDTEST=0,0,3,9',
            'AT+UWBDTEST=0,0,1,TX_ANT_0','AT+UWBDTEST=0,0,4,2000_750_1000',
            'AT+UWBDTEST=0,1,1,0','AT+UWBDTEST=0,0,0,0'])

    def test_calibrated_power_selects_separate_start(self):
        setup,cleanup=uwb_tx_plan(replace(config(),power_code=None,calibrated_power=True))
        self.assertEqual(Catalog().build(setup[-1][0]).wire,'AT+UWBDTEST=0,1,2,0')
        self.assertEqual(cleanup,[('s23_uwb_off',{})])

    def test_power_choice_must_be_explicit(self):
        for cfg in [replace(config(),power_code=None),replace(config(),calibrated_power=True),replace(config(),antenna=True)]:
            with self.assertRaises(CommandRejected):
                uwb_tx_plan(cfg)

    def test_invalid_plan_sends_nothing(self):
        for cfg in [replace(config(),channel=6),replace(config(),gap=0),replace(config(),packets='1000_0'),replace(config(),power_code=128)]:
            transport=ScriptedTransport()
            with self.assertRaises(CommandRejected):
                with uwb_tx(Controller(transport,profile()),cfg):
                    self.fail('invalid plan reached measurement')
            self.assertEqual(transport.sent,[])

    def test_wrong_real_build_is_rejected_even_with_allowlist(self):
        transport=ScriptedTransport()
        transport.simulated=False
        phone=Controller(transport,profile(build='LATEST',simulation_only=False,allowed_commands=frozenset(['s23_uwb_on'])))
        with self.assertRaises(CommandRejected):
            phone.execute('s23_uwb_on')
        self.assertEqual(transport.sent,[])

    def test_start_failure_runs_off(self):
        transport=ScriptedTransport(['+UWBDTEST:0,OK\r\nOK\r\n']*5+['+UWBDTEST:0,NG\r\nOK\r\n'])
        with self.assertRaises(ResponseError):
            with uwb_tx(Controller(transport,profile()),config()):
                self.fail('failed TX reached measurement')
        self.assertEqual(transport.sent[-1],'AT+UWBDTEST=0,0,0,0')

    def test_source_files_and_line_numbers_exist(self):
        root=Path(__file__).resolve().parents[1]
        entries=[e for e in Catalog().entries.values() if e['id'].startswith('s23_uwb_')]
        self.assertEqual(len(entries),9)
        for entry in entries:
            self.assertFalse(entry['device_verified'])
            for source in [entry['source']]+entry['downstream_sources']:
                lines=(root/source['file']).read_text(encoding='utf-8').splitlines()
                self.assertTrue(lines[source['line']-1].strip())


class NfcTests(unittest.TestCase):
    def test_request_numbers_and_all_numeric_payloads(self):
        for tech in (0,1,2):
            for rate in (0,1,2):
                request=NfcRequest(31,tech,rate)
                self.assertEqual(request.nci_payload,bytes([0x21,1,tech+1,rate+1]))
                argv=request.adb_argv('TEST_SERIAL')
                self.assertIn('com.samsung.android.nfc.test.extra.TECH',argv)
                self.assertIn('com.samsung.android.nfc.test.extra.RATE',argv)
        self.assertEqual(NfcRequest(32).nci_payload,b'\x21\x00')

    def test_invalid_values_do_not_fall_back_to_default(self):
        for values in [(31,3,0),(31,0,3),(31,True,0),(31,-1,0),(32,0,0),(33,None,None)]:
            with self.assertRaises(CommandRejected):
                NfcRequest(*values)
        with self.assertRaises(CommandRejected):
            NfcRequest(32).adb_argv('serial;bad')

    def test_real_transport_requires_source_match_and_permission(self):
        for p in [NfcProfile('phone','build','bad',True),NfcProfile('phone','build',nfc_prbs_spec()['apk_sha256'],False)]:
            with self.assertRaises(CommandRejected):
                AdbNfcTransport('TEST',p)

    def test_dispatch_success_never_substitutes_for_rf_confirmation(self):
        calls=[]
        def runner(argv,**kwargs):
            calls.append((argv,kwargs))
            return SimpleNamespace(returncode=0,stdout='Broadcast completed: result=0',stderr='')
        p=NfcProfile('TEST','TEST',nfc_prbs_spec()['apk_sha256'],True)
        phone=NfcPrbsController(AdbNfcTransport('TEST',p,runner=runner))
        with self.assertRaises(RFError):
            with phone.session(0,0,verify_started=lambda t:False,verify_stopped=lambda t:True):
                self.fail('unconfirmed start reached measurement')
        self.assertEqual([e['request_id'] for e in phone.log],[31,32])
        self.assertEqual(phone.log[0]['status'],'dispatched_unconfirmed')
        self.assertTrue(all(not e['rf_measured'] for e in phone.log))
        self.assertTrue(all(kwargs['shell'] is False for _,kwargs in calls))

    def test_nfc_body_failure_and_unconfirmed_stop_are_both_retained(self):
        transport=SimulatedNfcTransport()
        with self.assertRaises(BaseExceptionGroup) as result:
            with NfcPrbsController(transport).session(0,0,verify_started=lambda t:True,verify_stopped=lambda t:False):
                raise RuntimeError('instrument failed')
        self.assertIsInstance(result.exception.exceptions[0],RuntimeError)
        self.assertIsInstance(result.exception.exceptions[1],CleanupError)
        self.assertEqual([r.request_id for r in transport.sent],[31,32])

    def test_nfc_cancel_after_start_runs_stop(self):
        cancelled=threading.Event()
        transport=SimulatedNfcTransport()
        def confirm(timeout):
            cancelled.set()
            return True
        with self.assertRaises(InterruptedError):
            with NfcPrbsController(transport).session(2,1,verify_started=confirm,verify_stopped=lambda t:True,cancelled=cancelled):
                self.fail('cancelled start reached measurement')
        self.assertEqual([r.request_id for r in transport.sent],[31,32])

    def test_permission_denial_even_with_zero_exit_code(self):
        p=NfcProfile('TEST','TEST',nfc_prbs_spec()['apk_sha256'],True)
        transport=AdbNfcTransport('TEST',p,runner=lambda *a,**k:SimpleNamespace(returncode=0,stdout='Permission Denial',stderr=''))
        with self.assertRaises(RFError):
            transport.dispatch(NfcRequest(32),1)


if __name__=='__main__':
    unittest.main()
