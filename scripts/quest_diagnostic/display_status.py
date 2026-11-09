"""Read-only telemetry: never feeds control decisions or recorded observations."""
import time
from control import norm,sub,rotvec,qmul,qinv

def start_blockers(snapshot):
    p = snapshot.get('packet') or {}
    reasons = []
    if not snapshot.get('live'):
        age = snapshot.get('age_ms')
        if age is None or not 0 <= age < 250:
            reasons.append('input_stale')
        if p.get('visibility') != 'visible':
            reasons.append('quest_not_visible')
        if not reasons:
            reasons.append('input_not_live')
    if not p.get('preview_ok'):
        reasons.append('preview_unconfirmed')
    for side in ('left', 'right'):
        h = p.get('controllers', {}).get(side, {})
        profiles = h.get('profiles', [])
        buttons = h.get('buttons', [])
        if h.get('valid') is not True:
            reasons.append(side + ':invalid')
        if ('meta-quest-touch-plus' not in profiles or any('hand' in x.lower() for x in profiles)):
            reasons.append(side + ':not_touch_plus')
        if h.get('mapping') != 'xr-standard' or len(buttons) < 6:
            reasons.append(side + ':buttons_invalid')
        elif not buttons[1]['value'] < .2:
            reasons.append(side + ':squeeze_held')
    return reasons


def display_status(snapshot, controller, lifecycle, preview_only=False, start_blocked=False, current=None):
    p = snapshot.get('packet') or {}
    hands = {}
    for side in ('left', 'right'):
        h = p.get('controllers', {}).get(side, {})
        buttons = h.get('buttons', [])
        raw = h.get('diagnostic', {}).get('raw_buttons', [])
        reason = controller.states[side]['reason']
        hands[side] = dict(valid=h.get('valid') is True, input_reason=h.get('reason', 'missing'),
            control_reason=reason, ready=controller.states[side]['ready'],
            anchored=controller.states[side]['anchor'] is not None,
            handedness=h.get('handedness', side), source_id=h.get('source_id'),
            position=h.get('position'), quaternion_xyzw=h.get('quaternion_xyzw'),
            target_position=controller.targets[side][0],
            home_distance_m=norm(sub(controller.targets[side][0],controller.home[side][0])),
            home_rotation_rad=norm(rotvec(qmul(controller.targets[side][1],qinv(controller.home[side][1])))),
            tracking_error_m=norm(sub(controller.targets[side][0],current[side][0])) if current else None,
            active=bool(not preview_only and lifecycle.state == 'RUNNING' and reason == 'active'),
            raw_squeeze=raw[1] if len(raw)>1 else None, raw_trigger=raw[0] if raw else None,
            squeeze_pressed=buttons[1].get('pressed', False) if len(buttons) > 1 else False,
            squeeze=buttons[1]['value'] if len(buttons) > 1 else None,
            trigger=buttons[0]['value'] if buttons else None)
    return dict(version=1, observed_monotonic=time.monotonic(), input_seq=p.get('seq'),
        session=p.get('session'), client_build=p.get('client_build'), server_build=p.get('server_build'),
        compatibility=p.get('client_compatibility'), input_age_ms=snapshot.get('age_ms'),
        visibility=p.get('visibility'), preview_ok=p.get('preview_ok'),
        preview_guard_reason=p.get('preview_guard_reason'), preview=p.get('preview_status'),
        producer_age_at_receive_ms=p.get('producer_age_at_receive_ms'),
        basis_ready=controller.basis is not None, safety_epoch=p.get('safety_epoch'),
        episode_state=lifecycle.state, episode_result=getattr(lifecycle,'result',None), preview_only=preview_only,
        live=bool(snapshot.get('live')), hands=hands, start_blocked=start_blocked,
        start_blockers=start_blockers(snapshot) if lifecycle.state == 'WAITING' else [])
