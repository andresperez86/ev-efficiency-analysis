"""Interval-based electrical accounting with matching energy/distance support."""

from dataclasses import replace
from math import fsum, isfinite

from .contracts import Config, Interval, Sample

REQUIRED_FIELDS = ("speed_kmh", "trip_km", "voltage_v", "current_a", "power_w")


def wh_per_km(energy_wh: float, distance_km: float) -> float | None:
    if not all(isfinite(v) and v >= 0 for v in (energy_wh, distance_km)):
        raise ValueError("Energy and distance must be finite and nonnegative")
    return energy_wh / distance_km if distance_km > 0 else None


def make_intervals(samples: list[Sample], flags: list[set[str]], config: Config) -> list[Interval]:
    if len(samples) < 2 or len(flags) != len(samples):
        raise ValueError("Need at least two samples and one flag set per sample")
    origin = samples[0].timestamp
    intervals = []
    for i, (a, b) in enumerate(zip(samples, samples[1:])):
        dt = (b.timestamp - a.timestamp).total_seconds()
        combined = flags[i] | flags[i + 1]
        reasons = {f for f in combined if f in
                   {"shutdown_post_run", "invalid_voltage_state", "negative_speed", "power_vi_inconsistent"}
                   or f in {f"nonfinite_{field}" for field in REQUIRED_FIELDS}}
        if dt <= 0:
            reasons.add("nonpositive_timestamp_interval")
        if dt > config.max_gap_s:
            reasons.add("long_gap")
        if b.trip_km < a.trip_km:
            reasons.add("distance_reversal")
        intervals.append(Interval(a, b, (a.timestamp - origin).total_seconds(),
                                  (b.timestamp - origin).total_seconds(), not reasons,
                                  tuple(sorted(reasons)), config.moving_threshold_kmh))
    return intervals


def clip_interval(interval: Interval, start_s: float, end_s: float) -> Interval | None:
    lo, hi = max(interval.start_s, start_s), min(interval.end_s, end_s)
    if hi <= lo or interval.duration_s <= 0:
        return None
    span = interval.fraction_end - interval.fraction_start
    return replace(interval, start_s=lo, end_s=hi,
                   fraction_start=interval.fraction_start + span * (lo - interval.start_s) / interval.duration_s,
                   fraction_end=interval.fraction_start + span * (hi - interval.start_s) / interval.duration_s)


def integral(interval: Interval, field: str, *, consumption: bool = False) -> float:
    a = interval.value(field, interval.fraction_start, consumption=consumption)
    b = interval.value(field, interval.fraction_end, consumption=consumption)
    return (a + b) * .5 * interval.duration_s


def movement_parts(interval: Interval) -> list[tuple[Interval, bool]]:
    lo, hi = interval.fraction_start, interval.fraction_end
    v0, v1 = interval.left.speed_kmh, interval.right.speed_kmh
    cuts = [lo, hi]
    if v1 != v0:
        crossing = (interval.moving_threshold_kmh - v0) / (v1 - v0)
        if lo < crossing < hi:
            cuts.insert(1, crossing)
    parts = []
    for a, b in zip(cuts, cuts[1:]):
        start = interval.start_s + (a - lo) / (hi - lo) * interval.duration_s
        end = interval.start_s + (b - lo) / (hi - lo) * interval.duration_s
        part = replace(interval, start_s=start, end_s=end, fraction_start=a, fraction_end=b)
        parts.append((part, interval.value("speed_kmh", (a + b) / 2) > interval.moving_threshold_kmh))
    return parts


def account(intervals: list[Interval], samples: list[Sample]) -> dict:
    valid = [i for i in intervals if i.valid]
    duration = fsum(i.duration_s for i in valid)
    energy = fsum(integral(i, "power_w", consumption=True) for i in valid) / 3600
    distance = fsum(i.value("trip_km", i.fraction_end) - i.value("trip_km", i.fraction_start) for i in valid)
    moving_wh = stationary_wh = moving_distance = moving_s = stopped_s = 0.0
    for interval in valid:
        for part, moving in movement_parts(interval):
            e = integral(part, "power_w", consumption=True) / 3600
            if moving:
                moving_wh += e
                moving_s += part.duration_s
                moving_distance += part.value("trip_km", part.fraction_end) - part.value("trip_km", part.fraction_start)
            else:
                stationary_wh += e
                stopped_s += part.duration_s
    def mean(field: str, consumption: bool = False) -> float | None:
        return fsum(integral(i, field, consumption=consumption) for i in valid) / duration if duration else None
    def extrema(field: str, kind) -> float | None:
        values = [i.value(field, f) for i in valid for f in (i.fraction_start, i.fraction_end)]
        return kind(values) if values else None
    raw = [i for i in intervals if i.duration_s > 0
           and isfinite(i.left.power_w) and isfinite(i.right.power_w)]
    voltage_mean = mean("voltage_v")
    voltage_variance = fsum(i.duration_s * (i.value("voltage_v", i.fraction_start)**2
                           + i.value("voltage_v", i.fraction_start)*i.value("voltage_v", i.fraction_end)
                           + i.value("voltage_v", i.fraction_end)**2) / 3 for i in valid) / duration if duration else None
    elapsed = max((i.end_s for i in intervals), default=0) - min((i.start_s for i in intervals), default=0)
    return {"consumed_wh": energy, "distance_km": distance,
            "wh_per_km": wh_per_km(energy, distance), "moving_wh": moving_wh,
            "moving_distance_km": moving_distance, "moving_wh_per_km": wh_per_km(moving_wh, moving_distance),
            "stationary_wh": stationary_wh, "moving_s": moving_s, "stopped_s": stopped_s,
            "valid_duration_s": duration, "elapsed_duration_s": elapsed,
            "coverage_fraction": duration / elapsed if elapsed > 0 else None,
            "valid_interval_count": len(valid), "excluded_interval_count": len(intervals) - len(valid),
            "raw_signed_wh_diagnostic": fsum(integral(i, "power_w") for i in raw) / 3600,
            "raw_diagnostic_note": "Includes shutdown and long gaps; not valid consumption or recovered energy.",
            "average_power_w": mean("power_w", True), "peak_power_w": extrema("power_w", max),
            "average_current_a": mean("current_a", True), "peak_current_a": extrema("current_a", max),
            "current_mean_note": "Time weighted, clipped at zero at samples; raw values retained in quality tables.",
            "voltage_mean_v": voltage_mean, "voltage_min_v": extrema("voltage_v", min),
            "voltage_max_v": extrema("voltage_v", max),
            "voltage_std_v": max(0, voltage_variance - voltage_mean**2)**.5 if duration else None,
            "average_speed_kmh": mean("speed_kmh"),
            "trip_increment_all_rows_km": samples[-1].trip_km - samples[0].trip_km if samples else None}
