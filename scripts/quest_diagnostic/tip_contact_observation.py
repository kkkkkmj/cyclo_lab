"""Bounded, opt-in r2/l2 observation policy. No physics configuration setters."""
import numpy as np

# Diagnostic budgets, not hardware ratings or validated PhysX tolerances.
MAX_FORCE_N = 10.0
MAX_PENETRATION_M = .0005
MAX_LIMIT_EXCESS_RAD = .01
MAX_WRIST_DRIFT_M = .005
MAX_PAIR_ANGLE_ERROR_RAD = .05
DURATION_S = 8.0


def stop_reason(row, allowed_bodies):
    """Accept only the exact two distal rigid bodies; never a substring filter."""
    allowed=frozenset(allowed_bodies)
    if len(allowed)!=2:raise ValueError('Expected two distinct distal body paths')
    if row.get('limit_excess_rad') is None or max(row['limit_excess_rad'])>MAX_LIMIT_EXCESS_RAD:
        return 'joint_limit_excess'
    if row.get('wrist_drift_m',float('inf'))>MAX_WRIST_DRIFT_M:return 'wrist_drift'
    q=np.asarray(row.get('direct_q',{}).get('value'),dtype=float)
    if q.shape!=(4,) or not np.isfinite(q).all():return 'joint_measurement_invalid'
    if max(abs(q[0]-q[2]),abs(q[1]-q[3]))>MAX_PAIR_ANGLE_ERROR_RAD:return 'finger_asymmetry_budget_exceeded'
    contacts=row.get('all_pair_contacts',[])
    if len(contacts)!=4:return 'all_pair_contact_measurement_invalid'
    for pair in row.get('contact_pairs',[]):
        if frozenset((pair['body'],pair['other']))!=allowed:return 'unexpected_contact_pair'
    for c in contacts:
        if c.get('validation') is None or c.get('counts') is None or c.get('details') is None:
            return 'detailed_contact_measurement_invalid'
        sensors=c['validation']['sensor_paths']
        if len(sensors)!=1:return 'detailed_contact_measurement_invalid'
        body=sensors[0]
        net=c['net']['value']
        if net is None:return 'detailed_contact_measurement_invalid'
        net_norm=float(np.linalg.norm(net))
        if not np.isfinite(net_norm):return 'detailed_contact_measurement_invalid'
        if net_norm>MAX_FORCE_N:return 'tip_force_budget_exceeded'
        if not c['details'] and net_norm>1e-4:return 'unattributed_net_contact'
        total_force=0.;point_count=0;expected=np.asarray(c['counts'])
        for detail in c['details']:
            if frozenset((body,detail['other']))!=allowed:return 'unexpected_contact_pair'
            separation=np.asarray(detail['separation_m'],dtype=float)
            force=np.asarray(detail['normal_force_n'],dtype=float)
            if not separation.size or separation.shape!=force.shape or not np.isfinite(separation).all() or not np.isfinite(force).all():
                return 'detailed_contact_measurement_invalid'
            point_count+=len(separation)
            if separation.min() < -MAX_PENETRATION_M:return 'tip_penetration_budget_exceeded'
            total_force+=float(np.abs(force).sum())
        if point_count!=int(expected.sum()):return 'detailed_contact_measurement_invalid'
        # Do not sum both sensors: the same pair appears from each side.
        if total_force>MAX_FORCE_N:return 'tip_force_budget_exceeded'
    return None
