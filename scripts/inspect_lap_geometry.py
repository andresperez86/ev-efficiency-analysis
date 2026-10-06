"""Independent preimplementation inspection; no source changes."""
import csv
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

SOURCE = Path('C:/Users/ANDRÉS PÉREZ/Projects/ResultadosGP_limpios/datos_limpios/EIA_clean.csv')
A = (4.954031331051374, -74.02100721093194)
B = (4.954114777761632, -74.02094657622197)
# WGS84 local tangent-plane radii, at A; east/north in meters.
phi = math.radians(A[0])
e2 = 6.69437999014e-3
n = 6378137 / math.sqrt(1-e2*math.sin(phi)**2)
m = 6378137*(1-e2)/(1-e2*math.sin(phi)**2)**1.5
def project(lat, lon):
    return (math.radians(lon-A[1])*n*math.cos(phi), math.radians(lat-A[0])*m)
def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def sub(a,b): return (a[0]-b[0],a[1]-b[1])
def distance(p,a,b):
    d=sub(b,a); t=max(0,min(1,sum(x*y for x,y in zip(sub(p,a),d))/sum(x*x for x in d)))
    return math.hypot(p[0]-a[0]-t*d[0],p[1]-a[1]-t*d[1])
def inspect():
    with SOURCE.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); columns=reader.fieldnames; rows=list(reader)
    points=[project(float(r['gps_1']),float(r['gps_2'])) for r in rows]
    times=[datetime.fromisoformat(r['timestamp']) for r in rows]
    a=(0,0); b=project(*B); candidates=[]; line_passes=[]; steps=[]; gaps=[]
    minimum=min(distance(p,a,b) for p in points)
    for i,(p,q) in enumerate(zip(points,points[1:]),1):
        dt=(times[i]-times[i-1]).total_seconds(); gaps.append(dt)
        step=math.dist(p,q); steps.append(step/dt if dt>0 else float('inf'))
        r=sub(q,p); s=sub(b,a); den=cross(r,s)
        if abs(den)<1e-10: continue
        t=cross(sub(a,p),s)/den; u=cross(sub(a,p),r)/den
        if 0<=t<=1:
            line_passes.append(dict(index=i,seconds=(times[i-1]-times[0]).total_seconds()+t*dt,
                finish_fraction=u,direction=1 if cross(s,r)>0 else -1,
                distance_beyond_segment_m=max(0,-u,u-1)*math.dist(a,b),
                speed=float(rows[i-1]['car_velocity'])+t*(float(rows[i]['car_velocity'])-float(rows[i-1]['car_velocity']))))
        if 0<=t<=1 and 0<=u<=1:
            minimum=0
            candidates.append(dict(index=i,seconds=(times[i-1]-times[0]).total_seconds()+t*dt,
                fraction=t,finish_fraction=u,direction=1 if cross(s,r)>0 else -1,
                speed=float(rows[i-1]['car_velocity'])+t*(float(rows[i]['car_velocity'])-float(rows[i-1]['car_velocity'])),
                timestamp=times[i].isoformat(),
                interpolated_timestamp=(times[i-1]+timedelta(seconds=t*dt)).isoformat(),
                latitude=float(rows[i-1]['gps_1'])+t*(float(rows[i]['gps_1'])-float(rows[i-1]['gps_1'])),
                longitude=float(rows[i-1]['gps_2'])+t*(float(rows[i]['gps_2'])-float(rows[i-1]['gps_2'])),
                heading_degrees=(math.degrees(math.atan2(r[0],r[1]))+360)%360,
                x=p[0]+t*r[0],y=p[1]+t*r[1]))
        else:
            minimum=min(minimum,distance(a,p,q),distance(b,p,q))
    result=dict(columns=columns,rows=len(rows),latitude_range=[min(float(r['gps_1']) for r in rows),max(float(r['gps_1']) for r in rows)],
        longitude_range=[min(float(r['gps_2']) for r in rows),max(float(r['gps_2']) for r in rows)],
        finish_length_m=math.dist(a,b),minimum_trajectory_distance_m=minimum,
        minimum_sample_distance_m=min(distance(p,a,b) for p in points),sampling_s=dict(min=min(gaps),median=median(gaps),max=max(gaps)),
        maximum_gps_speed_mps=max(steps),gps_jump_intervals_over_30_mps=sum(v>30 for v in steps),
        repeated_gps_pairs=sum(p==q for p,q in zip(points,points[1:])),candidates=candidates,
        infinite_line_passes=line_passes,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    out=Path('outputs/reports'); out.mkdir(parents=True,exist_ok=True)
    (out/'lap_geometry_preflight.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    near=[p for p in line_passes if p['direction']==-1 and p['distance_beyond_segment_m']<10]
    misses=[p for p in near if p['distance_beyond_segment_m']>0]
    with (out/'finish_line_near_misses.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(line_passes[0])); writer.writeheader(); writer.writerows(line_passes)
    for number,c in enumerate(candidates,1):
        c['crossing_number']=number
        c['distance_to_finish_segment_m']=distance((c['x'],c['y']),a,b)
        c['time_since_previous_candidate_s']=c['seconds']-candidates[number-2]['seconds'] if number>1 else None
        c['validation_reason']='provisional_race_direction_geometry_matches; direction_not_independently_confirmed' if c['direction']==-1 else 'rejected_wrong_direction_under_inferred_race_direction'
    with Path('outputs/lap_crossings.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(candidates[0])); writer.writeheader(); writer.writerows(candidates)
    report=f'''# Finish-line preimplementation inspection

## Outcome

The supplied A–B is a nondegenerate finite segment and intersects the recorded
GPS polyline twice, in opposite directions. It is not validated as a reliable
lap boundary: {len(misses)} recurring passes miss endpoint B by
{min(p['distance_beyond_segment_m'] for p in misses):.6f}–{max(p['distance_beyond_segment_m'] for p in misses):.6f} m.
This independent inspection preserves source data. A conservative lap pipeline
can report zero complete laps with the exact segment; meaningful comparisons,
Pareto analysis and feature importance require resolution of this geometry issue.

## Source and coordinates

Source: `{SOURCE}`. Rows: {len(rows)}. SHA-256: `{result['source_sha256']}`.
Columns: {', '.join(columns)}.
Latitude is `gps_1`: {result['latitude_range']}; longitude is `gps_2`:
{result['longitude_range']}. Their magnitudes and spatial overlap support this
coordinate order. WGS84 is assumed, not independently confirmed by metadata.
A = {A}; B = {B}; length = {result['finish_length_m']:.6f} m.

Projection: local east/north linear tangent approximation using WGS84 meridional
and prime-vertical radii at A. Geographic degrees are converted to radians and
scaled to meters. The trajectory extends less than 300 m from A, appropriate
for this local approximation. Plot axes have equal scale.

## Sampling and GPS quality

Timestamp spacing min/median/max: {min(gaps):.6f}/{median(gaps):.6f}/{max(gaps):.6f} s;
approximate median frequency = {1/median(gaps):.6f} Hz.
Nonpositive gaps: {sum(v<=0 for v in gaps)}; gaps >5 s: {sum(v>5 for v in gaps)}.
Repeated consecutive GPS pairs: {result['repeated_gps_pairs']}.
Maximum implied GPS speed: {max(steps):.6f} m/s ({max(steps)*3.6:.3f} km/h).
No interval exceeds an exploratory 30 m/s jump threshold. This does not prove
GPS accuracy: maximum reported vehicle speed is only
{max(float(r['car_velocity']) for r in rows):.3f} km/h, and lateral drift/position
uncertainty remains material compared with the short finish segment.
Missing/nonfinite GPS values: {sum(not all(math.isfinite(v) for v in p) for p in points)}.

Minimum GPS-polyline-to-finite-segment distance = 0 m (true intersections).
Minimum recorded-point-to-segment distance = {result['minimum_sample_distance_m']:.6f} m.
These are distinct measurements; nearest-sample distance is not a crossing test.

## Candidate crossings

Direction uses the sign of cross(B−A, P−A): + is left of A→B, − is right.
The {len(near)} recurring near-finish passes travel + to − (left to right).
That is the inferred normal race direction; course/race evidence is still needed
for independent confirmation. The reverse candidate is consistent with a local
reversal, not a second race-direction finish.

| Candidate | Interpolated local timestamp | Speed km/h | Direction | Finish fraction | Interpretation |
|---|---|---:|---|---:|---|
'''
    for c in candidates:
        report+=f"| {c['crossing_number']} | {c['interpolated_timestamp']} | {c['speed']:.6f} | {'left to right' if c['direction']==-1 else 'right to left'} | {c['finish_fraction']:.6f} | {c['validation_reason']} |\n"
    report+='''
Timestamp strings in this source are naive and are interpreted as UTC−05:00,
preserving the established project policy. Intersections are interpolated along
each adjacent GPS segment and its actual timestamp interval.

Under the inferred race direction, only one finite-segment crossing remains:
**zero complete laps**. The two opposite-direction candidates are not a complete
race lap. Choosing either direction produces at most one accepted crossing.
The 30-second separation and 50-meter rearm rules cannot restore crossings that
never intersect the finite segment. Near misses remain diagnostics, never accepted
crossings. No line extension or proximity tolerance has been applied.

## Required clarification

Confirm whether A–B is the exact physical segment, provide corrected endpoints
that span the racing path, or provide evidence of an applicable GPS correction.
The detector must not silently extend B to manufacture laps. A finish tolerance
would change the requested geometric rule and requires an explicit decision.
With strict A–B, a later detector should report zero complete laps.

No original CSV was modified. Existing no-regeneration and validated-discharge
accounting policies remain in force. Electrical high-demand duration remains
descriptive rather than explanatory, because it derives from target channels.

Artifacts: `outputs/figures/gps_track_finish_line.png`,
`outputs/figures/detected_crossings.png`, `outputs/lap_crossings.csv`,
`outputs/reports/lap_geometry_preflight.json`, and
`outputs/reports/finish_line_near_misses.csv` (all infinite-line passes, including
far-away crossings, explicitly diagnostic).
'''
    (out/'lap_detection_report.md').write_text(report,encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==result['source_sha256']
    print(json.dumps(result,indent=2))
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'ev-lap-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    for ax in axes:
        ax.plot(*zip(*points),color='#24618f',lw=.8,label='GPS trajectory')
        ax.plot([a[0],b[0]],[a[1],b[1]],color='#c47720',lw=3,label='Finish A–B')
        ax.scatter([a[0],b[0]],[a[1],b[1]],color='#c47720')
        for c in candidates:
            ax.scatter(c['x'],c['y'],color='#333333',s=18)
        ax.set_aspect('equal'); ax.set_xlabel('East of A (m)'); ax.set_ylabel('North of A (m)'); ax.grid(alpha=.2)
    axes[0].set_title('EIA GPS trajectory and finish segment'); axes[0].legend()
    axes[1].set_xlim(-25,25); axes[1].set_ylim(-20,35); axes[1].set_title('Finish-line detail: geometric candidates')
    fig.tight_layout(); Path('outputs/figures').mkdir(exist_ok=True)
    fig.savefig('outputs/figures/gps_track_finish_line.png',dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,7))
    ax.plot(*zip(*points),color='#24618f',lw=.7,label='GPS trajectory')
    ax.plot([a[0],b[0]],[a[1],b[1]],color='#c47720',lw=3,label='Exact finish A–B')
    ax.annotate('A',a,xytext=(6,-12),textcoords='offset points')
    ax.annotate('B',b,xytext=(6,6),textcoords='offset points')
    for j,c in enumerate(candidates):
        ax.scatter(c['x'],c['y'],color='#333333',marker='o' if c['direction']==-1 else 'x',s=70,
            label='Candidate 1: inferred race direction' if j==0 else 'Candidate 2: reverse direction')
        ax.annotate(str(j+1),(c['x'],c['y']),xytext=(8,0),textcoords='offset points')
    for p in misses:
        ax.scatter(b[0]*p['finish_fraction'],b[1]*p['finish_fraction'],facecolors='none',edgecolors='#c47720',s=40)
    ax.scatter([],[],facecolors='none',edgecolors='#c47720',label='Infinite-line near misses: excluded')
    ax.set_xlim(-25,30); ax.set_ylim(-20,45); ax.set_aspect('equal'); ax.grid(alpha=.2)
    ax.set_xlabel('East of A (m)'); ax.set_ylabel('North of A (m)')
    ax.set_title('Finite finish segment: two opposite-direction candidates')
    ax.legend(loc='upper left',fontsize=8); fig.tight_layout()
    fig.savefig('outputs/figures/detected_crossings.png',dpi=180); plt.close(fig)
if __name__=='__main__': inspect()
