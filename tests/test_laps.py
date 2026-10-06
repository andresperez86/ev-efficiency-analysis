"""Analytic geometric and crossing-boundary fixtures, written before implementation."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from ev_analysis.contracts import Config, Sample
from ev_analysis.laps import LocalProjection, segment_intersection, detect_crossings, assign_laps, summarize_laps

ORIGIN = datetime(2025, 1, 1, tzinfo=timezone.utc)
PROJECTION = LocalProjection(0, 0)
A = PROJECTION.inverse(0, -10)
B = PROJECTION.inverse(0, 10)

def sample(t, x, y=0, speed=36, power=3600, trip=None):
    lat, lon = PROJECTION.inverse(x, y)
    return Sample(int(t)+2, ORIGIN+timedelta(seconds=t), speed,
                  t/100 if trip is None else trip, 50, power/50, power,
                  lat, lon, '', 'False', '1')

def race():
    # Eastward valid crossings at 1, 41, 81 seconds, with 60m rearming.
    return [sample(0,-10), sample(2,10), sample(10,60), sample(20,60,30),
            sample(30,-60,30), sample(40,-10), sample(42,10), sample(50,60),
            sample(60,60,30), sample(70,-60,30), sample(80,-10),sample(82,10)]

def detect(samples, **kwargs):
    return detect_crossings(samples, A, B, expected_direction=-1, **kwargs)

def test_coordinate_projection():
    assert PROJECTION.project(0, .001)[0] == pytest.approx(111.31949, abs=.001)
    assert PROJECTION.project(.001, 0)[1] == pytest.approx(110.57428, abs=.001)
    assert PROJECTION.inverse(*PROJECTION.project(4.95,-74.02)) == pytest.approx((4.95,-74.02))

def test_segment_intersection():
    assert segment_intersection((-2,0),(2,0),(0,-1),(0,1)) == pytest.approx((.5,.5))
    assert segment_intersection((0,0),(0,0),(0,-1),(0,1)) is None
    assert segment_intersection((0,-2),(0,2),(0,-1),(0,1)) is None  # collinear, no transverse crossing

def test_correct_finish_crossing():
    crossings=detect([sample(0,-10),sample(2,10)])
    assert len(crossings)==1 and crossings[0]['accepted']
    assert crossings[0]['distance_to_finish_segment_m'] == pytest.approx(0,abs=1e-8)

def test_outside_finite_segment():
    assert detect([sample(0,-10,20),sample(2,10,20)]) == []

def test_wrong_direction():
    crossing=detect([sample(0,10),sample(2,-10)])[0]
    assert not crossing['accepted'] and 'wrong_direction' in crossing['reason']

def test_gps_oscillation():
    crossings=detect([sample(0,-1),sample(2,1),sample(4,-1),sample(40,1)],max_gap_s=60)
    assert sum(c['accepted'] for c in crossings)==1
    assert 'not_rearmed' in crossings[-1]['reason']

def test_duplicate_suppression_at_endpoint():
    crossings=detect([sample(0,-10),sample(1,0),sample(2,10)])
    assert sum(c['accepted'] for c in crossings)==1

def test_minimum_30_seconds():
    points=[sample(0,-10),sample(2,10),sample(4,60),sample(6,60,30),
            sample(8,-60,30),sample(10,-10),sample(12,10)]
    crossings=detect(points)
    assert 'minimum_crossing_interval' in crossings[-1]['reason']

def test_rearm_requires_50_meters():
    points=[sample(0,-10),sample(2,10),sample(10,49),sample(20,49,11),
            sample(30,-49,11),sample(40,-10),sample(42,10)]
    assert 'not_rearmed' in detect(points,max_gap_s=120)[-1]['reason']
    points[2]=sample(10,50)
    assert detect(points,max_gap_s=120)[-1]['accepted']

def test_partial_first_lap():
    points=race(); labels=assign_laps(points,detect(points,max_gap_s=120))
    assert labels[0]['lap_status']=='partial_start' and labels[0]['lap_id'] is None

def test_partial_final_lap():
    points=race(); labels=assign_laps(points,detect(points,max_gap_s=120))
    assert labels[-1]['lap_status']=='partial_end' and labels[-1]['lap_id'] is None

def test_complete_lap_assignment():
    points=race(); labels=assign_laps(points,detect(points,max_gap_s=120))
    assert labels[1]['lap_id']==1 and labels[6]['lap_id']==2
    assert labels[1]['lap_status']=='complete'
    assert labels[1]['seconds_into_lap']==pytest.approx(1)
    assert labels[1]['distance_into_lap_km']==pytest.approx(.01)

def test_interpolated_timestamp():
    crossing=detect([sample(0,-10),sample(2,30)])[0]
    assert crossing['elapsed_s']==pytest.approx(.5)
    assert datetime.fromisoformat(crossing['interpolated_timestamp'])==ORIGIN+timedelta(seconds=.5)

def summaries(points=None):
    points=race() if points is None else points
    return summarize_laps(points,detect(points,max_gap_s=120),Config(max_gap_s=120),A)

def test_lap_duration():
    assert [r['lap_duration_s'] for r in summaries()]==pytest.approx([40,40])

def test_lap_distance():
    assert [r['trip_distance_km'] for r in summaries()]==pytest.approx([.4,.4])
    assert summaries()[0]['lap_distance_km']==pytest.approx(.4)
    assert summaries()[0]['gps_distance_km']>0

def test_energy_integration():
    assert summaries()[0]['consumed_wh']==pytest.approx(40)
    # Unequal intervals and linearly varying power: boundary clipping must conserve quadrature.
    points=race(); points=[replace(p,power_w=3600+100*(p.timestamp-ORIGIN).total_seconds(),
        current_a=(3600+100*(p.timestamp-ORIGIN).total_seconds())/50) for p in points]
    assert summaries(points)[0]['consumed_wh']==pytest.approx((3600+100*21)*40/3600)

def test_wh_per_km():
    assert summaries()[0]['wh_per_km']==pytest.approx(100)

def test_negative_energy_is_not_regeneration():
    points=[replace(p,power_w=-50,current_a=-1) for p in race()]
    assert summaries(points)[0]['consumed_wh']==0
    assert summaries(points)[0]['negative_power_samples']>0

def test_stationary_rejected():
    assert 'not_moving' in detect([sample(0,-10,speed=0),sample(2,10,speed=0)])[0]['reason']

def test_long_gap_and_jump_rejected():
    assert 'timestamp_gap' in detect([sample(0,-10),sample(40,10)])[0]['reason']
    assert 'gps_jump' in detect([sample(0,-60),sample(1,60)])[0]['reason']

def test_zero_crossings_are_unassigned():
    assert all(p['lap_status']=='unassigned_no_crossing' for p in assign_laps(race(),[]))

def test_invalid_electrical_support_matches_distance():
    points=race(); points[3]=replace(points[3],voltage_v=0)
    row=summaries(points)[0]
    assert row['coverage_fraction']<1
    assert row['lap_distance_km']<row['trip_distance_km']
    assert row['wh_per_km']==pytest.approx(100)

def test_touch_and_return_is_not_crossing():
    assert not any(c['accepted'] for c in detect([sample(0,-10),sample(1,0),sample(2,-10)]))

def test_lap_energy_partition_conserves_clipped_support():
    from ev_analysis.metrics import account, clip_interval, make_intervals
    from ev_analysis.quality import flag_samples
    points=race(); config=Config(max_gap_s=120)
    intervals=make_intervals(points,flag_samples(points,config),config)
    parts=[p for i in intervals if (p:=clip_interval(i,1,81)) is not None]
    assert sum(r['consumed_wh'] for r in summaries())==pytest.approx(account(parts,[])['consumed_wh'])

def test_lap_export_preserves_source(tmp_path):
    import csv
    import hashlib
    from ev_analysis.ingestion import COLUMNS
    from ev_analysis.lap_pipeline import run_lap_analysis
    source=tmp_path/'source.csv'
    with source.open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(COLUMNS)
        for s in race():
            writer.writerow([s.timestamp.isoformat(),s.speed_kmh,s.trip_km,s.voltage_v,
                s.current_a,s.power_w,s.latitude,s.longitude,'','False','1'])
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    result=run_lap_analysis(source,tmp_path/'out',finish_a=A,finish_b=B,
        direction=-1,direction_confirmed=True,config=Config(max_gap_s=120))
    assert len(result['lap_dataframe'])==2
    assert result['lap_dataframe'].iloc[0]['consumed_wh']==pytest.approx(40)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    for name in ['lap_crossings.csv','lap_summary.csv','telemetry_with_laps.csv']:
        assert (tmp_path/'out'/name).is_file()
    assert len(list((tmp_path/'out'/'figures').glob('*.png')))==7
    assert result['modeling_status']=='not_run'
