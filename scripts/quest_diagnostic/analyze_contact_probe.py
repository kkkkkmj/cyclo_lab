"""Offline verification only: run after teleop has exited and closed its writer."""
import argparse,json,csv,hashlib,shutil,time,collections
from pathlib import Path
import numpy as np
import h5py

def verify(dataset,log,exit_file,*,postmortem=False):
    if not postmortem and exit_file.read_text().strip()!='DOCKER_EXEC_EXIT=0':raise RuntimeError('Normal Docker exit not confirmed; do not open a possibly active writer')
    if not postmortem and 'RECORD_FINALIZED:' not in log.read_text():raise RuntimeError('Writer finalization not confirmed; do not open dataset')
    episodes=[]
    with h5py.File(dataset,'r') as f:
        for name,g in f['data'].items():
            lengths={};finite={}
            def visit(k,v):
                if isinstance(v,h5py.Dataset) and k.split('/')[0] in ('actions','obs','states','processed_actions','timing'):
                    lengths[k]=len(v);finite[k]=True
                    for start in range(0,len(v),64):
                        block=v[start:start+64]
                        if np.issubdtype(block.dtype,np.number):finite[k] &= bool(np.isfinite(block).all())
            g.visititems(visit)
            n=lengths.get('actions',0)
            valid=n>0 and any(k.startswith('states/') for k in lengths) and any(k.startswith('obs/') for k in lengths) and all(v==n for v in lengths.values()) and all(finite.values())
            episodes.append(dict(name=name,frames=n,aligned=valid,lengths=lengths,finite=finite,metadata=json.loads(g.attrs.get('toast_episode_metadata','{}'))))
    return dict(app_finalization_confirmed='RECORD_FINALIZED:' in log.read_text(),audit_mode=postmortem,episodes=episodes,verified=bool(episodes) and all(e['aligned'] for e in episodes))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--postmortem-readonly',action='store_true',help='Audit a stable copied HDF5 without asserting app finalization; contact analysis survives HDF5 errors');a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    logtext=(a.run_dir/'teleop.log').read_text()
    if a.postmortem_readonly:
        try:
            def stamp(path):
                st=path.stat();h=hashlib.sha256()
                with path.open('rb') as f:
                    for b in iter(lambda:f.read(1048576),b''):h.update(b)
                return dict(size=st.st_size,mtime_ns=st.st_mtime_ns,sha256=h.hexdigest())
            before=stamp(a.dataset);time.sleep(2);stable=stamp(a.dataset)
            if before!=stable:raise RuntimeError('Source changed during stability observation')
            copied=a.output/'dataset_snapshot.hdf5';shutil.copy2(a.dataset,copied)
            after=stamp(a.dataset);copy=stamp(copied)
            if before!=after or copy['sha256']!=before['sha256']:raise RuntimeError('Source/copy changed; snapshot not usable')
            (a.output/'snapshot_provenance.json').write_text(json.dumps(dict(source=str(a.dataset),before=before,after=after,copy=copy,writer_absence='not established by stability alone'),indent=2))
            a.dataset=copied
            result=verify(a.dataset,a.run_dir/'teleop.log',a.run_dir/'exit_status.txt',postmortem=True)
        except Exception as e:result=dict(episodes=[],verified=False,app_finalization_confirmed=False,hdf5_error=repr(e),audit_mode=True)
    else:result=verify(a.dataset,a.run_dir/'teleop.log',a.run_dir/'exit_status.txt')
    (a.output/'storage.json').write_text(json.dumps(result,indent=2))
    events=[];errors=[];closed=False;config=None;steps={};preview=[]
    with (a.run_dir/'contact.jsonl').open() as f:
        for line_no,line in enumerate(f,1):
            try:r=json.loads(line)
            except Exception as e:errors.append(dict(line=line_no,error=str(e)));continue
            if r['event']=='configuration':config=r
            if r['event']=='closed':closed=True
            if r['event']=='sample_error':errors.append(r)
            if r['event']=='control_end' and r['observed_substeps']!=r['expected']:errors.append(r)
            if r['event']=='preview':preview.append(r)
            if r['event']=='physics':events.append(r)
    alignment=[]
    if result['verified']:
      with h5py.File(a.dataset,'r') as h:
        for ep in result['episodes']:
            number=ep['metadata'].get('episode_number')
            selected={r['context']['control_index']:r for r in events if r['context']['episode_number']==number and r['context']['recording']}
            actions=h['data'][ep['name']]['actions'][:]
            matched=[];unlinked=[];different=[]
            for i,action in enumerate(actions):
                if i not in selected:unlinked.append(i);continue
                logged=np.asarray(selected[i]['context']['action'])
                if logged.shape==action.shape and np.allclose(logged,action,rtol=0,atol=1e-6):matched.append(i)
                else:different.append(i)
            alignment.append(dict(demo=ep['name'],episode_number=number,matched_action_rows=len(matched),unlinked_rows=unlinked,different_rows=different,
                criteria='episode metadata + zero-based control_index + actual stored action comparison; no frame_id indexing'))
    (a.output/'alignment.json').write_text(json.dumps(alignment,indent=2))
    keys=[(r['context']['episode_number'],r['context']['control_index'],r['substep']) for r in events]
    duplicates=[list(k) for k,n in collections.Counter(keys).items() if n>1]
    groups=collections.defaultdict(list)
    for r in events:groups[(r['context']['episode_number'],r['context']['control_index'])].append(r['substep'])
    incomplete=[dict(episode=k[0],control=k[1],substeps=v) for k,v in groups.items() if v!=list(range(1,config['decimation']+1))]
    gaps=[dict(previous=events[i-1]['physics_step_global'],current=r['physics_step_global']) for i,r in enumerate(events) if i and r['physics_step_global']!=events[i-1]['physics_step_global']+1]
    filter_failed='Filter pattern' in logtext and 'did not match the correct number of entries' in logtext
    force_validity='invalid: PhysX filter cardinality error in runtime log; zero values cannot establish no contact' if filter_failed else 'not independently validated; no explicit filter error found'
    rows=[]
    for r in events:
        q=r['direct_q']['value'];cache=r['cache_q']['value'];lim=r['hard_limits']['value'];ep=r['context']['episode_number']
        for i,name in enumerate(config['frames']):
            rel=r['links'][i]['relative'];force=r['contacts'][i]['table']['value']
            rows.append(dict(episode=ep,control_index=r['context']['control_index'],substep=r['substep'],time_s=r['simulation_time_s'],joint=name['name'],
                direct_q=None if q is None else q[i],cache_q=None if cache is None else cache[i],
                relative_q=None if rel is None else rel['angle_rad'],off_axis=None if rel is None else rel['off_axis_residual_rad'],
                excess=None if r['limit_excess_rad'] is None else r['limit_excess_rad'][i],
                table_normal_resultant_norm=None if force is None or filter_failed else float(np.linalg.norm(np.asarray(force))),
                note='Nonzero filtered normal force supports contact; zero cannot exclude it'))
    if rows:
        with (a.output/'joint_steps.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for ep in sorted({r['episode'] for r in rows}):
            fig,axs=plt.subplots(4,1,figsize=(12,10),sharex=True)
            for i,ax in enumerate(axs):
                data=[r for r in rows if r['episode']==ep and r['joint']==f'gripper_r_joint{i+1}']
                for k in ('direct_q','cache_q','relative_q'):ax.plot([r['time_s'] for r in data],[np.nan if r[k] is None else r[k] for r in data],label=k)
                lo,hi=np.radians(config['frames'][i]['usd_limits_deg']);ax.axhline(lo,color='r',ls='--');ax.axhline(hi,color='r',ls='--');ax.set_ylabel(f'joint{i+1} rad');ax.legend()
            axs[-1].set_xlabel('episode simulation seconds (post physics step)');fig.tight_layout();fig.savefig(a.output/f'episode_{ep}_angles.png');plt.close(fig)
    summary=dict(app_finalization_confirmed=result.get('app_finalization_confirmed',False),force_validity=force_validity,duplicate_steps=duplicates,incomplete_control_steps=incomplete,physics_counter_gaps=gaps,storage_verified=result['verified'],probe_closed=closed,physics_samples=len(events),errors=errors,preview_links=preview,
        missing_measurements={k:sum(r[k]['value'] is None for r in events) for k in ('direct_q','cache_q','hard_limits','measured_drive_effort')},
        note='No interpolation. Episode/control_index is recorder alignment candidate; frame_id is never an HDF5 index. Check timing/actions before joining datasets.')
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='preview_links'},indent=2))
    if not result['verified'] or not closed or filter_failed or errors or duplicates or incomplete or gaps or any(x['unlinked_rows'] or x['different_rows'] for x in alignment):raise SystemExit(1)
if __name__=='__main__':main()
