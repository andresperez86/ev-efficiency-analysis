from math import nan

import pytest

from ev_analysis.contracts import Config
from ev_analysis.features import build_windows, EXPLANATORY_FEATURES
from ev_analysis.eda import pearson, spearman, pareto_front, relationship_table
from ev_analysis.modeling import model_importance
from ev_analysis.metrics import make_intervals
from ev_analysis.quality import flag_samples
from test_metrics import samples


def test_nonoverlapping_windows_clip_at_exact_boundaries() -> None:
    data = samples(times=(0, 2, 4), powers=(360, 360, 360),
                   speeds=(36, 36, 36), trips=(0, .02, .04))
    cfg = Config(window_s=2)
    windows = build_windows(make_intervals(data, flag_samples(data, cfg), cfg), data, cfg)
    assert len(windows) == 2
    assert sum(w['consumed_wh'] for w in windows) == pytest.approx(.4)
    assert [w['wh_per_km'] for w in windows] == pytest.approx([10, 10])
    assert windows[0]['average_speed_kmh'] == pytest.approx(36)
    assert windows[0]['speed_std_kmh'] == pytest.approx(0)
    assert windows[0]['stopped_pct'] == pytest.approx(0)


def test_partial_window_and_zero_distance_not_model_eligible() -> None:
    data = samples(times=(0, 2, 3), speeds=(0, 0, 0), trips=(0, 0, 0))
    cfg = Config(window_s=2)
    windows = build_windows(make_intervals(data, flag_samples(data, cfg), cfg), data, cfg)
    assert len(windows) == 2
    assert not any(w['model_eligible'] for w in windows)
    assert windows[-1]['complete_window'] is False


def test_target_components_never_in_feature_allowlist() -> None:
    assert not {'power', 'current', 'voltage', 'consumed_wh', 'distance_km',
                'wh_per_km', 'average_power_w', 'peak_current_a'} & set(EXPLANATORY_FEATURES)


def test_correlations_and_tied_ranks() -> None:
    assert pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert spearman([1, 1, 2], [4, 4, 5]) == pytest.approx(1)
    assert pearson([1, 1, 1], [1, 2, 3]) is None
    assert pearson([1, nan], [2, 3]) is None
    with pytest.raises(ValueError):
        pearson([1, 2], [1])


def test_pareto_minimize_energy_maximize_speed() -> None:
    periods = [{'period_id': i, 'wh_per_km': e, 'average_speed_kmh': s}
               for i, (e, s) in enumerate([(10, 30), (12, 40), (13, 20), (10, 30)])]
    assert pareto_front(periods) == [0, 1, 3]


def test_relationship_table_excludes_ineligible_rows() -> None:
    periods = [{'model_eligible': True, 'period_id': v, 'wh_per_km': v, **{f: v for f in EXPLANATORY_FEATURES}}
               for v in range(1, 7)]
    periods.append({'model_eligible': False})
    results = relationship_table(periods)
    assert all(r['n'] == 6 for r in results)
    assert results[0]['pearson'] == pytest.approx(1)


def test_modeling_rejects_too_few_periods() -> None:
    assert model_importance([])['status'] == 'insufficient_periods'


def test_sparse_binary_feature_does_not_get_misleading_bootstrap_interval() -> None:
    periods = [{'model_eligible': True, 'period_id': i, 'wh_per_km': float(i+1),
                **{f: float(i) for f in EXPLANATORY_FEATURES}, 'stop_count': int(i == 3)}
               for i in range(12)]
    stop = next(r for r in relationship_table(periods) if r['feature'] == 'stop_count')
    assert stop['sparse_feature_warning'] is True
    assert stop['spearman_block_bootstrap_p025'] is None


def test_optional_modeling_dependency_gate(monkeypatch) -> None:
    import builtins
    original_import = builtins.__import__
    def no_numpy(name, *args, **kwargs):
        if name == 'numpy':
            raise ImportError('not installed')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_numpy)
    periods = [{'model_eligible': True} for _ in range(25)]
    assert model_importance(periods)['status'] == 'dependencies_unavailable'


def test_modeling_known_signal_when_dependencies_available() -> None:
    pytest.importorskip('numpy')
    pytest.importorskip('sklearn')
    periods = [{'model_eligible': True, 'period_id': i, 'wh_per_km': 10 + i * .1,
                **{f: float(i) for f in EXPLANATORY_FEATURES}} for i in range(48)]
    result = model_importance(periods)
    assert result['status'] == 'computed'
    assert len(result['folds']) == 3
    assert all(f['train_end_period'] < f['test_start_period'] for f in result['folds'])
    assert len(result['importance']) == len(EXPLANATORY_FEATURES)
