"""Explicit facility scan limits; no inferred site configuration or RF band coverage."""
import math
from dgm_lab.core import number
from .radio_contracts import exact

FACILITIES = {"Co3000", "OspSwitch"}
SCAN_FAULTS = ("motion-timeout", "motion-stop-timeout", "switch-timeout", "switch-stop-timeout")


def scan_template():
    return {"heights_cm": [100, 200], "angles_deg": [0, 90, 180], "polarizations": ["H", "V"],
            "rf_paths": ["dut"], "motion_timeout": 15, "settle_seconds": .01,
            "path_frequency_limits_hz": {"dut": [0, 50e9]}, "site_verified": False, "evidence_notes": "",
            "simulation": {"peak_angle_deg": 90, "peak_height_cm": 200, "peak_polarization": "V",
                "cross_polar_loss_db": 6, "route_loss_db": {"dut": 0}}}


def validate_scan(plan):
    scan = plan["scan"]
    exact(scan, scan_template(), "scan")
    for key, low, high in (("heights_cm", 100, 400), ("angles_deg", 0, 360)):
        values = scan[key]
        if not isinstance(values, list) or not values: raise ValueError("Nonempty scan grid required")
        for value in values:
            number(value, key, low, high)
            if not math.isclose(value * 10, round(value * 10), abs_tol=1e-7, rel_tol=0):
                raise ValueError("CO3000 grid resolution is 0.1")
        if len(set(values)) != len(values): raise ValueError("Duplicate grid values")
    for key, allowed in (("polarizations", {"H", "V"}), ("rf_paths", None)):
        values = scan[key]
        if not isinstance(values, list) or not values or any(not isinstance(x, str) for x in values):
            raise ValueError(f"Nonempty string list required: {key}")
        if len(set(values)) != len(values) or (allowed and not set(values) <= allowed):
            raise ValueError(f"Invalid or duplicate {key}")
    count = math.prod(len(scan[k]) for k in ("heights_cm", "angles_deg", "polarizations", "rf_paths")) * plan["sample_count"]
    if count > 500: raise ValueError("Maximum 500 total scan samples")
    number(scan["motion_timeout"], "motion_timeout", .6, 3600)
    number(scan["settle_seconds"], "scan settle_seconds", 0, 30)
    exact(scan["path_frequency_limits_hz"], scan["rf_paths"], "path frequency limits")
    for limits in scan["path_frequency_limits_hz"].values():
        if not isinstance(limits, list) or len(limits) != 2: raise ValueError("Path frequency limits require [min,max] Hz")
        low = number(limits[0], "path minimum Hz", 0, 1e12)
        high = number(limits[1], "path maximum Hz", 0, 1e12)
        if not low < high or not low <= plan["sweep"]["start_hz"] < plan["sweep"]["stop_hz"] <= high:
            raise ValueError("Sweep outside declared RF path frequency limits")
    if type(scan["site_verified"]) is not bool or not isinstance(scan["evidence_notes"], str):
        raise ValueError("Explicit scan commissioning fields required")
    model = scan["simulation"]
    if plan["simulation_only"]:
        if not set(scan["rf_paths"]) <= {"dut", "generator"}: raise ValueError("Virtual OSP implements dut/generator measurement paths")
        exact(model, scan_template()["simulation"], "scan simulation")
        number(model["peak_angle_deg"], "peak angle", 0, 360)
        number(model["peak_height_cm"], "peak height", 100, 400)
        number(model["cross_polar_loss_db"], "cross-polar loss", 0, 60)
        if model["peak_polarization"] not in ("H", "V"): raise ValueError("Invalid peak polarization")
        exact(model["route_loss_db"], scan["rf_paths"], "synthetic route losses")
        for loss in model["route_loss_db"].values(): number(loss, "route loss", 0, 200)
    elif model is not None or scan["site_verified"] is not True or not scan["evidence_notes"].strip():
        raise ValueError("Hardware scan requires simulation=null and commissioned motion/RF-path evidence")
    return count


def check_scan_site(plan, profiles):
    scan = plan["scan"]
    motion = profiles["Co3000"]["config"]["parameters"]
    if motion.get("motion_enabled") is not True: raise ValueError("Commissioned motion_enabled=true required")
    for axis, unit, key in (("MA1", "CM", "heights_cm"), ("DT1", "DG", "angles_deg")):
        limits = motion["axes"].get(axis, {})
        if limits.get("unit") != unit or any(not limits["min"] <= v <= limits["max"] for v in scan[key]):
            raise ValueError(f"Scan exceeds commissioned {axis}/{unit} range")
    route = profiles["OspSwitch"]["config"]["parameters"]
    if route.get("switching_enabled") is not True: raise ValueError("Commissioned switching_enabled=true required")
    if not set(scan["rf_paths"]) <= set(route["paths"]) or route["safe_path"] in scan["rf_paths"]:
        raise ValueError("Measurement paths must exist and differ from safe_path")
    # A renamed safe relay map is still the safe map, not a distinct measurement path.
    normalized = lambda name: sorted((p["module"], p["relay"], p["state"]) for p in route["paths"][name])
    if any(normalized(name) == normalized(route["safe_path"]) for name in scan["rf_paths"]):
        raise ValueError("Measurement relay map equals safe relay map")
