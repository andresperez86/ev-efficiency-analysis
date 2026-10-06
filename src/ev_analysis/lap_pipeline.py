"""Reproducible lap exports; geometry approval does not imply model validation."""
import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .contracts import Config
from .ingestion import load_csv, read_records
from .laps import (FINISH_A, FINISH_B, LocalProjection, detect_crossings,
                   assign_laps, summarize_laps, point_segment_distance, valid_gps)
from .quality import flag_samples

SUMMARY_COLUMNS = ['lap_id','lap_status','start_timestamp','end_timestamp','lap_duration_s',
    'lap_distance_km','trip_distance_km','gps_distance_km','gps_minus_trip_distance_km',
    'gps_coverage_fraction','average_speed_kmh','median_speed_kmh','max_speed_kmh',
    'speed_std_kmh','moving_average_speed_kmh','stopped_s','moving_s','stopped_pct',
    'consumed_wh','wh_per_km','average_power_w','peak_power_w','average_current_a',
    'peak_current_a','voltage_mean_v','voltage_min_v','voltage_std_v','voltage_variation_v',
    'acceleration_event_count','deceleration_event_count','cruising_duration_s','stop_count',
    'high_power_duration_s','high_current_duration_s','missing_samples','irregular_timestamp_gaps',
    'negative_current_samples','negative_power_samples','gps_jumps','invalid_electrical_measurements',
    'shutdown_samples','coverage_fraction','model_eligible']


def write_csv(path, rows, columns=None):
    columns=columns or list(rows[0]) if rows else columns or []
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader(); writer.writerows(rows)


def render_figures(samples,crossings,laps,output,finish_a,finish_b,max_gap_s=5):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'ev-lap-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    projection=LocalProjection(*finish_a); a=(0,0); b=projection.project(*finish_b)
    # NaN separators prevent visually bridging invalid GPS.
    points=[projection.project(s.latitude,s.longitude) if valid_gps(s) else (float('nan'),float('nan')) for s in samples]
    def save(fig,name):
        fig.tight_layout(); fig.savefig(output/name,dpi=180); plt.close(fig)
    def setup(ax,xlabel,ylabel,title):
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title); ax.grid(alpha=.2)
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax in axes:
        ax.plot(*zip(*points),color='#24618f',lw=.8,label='GPS trajectory')
        ax.plot([0,b[0]],[0,b[1]],color='#c47720',lw=3,label='Finish A–B')
        ax.scatter([0,b[0]],[0,b[1]],color='#c47720')
        ax.set_aspect('equal'); setup(ax,'East of A (m)','North of A (m)','GPS trajectory and exact finish segment')
    axes[0].legend(); axes[1].set_xlim(-25,30); axes[1].set_ylim(-20,45)
    axes[1].set_title('Finish-line detail'); save(fig,'gps_track_finish_line.png')
    fig,ax=plt.subplots(figsize=(9,7))
    ax.plot(*zip(*points),color='#24618f',lw=.7,label='GPS trajectory')
    ax.plot([0,b[0]],[0,b[1]],color='#c47720',lw=3,label='Exact finish A–B')
    ax.annotate('A',a,xytext=(6,-12),textcoords='offset points'); ax.annotate('B',b,xytext=(6,6),textcoords='offset points')
    for c in crossings:
        p=projection.project(c['latitude'],c['longitude'])
        ax.scatter(*p,color='#333333',marker='o' if c['accepted'] else 'x',s=65,
            label=f"Candidate {c['candidate_id']}: {'accepted under supplied direction' if c['accepted'] else c['reason']}")
        ax.annotate(str(c['candidate_id']),p,xytext=(8,0),textcoords='offset points')
    ax.set_xlim(-25,30); ax.set_ylim(-20,45); ax.set_aspect('equal')
    setup(ax,'East of A (m)','North of A (m)','Finite-segment crossing validation')
    ax.legend(loc='upper left',fontsize=8); save(fig,'detected_crossings.png')
    def empty(ax):
        ax.text(.5,.5,'No complete laps with the exact finish segment',ha='center',va='center',transform=ax.transAxes)
        ax.set_axis_off()
    for name,field,label in [('wh_per_km_by_lap.png','wh_per_km','Consumed energy per distance (Wh/km)'),
                             ('lap_time_by_lap.png','lap_duration_s','Lap duration (s)')]:
        fig,ax=plt.subplots(figsize=(9,5))
        if laps: ax.bar([r['lap_id'] for r in laps],[r[field] if r[field] is not None else float('nan') for r in laps],color='#24618f'); ax.set_xticks([r['lap_id'] for r in laps])
        else: empty(ax)
        setup(ax,'Complete lap',label,label+' by complete lap'); save(fig,name)
    fig,ax=plt.subplots(figsize=(9,5))
    if laps:
        for r in laps:
            if r['wh_per_km'] is None: continue
            ax.scatter(r['lap_duration_s'],r['wh_per_km'],marker='o' if r['pareto_efficient'] else 'x',
                       color='#24618f' if r['pareto_efficient'] else '#777777')
            ax.annotate(f"Lap {r['lap_id']}",(r['lap_duration_s'],r['wh_per_km']),xytext=(5,5),textcoords='offset points')
        ax.scatter([],[],color='#24618f',label='Pareto efficient: time and Wh/km'); ax.legend()
    else: empty(ax)
    setup(ax,'Lap duration (s)','Consumed energy per distance (Wh/km)','Efficiency versus lap duration'); save(fig,'efficiency_vs_lap_time.png')
    # Profile figures are descriptive raw-channel interpolations, including
    # negative electrical readings; these are not consumption integration.
    for name,field,label in [('speed_profiles_by_lap.png','speed_kmh','Speed (km/h)'),
                            ('power_profiles_by_lap.png','power_w','Raw power (W; negative values are flagged)')]:
        fig,ax=plt.subplots(figsize=(10,6)); colors=['#24618f','#c47720','#6d7857','#a26385','#555555']
        accepted=[c for c in crossings if c['accepted']]
        for j,r in enumerate(laps):
            start,end=accepted[j]['elapsed_s'],accepted[j+1]['elapsed_s']
            origin=samples[0].timestamp
            for k,(left,right) in enumerate(zip(samples,samples[1:])):
                lo=(left.timestamp-origin).total_seconds(); hi=(right.timestamp-origin).total_seconds()
                if hi<=lo or hi-lo>max_gap_s: continue
                a,b=max(start,lo),min(end,hi)
                if b<=a: continue
                values=[getattr(left,field)+(getattr(right,field)-getattr(left,field))*(v-lo)/(hi-lo) for v in (a,b)]
                ax.plot([a-start,b-start],values,color=colors[j%len(colors)],lw=1,
                    label=f"Lap {r['lap_id']}" if lo<=start<hi else None)
        if laps:
            handles,labels=ax.get_legend_handles_labels()
            if handles: ax.legend(fontsize=8,ncol=3)
        else: empty(ax)
        setup(ax,'Seconds into complete lap',label,label+' by complete lap'); save(fig,name)


def run_lap_analysis(source,output,*,finish_a=FINISH_A,finish_b=FINISH_B,direction=-1,
                     direction_confirmed=False,config=Config(),high_power_w=800,high_current_a=20):
    import pandas as pd
    source,output=Path(source),Path(output)
    output.mkdir(parents=True,exist_ok=True); reports=output/'reports'; reports.mkdir(exist_ok=True)
    figures=output/'figures'; figures.mkdir(exist_ok=True)
    # Guard the source against accidental export collisions.
    export_paths=[output/n for n in ('lap_crossings.csv','lap_summary.csv','telemetry_with_laps.csv')]
    if source.resolve() in [p.resolve() for p in export_paths]: raise ValueError('Output would overwrite source')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    samples=load_csv(source); columns,records=read_records(source)
    if len(samples)<2: raise ValueError('At least two samples are required')
    if not any(valid_gps(s) for s in samples): raise ValueError('No valid GPS coordinates')
    from math import isfinite
    if any(not isfinite(v) or v<=0 for v in (high_power_w,high_current_a)):
        raise ValueError('High-demand thresholds must be finite and positive')
    crossings=detect_crossings(samples,finish_a,finish_b,expected_direction=direction,
        max_gap_s=config.max_gap_s,moving_threshold_kmh=config.moving_threshold_kmh)
    labels=assign_laps(samples,crossings)
    laps=summarize_laps(samples,crossings,config,finish_a,high_power_w=high_power_w,high_current_a=high_current_a)
    for r in laps:
        r['pareto_efficient']=r['model_eligible'] and r['wh_per_km'] is not None and not any(
            other['model_eligible'] and other['wh_per_km'] is not None and
            other['wh_per_km']<=r['wh_per_km'] and other['lap_duration_s']<=r['lap_duration_s'] and
            (other['wh_per_km']<r['wh_per_km'] or other['lap_duration_s']<r['lap_duration_s']) for other in laps)
    lap_columns=list(laps[0]) if laps else SUMMARY_COLUMNS+['pareto_efficient']
    if not laps:
        from math import isfinite
        for level in sorted({s.speed_kmh for s in samples if isfinite(s.speed_kmh) and s.speed_kmh>=0}):
            tag=f'{level:.8f}'.rstrip('0').rstrip('.')
            lap_columns.extend([f'speed_level_{tag}_s',f'speed_level_{tag}_pct'])
    dataframe=pd.DataFrame(laps,columns=lap_columns); dataframe.to_csv(output/'lap_summary.csv',index=False)
    crossing_columns=list(crossings[0]) if crossings else ['candidate_id','crossing_id','timestamp',
        'interpolated_timestamp','elapsed_s','latitude','longitude','speed_kmh','direction','direction_label',
        'distance_to_finish_segment_m','time_since_previous_crossing_s','accepted','reason',
        'left_source_row','right_source_row','vehicle_fraction','finish_fraction','trip_at_crossing_km']
    write_csv(output/'lap_crossings.csv',crossings,crossing_columns)
    flags=flag_samples(samples,config)
    # GPS annotations do not alter electrical accounting. They expose intervals
    # that are inadmissible for crossing validation or GPS-derived distance.
    projection=LocalProjection(*finish_a)
    from math import hypot
    for index,(left,right) in enumerate(zip(samples,samples[1:]),1):
        dt=(right.timestamp-left.timestamp).total_seconds()
        if not 0<dt<=config.max_gap_s:
            flags[index].add('gps_timestamp_gap')
        if valid_gps(left) and valid_gps(right):
            a,b=projection.project(left.latitude,left.longitude),projection.project(right.latitude,right.longitude)
            distance=hypot(b[0]-a[0],b[1]-a[1])
            if distance==0: flags[index].add('repeated_gps_point')
            elif dt>0 and distance/dt>30: flags[index].add('gps_jump')
    telemetry=[dict(record,**label,source_row=s.source_row,quality_flags=';'.join(sorted(flag)))
        for record,label,s,flag in zip(records,labels,samples,flags)]
    write_csv(output/'telemetry_with_laps.csv',telemetry)
    render_figures(samples,crossings,laps,figures,finish_a,finish_b,config.max_gap_s)
    projection=LocalProjection(*finish_a); b=projection.project(*finish_b)
    accepted=[c for c in crossings if c['accepted']]
    dt=[(y.timestamp-x.timestamp).total_seconds() for x,y in zip(samples,samples[1:])]
    from statistics import median
    points=[projection.project(s.latitude,s.longitude) for s in samples if valid_gps(s)]
    minimum_sample=min((point_segment_distance(p,(0,0),b) for p in points),default=None)
    gps_speeds=[]
    for left,right in zip(samples,samples[1:]):
        gap=(right.timestamp-left.timestamp).total_seconds()
        if gap>0 and valid_gps(left) and valid_gps(right):
            p,q=projection.project(left.latitude,left.longitude),projection.project(right.latitude,right.longitude)
            gps_speeds.append(hypot(q[0]-p[0],q[1]-p[1])/gap)
    detection=f'''# Lap detection report

Source: `{source}`; {len(samples)} rows. SHA-256: `{before}`.
Original columns: {', '.join(columns)}.
Latitude `gps_1` range: {min(s.latitude for s in samples if valid_gps(s))} to {max(s.latitude for s in samples if valid_gps(s))}.
Longitude `gps_2` range: {min(s.longitude for s in samples if valid_gps(s))} to {max(s.longitude for s in samples if valid_gps(s))}.
Finish A: {finish_a}; B: {finish_b}; finite length {hypot(*b):.6f} m.
Projection: WGS84 local east/north tangent approximation at A; datum is assumed.
GPS-polyline distance to line is zero where true candidate intersections exist;
nearest recorded GPS point distance is {minimum_sample} m.
Timestamp spacing min/median/max: {min(dt):.6f}/{median(dt):.6f}/{max(dt):.6f} s.
Approximate median sampling frequency: {1/median(dt) if median(dt)>0 else None} Hz.
Nonpositive timestamp gaps: {sum(v<=0 for v in dt)}; gaps above policy: {sum(v>config.max_gap_s for v in dt)}.
Maximum GPS interval speed: {max(gps_speeds,default=0):.6f} m/s.
Intervals above GPS jump threshold: {sum(v>30 for v in gps_speeds)}.
Repeated consecutive GPS pairs: {sum('repeated_gps_point' in f for f in flags)}.
Maximum reported vehicle speed: {max(s.speed_kmh for s in samples if isfinite(s.speed_kmh)):.6f} km/h.
GPS speed exceeding reported vehicle speed merits calibration/jitter review;
the exploratory jump threshold is not proof of positional accuracy.
GPS jump policy: reject interval-implied speed >30 m/s; no interpolation across
invalid coordinates, nonpositive time differences or gaps >{config.max_gap_s} s.

Candidate intersections: {len(crossings)}. Accepted under selected direction: {len(accepted)}.
Complete laps: {len(laps)}. Direction: {direction} ({'left to right' if direction==-1 else 'right to left'} relative to A→B).
Direction independently confirmed: {direction_confirmed}.
For the supplied EIA geometry, preflight inferred left-to-right from recurring
passes. It found twelve passes beyond B by 0.073–5.410 m, so the physical segment
is nondegenerate but does not reliably span the recorded racing path. The reverse
candidate occurs amid stop/start readings. See `lap_geometry_preflight.json` and
`finish_line_near_misses.csv` for the independent preimplementation inspection.
No infinite-line crossing, endpoint extension or proximity tolerance is accepted.

| Candidate | Interpolated timestamp | Speed km/h | Direction | Accepted | Reason |
|---|---|---:|---|---|---|
'''
    for c in crossings:
        detection+=f"| {c['candidate_id']} | {c['interpolated_timestamp']} | {c['speed_kmh']:.6f} | {c['direction_label']} | {c['accepted']} | {c['reason']} |\n"
    detection+='''
Only finite transverse intersections count. The crossing must be moving (>1 km/h),
in the selected direction, at least 30 seconds after the previous accepted
crossing, and armed by a trustworthy GPS sample at least 50 meters away from
the finite finish segment (numerical tolerance 1 micrometer). A line touch with
no confirmed side change is rejected. Rearming is spatial distance from the
line, not cumulative path length. Rejected candidates do not reset these rules.
Crossing time, GPS location, speed and trip are interpolated within the original
adjacent interval. `timestamp` is the right-hand source timestamp;
`interpolated_timestamp` is the crossing timestamp. Timestamps use UTC−05:00.

Telemetry labels use half-open lap intervals: before first crossing is
`partial_start`, after final crossing is `partial_end`, between accepted
crossings is `complete`. With no crossings use `unassigned_no_crossing`.
With one crossing there are two partial segments and zero complete laps.
`crossing_id` is the most recent accepted crossing, not a nearest-sample event.
`distance_into_lap` and `distance_into_lap_km` use trip increments in km;
these per-sample annotations are descriptive, not the accounting denominator.

See `detected_crossings.png` and `gps_track_finish_line.png` for visual review.
The supplied exact geometry requires clarification before claiming validated
race laps. Models remain gated; acceptance here is conditional on direction.
'''
    (reports/'lap_detection_report.md').write_text(detection,encoding='utf-8')
    efficiency='''# Lap efficiency report

Consumed Wh integrates max(endpoint power,0) over actual elapsed seconds with
trapezoidal quadrature, after established electrical quality/shutdown exclusions.
Boundary clipping preserves the original clipped-endpoint linear power function.
There is no recovered energy or regenerative braking. Negative readings are
flagged; raw signed Wh is diagnostic only. No original data is modified.

Primary `lap_distance_km` is accepted trip distance over the same support as
consumed energy. `trip_distance_km` is the complete boundary-to-boundary trip
increment. GPS distance has its own gap/jump-filtered coverage. Their difference
is reported without treating GPS as an authoritative odometer. Coverage must
be inspected before comparisons. Zero accepted distance produces undefined Wh/km.

Speed statistics follow existing time-weighted piecewise-linear conventions;
median is a duration-weighted midpoint approximation. Discrete-level exposure
uses nearest observed-level regions, not exact instantaneous plateau time.
Event counts reset at lap boundaries and invalid intervals. Cruising requires
moving speed and acceleration magnitude below 0.5 m/s². High-power and current
thresholds are exploratory policies (default 800 W/20 A), not engineering limits.
Quality sample counts use timestamps in [lap start,lap end); touching interval
exclusions still affect both sides of each boundary.

Electrical high-demand durations are descriptive relationships only. They remain
excluded from explanatory importance because they use target channels. Driving
features are candidate associations, not causal interventions. Race pace and
Wh/km may be mathematically coupled; the lowest-energy lap is not automatically
the best strategy. Pareto selection minimizes both Wh/km and lap duration among
laps with >=90% accepted accounting duration and positive accepted distance.

'''
    if not laps:
        efficiency+='**Zero complete laps.** Lap rankings, relationships, Pareto selection and\nimportance cannot be estimated. The five comparison/profile PNGs explicitly\nshow this status. Resolve finish geometry before interpreting lap behavior.\n'
    else:
        eligible=[r for r in laps if r['model_eligible'] and r['wh_per_km'] is not None]
        efficiency+='| Comparison | Lap | Value |\n|---|---:|---:|\n'
        for label,field,fn in [('Fastest','lap_duration_s',min),('Slowest','lap_duration_s',max),
                ('Lowest Wh/km','wh_per_km',min),('Highest Wh/km','wh_per_km',max),
                ('Lowest consumed Wh','consumed_wh',min),('Highest consumed Wh','consumed_wh',max)]:
            if eligible:
                r=fn(eligible,key=lambda r:r[field]); efficiency+=f"| {label} | {r['lap_id']} | {r[field]:.6f} |\n"
        efficiency+='\nAll requested speed, stopped-time, electrical-demand and quality metrics are in `lap_summary.csv`.\n'
        efficiency+=f"Pareto-efficient lap IDs: {[r['lap_id'] for r in laps if r['pareto_efficient']]}.\n"
        if len(eligible)>=3:
            frame=pd.DataFrame(eligible); relations=[]
            for field in ['lap_duration_s','average_speed_kmh','max_speed_kmh','speed_std_kmh','stopped_s','high_power_duration_s']:
                relations.append({'variable':field,'pearson':frame['wh_per_km'].corr(frame[field],method='pearson'),
                    'spearman':frame['wh_per_km'].corr(frame[field],method='spearman')})
            pd.DataFrame(relations).to_csv(reports/'lap_associations.csv',index=False)
            efficiency+='Exploratory Pearson/Spearman relationships: `lap_associations.csv`; small samples and constant predictors may be undefined.\n'
        else: efficiency+='Too few complete laps for useful relationship estimates.\n'
    efficiency+='\nMI, Random Forest, permutation importance and SHAP were **not run**: lap reconstruction requires validation before modeling.\n'
    (reports/'lap_efficiency_report.md').write_text(efficiency,encoding='utf-8')
    after=hashlib.sha256(source.read_bytes()).hexdigest()
    if before!=after: raise RuntimeError('Source hash changed during analysis')
    manifest=dict(source=str(source),source_sha256=before,source_preserved=True,finish_a=finish_a,finish_b=finish_b,
        expected_direction=direction,direction_confirmed=direction_confirmed,minimum_crossing_interval_s=30,
        rearm_distance_m=50,max_gps_speed_mps=30,high_power_w=high_power_w,high_current_a=high_current_a,
        accounting_config=config.__dict__,complete_laps=len(laps),modeling_status='not_run',
        lap_validation_status='pending_finish_geometry_and_direction_confirmation' if not direction_confirmed else 'requires_lap_review')
    import sys
    import importlib.metadata
    manifest['python']=sys.version.split()[0]
    manifest['packages']={name:importlib.metadata.version(name) for name in ('pandas','matplotlib')}
    (reports/'lap_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return dict(lap_dataframe=dataframe,crossings=crossings,modeling_status='not_run',manifest=manifest)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True); parser.add_argument('--output',type=Path,default=Path('outputs'))
    parser.add_argument('--finish-a',type=float,nargs=2,default=FINISH_A,metavar=('LAT','LON'))
    parser.add_argument('--finish-b',type=float,nargs=2,default=FINISH_B,metavar=('LAT','LON'))
    parser.add_argument('--direction',type=int,choices=(-1,1),default=-1,help='-1: left to right relative to A→B; +1: reverse')
    parser.add_argument('--direction-confirmed',action='store_true',help='Record external confirmation of selected race direction')
    parser.add_argument('--high-power-w',type=float,default=800); parser.add_argument('--high-current-a',type=float,default=20)
    args=parser.parse_args()
    result=run_lap_analysis(args.source,args.output,finish_a=args.finish_a,finish_b=args.finish_b,
        direction=args.direction,direction_confirmed=args.direction_confirmed,
        high_power_w=args.high_power_w,high_current_a=args.high_current_a)
    print(json.dumps(result['manifest'],indent=2))


if __name__=='__main__': main()
