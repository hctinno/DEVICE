"""Trace-bin E-field correction and declared-limit comparison (not certification)."""
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
import math

from dgm_lab.analyzers import Sweep

COMPONENTS = {"antenna_factor": "dB/m", "cable_loss": "dB", "switch_loss": "dB", "preamp_gain": "dB"}
CONVERSION_50_OHM = 90 + 10 * math.log10(50)


def exact(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{name}: expected exactly {sorted(keys)}")


def finite(value, name, minimum=None):
    if type(value) not in (int, float) or not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f"{name}: finite number >= {minimum} required")
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{name}: nonempty text required")


def interpolate(x, x0, y0, x1, y1, method):
    if not x0 <= x <= x1: raise ValueError("Extrapolation is forbidden")
    if method == "constant": return y0
    if method == "linear_log_hz": x, x0, x1 = map(math.log10, (x, x0, x1))
    return y0 + (y1-y0) * (x-x0) / (x1-x0)


def context(plan, measurement=None):
    """Return sweep, paths, polarizations without connecting to a device."""
    if isinstance(plan, dict):
        from .radio_contracts import validate_plan
        sweep = validate_plan(plan)
        if plan["schema_version"] != 2: raise ValueError("Evaluation requires a schema-2 facility scan")
        result = asdict(sweep), plan["scan"]["rf_paths"], plan["scan"]["polarizations"]
    else:
        plan.validate()
        result = asdict(Sweep(plan.center_hz-120e6, plan.center_hz+120e6, 1e6, 1e6, 10, 10,
                             points=101, sweep_seconds=.01)), ["dut"], list(plan.polarizations)
    if measurement is not None:
        from .receiver_measurement import measurement_settings
        return measurement_settings(measurement), result[1], result[2]
    return result


def evaluation_template(plan, measurement=None):
    """Synthetic teaching data; neither a calibration certificate nor an FCC limit."""
    if measurement is not None:
        from .receiver_measurement import validate_measurement
        validate_measurement(measurement, plan, simulated=True)
    sweep, paths, pols = context(plan, measurement)
    lo, hi = sweep["start_hz"], sweep["stop_hz"]
    def table(kind):
        value = {"antenna_factor": 20, "cable_loss": 2, "switch_loss": 1, "preamp_gain": 0}[kind]
        return {"unit": COMPONENTS[kind], "interpolation": "linear_hz", "points": [[lo, value], [hi, value]],
                "asset_id": "SYNTHETIC-"+kind, "source": "Synthetic fixture, not a certificate",
                "source_sha256": "0"*64, "provenance": "synthetic", "valid_from": "2000-01-01", "valid_until": "2099-12-31"}
    result = {"schema_version": 2 if measurement is not None else 1, "simulation_only": True,
            "setup": {"quantity": "electric_field", "unit": "dBuV/m", "impedance_ohm": 50,
                      "distance_m": 3, "receiver_reference": "input", "receiver_corrections_disabled": True,
                      "site_verified": False, "evidence_notes": "Synthetic setup only"},
            "paths": {p: {pol: {k: table(k) for k in COMPONENTS} for pol in pols} for p in paths},
            "criterion": {"id": "SYNTHETIC-DEMO", "source": "Synthetic demonstration, NOT a regulatory limit",
                          "edition": "demo-1", "clause": "demo-only", "provenance": "synthetic",
                          "unit": "dBuV/m", "distance_m": 3, "detector": sweep["detector"],
                          "rbw_hz": sweep["rbw_hz"], "vbw_hz": sweep["vbw_hz"],
                          "minimum_sweep_seconds": sweep.get("sweep_seconds", 0),
                          "segments": [{"start_hz": lo, "stop_hz": hi, "start_dbuv_m": 120,
                                        "stop_dbuv_m": 120, "interpolation": "constant"}]},
            "decision": {"rule": "simple", "expanded_uncertainty_db": 0, "coverage_factor": 2,
                         "source": "Synthetic uncertainty; simple rule ignores uncertainty"}}
    if measurement is not None:
        result["criterion"].pop("minimum_sweep_seconds")
        result["criterion"].update(acquisition="receiver_grid", filter_type="CISPR",
                                   minimum_dwell_seconds=sweep["dwell_seconds"])
    return result


class Evaluation:
    def __init__(self, config, plan, *, simulated, measurement=None):
        self.config = deepcopy(config)
        self.simulated = simulated
        self.measurement = deepcopy(measurement)
        if measurement is not None:
            from .receiver_measurement import validate_measurement
            validate_measurement(measurement, plan, simulated=simulated)
        self.sweep, self.paths, self.pols = context(plan, measurement)
        self.reasons, self.rows = [], []
        self._validate()
        self.sha256 = hashlib.sha256(json.dumps(self.config, sort_keys=True, separators=(",", ":"),
                                               ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
        self.measurement_sha256 = hashlib.sha256(json.dumps(self.measurement, sort_keys=True, separators=(",", ":"),
                                               ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest() if self.measurement is not None else None

    def _validate(self):
        c = self.config
        exact(c, ("schema_version", "simulation_only", "setup", "paths", "criterion", "decision"), "evaluation")
        version = 2 if self.measurement is not None else 1
        if type(c["schema_version"]) is not int or c["schema_version"] != version:
            raise ValueError("Evaluation schema_version must match acquisition: " + str(version))
        if type(c["simulation_only"]) is not bool: raise ValueError("simulation_only must be boolean")
        if not self.simulated and c["simulation_only"]: raise ValueError("Synthetic evaluation forbidden on hardware")
        s = c["setup"]
        exact(s, ("quantity", "unit", "impedance_ohm", "distance_m", "receiver_reference", "receiver_corrections_disabled", "site_verified", "evidence_notes"), "setup")
        if (s["quantity"] != "electric_field" or s["unit"] != "dBuV/m" or
                finite(s["impedance_ohm"], "impedance") != 50 or s["receiver_reference"] != "input" or
                s["receiver_corrections_disabled"] is not True):
            raise ValueError("Requires E-field, 50 ohm input dBm and disabled receiver corrections")
        finite(s["distance_m"], "distance", .001)
        text(s["evidence_notes"], "setup evidence")
        if type(s["site_verified"]) is not bool or (not self.simulated and not s["site_verified"]):
            raise ValueError("Hardware requires declared verified measurement setup")
        exact(c["paths"], self.paths, "RF paths")
        for path in self.paths:
            exact(c["paths"][path], self.pols, "polarizations")
            for pol in self.pols:
                tables = c["paths"][path][pol]
                exact(tables, COMPONENTS, "correction components")
                for kind, table in tables.items():
                    if kind == "preamp_gain" and table is None: continue
                    self._table(table, kind)
        limit = c["criterion"]
        timing = {"acquisition", "filter_type", "minimum_dwell_seconds"} if version == 2 else {"minimum_sweep_seconds"}
        exact(limit, {"id", "source", "edition", "clause", "provenance", "unit", "distance_m", "detector", "rbw_hz", "vbw_hz", "segments"} | timing, "criterion")
        for key in ("id", "source", "edition", "clause"): text(limit[key], key)
        self._provenance(limit, "declared_standard")
        if limit["unit"] != "dBuV/m": raise ValueError("Only dBuV/m limits supported; no H-field conversion")
        for key in ("distance_m", "rbw_hz"): finite(limit[key], key, .001)
        if version == 2:
            finite(limit["minimum_dwell_seconds"], "minimum dwell time", .001)
            if limit["vbw_hz"] is not None: raise ValueError("Receiver-grid VBW must be null (not applicable)")
            if limit["acquisition"] != "receiver_grid" or limit["filter_type"] != "CISPR":
                self.reasons.append("Receiver acquisition/filter criterion mismatch")
            if limit["detector"] not in ("POS", "QP", "LINEAR_AVER", "CISPR_AVER", "AVER", "RMS", "SAMP", "NEG"):
                raise ValueError("Unknown criterion detector")
            if limit["detector"] != self.sweep["detector"]: self.reasons.append("Receiver detector criterion mismatch")
            if self.sweep["dwell_seconds"] < limit["minimum_dwell_seconds"]: self.reasons.append("dwell time below criterion")
        else:
            finite(limit["vbw_hz"], "vbw_hz", .001)
            finite(limit["minimum_sweep_seconds"], "minimum sweep time", 0)
            if limit["detector"] not in ("POS", "QP", "AVER", "RMS", "SAMP", "NEG"): raise ValueError("Unknown criterion detector")
            if limit["detector"] != "POS" or self.sweep["detector"] != "POS":
                self.reasons.append("Swept workflow supports POS comparisons only; use verified receiver-grid for QP/average")
            if self.sweep["sweep_seconds"] < limit["minimum_sweep_seconds"]: self.reasons.append("sweep time below criterion")
        for key in ("rbw_hz", "vbw_hz"):
            if limit[key] != self.sweep[key]: self.reasons.append(key+" mismatch")
        if limit["distance_m"] != s["distance_m"]: self.reasons.append("distance mismatch; no automatic conversion")
        segments = limit["segments"]
        if not isinstance(segments, list) or not segments: raise ValueError("Nonempty limit segments required")
        previous = None
        for seg in segments:
            exact(seg, ("start_hz", "stop_hz", "start_dbuv_m", "stop_dbuv_m", "interpolation"), "limit segment")
            lo, hi = finite(seg["start_hz"], "start", .001), finite(seg["stop_hz"], "stop", .001)
            finite(seg["start_dbuv_m"], "limit"); finite(seg["stop_dbuv_m"], "limit")
            if lo >= hi or (previous is not None and lo < previous): raise ValueError("Limit segments must be ordered, nonoverlapping")
            if previous is not None and lo > previous and lo > self.sweep["start_hz"] and previous < self.sweep["stop_hz"]:
                self.reasons.append("Limit coverage gap")
            previous = hi
            if seg["interpolation"] not in ("constant", "linear_hz", "linear_log_hz"): raise ValueError("Invalid limit interpolation")
            if seg["interpolation"] == "constant" and seg["start_dbuv_m"] != seg["stop_dbuv_m"]:
                raise ValueError("Constant segment endpoints must agree")
        if segments[0]["start_hz"] > self.sweep["start_hz"] or segments[-1]["stop_hz"] < self.sweep["stop_hz"]:
            self.reasons.append("Limit does not cover sweep")
        d = c["decision"]
        exact(d, ("rule", "expanded_uncertainty_db", "coverage_factor", "source"), "decision")
        if d["rule"] not in ("simple", "guarded"): raise ValueError("Decision rule must be simple or guarded")
        finite(d["expanded_uncertainty_db"], "expanded uncertainty", 0)
        finite(d["coverage_factor"], "coverage factor", 1)
        text(d["source"], "uncertainty source")

    def _provenance(self, item, hardware_kind):
        if item["provenance"] not in ("synthetic", hardware_kind): raise ValueError("Unknown provenance")
        if not self.simulated and item["provenance"] != hardware_kind: raise ValueError("Synthetic provenance forbidden on hardware")

    def _table(self, table, kind):
        exact(table, ("unit", "interpolation", "points", "asset_id", "source", "source_sha256", "provenance", "valid_from", "valid_until"), kind)
        if table["unit"] != COMPONENTS[kind]: raise ValueError("Wrong correction unit: "+kind)
        for key in ("asset_id", "source"): text(table[key], key)
        digest = table["source_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("Certificate SHA256 must be 64 lowercase hex characters")
        self._provenance(table, "calibration_certificate")
        if not self.simulated and digest == "0"*64: raise ValueError("Hardware certificate digest cannot be synthetic placeholder")
        start, end = date.fromisoformat(table["valid_from"]), date.fromisoformat(table["valid_until"])
        if not start <= datetime.now(timezone.utc).date() <= end: raise ValueError("Calibration outside validity dates (UTC)")
        if table["interpolation"] not in ("linear_hz", "linear_log_hz"): raise ValueError("Invalid calibration interpolation")
        points = table["points"]
        if not isinstance(points, list) or len(points) < 2: raise ValueError("At least two calibration points required")
        previous = 0
        for point in points:
            if not isinstance(point, list) or len(point) != 2: raise ValueError("Calibration point must be [Hz, value]")
            hz, value = point
            finite(hz, "calibration Hz", .001); finite(value, "correction")
            if hz <= previous: raise ValueError("Calibration frequencies must strictly increase")
            if kind != "antenna_factor" and value < 0: raise ValueError("Loss/gain magnitudes must be nonnegative")
            previous = hz
        if points[0][0] > self.sweep["start_hz"] or points[-1][0] < self.sweep["stop_hz"]:
            raise ValueError("Calibration does not cover full sweep; extrapolation forbidden")

    def preflight(self):
        return {"config_sha256": self.sha256, "assessment_ready": not self.reasons, "reasons": self.reasons,
                "measurement_sha256": self.measurement_sha256,
                "scope": "declared_limit_comparison", "regulatory_certification": False, "simulated": self.simulated}

    def bind(self, plan, simulated, measurement=None):
        if self.rows or measurement != self.measurement or context(plan, measurement) != (self.sweep, self.paths, self.pols) or simulated != self.simulated:
            raise ValueError("Evaluation must be fresh and match the scan plan and execution mode")

    def _correction(self, table, hz):
        if table is None: return 0
        for (x0, y0), (x1, y1) in zip(table["points"], table["points"][1:]):
            if x0 <= hz <= x1: return interpolate(hz, x0, y0, x1, y1, table["interpolation"])
        raise ValueError("Trace bin outside calibration range")

    def _limit(self, hz):
        values = [interpolate(hz, s["start_hz"], s["start_dbuv_m"], s["stop_hz"], s["stop_dbuv_m"], s["interpolation"])
                  for s in self.config["criterion"]["segments"] if s["start_hz"] <= hz <= s["stop_hz"]]
        return min(values) if values else None  # strictest shared endpoint

    def correct(self, sample):
        trace = sample["trace"]
        if self.measurement is not None:
            from .receiver_measurement import validate_trace
            validate_trace(trace, self.measurement)
        if trace["settings"] != self.sweep: raise ValueError("Returned trace settings mismatch")
        frequencies, values = trace["frequencies_hz"], trace["values_dbm"]
        if len(frequencies) != self.sweep["points"] or len(frequencies) != len(values): raise ValueError("Trace length mismatch")
        timestamp = datetime.fromisoformat(trace["utc"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None: raise ValueError("Trace timestamp must have timezone")
        day = timestamp.astimezone(timezone.utc).date()
        path = sample.get("rf_path", "dut")
        tables = self.config["paths"][path][sample["polarization"]]
        days = [day]
        if self.measurement is not None:
            for point in trace["receiver_points"]:
                timestamp = datetime.fromisoformat(point["utc"].replace("Z", "+00:00"))
                if timestamp.tzinfo is None: raise ValueError("Receiver point timestamp must have timezone")
                days.append(timestamp.astimezone(timezone.utc).date())
        for table in tables.values():
            if table and any(not date.fromisoformat(table["valid_from"]) <= d <= date.fromisoformat(table["valid_until"]) for d in days):
                raise ValueError("Calibration invalid at acquisition time")
        bins = []
        for i, (hz, raw) in enumerate(zip(frequencies, values)):
            finite(hz, "trace frequency", .001); finite(raw, "raw dBm")
            expected = self.measurement["frequencies_hz"][i] if self.measurement is not None else self.sweep["start_hz"] + i*(self.sweep["stop_hz"]-self.sweep["start_hz"])/(len(values)-1)
            if not math.isclose(hz, expected, rel_tol=1e-12, abs_tol=1e-5): raise ValueError("Trace frequency grid mismatch")
            terms = {k: self._correction(t, hz) for k, t in tables.items()}
            voltage = trace["values_dbuv"][i] if self.measurement is not None else raw + CONVERSION_50_OHM
            corrected = voltage + terms["antenna_factor"] + terms["cable_loss"] + terms["switch_loss"] - terms["preamp_gain"]
            finite(corrected, "corrected field")
            limit = self._limit(hz)
            if limit is not None: finite(limit, "interpolated limit")
            margin = limit-corrected if limit is not None else None
            verdict = "NOT_EVALUATED"
            if not self.reasons and margin is not None:
                uncertainty = self.config["decision"]["expanded_uncertainty_db"] if self.config["decision"]["rule"] == "guarded" else 0
                verdict = "PASS" if margin >= uncertainty else "FAIL" if margin < -uncertainty else "INDETERMINATE"
            bins.append({"bin": i, "frequency_hz": hz, "raw_dbm": raw, "conversion_db": CONVERSION_50_OHM,
                         "input_dbuv": voltage, "input_unit": "dBuV" if self.measurement is not None else "dBm",
                         "components": terms, "field_dbuv_m": corrected, "limit_dbuv_m": limit,
                         "margin_db": margin, "verdict": verdict})
        peak = max(bins, key=lambda b: b["field_dbuv_m"])
        compared = [b for b in bins if b["margin_db"] is not None]
        worst = min(compared, key=lambda b: b["margin_db"]) if compared else None
        identity = {k: sample[k] for k in ("index", "height_cm", "angle_deg", "polarization")}
        identity["rf_path"] = path
        result = {"config_sha256": self.sha256, "unit": "dBuV/m", "bins": bins, "peak": peak, "worst_margin": worst}
        sample["evaluation"] = result
        self.rows.append({**identity, "peak": peak, "worst_margin": worst,
                          "verdicts": sorted({b["verdict"] for b in bins})})
        return result

    def summary(self, *, completed):
        verdicts = {v for row in self.rows for v in row["verdicts"]}
        reasons = list(self.reasons)
        if not completed: reasons.append("Run/cleanup/evidence incomplete; partial comparisons are not final")
        if not self.rows: reasons.append("No samples")
        if reasons or "NOT_EVALUATED" in verdicts: verdict = "NOT_EVALUATED"
        elif "FAIL" in verdicts: verdict = "FAIL"
        elif "INDETERMINATE" in verdicts: verdict = "INDETERMINATE"
        else: verdict = "PASS"
        def location(row, key):
            return {**{k: v for k, v in row.items() if k not in ("peak", "worst_margin", "verdicts")}, **row[key]}
        peak = max(self.rows, key=lambda r: r["peak"]["field_dbuv_m"]) if self.rows else None
        compared = [r for r in self.rows if r["worst_margin"] is not None]
        worst = min(compared, key=lambda r: r["worst_margin"]["margin_db"]) if compared else None
        return {**self.preflight(), "verdict": verdict, "reasons": reasons, "samples": len(self.rows),
                "criterion": deepcopy(self.config["criterion"]), "decision": deepcopy(self.config["decision"]),
                "maximum_field": location(peak, "peak") if peak else None,
                "worst_margin": location(worst, "worst_margin") if worst else None}


def assessment_exit(summary):
    if summary.get("status") != "completed": return 130 if summary.get("status") == "cancelled" else 2
    return {"PASS": 0, "FAIL": 4, "INDETERMINATE": 5, "NOT_EVALUATED": 3}.get(summary.get("assessment", {}).get("verdict"), 0)
