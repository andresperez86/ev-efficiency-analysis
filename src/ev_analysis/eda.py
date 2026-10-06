"""Descriptive relationships and efficiency/performance comparisons."""

from math import fsum, isfinite, sqrt
from collections import Counter
from random import Random
from statistics import fmean, median

from .features import EXPLANATORY_FEATURES


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y):
        raise ValueError("Correlation vectors must have equal lengths")
    pairs = [(a, b) for a, b in zip(x, y) if isfinite(a) and isfinite(b)]
    if len(pairs) < 3:
        return None
    a, b = zip(*pairs)
    ma, mb = fmean(a), fmean(b)
    va, vb = fsum((v - ma)**2 for v in a), fsum((v - mb)**2 for v in b)
    if va == 0 or vb == 0:
        return None
    return max(-1.0, min(1.0, fsum((u - ma)*(v - mb) for u, v in pairs) / sqrt(va * vb)))


def ranks(values: list[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        for i in ordered[start:end]:
            result[i] = (start + end + 1) / 2
        start = end
    return result


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y):
        raise ValueError("Correlation vectors must have equal lengths")
    pairs = [(a, b) for a, b in zip(x, y) if isfinite(a) and isfinite(b)]
    if not pairs:
        return None
    a, b = zip(*pairs)
    return pearson(ranks(list(a)), ranks(list(b)))


def relationship_table(windows: list[dict], seed: int = 42) -> list[dict]:
    eligible = [w for w in windows if w["model_eligible"]]
    table = []
    for field in EXPLANATORY_FEATURES:
        pairs = [(w[field], w["wh_per_km"], w["period_id"]) for w in eligible
                 if isinstance(w.get(field), (int, float)) and isfinite(w[field])]
        x, y = [p[0] for p in pairs], [p[1] for p in pairs]
        r, rho = pearson(x, y), spearman(x, y)
        counts = Counter(x)
        sparse = len(counts) <= 2 and (not counts or min(counts.values()) < 3)
        # Exploratory moving-block bootstrap; never cross an excluded period.
        blocks = [pairs[i:i+3] for i in range(max(0, len(pairs)-2))
                  if pairs[i+2][2] - pairs[i][2] == 2]
        bootstrap = []
        rng = Random(seed)
        if len(pairs) >= 9 and blocks and not sparse:
            for _ in range(300):
                draw = []
                while len(draw) < len(pairs):
                    draw.extend(rng.choice(blocks))
                draw = draw[:len(pairs)]
                value = spearman([p[0] for p in draw], [p[1] for p in draw])
                if value is not None:
                    bootstrap.append(value)
        bootstrap.sort()
        score = fmean(abs(v) for v in (r, rho) if v is not None) if r is not None or rho is not None else None
        table.append({"feature": field, "n": len(pairs), "pearson": r, "spearman": rho,
                      "association_score": score,
                      "unique_feature_values": len(set(x)), "nonzero_periods": sum(v != 0 for v in x),
                      "sparse_feature_warning": sparse,
                      "bootstrap_valid_replicates": len(bootstrap),
                      "direction_disagrees": r is not None and rho is not None and r * rho < 0,
                      "spearman_block_bootstrap_p025": bootstrap[int(.025*(len(bootstrap)-1))] if bootstrap else None,
                      "spearman_block_bootstrap_p975": bootstrap[int(.975*(len(bootstrap)-1))] if bootstrap else None,
                      "interpretation": "Descriptive association; no causal claim; exploratory bootstrap, not multiplicity adjusted"})
    table.sort(key=lambda row: row["association_score"] if row["association_score"] is not None else -1, reverse=True)
    for i, row in enumerate(table, 1):
        row["descriptive_rank"] = i
    return table


def pareto_front(windows: list[dict]) -> list[int]:
    return [w["period_id"] for w in windows if not any(
        v["wh_per_km"] <= w["wh_per_km"] and v["average_speed_kmh"] >= w["average_speed_kmh"]
        and (v["wh_per_km"] < w["wh_per_km"] or v["average_speed_kmh"] > w["average_speed_kmh"])
        for v in windows)]


def compare_periods(windows: list[dict]) -> dict:
    eligible = [w for w in windows if w["model_eligible"]]
    if not eligible:
        return {"eligible_count": 0}
    ordered = sorted(eligible, key=lambda w: w["wh_per_km"])
    size = max(1, len(ordered) // 4)
    def summarize(group: list[dict]) -> dict:
        return {f: median([w[f] for w in group]) for f in ("wh_per_km", "average_speed_kmh", "stopped_pct", "speed_std_kmh", "acceleration_pct")}
    # Same-session pace matching is exploratory and does not control course position.
    pairs = []
    for i, a in enumerate(eligible):
        for b in eligible[i+1:]:
            if abs(a["average_speed_kmh"] - b["average_speed_kmh"]) <= 2:
                efficient, inefficient = sorted((a, b), key=lambda w: w["wh_per_km"])
                pairs.append({"efficient_period": efficient["period_id"], "inefficient_period": inefficient["period_id"],
                              "difference_wh_per_km": inefficient["wh_per_km"] - efficient["wh_per_km"],
                              "speed_difference_kmh": inefficient["average_speed_kmh"] - efficient["average_speed_kmh"]})
    return {"eligible_count": len(eligible), "most_efficient_period": ordered[0]["period_id"],
            "least_efficient_period": ordered[-1]["period_id"],
            "fastest_period": max(eligible, key=lambda w: w["average_speed_kmh"])["period_id"],
            "slowest_period": min(eligible, key=lambda w: w["average_speed_kmh"])["period_id"],
            "pareto_periods": pareto_front(eligible), "efficient_quartile_medians": summarize(ordered[:size]),
            "inefficient_quartile_medians": summarize(ordered[-size:]),
            "pace_matched_pairs_2kmh": sorted(pairs, key=lambda p: p["difference_wh_per_km"], reverse=True)}
