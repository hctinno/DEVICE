"""Offline chipset command fragments; deliberately no shell/ADB execution.

Command syntax, driver encoding, and hardware readiness are separate evidence
levels. Every plan returned here is uncommissioned and cannot execute itself.
"""
from dataclasses import asdict, dataclass
from importlib.resources import files
import json
import re


def catalog() -> dict:
    return json.loads(files("dgm_rf").joinpath("data/chipset-commands.json").read_text(encoding="utf-8"))


def enum_value(group: str, symbol: str) -> int:
    for row in catalog()["qualcomm_enums"].get(group, []):
        if row["symbol"] == symbol and "INVALID" not in symbol:
            return row["value"]
    raise ValueError(f"unknown or sentinel enum: {group}.{symbol}")


def _integer(value: int, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def _mac(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", value):
        raise ValueError("invalid MAC address")
    return value.lower()


@dataclass(frozen=True)
class FragmentPlan:
    evidence_level: str
    commands: tuple[tuple[str, ...], ...]
    cleanup: tuple[tuple[str, ...], ...]
    missing: tuple[str, ...]
    sources: tuple[str, ...]
    executable: bool = False
    physical_phone_verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def wl_tx_packets(destination_mac: str, *, gap_us: int, frame_bytes: int, frame_count: int) -> FragmentPlan:
    """Documented packet engine fragment, not a complete RF setup.

    Counts/gap/length use conservative library serialization bounds, NOT a claim
    about chip limits. The manufacturer's p78 ipg range has a us/ms contradiction.
    No sync token is emitted: continuous TX plus sync can block the host.
    """
    mac = _mac(destination_mac)
    _integer(gap_us, "gap_us", 1, 2**31 - 1)
    _integer(frame_bytes, "frame_bytes", 1, 65535)
    _integer(frame_count, "frame_count", 0, 2**31 - 1)
    return FragmentPlan("documented_cli", (("wl", "pkteng_start", mac, "tx", str(gap_us), str(frame_bytes), str(frame_count)),),
                        (("wl", "pkteng_stop", "tx"),),
                        ("matched wl/driver/MFG firmware", "channel/rate/power/chain setup", "device-specific argument limits", "RF ON/OFF measurement"),
                        ("infineon-wl-cli:p78-79",))


def wl_rx_packets(dut_mac: str, *, expected_packets: int, timeout_ms: int) -> FragmentPlan:
    mac = _mac(dut_mac)
    _integer(expected_packets, "expected_packets", 1, 2**31 - 1)
    _integer(timeout_ms, "timeout_ms", 1, 3000)
    return FragmentPlan("documented_cli", (("wl", "pkteng_start", mac, "rx", "sync", str(expected_packets), str(timeout_ms)),),
                        (("wl", "pkteng_stop", "rx"),),
                        ("matched wl/driver/MFG firmware", "channel/rate/RX setup", "response parser and measured RX counts"),
                        ("infineon-wl-cli:p78-79",))


def wl_6g_he_candidate(primary_channel: int, width_mhz: int, mcs: int, nss: int) -> FragmentPlan:
    """Cross-source candidate: shared Android parser plus Infineon HE syntax.

    Only conventional contiguous 6 GHz 20/40/80/160 channel blocks supported.
    The library caps primary20 at 233; the shared header has a broader 253.
    This does not establish availability in a jurisdiction or a smartphone.
    """
    _integer(primary_channel, "primary_channel", 1, 233)
    if type(width_mhz) is not int or width_mhz not in {20, 40, 80, 160}:
        raise ValueError("width_mhz must be 20, 40, 80, or 160")
    if (primary_channel - 1) % 4:
        raise ValueError("primary_channel must be a conventional 6 GHz 20 MHz primary (1+4n)")
    block_size = width_mhz // 20
    block = ((primary_channel - 1) // 4) // block_size
    center = 1 + block * block_size * 4 + (block_size - 1) * 2
    if center > {20: 233, 40: 227, 80: 215, 160: 207}[width_mhz]:
        raise ValueError("primary_channel has no complete block of requested width")
    _integer(mcs, "mcs", 0, 11)
    # Library limits to 1/2-stream candidates; this is not a generic chip maximum.
    _integer(nss, "nss", 1, 2)
    return FragmentPlan("cross_source_candidate", (("wl", "chanspec", f"6g{primary_channel}/{width_mhz}"),
                        ("wl", "6g_rate", "-e", f"{mcs}x{nss}")), (),
                        ("same-device wl chanspec and HE bandwidth acceptance", "MFG firmware", "power/chain/setup/TX procedure", "channel readback and RF bandwidth measurement"),
                        ("android-bcm4389-chanspec:713-857", "android-bcm4389-channel-limits:48-55", "infineon-an225347:p35"))


def qualcomm_he_fields(width_mhz: int, gi_symbol: str, nss: int) -> dict:
    """Return candidate fields, never fabricate a complete myftm TX command."""
    if type(width_mhz) is not int or width_mhz not in {20, 40, 80, 160}:
        raise ValueError("width_mhz must be 20, 40, 80, or 160")
    _integer(nss, "nss", 1, 2)
    rate_bw = enum_value("TCMD_RATEBW", f"TCMD_RATEBW_HE{width_mhz}")
    gi = enum_value("TCMD_GI", gi_symbol)
    return {"dialect": catalog()["qualcomm_dialect"], "evidence_level": "header_and_help_mapping_candidate",
            "fields": {"rateBw": rate_bw, "gI": gi, "nss": nss},
            "argument_fragment": ["--rateBw", str(rate_bw), "--gI", str(gi), "--nss", str(nss)],
            "start": None, "stop": None, "executable": False, "physical_phone_verified": False,
            "missing": ["CLI parser mapping", "complete TX/RX start/stop sequence", "HE GI/LTF combination validity", "Android-compatible build and OEM test firmware"]}


def android_discovery(serial: str) -> tuple[tuple[str, ...], ...]:
    """Build read-only identification commands, without running ADB."""
    if not isinstance(serial, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", serial):
        raise ValueError("invalid ADB serial")
    commands = [("getprop", key) for key in ("ro.product.model", "ro.build.fingerprint", "ro.product.cpu.abi", "ro.board.platform", "ro.hardware", "ro.build.type")]
    commands += [("id",), ("getenforce",), ("ls", "/sys/class/net"),
                 ("ls", "/vendor/bin/wl", "/vendor/bin/myftm", "/vendor/bin/ftmdaemon"),
                 ("readlink", "/sys/class/net/wlan0/device/driver")]
    return tuple(("adb", "-s", serial, "shell", *command) for command in commands)
