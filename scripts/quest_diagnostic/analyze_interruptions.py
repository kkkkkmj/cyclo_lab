"""Read-only, episode-aware input/control analysis and exact HDF alignment.

Missing samples remain unknown. No simulation, interpolation, or timestamp-nearest matching.
Output directory must be new. Log line numbers are 1-based; HDF frame indices are 0-based.
"""
import argparse
import collections
import hashlib
import itertools
import json
from pathlib import Path

import h5py
import numpy as np


def stats(values):
    a = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if not len(a):
        return dict(n=0, min=None, median=None, max=None, p95=None)
    return dict(n=len(a), min=float(a.min()), median=float(np.median(a)),
                max=float(a.max()), p95=float(np.percentile(a, 95)))


def fingerprint(path):
    path = Path(path)
    before = path.stat()
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    after = path.stat()
    return dict(path=str(path.resolve()), size=after.st_size, mtime_ns=after.st_mtime_ns,
                sha256=h.hexdigest(), stable_during_hash=(before.st_size, before.st_mtime_ns) ==
                (after.st_size, after.st_mtime_ns))


def read_log(path):
    events, bad = [], []
    run, episode, active, generation = None, 0, None, 0
    last_newline = None
    with Path(path).open('rb') as f:
        for line, raw in enumerate(f, 1):
            last_newline = raw.endswith(b'\n')
            try:
                x = json.loads(raw)
                if not isinstance(x, dict) or 'event' not in x:
                    raise ValueError('event object required')
            except (ValueError, UnicodeError) as e:
                bad.append(dict(line=line, error=str(e)))
                generation += 1  # Never merge segments across unreadable lines.
                continue
            if x['event'] == 'begin':
                run = x.get('run_id'); episode = 0; active = None; generation += 1
            x['_line'] = line; x['_run_id'] = run; x['_generation'] = generation
            if x['event'] == 'decision':
                state = x.get('teleop', {}).get('episode_state')
                if state == 'RUNNING' and x.get('phase_before') != 'RUNNING':
                    episode += 1; active = episode
                elif active is None and (state == 'RUNNING' or x.get('phase_before') == 'RUNNING'):
                    active = 'unobserved_start'
                x['_episode'] = active
                x['_scope'] = [run, active, generation]
                if state != 'RUNNING':
                    active = None
            events.append(x)
    decisions = [x for x in events if x['event'] == 'decision']
    return events, decisions, dict(lines=line if last_newline is not None else 0,
        valid_events=len(events), invalid_lines=bad, final_newline=last_newline,
        events=dict(collections.Counter(x['event'] for x in events)),
        has_end_event=any(x['event'] == 'end' for x in events),
        last_decision_state=decisions[-1].get('teleop', {}).get('episode_state') if decisions else None,
        completeness='not_proven_by_valid_JSON')


def load_episodes(path):
    episodes = {}
    with h5py.File(path, 'r') as f:
        for name, e in f.get('data', {}).items():
            arrays = {}
            for key in ('actions', 'processed_actions', 'timing/wall_monotonic',
                        'timing/simulation_time', 'states/articulation/robot/joint_position',
                        'states/articulation/robot/joint_velocity'):
                arrays[key] = e[key][:] if key in e else None
            metadata = json.loads(e.attrs.get('toast_episode_metadata', '{}'))
            episodes[name] = dict(arrays=arrays, metadata=metadata,
                                  shapes={k: list(v.shape) if v is not None else None for k, v in arrays.items()})
    return episodes


def align(decisions, episodes, begins):
    """Accept only unique exact tick + finite equal-shape action + matching available metadata."""
    by_tick = collections.defaultdict(list)
    for x in decisions:
        by_tick[x.get('tick_monotonic')].append(x)
    candidates = collections.defaultdict(list)
    reports = {}
    for name, ep in episodes.items():
        arrays = ep['arrays']; ticks = arrays['timing/wall_monotonic']; actions = arrays['actions']
        report = dict(shapes=ep['shapes'], metadata=ep['metadata'], matched_frames=0,
                      issues=[], action_max_abs=None)
        reports[name] = report
        if ticks is None or ticks.ndim != 2 or ticks.shape[1] != 1 or actions is None or actions.ndim != 2 or len(actions) != len(ticks):
            report['issues'].append(dict(reason='missing_or_invalid_timing_action_shape')); continue
        for i, tick in enumerate(ticks[:, 0]):
            found = by_tick.get(float(tick), [])
            reason = None
            if len(found) != 1:
                reason = 'log_tick_missing' if not found else 'duplicate_log_tick'
            else:
                x = found[0]; action = x.get('action')
                if action is None:
                    reason = 'log_action_missing'
                else:
                    value = np.asarray(action, dtype=float)
                    if value.shape != actions[i].shape: reason = 'action_shape_mismatch'
                    elif not np.isfinite(value).all() or not np.isfinite(actions[i]).all(): reason = 'nonfinite_action'
                    elif not np.allclose(value, actions[i], atol=1e-6, rtol=0): reason = 'action_mismatch'
                meta = ep['metadata']; begin = begins.get(x['_run_id'], {})
                for key in ('scenario_id', 'seed'):
                    if key in meta and key in begin and meta[key] != begin[key]: reason = key + '_mismatch'
                if isinstance(x['_episode'], int) and meta.get('episode_number') is not None and x['_episode'] != meta['episode_number']:
                    reason = 'episode_number_mismatch'
            if reason:
                report['issues'].append(dict(frame=i, tick=float(tick), log_line=found[0]['_line'] if len(found)==1 else None, reason=reason))
            else:
                error = float(np.max(np.abs(np.asarray(x['action']) - actions[i])))
                candidates[x['_line']].append(dict(episode=name, frame=i, action_max_abs=error))
    links = {}
    for line, matches in candidates.items():
        if len(matches) != 1:
            for match in matches: reports[match['episode']]['issues'].append(dict(frame=match['frame'], reason='duplicate_hdf_tick'))
            continue
        link = matches[0]; links[line] = link; r = reports[link['episode']]
        r['matched_frames'] += 1
        r['action_max_abs'] = max(r['action_max_abs'] or 0, link['action_max_abs'])
    return links, reports


def joint_summary(rows, links, episodes):
    pos, vel, refs, missing = [], [], [], collections.Counter()
    for x in rows:
        link = links.get(x['_line'])
        if link is None:
            reason=('waiting_or_non_action' if x.get('action') is None else
                    'log_episode_absent_from_HDF' if isinstance(x.get('_episode'),int) and
                    all(e['metadata'].get('episode_number')!=x['_episode'] for e in episodes.values()) else
                    'no_verified_HDF_frame')
            missing[reason] += 1; continue
        e = episodes[link['episode']]['arrays']; i = link['frame']
        p = e['states/articulation/robot/joint_position']; v = e['states/articulation/robot/joint_velocity']
        if p is None or v is None or p.ndim != 2 or v.ndim != 2 or p.shape != v.shape or i >= len(p):
            missing['missing_or_invalid_joint_shape'] += 1; continue
        if not np.isfinite(p[i]).all() or not np.isfinite(v[i]).all():
            missing['nonfinite_joint_state'] += 1; continue
        pos.append(p[i]); vel.append(v[i]); refs.append(link)
    if pos and len({len(x) for x in pos}) != 1:
        return dict(status='확인 불가', reason='inconsistent_joint_width', matched_samples=0,
                    requested_samples=len(rows), joint_min=None, joint_max=None, joint_velocity_max_abs=None)
    return dict(status='확인 불가' if not pos else '부분 확인' if missing else '확인됨',
        matched_samples=len(pos), requested_samples=len(rows), missing_reasons=dict(missing), references=refs,
        joint_min=np.min(pos, axis=0).tolist() if pos else None,
        joint_max=np.max(pos, axis=0).tolist() if pos else None,
        joint_velocity_max_abs=np.max(np.abs(vel), axis=0).tolist() if vel else None)


def hand(x, side='right'):
    return x.get('teleop', {}).get('hands', {}).get(side, {})


def path_stats(rows, getter):
    distances=[]
    for a, b in zip(rows, rows[1:]):
        va, vb = getter(a), getter(b)
        if va is not None and vb is not None:
            distances.append(float(np.linalg.norm(np.asarray(vb)-va)))
    return dict(valid_pairs=len(distances), path_m=sum(distances) if distances else None)


def segment(rows, t0, links, episodes, previous=None, following=None):
    first, last = rows[0], rows[-1]
    end = following['tick_monotonic'] if following else last['tick_monotonic']
    packets=[x.get('input_snapshot', {}).get('packet') or {} for x in rows]
    actions=[x['action'][6:12] for x in rows if x.get('action') is not None]
    ages=[x.get('teleop', {}).get('preview', {}).get('frame_age_ms') for x in rows]
    return dict(log_episode=first['_episode'],run_id=first['_run_id'],
        lines=[first['_line'],last['_line']],start_s=first['tick_monotonic']-t0,end_s=end-t0,
        duration_s=end-first['tick_monotonic'],right_censored=following is None and last.get('teleop',{}).get('episode_state')=='RUNNING',
        samples=len(rows),reason=hand(first).get('control_reason'),
        previous_reason=hand(previous).get('control_reason') if previous else None,
        next_reason=hand(following).get('control_reason') if following else None,
        seq=[packets[0].get('seq'),packets[-1].get('seq')],
        repeated_seq_pairs=sum(a.get('seq')==b.get('seq') for a,b in zip(packets,packets[1:])),
        squeeze=stats([hand(x).get('squeeze') for x in rows]),
        raw_squeeze=stats([(hand(x).get('raw_squeeze') or {}).get('value') for x in rows]),
        invalid_inputs=dict(collections.Counter(hand(x).get('input_reason') for x in rows if not hand(x).get('valid'))),
        input_age_ms=stats([x.get('input_age_at_decision_ms') for x in rows]),
        controller_motion=path_stats(rows,lambda x:hand(x).get('position')),
        wrist_motion=path_stats(rows,lambda x:(x.get('measured_before_step') or {}).get('right',[None])[0]),
        action_max_abs=float(np.max(np.abs(actions))) if actions else None,
        preview_stages=dict(collections.Counter((x.get('teleop',{}).get('preview') or {}).get('stage') for x in rows)),
        drawn_frames=[(x.get('teleop',{}).get('preview') or {}).get('drawn_frame_id') for x in (first,last)],
        frame_age_ms=stats(ages),step_ms=stats([x.get('step_ms') for x in rows]),
        entry_safety_event=packets[0].get('safety_event'),
        reference_changes=first.get('reference_changes'),
        entry_preview_guard=packets[0].get('preview_guard_reason'),
        entry_producer_validation=packets[0].get('producer_validation'),
        joints=joint_summary(rows,links,episodes))


def input_audit(events, decisions, t0):
    """Independent log evidence, including WAITING and unsaved episodes."""
    audits=[]; changes=[]; previous=None
    configurations={x['_run_id']:x for x in events if x['event']=='joint_configuration'}
    for x in decisions:
        p=x.get('input_snapshot',{}).get('packet') or {}
        value=(x['_run_id'],p.get('safety_epoch'))
        if value!=previous:
            changes.append(dict(line=x['_line'],t_s=x['tick_monotonic']-t0,
                log_episode=x['_episode'],event=p.get('safety_event')))
        previous=value
    for scope,g in itertools.groupby(decisions,lambda x:tuple(x['_scope'])):
        rows=list(g)
        if scope[1] is None:continue
        active=[x for x in rows if hand(x).get('control_reason')=='active']
        packets=[x.get('input_snapshot',{}).get('packet') or {} for x in rows]
        samples=[x for x in events if x['event']=='joint_sample' and x['_run_id']==scope[0]
                 and rows[0]['tick_monotonic']<=x['tick_monotonic']<=rows[-1]['tick_monotonic']]
        limits=collections.Counter(k for x in active for k,v in x.get('teleop',{}).get('limits_hit',{}).get('right',{}).items() if v)
        stationary=[]
        # No window crosses a non-active sample. This is an offline search, not a control threshold.
        for is_active,items in itertools.groupby(rows,lambda x:hand(x).get('control_reason')=='active'):
            seq=list(items)
            if not is_active:continue
            for i,x in enumerate(seq):
                j=i
                while j+1<len(seq) and seq[j]['tick_monotonic']-x['tick_monotonic']<.5:j+=1
                if seq[j]['tick_monotonic']-x['tick_monotonic']<.5:continue
                window=seq[i:j+1]
                cp=path_stats(window,lambda x:hand(x).get('position'))
                wp=path_stats(window,lambda x:(x.get('measured_before_step') or {}).get('right',[None])[0])
                if cp['valid_pairs']==len(window)-1 and wp['valid_pairs']==len(window)-1 and cp['path_m']>.01 and wp['path_m']<.002:
                    stationary.append(dict(start_s=x['tick_monotonic']-t0,end_s=seq[j]['tick_monotonic']-t0,controller_path=cp,wrist_path=wp))
        high=[]
        for flag,items in itertools.groupby(rows,lambda x:hand(x).get('control_reason')=='active' and (hand(x).get('tracking_error_m') or 0)>=.08):
            segment_rows=list(items)
            if not flag:continue
            lo,hi=segment_rows[0]['tick_monotonic'],segment_rows[-1]['tick_monotonic']
            diagnostics=[x for x in samples if lo<=x['tick_monotonic']<=hi]
            config=configurations.get(scope[0],{}); ids=[i for i,n in enumerate(config.get('joint_names',[])) if n.startswith('arm_r')]
            evaluated=[]
            for x in diagnostics:
                if not ids:continue
                evaluated.append(dict(line=x['_line'],t_s=x['tick_monotonic']-t0,
                    position=x['position'],target=x['target'],velocity=x['velocity'],
                    right_target_error_max_rad=max(abs(x['target'][i]-x['position'][i]) for i in ids),
                    right_soft_position_margin_min_rad=min(min(x['position'][i]-config['soft_position_limits'][i][0],config['soft_position_limits'][i][1]-x['position'][i]) for i in ids),
                    right_velocity_limit_ratio_max=max(abs(x['velocity'][i])/config['velocity_limits'][i] for i in ids if config['velocity_limits'][i]>0)))
            raw_errors=[]
            for x in segment_rows:
                raw=(x.get('raw_targets') or {}).get('right');measured=(x.get('measured_before_step') or {}).get('right')
                if raw and measured:raw_errors.append(float(np.linalg.norm(np.asarray(raw[0])-measured[0])))
            high.append(dict(start_s=lo-t0,end_s=hi-t0,samples=len(segment_rows),
                raw_target_error_m=stats(raw_errors),limited_target_error_m=stats([hand(x).get('tracking_error_m') for x in segment_rows]),
                wrist_motion=path_stats(segment_rows,lambda x:(x.get('measured_before_step') or {}).get('right',[None])[0]),
                diagnostic_joint_samples=evaluated,
                diagnostic_joint_scope='Sparse post-step log samples only; NOT replacements for absent HDF frames'))
        audits.append(dict(log_episode=scope[1],run_id=scope[0],active_samples=len(active),
            control_states=dict(collections.Counter(hand(x).get('control_reason') for x in rows)),
            epoch_values=sorted(set(p.get('safety_epoch') for p in packets if p.get('safety_epoch') is not None)),
            preview_false=sum(p.get('preview_ok') is not True for p in packets),
            invalid_right=sum(hand(x).get('valid') is not True for x in rows),
            repeated_seq_pairs=sum(a.get('seq')==b.get('seq') for a,b in zip(packets,packets[1:])),
            visibility_counts=dict(collections.Counter(p.get('visibility') for p in packets)),
            input_age_ms=stats([x.get('input_age_at_decision_ms') for x in rows]),
            frame_age_ms=stats([(x.get('teleop',{}).get('preview') or {}).get('frame_age_ms') for x in rows]),
            limits_hit=dict(limits),step_ms=stats([x.get('step_ms') for x in rows]),
            diagnostic_joint_samples=len(samples),high_tracking_error=high,
            stationary_windows=stationary,
            stationary_search='>=0.5 wall s continuous active, controller path >0.01m, wrist path <0.002m; shorter or rotational stalls not excluded'))
    return dict(episodes=audits,safety_events_including_waiting=changes,joint_configurations=configurations)


def analyze(log, dataset, output):
    out=Path(output); out.mkdir(parents=True,exist_ok=False)
    before=[fingerprint(log),fingerprint(dataset)]
    events,decisions,integrity=read_log(log); episodes=load_episodes(dataset)
    begins={x.get('run_id'):x for x in events if x['event']=='begin'}
    links, hdf=align(decisions,episodes,begins)
    t0=next((x['tick_monotonic'] for x in decisions if x['_episode'] is not None),
            decisions[0]['tick_monotonic'] if decisions else 0)
    blocks=[]; candidates=[]; high=[]; log_episodes=[]
    for scope, iterator in itertools.groupby(decisions,lambda x:tuple(x['_scope'])):
        rows=list(iterator)
        if scope[1] is None:continue
        log_episodes.append(dict(run_id=scope[0],episode=scope[1],lines=[rows[0]['_line'],rows[-1]['_line']],
            decisions=len(rows),action_samples=sum(x.get('action') is not None for x in rows),
            recording_samples=sum(x.get('teleop',{}).get('recording') is True for x in rows),
            hdf_matches=sum(x['_line'] in links for x in rows),start_s=rows[0]['tick_monotonic']-t0,
            end_s=rows[-1]['tick_monotonic']-t0,last_state=rows[-1].get('teleop',{}).get('episode_state')))
        groups=[]
        for reason,g in itertools.groupby(enumerate(rows),lambda z:hand(z[1]).get('control_reason')):
            g=list(g);i,j=g[0][0],g[-1][0];groups.append((reason,i,j))
            blocks.append(segment(rows[i:j+1],t0,links,episodes,rows[i-1] if i else None,rows[j+1] if j+1<len(rows) else None))
        for reason,i,j in groups:
            previous=hand(rows[i-1]).get('control_reason') if i else None
            held=any((hand(x).get('squeeze') or 0)>=.8 for x in rows[i:j+1])
            if reason in ('active','anchored','ready'): # include actual release transitions separately
                if reason!='ready' or previous!='active':continue
            elif previous!='active' and not held:continue
            # Merge the consequence of one preview failure into its rearm wait.
            if reason=='look_forward_release_both_squeezes' and previous=='preview_not_live':continue
            k=j
            if reason=='preview_not_live':
                while k+1<len(rows) and hand(rows[k+1]).get('control_reason')=='look_forward_release_both_squeezes':k+=1
            candidates.append(segment(rows[i:k+1],t0,links,episodes,rows[i-1] if i else None,rows[k+1] if k+1<len(rows) else None))
        for side in ('left','right'):
            for flag,g in itertools.groupby(rows,lambda x:hand(x,side).get('control_reason')=='active' and (hand(x,side).get('tracking_error_m') or 0)>=.08):
                g=list(g)
                if flag:high.append(dict(side=side,log_episode=scope[1],lines=[g[0]['_line'],g[-1]['_line']],
                    start_s=g[0]['tick_monotonic']-t0,end_s=g[-1]['tick_monotonic']-t0,
                    error_m=stats([hand(x,side).get('tracking_error_m') for x in g]),joints=joint_summary(g,links,episodes)))
    with (out/'timeline.jsonl').open('x') as f:
        for x in decisions:
            link=links.get(x['_line']);status=joint_summary([x],links,episodes)
            row=dict(log_line=x['_line'],log_episode=x['_episode'],t_s=x['tick_monotonic']-t0,
                hdf=link,alignment_status='verified_time_action_metadata' if link else '확인 불가 / no_verified_HDF_frame',
                unlinked_reason=None if link else 'waiting_or_non_action' if x.get('action') is None else 'action_not_matched_to_saved_episode',
                joint_state_status=status['status'],decision=x)
            if status['matched_samples']:
                e=episodes[link['episode']]['arrays'];i=link['frame']
                row.update(post_action_joint_position=e['states/articulation/robot/joint_position'][i].tolist(),
                           post_action_joint_velocity=e['states/articulation/robot/joint_velocity'][i].tolist())
            else:row.update(post_action_joint_position=None,post_action_joint_velocity=None)
            f.write(json.dumps(row,ensure_ascii=False)+'\n')
    independent=input_audit(events,decisions,t0)
    with (out/'diagnostic_joint_samples.jsonl').open('x') as f:
        for x in events:
            if x['event']=='joint_sample':f.write(json.dumps(x)+'\n')
    for candidate in candidates:
        if candidate['reason']=='episode_waiting':
            next_start=next((e['start_s'] for e in log_episodes if e['run_id']==candidate['run_id'] and e['start_s']>candidate['start_s']),None)
            candidate['next_episode_start_s']=next_start
            candidate['waiting_to_next_start_s']=None if next_start is None else next_start-candidate['start_s']
    after=[fingerprint(log),fingerprint(dataset)]
    unchanged=before==after
    summary=dict(schema_version=2,time_origin_host_monotonic=t0,integrity=integrity,
        provenance=dict(before=before,after=after,unchanged=unchanged),hdf_episodes=hdf,
        input_control_audit=independent,log_episodes=log_episodes,verified_hdf_frames=len(links),segments=blocks,
        right_stop_candidates=candidates,large_tracking_errors=high,
        unmatched_action_decisions=[dict(line=x['_line'],log_episode=x['_episode'],tick=x['tick_monotonic'],reason='no_verified_HDF_frame') for x in decisions if x.get('action') is not None and x['_line'] not in links],
        scope_notes=['HDF frames joined by exact host monotonic tick + finite action agreement (1e-6 float conversion tolerance, not physics validation tolerance) + available scenario/seed/episode metadata.',
            'HDF frame index is local to its named episode. Log line number is 1-based. No nearest-time matching or index shifts.',
            'pre-action wrist log and post-action HDF joints are distinct sample times.',
            'No cross-episode duration, velocity, control transition, or CPU controller reconstruction.',
            'Input/control evidence remains available without HDF. Missing joints are null, not zero.',
            'A clean final JSON line does not establish run completion.'])
    (out/'interruptions.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    lines=['|Log episode|Start s|Duration s|Status|SQ median|action max|HDF joints|', '|---|---|---|---|---|---|---|']
    # Preserve legacy JSON status enums for existing recordings/consumers; translate report labels only.
    status_labels = {'확인 불가': 'Unavailable', '부분 확인': 'Partially verified', '확인됨': 'Verified'}
    for z in candidates:lines.append(f"|{z['log_episode']}|{z['start_s']:.3f}|{z['duration_s']:.3f}|{z['reason']}|{z['squeeze']['median']}|{z['action_max_abs']}|{status_labels[z['joints']['status']]} ({z['joints']['matched_samples']}/{z['samples']})|")
    (out/'candidates.md').write_text('\n'.join(lines)+'\n')
    if not unchanged:raise RuntimeError('Source changed during analysis; output is not a stable snapshot. See provenance.')
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--log',required=True);p.add_argument('--dataset',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();s=analyze(a.log,a.dataset,a.output_dir)
    print(json.dumps(dict(output=a.output_dir,integrity=s['integrity'],log_episodes=s['log_episodes'],verified_hdf_frames=s['verified_hdf_frames'],unmatched_actions=len(s['unmatched_action_decisions']),candidates=len(s['right_stop_candidates']),sources_unchanged=s['provenance']['unchanged']),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
