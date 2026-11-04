"""Schema v1 validation without opening any device transport."""
import json
import math
from pathlib import Path
from .catalog import ProfileError, UnsupportedDevice, describe


def load_profile(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _keys(obj, allowed, required, label):
    if not isinstance(obj, dict):
        raise ProfileError(f"{label} must be an object")
    unknown = set(obj) - set(allowed)
    missing = set(required) - set(obj)
    if unknown or missing:
        raise ProfileError(f"{label}: unknown={sorted(unknown)}, missing={sorted(missing)}")


def _phone_profile(config, mode):
    from dgm_rf import Catalog, Profile
    from dgm_rf.core import scalar, RFError
    _keys(config["parameters"], {"profile"}, {"profile"}, "parameters")
    data = config["parameters"]["profile"]
    fields = {"model", "build", "simulation_only", "evidence_notes", "allowed_commands", "argument_domains"}
    _keys(data, fields, fields, "phone profile")
    for field in ("model", "build", "evidence_notes"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ProfileError(f"phone profile {field} must be nonempty")
    if type(data["simulation_only"]) is not bool or data["simulation_only"] != (mode == "simulation"):
        raise ProfileError("phone simulation_only must match mode")
    allowlist = data["allowed_commands"]
    if not isinstance(allowlist, list) or not all(isinstance(x, str) for x in allowlist) or len(allowlist) != len(set(allowlist)):
        raise ProfileError("allowed_commands must be a unique list of command IDs")
    catalog = Catalog()
    for command in allowlist:
        if command not in catalog.entries or catalog.entries[command]["status"] not in {"static_ready", "needs_profile"}:
            raise ProfileError(f"Command not executable in source catalog: {command}")
        scope = catalog.entries[command].get("device_scope")
        if mode == "hardware" and scope and (data["model"] != scope["model"] or data["build"] != scope["build"]):
            raise ProfileError(f"Command restricted to another model/build: {command}")
    if mode == "hardware" and not allowlist:
        raise ProfileError("Hardware phone requires explicit allowed_commands")
    domains = data["argument_domains"]
    if not isinstance(domains, dict):
        raise ProfileError("argument_domains must be an object")
    for command, parameters in domains.items():
        if command not in catalog.entries or not isinstance(parameters, dict):
            raise ProfileError(f"Invalid argument domain: {command}")
        for parameter, values in parameters.items():
            if parameter not in catalog.entries[command]["parameters"] or not isinstance(values, list) or not values:
                raise ProfileError(f"Invalid argument domain: {command}.{parameter}")
            if any(type(value) not in (str, int, float) for value in values):
                raise ProfileError("Domain values must be scalar tokens")
            spec = catalog.entries[command]["parameters"][parameter]
            for value in values:
                if type(value) is float and not math.isfinite(value):
                    raise ProfileError("Domain numbers must be finite")
                try:
                    token = scalar(value, spec["type"])
                except RFError as exc:
                    raise ProfileError(f"Invalid domain token: {command}.{parameter}") from exc
                if spec["domain"] is not None and token not in spec["domain"]:
                    raise ProfileError(f"Domain contradicts source table: {command}.{parameter}")
    transport = config["transport"]
    if mode == "hardware":
        _keys(transport, {"kind", "port", "baudrate"}, {"kind", "port", "baudrate"}, "phone transport")
        if transport["kind"] != "serial" or not isinstance(transport["port"], str) or not transport["port"].strip() or "REPLACE" in transport["port"].upper():
            raise ProfileError("Explicit phone serial port required")
        if type(transport["baudrate"]) is not int or transport["baudrate"] <= 0:
            raise ProfileError("Positive integer baudrate required")
    return Profile(**{**data, "allowed_commands": frozenset(allowlist)})


def require_profile(profile):
    _keys(profile, {"schema_version", "device_id", "mode", "config"}, {"schema_version", "device_id", "mode", "config"}, "profile")
    if type(profile["schema_version"]) is not int or profile["schema_version"] != 1:
        raise ProfileError("schema_version must be integer 1")
    entry = describe(profile["device_id"])
    if entry["backend"] is None:
        raise UnsupportedDevice(f"{entry['id']} is {entry['status']}: {entry['site_requirements']}")
    mode = profile["mode"]
    if mode not in ("hardware", "simulation"):
        raise ProfileError("mode must be hardware or simulation")
    config = profile["config"]
    _keys(config, {"driver", "parameters", "transport", "notes"}, {"driver", "parameters", "transport"}, "config")
    if "notes" in config and not isinstance(config["notes"], str):
        raise ProfileError("config.notes must be a string")
    if config["driver"] != entry["id"]:
        raise ProfileError("device_id and config.driver must match")
    if not isinstance(config["parameters"], dict) or not isinstance(config["transport"], dict):
        raise ProfileError("parameters and transport must be objects")
    if mode == "simulation":
        if not entry["simulation_available"]:
            raise UnsupportedDevice(f"No simulator for {entry['id']}")
        if config["transport"] != {"kind": "simulation"}:
            raise ProfileError("Simulation requires exactly transport={kind: simulation}; no real address")
    if entry["id"] == "PhoneAt":
        _phone_profile(config, mode)
    else:
        from dgm_lab.registry import DRIVERS
        from dgm_lab.capabilities import validate_profile
        if mode == "hardware":
            validate_profile(config)
        else:
            DRIVERS[entry["id"]](None, **config["parameters"])
    return entry


def check_profile(profile):
    try:
        entry = require_profile(profile)
        return {"valid": True, "device_id": entry["id"], "mode": profile["mode"], "issues": [],
                "connection_attempted": False, "physical_verified": False, "remaining": entry["site_requirements"]}
    except (ValueError, TypeError, KeyError, RuntimeError) as exc:
        return {"valid": False, "issues": [f"{type(exc).__name__}: {exc}"], "connection_attempted": False, "physical_verified": False}
