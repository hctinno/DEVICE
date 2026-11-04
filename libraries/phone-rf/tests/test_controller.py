import threading
import unittest
from unittest.mock import patch
from dgm_rf import *
from dgm_rf.core import parse_response


def simulation_profile():
    return Profile("SIM", "fixture", argument_domains={
        "wifitest_0_0_0": {"value":["17"]}, "wifitest_0_0_3": {"value":["0.0"]},
        "wifitest_0_0_4": {"value":["1000"]}, "wifitest_0_0_5": {"value":["1000"]}})


def config():
    return WlanTxConfig(3,9,17,15,1,5,1,"0.0",1000,1000)


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()

    def test_he160_and_6ghz_from_source_table(self):
        self.assertEqual(self.catalog.build("wifitest_0_0_6",value=3).wire,"AT+WIFITEST=0,0,6,3")
        self.assertEqual(self.catalog.build("wifitest_0_0_7",value=9).wire,"AT+WIFITEST=0,0,7,9")

    def test_unknowns_and_cellular_cannot_execute(self):
        for entry in self.catalog.search(radio="cellular"):
            with self.assertRaises(CommandRejected):
                self.catalog.build(entry["id"])
        with self.assertRaises(CommandRejected):
            self.catalog.build("uwbdtest_0_1_1",value=1)

    def test_channel_cannot_be_guessed(self):
        with self.assertRaises(CommandRejected):
            self.catalog.build("wifitest_0_0_0",value=15)
        with self.assertRaises(CommandRejected):
            self.catalog.build("wifitest_0_0_0",profile=simulation_profile(),value=15)

    def test_injection_and_wrong_parameters_rejected(self):
        for value in ["3\rAT+RESET", "3,0", True, float("nan"), "999"]:
            with self.subTest(value=value), self.assertRaises(CommandRejected):
                self.catalog.build("wifitest_0_0_6",value=value)
        with self.assertRaises(CommandRejected):
            self.catalog.build("fcbttest_3_4_1",value=1)

    def test_fixed_bt_phy(self):
        self.assertEqual(self.catalog.build("fcbttest_3_4_1").wire,"AT+FCBTTEST=3,4,1")

    def test_invalid_he_rate_and_gi(self):
        for rate,gi in [(1,5),(15,1)]:
            with self.assertRaises(CommandRejected):
                wlan_tx_plan(WlanTxConfig(3,9,17,rate,1,gi,1,"0.0",1000,1000))

    def test_all_five_radios_present_and_no_fake_device_validation(self):
        self.assertEqual({c["radio"] for c in self.catalog.entries.values()},{"wlan","bluetooth","cellular","nfc","uwb"})
        self.assertFalse(any(c["device_verified"] for c in self.catalog.entries.values()))


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.command=Catalog().build("wifitest_0_2_0",value=0)

    def test_ng_then_ok_is_failure(self):
        with self.assertRaises(ResponseError):
            parse_response(self.command,"\r\n+WIFITEST:0,NG\r\n\r\nOK\r\n")

    def test_cme_then_ok_is_failure(self):
        with self.assertRaises(ResponseError):
            parse_response(self.command,"+CME Error:NA\r\nOK\r\n")

    def test_wrong_family_and_argument_are_not_success(self):
        for raw in ["+FCBTTEST:0,OK\r\nOK\r\n","+WIFITEST:1,OK\r\nOK\r\n","OK\r\n","+WIFITEST:0,UNKNOWN\r\nOK\r\n"]:
            with self.subTest(raw=raw),self.assertRaises(ResponseError):
                parse_response(self.command,raw)

    def test_echo_and_success(self):
        self.assertEqual(parse_response(self.command,self.command.wire+"\r\n+WIFITEST:0,OK\r\nOK\r\n"),"OK")

    def test_duplicate_results_are_ambiguous(self):
        with self.assertRaises(ResponseError):
            parse_response(self.command,"+WIFITEST:0,OK\r\n+WIFITEST:0,OK\r\nOK\r\n")


class SequenceTests(unittest.TestCase):
    def test_complete_wlan_cycle(self):
        t=ScriptedTransport();c=Controller(t,simulation_profile())
        with c.wlan_tx(config()):
            self.assertEqual(t.sent[-1],"AT+WIFITEST=0,2,1,1")
        self.assertEqual(t.sent[-2:],["AT+WIFITEST=0,2,0,0","AT+WIFITEST=0,1,0,0"])
        self.assertEqual(len(c.log),14)
        self.assertTrue(all(x["simulated"] for x in c.log))

    def test_failed_setup_still_cleans_up(self):
        t=ScriptedTransport(["+WIFITEST:0,NG\r\nOK\r\n"]);c=Controller(t,simulation_profile())
        with self.assertRaises(ResponseError):
            with c.wlan_tx(config()):
                self.fail("body must not run")
        self.assertEqual(t.sent[-2:],["AT+WIFITEST=0,2,0,0","AT+WIFITEST=0,1,0,0"])

    def test_measurement_exception_cleanup(self):
        t=ScriptedTransport();c=Controller(t,simulation_profile())
        with self.assertRaisesRegex(ValueError,"instrument"):
            with c.wlan_tx(config()):
                raise ValueError("instrument failed")
        self.assertTrue(t.sent[-1].endswith("0,1,0,0"))

    def test_cancellation_cleanup(self):
        event=threading.Event();event.set()
        t=ScriptedTransport();c=Controller(t,simulation_profile())
        with self.assertRaises(InterruptedError):
            with c.wlan_tx(config(),cancelled=event):
                self.fail()
        self.assertEqual(len(t.sent),2)

    def test_bad_late_parameter_prevents_all_io(self):
        bad=WlanTxConfig(3,9,17,15,1,5,1,"22.5",1000,1000)
        t=ScriptedTransport();c=Controller(t,simulation_profile())
        with self.assertRaises(CommandRejected):
            with c.wlan_tx(bad):
                self.fail()
        self.assertEqual(t.sent,[])

    def test_timeout_preserves_error_and_unconfirmed_cleanup(self):
        t=ScriptedTransport([TimeoutError("no response")]);c=Controller(t,simulation_profile())
        with self.assertRaises(ExceptionGroup) as result:
            with c.wlan_tx(config()):
                self.fail()
        self.assertIsInstance(result.exception.exceptions[0],TimeoutError)
        self.assertIsInstance(result.exception.exceptions[1],CleanupError)
        self.assertEqual([x["status"] for x in c.log][-2:],["cleanup_sent_unconfirmed"]*2)

    def test_stop_failure_still_closes(self):
        t=ScriptedTransport();c=Controller(t,simulation_profile())
        with self.assertRaises(CleanupError):
            with c.wlan_tx(config()):
                t.responses.append("+WIFITEST:0,NG\r\nOK\r\n")
        self.assertEqual(t.sent[-1],"AT+WIFITEST=0,1,0,0")

    def test_real_transport_requires_profile_before_io(self):
        t=ScriptedTransport();t.simulated=False
        c=Controller(t,simulation_profile())
        with self.assertRaises(CommandRejected):
            c.execute("wifitest_0_2_1",value=1)
        self.assertEqual(t.sent,[])

    def test_wrong_family_poison_connection(self):
        t=ScriptedTransport(["+FCBTTEST:0,OK\r\nOK\r\n"])
        c=Controller(t)
        with self.assertRaises(ResponseError):
            c.execute("wifitest_0_2_0",value=0)
        self.assertTrue(t.desynchronized)
        with self.assertRaises(RFError):
            c.execute("wifitest_0_1_0",value=0)
        self.assertEqual(len(t.sent),1)


class FakeSerial:
    def __init__(self,chunks=(),partial=False):
        self.chunks=iter(chunks);self.active=False;self.writes=[];self.partial=partial
    @property
    def in_waiting(self):
        return 0
    def write(self,data):
        self.writes.append(data);self.active=True
        return 1 if self.partial else len(data)
    def read(self,count):
        return next(self.chunks,b"")
    def close(self):
        self.active=False


class SerialTests(unittest.TestCase):
    def test_fragmented_response_and_cr_encoding(self):
        fake=FakeSerial([b"\r\n+WIFI",b"TEST:0,OK\r\n",b"\r\nO",b"K\r",b"\n"])
        t=SerialTransport("TEST",115200,serial_instance=fake)
        self.assertEqual(t.exchange("AT+WIFITEST=0,2,0,0",1),"\r\n+WIFITEST:0,OK\r\n\r\nOK\r\n")
        self.assertEqual(fake.writes,[b"AT+WIFITEST=0,2,0,0\r"])

    def test_partial_write_poison_connection(self):
        fake=FakeSerial(partial=True);t=SerialTransport("TEST",115200,serial_instance=fake)
        with self.assertRaises(OSError):
            t.exchange("AT+WIFITEST=0,2,0,0",1)
        self.assertTrue(t.desynchronized)

    def test_timeout_prevents_delayed_response_reuse(self):
        fake=FakeSerial();t=SerialTransport("TEST",115200,serial_instance=fake)
        with self.assertRaises(TimeoutError):
            t.exchange("AT+WIFITEST=0,2,0,0",0.001)
        with self.assertRaises(RFError):
            t.exchange("AT+WIFITEST=0,1,0,0",1)
        self.assertEqual(len(fake.writes),1)


if __name__=="__main__":
    unittest.main()
