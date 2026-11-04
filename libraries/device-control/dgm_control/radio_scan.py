"""Source-neutral facility scan; rank acquired samples and confirm peak-position return."""
from dataclasses import asdict
from contextlib import ExitStack
from dgm_lab.core import InstrumentError
from .radio_adapters import checkpoint, pause


def position_matches(states, pose):
    return (not any(s.busy for s in states) and abs(states[0].value-pose["height_cm"]) <= .1
            and abs(states[1].value-pose["angle_deg"]) <= .1 and states[0].polarization == "P"+pose["polarization"])


def measure_radio_scan(lab, token, event, fault=None, evaluation=None):
    plan, evidence = lab.plan, lab.evidence
    scan = plan["scan"]
    config = lab.measurement_config
    if evaluation is not None: evaluation.bind(plan, lab.simulated, config)
    reference = {"height_cm": scan["heights_cm"][0], "angle_deg": scan["angles_deg"][0], "polarization": scan["polarizations"][0]}
    samples, baselines = [], []
    with ExitStack() as stack, lab.open("Co3000") as motion, lab.open("OspSwitch") as route, lab.open("SpectrumAnalyzer") as analyzer:
        receiver = stack.enter_context(lab.open("EmiReceiver")) if config is not None else None
        if receiver is not None: stack.enter_context(receiver.active())
        def positions(): return [motion.call("position", axis=axis) for axis in ("MA1", "DT1")]

        def observe(phase, pose, path, *, fail=True):
            states = positions()
            matched = route.call("matches", name=path)
            row = {"phase": phase, "requested_pose": pose, "rf_path": path,
                   "positions": [asdict(s) for s in states], "route_matches": matched}
            evidence.write("observations.jsonl", row)
            valid = position_matches(states, pose) and matched
            if fail and not valid: raise InstrumentError("Scan position/polarization/route readback mismatch: " + phase)
            return row, valid

        def move(pose):
            checkpoint(token)
            states = positions()
            if states[0].busy or states[1].busy: raise InstrumentError("Cannot begin scan move: axis already busy")
            if states[0].polarization != "P"+pose["polarization"]:
                motion.call("polarize", axis="MA1", orientation=pose["polarization"], timeout=scan["motion_timeout"], cancelled=token.is_set)
            for axis, value, state in (("MA1", pose["height_cm"], states[0]), ("DT1", pose["angle_deg"], states[1])):
                if abs(state.value-value) > .1:
                    motion.call("move", axis=axis, value=value, timeout=scan["motion_timeout"], cancelled=token.is_set)
            pause(scan["settle_seconds"], token)

        # No switching between measurement paths while a source context is active.
        checkpoint(token)
        with motion.active(), route.active(name=scan["rf_paths"][0]), analyzer.active():
            for path in scan["rf_paths"]:
                checkpoint(token)
                lab.current_path = path
                route.call("select", name=path)
                move(reference)
                observe("reference-before-source", reference, path)
                before = lab.acquire(analyzer, "before-source")
                evidence.require_healthy()
                if plan["radio"] == "nfc" and before["peak_dbm"] > plan["verification"]["off_threshold_dbm"]:
                    raise InstrumentError("NFC reference baseline is not quiet")
                # Quiet RF at a moved antenna/null cannot prove OFF. Check fixed geometry on every NFC callback.
                lab.verification_guard = lambda: observe("nfc-reference-check", reference, path, fail=False)[1]
                try:
                    with lab.active_source(analyzer, token):
                        pause(plan["settle_seconds"], token)
                        for polarization in scan["polarizations"]:
                            for height in scan["heights_cm"]:
                                for angle in scan["angles_deg"]:
                                    pose = {"height_cm": height, "angle_deg": angle, "polarization": polarization}
                                    move(pose)
                                    for repeat in range(plan["sample_count"]):
                                        checkpoint(token)
                                        pre, _ = observe("before-sample", pose, path)
                                        if receiver is None:
                                            row = lab.acquire(analyzer, "sample")
                                        else:
                                            from .receiver_measurement import acquire_grid
                                            def save_point(point):
                                                evidence.write("observations.jsonl", {**point, **pose, "rf_path": path, "repeat": repeat, "sample_index": len(samples)})
                                                evidence.require_healthy()
                                            trace = acquire_grid(receiver, config, lambda: checkpoint(token), save_point)
                                            row = {"phase": "sample", "trace": trace, "peak_dbm": max(trace["values_dbm"]), "simulated": lab.simulated}
                                        post, _ = observe("after-sample", pose, path)
                                        checkpoint(token)
                                        row.update(index=len(samples), repeat=repeat, radio=plan["radio"], backend=plan["backend"],
                                                   rf_path=path, **pose, position_before=pre, position_after=post)
                                        if evaluation is not None: evaluation.correct(row)
                                        evidence.sample(row)
                                        samples.append(row)
                                        if fault == "cancel-after-sample": event.set()
                                        checkpoint(token)
                        if plan["radio"] == "nfc":
                            move(reference)
                            observe("reference-before-stop", reference, path)
                finally:
                    lab.verification_guard = None
                after = lab.acquire(analyzer, "after-source")
                baselines.append({"rf_path": path, "before": before, "after": after})
                checkpoint(token)
            peak = max(samples, key=lambda row: row["evaluation"]["peak"]["field_dbuv_m"] if evaluation is not None else row["peak_dbm"])
            # Source is already stopped; switch and move to the best acquired point.
            checkpoint(token)
            lab.current_path = peak["rf_path"]
            route.call("select", name=peak["rf_path"])
            peak_pose = {key: peak[key] for key in reference}
            move(peak_pose)
            returned, _ = observe("returned-to-sampled-peak", peak_pose, peak["rf_path"])
            evidence.require_healthy()
            checkpoint(token)
        # active() already attempted source OFF, analyzer abort, safe route, and all-axis ES.
        safe_path = lab.facility_parameters("OspSwitch")["safe_path"]
        final, _ = observe("after-facility-cleanup", peak_pose, safe_path)
        evidence.require_healthy()
        checkpoint(token)
        return {"radio": plan["radio"], "backend": plan["backend"], "sample_count": len(samples),
                "sampled_peak": {key: peak[key] for key in ("index", "repeat", "rf_path", "height_cm", "angle_deg", "polarization", "peak_dbm")},
                "returned_to_sampled_peak": True, "peak_return_readback": returned, "final_facility_readback": final,
                "peak_trace_dbm": peak["peak_dbm"], "path_baselines": baselines,
                "ranking": "corrected_field_dbuv_m" if evaluation is not None else "raw_trace_dbm",
                "note": "Maximum among acquired samples only; not a continuous/global/FCC maximum. Final RF route is safe_path."}
