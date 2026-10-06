from datetime import datetime, timedelta, timezone
from math import nan

import pytest

from ev_analysis.contracts import Config, Sample
from ev_analysis.ingestion import load_csv
from ev_analysis.metrics import account, make_intervals, wh_per_km
from ev_analysis.quality import flag_samples


def samples(times=(0, 2, 5), powers=(360, 360, 360), speeds=(36, 36, 36),
            trips=(0, 0.02, 0.05), volts=(50, 50, 50)) -> list[Sample]:
    origin = datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=-5)))
    return [Sample(i + 2, origin + timedelta(seconds=t), s, d, v,
                   p / v if v else 0, p, 4.95, -74.02, str(t), "False", "1")
            for i, (t, p, s, d, v) in enumerate(zip(times, powers, speeds, trips, volts))]


def summarize(data: list[Sample], config: Config = Config()) -> dict:
    return account(make_intervals(data, flag_samples(data, config), config), data)


def test_irregular_timestamp_integration_and_distance() -> None:
    result = summarize(samples())
    assert result["consumed_wh"] == pytest.approx(0.5)
    assert result["distance_km"] == pytest.approx(0.05)
    assert result["wh_per_km"] == pytest.approx(10)
    assert result["average_power_w"] == pytest.approx(360)
    assert result["moving_wh_per_km"] == pytest.approx(10)


def test_trapezoidal_power() -> None:
    result = summarize(samples(times=(0, 2), powers=(0, 720), speeds=(36, 36), trips=(0, .02), volts=(50, 50)))
    assert result["consumed_wh"] == pytest.approx(.2)


def test_negative_power_is_flagged_and_clipped_never_recovered() -> None:
    data = samples(times=(0, 2), powers=(-360, 360), speeds=(36, 36), trips=(0, .02), volts=(50, 50))
    assert "negative_power" in flag_samples(data, Config())[0]
    result = summarize(data)
    assert result["consumed_wh"] == pytest.approx(.1)
    assert result["raw_signed_wh_diagnostic"] == pytest.approx(0)


def test_shutdown_and_boundary_are_excluded() -> None:
    data = samples(times=(0, 1, 2, 3), powers=(360, 360, 0, 0),
                   speeds=(36, 36, 0, 0), trips=(0, .01, .01, .01), volts=(50, 50, 0, 0))
    flags = flag_samples(data, Config())
    assert "shutdown_post_run" in flags[-1]
    result = summarize(data)
    assert result["consumed_wh"] == pytest.approx(.1)
    assert result["distance_km"] == pytest.approx(.01)
    assert result["excluded_interval_count"] == 2


def test_shutdown_includes_stationary_voltage_collapse_before_zero() -> None:
    data = samples(times=(0, 1, 2), powers=(360, .1, 0),
                   speeds=(0, 0, 0), trips=(0, 0, 0), volts=(50, 3, 0))
    flags = flag_samples(data, Config())
    assert 'shutdown_post_run' not in flags[0]
    assert 'shutdown_post_run' in flags[1]
    assert summarize(data)['consumed_wh'] == 0


def test_early_low_voltage_is_not_terminal_shutdown() -> None:
    data = samples(volts=(3, 50, 50))
    assert 'shutdown_post_run' not in flag_samples(data, Config())[0]


def test_stationary_energy_and_zero_distance() -> None:
    result = summarize(samples(speeds=(0, 0, 0), trips=(4, 4, 4)))
    assert result["stationary_wh"] == pytest.approx(.5)
    assert result["stopped_s"] == pytest.approx(5)
    assert result["wh_per_km"] is None
    assert result["moving_wh_per_km"] is None


def test_moving_stop_crossing_partitions_energy_and_distance() -> None:
    result = summarize(samples(times=(0, 2), powers=(360, 360), speeds=(0, 2), trips=(0, .001), volts=(50, 50)))
    assert result["moving_s"] == pytest.approx(1)
    assert result["stopped_s"] == pytest.approx(1)
    assert result["stationary_wh"] == pytest.approx(.1)
    assert result["moving_wh"] == pytest.approx(.1)
    assert result["moving_distance_km"] == pytest.approx(.0005)


@pytest.mark.parametrize("field", ["power_w", "speed_kmh", "trip_km", "voltage_v", "current_a"])
def test_missing_nonfinite_values_exclude_adjacent_intervals(field: str) -> None:
    from dataclasses import replace
    data = samples()
    data[1] = replace(data[1], **{field: nan})
    assert summarize(data)["consumed_wh"] == 0
    assert summarize(data)["excluded_interval_count"] == 2


def test_long_gaps_not_bridged() -> None:
    result = summarize(samples(times=(0, 2, 12)))
    assert result["consumed_wh"] == pytest.approx(.2)
    assert result["excluded_interval_count"] == 1


def test_reversed_distance_excluded() -> None:
    result = summarize(samples(trips=(0, .02, .01)))
    assert result["distance_km"] == pytest.approx(.02)
    assert result["excluded_interval_count"] == 1


def test_nonpositive_time_excluded() -> None:
    assert summarize(samples(times=(0, 0, 2)))["excluded_interval_count"] == 1


def test_invalid_voltage_excluded_even_if_power_positive() -> None:
    data = samples(volts=(-50, 50, 50))
    assert summarize(data)["consumed_wh"] == pytest.approx(.3)


def test_input_errors() -> None:
    with pytest.raises(ValueError):
        make_intervals([], [], Config())
    with pytest.raises(ValueError):
        wh_per_km(-1, 1)
    with pytest.raises(ValueError):
        Config(max_gap_s=0)
    with pytest.raises(ValueError):
        Config(moving_threshold_kmh=-1)
    with pytest.raises(ValueError):
        make_intervals(samples(), [], Config())


def test_csv_missing_and_timezone(tmp_path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("timestamp,car_velocity,car_trip,car_voltage,car_current,power,gps_1,gps_2,timestamp_original,retroceso_detectado,segmento\n2025-01-01 12:00:00,0,0,50,0,,4.95,-74.02,2025-01-01 12:00:00,False,1\n", encoding="utf-8")
    data = load_csv(path)
    assert data[0].timestamp.utcoffset().total_seconds() == -18000
    assert "nonfinite_power_w" in flag_samples(data, Config())[0]


def test_csv_invalid_schema(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        load_csv(path)
