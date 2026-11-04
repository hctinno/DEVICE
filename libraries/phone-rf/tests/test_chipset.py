import json
from pathlib import Path
import subprocess
import sys
import unittest

from dgm_rf.chipset import (android_discovery, catalog, enum_value, qualcomm_he_fields,
                            wl_6g_he_candidate, wl_tx_packets, wl_rx_packets)


class ChipsetEvidenceTests(unittest.TestCase):
    def test_each_record_has_traceable_source(self):
        data = catalog()
        self.assertEqual(len(data["commands"]), 29)
        for record in data["commands"]:
            self.assertIn(record["evidence"], data["sources"])
            self.assertTrue(record["locator"])
        self.assertFalse(data["phone_verified"])

    def test_he160_is_not_eht20_or_mhz(self):
        result = qualcomm_he_fields(160, "TCMD_GI_LTF_MODE4_GI_3200", 1)
        self.assertEqual(result["fields"], {"rateBw": 16, "gI": 52, "nss": 1})
        self.assertEqual(enum_value("TCMD_RATEBW", "TCMD_RATEBW_11BE_EHT20"), 30)
        self.assertIsNone(result["start"])
        self.assertIsNone(result["stop"])
        self.assertFalse(result["executable"])

    def test_enum_sentinels_and_unknowns_rejected(self):
        for group, name in [("TCMD_RATEBW", "TCMD_RATEBW_INVALID"), ("wrong", "TCMD_RATEBW_HE160")]:
            with self.assertRaises(ValueError):
                enum_value(group, name)

    def test_six_ghz_primary_is_not_center(self):
        plan = wl_6g_he_candidate(1, 160, 11, 2)
        self.assertEqual(plan.commands[0], ("wl", "chanspec", "6g1/160"))
        self.assertEqual(plan.commands[1], ("wl", "6g_rate", "-e", "11x2"))
        self.assertEqual(plan.evidence_level, "cross_source_candidate")
        with self.assertRaises(ValueError):
            wl_6g_he_candidate(15, 160, 0, 1)

    def test_partial_last_channel_block_rejected(self):
        wl_6g_he_candidate(233, 20, 0, 1)
        wl_6g_he_candidate(229, 40, 0, 1)
        wl_6g_he_candidate(221, 160, 0, 1)
        for channel, width in [(233, 40), (225, 80), (225, 160)]:
            with self.assertRaises(ValueError):
                wl_6g_he_candidate(channel, width, 0, 1)

    def test_unsupported_he_width_and_streams(self):
        for args in [(1, 320, 0, 1), (1, 80, 12, 1), (1, 80, 0, 3), (True, 20, 0, 1)]:
            with self.assertRaises(ValueError):
                wl_6g_he_candidate(*args)

    def test_continuous_tx_does_not_use_sync(self):
        plan = wl_tx_packets("00:11:22:33:44:55", gap_us=40, frame_bytes=1000, frame_count=0)
        self.assertEqual(plan.commands[0][-4:], ("tx", "40", "1000", "0"))
        self.assertNotIn("sync", plan.commands[0])
        self.assertEqual(plan.cleanup, (("wl", "pkteng_stop", "tx"),))
        self.assertFalse(plan.executable)

    def test_rx_arguments_differ_from_tx(self):
        plan = wl_rx_packets("00:11:22:33:44:55", expected_packets=100, timeout_ms=1000)
        self.assertEqual(plan.commands[0][-4:], ("rx", "sync", "100", "1000"))
        self.assertEqual(plan.cleanup[0][-1], "rx")
        with self.assertRaises(ValueError):
            wl_rx_packets("00:11:22:33:44:55", expected_packets=100, timeout_ms=3001)

    def test_no_shell_metacharacters_or_fractional_wire_values(self):
        with self.assertRaises(ValueError):
            wl_tx_packets("00:11:22:33:44:55;reboot", gap_us=40, frame_bytes=1000, frame_count=0)
        for bad in [True, 0.5, "40", -1]:
            with self.assertRaises(ValueError):
                wl_tx_packets("00:11:22:33:44:55", gap_us=bad, frame_bytes=1000, frame_count=0)

    def test_discovery_does_not_change_device(self):
        commands = android_discovery("EXAMPLE:5555")
        self.assertEqual(len(commands), 11)
        self.assertTrue(all(command[:4] == ("adb", "-s", "EXAMPLE:5555", "shell") for command in commands))
        self.assertTrue(all(command[4] in {"getprop", "id", "getenforce", "ls", "readlink"} for command in commands))
        for serial in ["-s", "x;reboot", "$(id)", ""]:
            with self.assertRaises(ValueError):
                android_discovery(serial)

    def test_cli_prints_offline_json(self):
        run = subprocess.run([sys.executable, "-m", "dgm_rf", "chipset-demo"], capture_output=True, text=True, encoding="utf-8", check=True)
        result = json.loads(run.stdout)
        self.assertEqual(result["mode"], "OFFLINE_ONLY")
        self.assertFalse(result["physical_phone_verified"])

    def test_header_fact_exact_source_location(self):
        data = catalog()
        row = next(row for row in data["qualcomm_enums"]["TCMD_RATEBW"] if row["symbol"] == "TCMD_RATEBW_HE160")
        self.assertEqual(row["line"], 166)
        self.assertEqual(data["sources"]["qualcomm-myftm"]["sha256"], "62568accc57f60a4a46d7093485af5c697866b067c5e2e7cc57a47b63d48ede2")


if __name__ == "__main__":
    unittest.main()
