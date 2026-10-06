"""Explicit sample flags and an inspectable source profile."""

from math import isfinite
from statistics import fmean, median, pstdev

from .contracts import Config, Sample
from .ingestion import NUMERIC


def flag_samples(samples: list[Sample], config: Config) -> list[set[str]]:
    flags: list[set[str]] = []
    for sample in samples:
        issues = {f"nonfinite_{field}" for field in NUMERIC.values()
                  if not isfinite(getattr(sample, field))}
        for field, label in (("power_w", "negative_power"), ("current_a", "negative_current"),
                             ("voltage_v", "negative_voltage"), ("speed_kmh", "negative_speed")):
            if getattr(sample, field) < 0:
                issues.add(label)
        if sample.voltage_v <= config.minimum_voltage_v:
            issues.add("invalid_voltage_state")
        if isfinite(sample.latitude) and not -90 <= sample.latitude <= 90:
            issues.add("invalid_latitude")
        if isfinite(sample.longitude) and not -180 <= sample.longitude <= 180:
            issues.add("invalid_longitude")
        if all(isfinite(v) for v in (sample.power_w, sample.voltage_v, sample.current_a)):
            if abs(sample.power_w - sample.voltage_v * sample.current_a) > max(1.0, abs(sample.power_w) * .01):
                issues.add("power_vi_inconsistent")
        flags.append(issues)
    # Only a trailing stationary low-voltage run is classified as shutdown.
    for index in range(len(samples) - 1, -1, -1):
        s = samples[index]
        if (isfinite(s.voltage_v) and abs(s.voltage_v) <= config.shutdown_voltage_v
                and isfinite(s.speed_kmh) and 0 <= s.speed_kmh <= config.moving_threshold_kmh):
            flags[index].add("shutdown_post_run")
        else:
            break
    return flags


def numeric_summary(values: list[float]) -> dict:
    finite = sorted(v for v in values if isfinite(v))
    if not finite:
        return {"finite_count": 0, "nonfinite_count": len(values)}
    def quantile(p: float) -> float:
        pos = (len(finite) - 1) * p
        lo = int(pos)
        hi = min(lo + 1, len(finite) - 1)
        return finite[lo] + (finite[hi] - finite[lo]) * (pos - lo)
    q1, q3 = quantile(.25), quantile(.75)
    iqr = q3 - q1
    return {"finite_count": len(finite), "nonfinite_count": len(values) - len(finite),
            "min": finite[0], "p25": q1, "median": median(finite), "p75": q3,
            "max": finite[-1], "mean": fmean(finite), "std": pstdev(finite),
            "unique_count": len(set(finite)), "negative_count": sum(v < 0 for v in finite),
            "iqr_outlier_count_diagnostic": sum(v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr for v in finite)}


def profile(samples: list[Sample], columns: list[str], records: list[dict[str, str]],
            flags: list[set[str]]) -> dict:
    if not samples:
        raise ValueError("Empty dataset")
    times = [s.timestamp for s in samples]
    dt = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    counts = {label: sum(label in f for f in flags) for label in sorted(set().union(*flags))}
    return {"rows": len(samples), "columns": len(columns),
            "time_start": min(times).isoformat(), "time_end": max(times).isoformat(),
            "sampling_interval_s": numeric_summary(dt),
            "missing_values": {c: sum(r.get(c) is None or r[c].strip().lower() in
                                      ("", "nan", "null", "none", "na", "n/a") for r in records) for c in columns},
            "duplicate_rows": len(records) - len(set(tuple(r.get(c) for c in columns) for r in records)),
            "duplicate_timestamps": len(times) - len(set(times)),
            "nonpositive_intervals": sum(t <= 0 for t in dt),
            "constant_columns": [c for c in columns if len(set(r.get(c) for r in records)) == 1],
            "trip_decreases": sum(b.trip_km < a.trip_km for a, b in zip(samples, samples[1:])),
            "timestamp_changed_rows": sum(r["timestamp"] != r["timestamp_original"] for r in records),
            "numeric": {column: numeric_summary([getattr(s, field) for s in samples]) for column, field in NUMERIC.items()},
            "quality_flag_counts": counts,
            "speed_levels_kmh": sorted(set(s.speed_kmh for s in samples if isfinite(s.speed_kmh))),
            "shutdown_start": next((s.timestamp.isoformat() for s, f in zip(samples, flags) if "shutdown_post_run" in f), None)}
