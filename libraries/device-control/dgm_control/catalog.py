from importlib.resources import files
from importlib import metadata, util
import json
import platform


class ProfileError(ValueError):
    pass


class UnsupportedDevice(ProfileError):
    pass


def _data():
    return json.loads(files("dgm_control").joinpath("data/catalog.json").read_text(encoding="utf-8"))


def devices(kind=None):
    if kind not in (None, "instrument", "facility", "smartphone"):
        raise ValueError("kind must be instrument, facility or smartphone")
    return [row for row in _data()["devices"] if kind is None or row["kind"] == kind]


def describe(device_id):
    for row in devices():
        if row["id"] == device_id:
            return row
    raise UnsupportedDevice(f"Unknown device_id {device_id!r}; use dgm-control list")


def profile_template(device_id, mode="hardware"):
    entry = describe(device_id)
    if mode not in ("hardware", "simulation"):
        raise ProfileError("mode must be hardware or simulation")
    templates = _data()[mode + "_templates"]
    if device_id not in templates:
        raise UnsupportedDevice(f"No {mode} backend for {device_id}: {entry['site_requirements']}")
    return templates[device_id]


def doctor():
    installed = {}
    for name in ("dgm-device-control", "dgm-lab-control", "dgm-rf-command-library"):
        try:
            installed[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed[name] = "not installed (source tree may still work)"
    return {"python": platform.python_version(), "supported_python": tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 11),
            "packages": installed, "optional_modules": {name: util.find_spec(name) is not None for name in ("pyvisa", "serial")},
            "connection_attempted": False, "visa_runtime_tested": False, "hardware_verified": False,
            "note": "Module presence is not VISA backend/USB driver/device readiness."}
