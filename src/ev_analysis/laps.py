"""Finite directed finish crossings and boundary-clipped lap accounting.

No source mutations, line extension, regeneration or missing-data interpolation.
"""
from bisect import bisect_right
from dataclasses import dataclass, replace
from datetime import timedelta
from math import cos, sin, radians, degrees, sqrt, hypot, isfinite, fsum, inf

from .contracts import Config, Sample
from .features import build_windows, band_duration
from .metrics import make_intervals, clip_interval, integral, movement_parts
from .quality import flag_samples

FINISH_A = (4.954031331051374, -74.02100721093194)
FINISH_B = (4.954155352342866, -74.02092561319948)


@dataclass(frozen=True)
class LocalProjection:
    """WGS84 local east/north approximation for a small race course."""
    latitude: float
    longitude: float

    def __post_init__(self):
        if not (isfinite(self.latitude) and abs(self.latitude)<89
                and isfinite(self.longitude) and abs(self.longitude)<=180):
            raise ValueError('Local projection requires finite nonpolar geographic origin')

    @property
    def scales(self):
        phi=radians(self.latitude); e2=6.69437999014e-3
        return (6378137/sqrt(1-e2*sin(phi)**2)*cos(phi),
                6378137*(1-e2)/(1-e2*sin(phi)**2)**1.5)

    def project(self, latitude, longitude):
        east,north=self.scales
        return radians(longitude-self.longitude)*east, radians(latitude-self.latitude)*north

    def inverse(self, east, north):
        xscale,yscale=self.scales
        return self.latitude+degrees(north/yscale), self.longitude+degrees(east/xscale)


def subtract(a,b): return a[0]-b[0],a[1]-b[1]
def cross(a,b): return a[0]*b[1]-a[1]*b[0]


def segment_intersection(p,q,a,b):
    """Return vehicle/finish fractions for finite noncollinear intersection."""
    r,s=subtract(q,p),subtract(b,a); denominator=cross(r,s)
    if abs(denominator)<=1e-10: return None
    t,u=cross(subtract(a,p),s)/denominator,cross(subtract(a,p),r)/denominator
    if 0<=t<=1 and 0<=u<=1: return t,u
    return None


def point_segment_distance(p,a,b):
    d=subtract(b,a); length2=sum(v*v for v in d)
    if length2==0: return hypot(*subtract(p,a))
    fraction=max(0,min(1,sum(x*y for x,y in zip(subtract(p,a),d))/length2))
    return hypot(p[0]-a[0]-fraction*d[0],p[1]-a[1]-fraction*d[1])


def valid_gps(sample):
    return (isfinite(sample.latitude) and abs(sample.latitude)<=90
            and isfinite(sample.longitude) and abs(sample.longitude)<=180)


def detect_crossings(samples, finish_a=FINISH_A, finish_b=FINISH_B, *,
                     expected_direction, minimum_interval_s=30, rearm_distance_m=50,
                     max_gap_s=5, max_gps_speed_mps=30, moving_threshold_kmh=1):
    """Keep every finite-segment candidate, including rejected candidates.

    Direction -1 means left-to-right relative to directed A→B. Rearming uses
    distance from the finite line, not accumulated travel. Rejected candidates
    do not reset the accepted-crossing clock. Direction is supplied explicitly.
    """
    if expected_direction not in (-1,1): raise ValueError('Expected direction must be -1 or +1')
    if any(not isfinite(v) or v<=0 for v in
           (minimum_interval_s,rearm_distance_m,max_gap_s,max_gps_speed_mps)):
        raise ValueError('Crossing thresholds must be finite and positive')
    projection=LocalProjection(*finish_a); a=(0.,0.); b=projection.project(*finish_b)
    if hypot(*b)<1e-6: raise ValueError('Finish segment must have positive length')
    flags=flag_samples(samples,Config(max_gap_s=max_gap_s,moving_threshold_kmh=moving_threshold_kmh))
    points=[projection.project(s.latitude,s.longitude) if valid_gps(s) else None for s in samples]
    crossings=[]; last=None; armed=True; accepted_count=0
    for i in range(1,len(samples)):
        left,right=samples[i-1:i+1]; p,q=points[i-1:i+1]
        if p is None or q is None: continue
        dt=(right.timestamp-left.timestamp).total_seconds()
        step=hypot(*subtract(q,p))
        gps_valid=0<dt<=max_gap_s and step/dt<=max_gps_speed_mps
        # Only trustworthy endpoints can rearm; also check the right endpoint
        # after evaluating a candidate, since it occurs later than the crossing.
        if last is not None and gps_valid and point_segment_distance(p,a,b)>=rearm_distance_m-1e-6:
            armed=True
        hit=segment_intersection(p,q,a,b)
        if hit is not None:
            t,u=hit; offset=(left.timestamp-samples[0].timestamp).total_seconds()+t*dt
            timestamp=left.timestamp+timedelta(seconds=t*dt)
            x=p[0]+t*(q[0]-p[0]); y=p[1]+t*(q[1]-p[1])
            latitude,longitude=projection.inverse(x,y)
            speed=left.speed_kmh+t*(right.speed_kmh-left.speed_kmh)
            sign=-1 if cross(b,subtract(q,p))<0 else 1
            reasons=[]
            if dt<=0 or dt>max_gap_s: reasons.append('timestamp_gap')
            if dt>0 and step/dt>max_gps_speed_mps: reasons.append('gps_jump')
            if not isfinite(speed) or speed<=moving_threshold_kmh: reasons.append('not_moving')
            if 'shutdown_post_run' in flags[i-1]|flags[i]: reasons.append('shutdown')
            if sign!=expected_direction: reasons.append('wrong_direction')
            if t==0: reasons.append('endpoint_departure_duplicate_or_unconfirmed')
            if t==1:
                # A touch is not a transverse crossing: verify a subsequent
                # non-line endpoint on the other side, across trustworthy gaps.
                side=cross(b,p); confirmed=False
                for j in range(i+1,len(samples)):
                    if points[j] is None: break
                    next_dt=(samples[j].timestamp-samples[j-1].timestamp).total_seconds()
                    if not 0<next_dt<=max_gap_s: break
                    if hypot(*subtract(points[j],points[j-1]))/next_dt>max_gps_speed_mps: break
                    next_side=cross(b,points[j])
                    if abs(next_side)>1e-8:
                        confirmed=next_side*side<0; break
                if not confirmed: reasons.append('touch_without_confirmed_crossing')
            elapsed_previous=offset-last if last is not None else None
            if last is not None and elapsed_previous<minimum_interval_s: reasons.append('minimum_crossing_interval')
            if not armed: reasons.append('not_rearmed')
            accepted=not reasons
            if accepted:
                accepted_count+=1; last=offset; armed=False
            crossings.append(dict(candidate_id=len(crossings)+1,crossing_id=accepted_count if accepted else None,
                timestamp=right.timestamp.isoformat(),interpolated_timestamp=timestamp.isoformat(),
                elapsed_s=offset,latitude=latitude,longitude=longitude,speed_kmh=speed,
                direction=sign,direction_label='left_to_right' if sign==-1 else 'right_to_left',
                distance_to_finish_segment_m=point_segment_distance((x,y),a,b),
                time_since_previous_crossing_s=elapsed_previous,accepted=accepted,
                reason='accepted' if accepted else ';'.join(reasons),
                left_source_row=left.source_row,right_source_row=right.source_row,
                vehicle_fraction=t,finish_fraction=u,
                trip_at_crossing_km=left.trip_km+t*(right.trip_km-left.trip_km)))
        if last is not None and gps_valid and point_segment_distance(q,a,b)>=rearm_distance_m-1e-6:
            armed=True
    return crossings


def assign_laps(samples,crossings):
    accepted=[c for c in crossings if c['accepted']]; boundaries=[c['elapsed_s'] for c in accepted]
    output=[]
    for s in samples:
        seconds=(s.timestamp-samples[0].timestamp).total_seconds()
        index=bisect_right(boundaries,seconds)
        if not accepted: status='unassigned_no_crossing'
        elif index==0: status='partial_start'
        elif index==len(accepted): status='partial_end'
        else: status='complete'
        start=accepted[index-1] if index else None
        distance=s.trip_km-start['trip_at_crossing_km'] if start else None
        output.append(dict(lap_id=index if status=='complete' else None,lap_status=status,
            crossing_id=start['crossing_id'] if start else None,
            seconds_into_lap=seconds-start['elapsed_s'] if start else None,
            distance_into_lap=distance if distance is not None and isfinite(distance) else None,
            distance_into_lap_km=distance if distance is not None and isfinite(distance) else None))
    return output


def summarize_laps(samples,crossings,config=Config(),finish_a=FINISH_A,*,
                   max_gps_speed_mps=30,high_power_w=800,high_current_a=20):
    """One dictionary per complete lap; primary distance shares energy support."""
    flags=flag_samples(samples,config); intervals=make_intervals(samples,flags,config)
    accepted=[c for c in crossings if c['accepted']]; rows=[]
    projection=LocalProjection(*finish_a)
    levels=sorted({s.speed_kmh for s in samples if isfinite(s.speed_kmh) and s.speed_kmh>=0})
    for lap_id,(start,end) in enumerate(zip(accepted,accepted[1:]),1):
        lo,hi=start['elapsed_s'],end['elapsed_s']; duration=hi-lo
        parts=[p for i in intervals if (p:=clip_interval(i,lo,hi)) is not None]
        shifted=[replace(p,start_s=p.start_s-lo,end_s=p.end_s-lo) for p in parts]
        row=build_windows(shifted,[],replace(config,window_s=duration))[0]
        for key in ('period_id','period_note','complete_window'): row.pop(key,None)
        row.update(lap_id=lap_id,lap_status='complete',start_timestamp=start['interpolated_timestamp'],
            end_timestamp=end['interpolated_timestamp'],lap_duration_s=duration,
            lap_distance_km=row['distance_km'],trip_distance_km=end['trip_at_crossing_km']-start['trip_at_crossing_km'])
        # GPS coverage is explicitly separate; missing/gapped/jumped GPS is never bridged.
        gps_m=0.; gps_seconds=0.; jump_count=0
        for p in parts:
            if valid_gps(p.left) and valid_gps(p.right):
                x,y=projection.project(p.left.latitude,p.left.longitude),projection.project(p.right.latitude,p.right.longitude)
                original_dt=(p.right.timestamp-p.left.timestamp).total_seconds()
                step=hypot(*subtract(y,x))
                if original_dt>0 and step/original_dt>max_gps_speed_mps: jump_count+=1
                elif 0<original_dt<=config.max_gap_s:
                    gps_m+=step*(p.fraction_end-p.fraction_start); gps_seconds+=p.duration_s
        row.update(gps_distance_km=gps_m/1000,gps_coverage_fraction=gps_seconds/duration,
            gps_minus_trip_distance_km=gps_m/1000-row['trip_distance_km'],gps_jumps=jump_count)
        valid=[p for p in parts if p.valid]; moving=[p for i in valid for p,m in movement_parts(i) if m]
        row['moving_average_speed_kmh']=fsum(integral(p,'speed_kmh') for p in moving)/row['moving_s'] if row['moving_s'] else None
        row['voltage_variation_v']=row['voltage_max_v']-row['voltage_min_v'] if valid else None
        if valid:
            row['peak_power_w']=max(0,row['peak_power_w']); row['peak_current_a']=max(0,row['peak_current_a'])
        # Exposure to discrete quantized levels uses nearest-level regions over
        # the piecewise-linear speed, not falsely exact plateaus between samples.
        for j,level in enumerate(levels):
            lower=(levels[j-1]+level)/2 if j else -inf
            upper=(levels[j+1]+level)/2 if j+1<len(levels) else inf
            seconds=fsum(band_duration(p,lower,upper) for p in valid)
            tag=f'{level:.8f}'.rstrip('0').rstrip('.')
            row[f'speed_level_{tag}_s']=seconds
            row[f'speed_level_{tag}_pct']=100*seconds/row['valid_duration_s'] if valid else None
        def above(field,threshold):
            total=0.
            for p in valid:
                x=p.value(field,p.fraction_start,consumption=True)
                y=p.value(field,p.fraction_end,consumption=True)
                if min(x,y)>=threshold: total+=p.duration_s
                elif max(x,y)>threshold: total+=p.duration_s*(max(x,y)-threshold)/abs(y-x)
            return total
        row.update(high_power_duration_s=above('power_w',high_power_w),high_power_threshold_w=high_power_w,
            high_current_duration_s=above('current_a',high_current_a),high_current_threshold_a=high_current_a)
        cruising=0.
        for p in moving:
            dt=(p.right.timestamp-p.left.timestamp).total_seconds()
            if abs((p.right.speed_kmh-p.left.speed_kmh)/3.6/dt)<config.acceleration_threshold_mps2:
                cruising+=p.duration_s
        row['cruising_duration_s']=cruising
        selected=[(s,f) for s,f in zip(samples,flags)
                  if lo<=(s.timestamp-samples[0].timestamp).total_seconds()<hi]
        row['missing_samples']=sum(any(label.startswith('nonfinite_') for label in f) for _,f in selected)
        row['irregular_timestamp_gaps']=sum((p.right.timestamp-p.left.timestamp).total_seconds()>config.max_gap_s for p in parts)
        row['negative_current_samples']=sum('negative_current' in f for _,f in selected)
        row['negative_power_samples']=sum('negative_power' in f for _,f in selected)
        row['shutdown_samples']=sum('shutdown_post_run' in f for _,f in selected)
        row['invalid_electrical_measurements']=sum(bool(f & {'invalid_voltage_state','power_vi_inconsistent',
            'nonfinite_voltage_v','nonfinite_current_a','nonfinite_power_w'}) for _,f in selected)
        row['model_eligible']=row['coverage_fraction']>=config.minimum_window_coverage and row['distance_km']>0
        rows.append(row)
    return rows
