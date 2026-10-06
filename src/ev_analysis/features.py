"""Nonoverlapping operating-period features; these periods are not laps."""

from math import ceil, fsum, sqrt

from .contracts import Config, Interval, Sample
from .metrics import account, clip_interval, integral, movement_parts

EXPLANATORY_FEATURES = (
    "average_speed_kmh", "median_speed_kmh", "max_speed_kmh", "speed_std_kmh",
    "p10_speed_kmh", "p90_speed_kmh", "stopped_pct", "stop_count",
    "acceleration_event_count", "acceleration_pct", "deceleration_event_count",
    "deceleration_pct", "speed_0_16_pct", "speed_16_32_pct", "speed_32_40_pct",
    "speed_40_plus_pct",
)


def weighted_quantile(values: list[tuple[float, float]], probability: float) -> float | None:
    if not values:
        return None
    target = fsum(w for _, w in values) * probability
    cumulative = 0.0
    for value, weight in sorted(values):
        cumulative += weight
        if cumulative >= target:
            return value
    return max(v for v, _ in values)


def band_duration(interval: Interval, low: float, high: float) -> float:
    a, b = interval.fraction_start, interval.fraction_end
    v0, v1 = interval.left.speed_kmh, interval.right.speed_kmh
    cuts = [a, b]
    if v0 != v1:
        cuts += [f for bound in (low, high) if a < (f := (bound - v0) / (v1 - v0)) < b]
    cuts.sort()
    return fsum((right - left) / (b - a) * interval.duration_s for left, right in zip(cuts, cuts[1:])
                if low <= interval.value("speed_kmh", (left + right) / 2) < high)


def build_windows(intervals: list[Interval], samples: list[Sample], config: Config) -> list[dict]:
    end = max((i.end_s for i in intervals), default=0)
    windows = []
    for index in range(ceil(end / config.window_s)):
        start, stop = index * config.window_s, min((index + 1) * config.window_s, end)
        parts = [p for i in intervals if (p := clip_interval(i, start, stop)) is not None]
        valid = [p for p in parts if p.valid]
        metrics = account(parts, [])
        duration = metrics["valid_duration_s"]
        midpoint_speeds = [(p.value("speed_kmh", (p.fraction_start + p.fraction_end) / 2), p.duration_s) for p in valid]
        mean = metrics["average_speed_kmh"]
        second = fsum(p.duration_s * (p.value("speed_kmh", p.fraction_start)**2
                      + p.value("speed_kmh", p.fraction_start)*p.value("speed_kmh", p.fraction_end)
                      + p.value("speed_kmh", p.fraction_end)**2) / 3 for p in valid) / duration if duration else 0
        counts = {"acceleration_event_count": 0, "deceleration_event_count": 0, "stop_count": 0}
        accel_s = decel_s = 0.0
        previous_state = None
        previous_moving = None
        previous_end = None
        for p in valid:
            if previous_end is not None and abs(p.start_s - previous_end) > 1e-6:
                previous_state = previous_moving = None
            original_dt = (p.right.timestamp - p.left.timestamp).total_seconds()
            acceleration = (p.right.speed_kmh - p.left.speed_kmh) / 3.6 / original_dt
            state = 1 if acceleration >= config.acceleration_threshold_mps2 else -1 if acceleration <= -config.acceleration_threshold_mps2 else 0
            if state == 1:
                accel_s += p.duration_s
                if previous_state != 1:
                    counts["acceleration_event_count"] += 1
            elif state == -1:
                decel_s += p.duration_s
                if previous_state != -1:
                    counts["deceleration_event_count"] += 1
            for _, moving in movement_parts(p):
                if not moving and previous_moving is not False:
                    counts["stop_count"] += 1
                previous_moving = moving
            previous_state, previous_end = state, p.end_s
        complete = abs(stop - start - config.window_s) < 1e-6
        eligible = complete and bool(duration) and duration / config.window_s >= config.minimum_window_coverage and metrics["distance_km"] > 0
        row = {"period_id": index, "start_s": start, "end_s": stop,
               "complete_window": complete, "model_eligible": eligible,
               "period_note": "Fixed-time operating period, not a lap", **metrics,
               "median_speed_kmh": weighted_quantile(midpoint_speeds, .5),
               "max_speed_kmh": max((p.value("speed_kmh", f) for p in valid for f in (p.fraction_start, p.fraction_end)), default=None),
               "speed_std_kmh": sqrt(max(0, second - mean**2)) if duration else None,
               "p10_speed_kmh": weighted_quantile(midpoint_speeds, .1),
               "p90_speed_kmh": weighted_quantile(midpoint_speeds, .9),
               "stopped_pct": 100 * metrics["stopped_s"] / duration if duration else None,
               "acceleration_pct": 100 * accel_s / duration if duration else None,
               "deceleration_pct": 100 * decel_s / duration if duration else None,
               "pace_seconds_per_km": duration / metrics["distance_km"] if metrics["distance_km"] else None,
               **counts}
        for label, low, high in (("speed_0_16_pct", 0, 16), ("speed_16_32_pct", 16, 32),
                                 ("speed_32_40_pct", 32, 40), ("speed_40_plus_pct", 40, float("inf"))):
            row[label] = 100 * fsum(band_duration(p, low, high) for p in valid) / duration if duration else None
        windows.append(row)
    return windows
