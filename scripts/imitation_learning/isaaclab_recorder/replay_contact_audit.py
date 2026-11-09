"""Reuse ContactProbe for initial-state + action physics replay; no state setters."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'quest_diagnostic'))
from contact_probe import ContactProbe,value

def json_rows(path):
    with Path(path).open() as file:
        for line in file:yield json.loads(line)

def contact_metrics(path):
    result=dict(samples=0,invalid_samples=0,valid_table_contact_samples=0,net_force_samples=0,max_excess_rad=[0.]*4,outside_samples=[0]*4,first_excess_step=[None]*4,max_link_angle_error_rad=[0.]*4,modes=[],closed=False)
    previous=None;dt=None
    for r in json_rows(path):
        if r['event']=='configuration':dt=r['physics_dt'];result['usd_sha256']=r['usd_sha256'];result['joint_names']=[f['name'] for f in r['frames']]
        if r['event']=='closed':result['closed']=True
        if r['event']=='sample_error':result['invalid_samples']+=1
        if r['event']!='physics':continue
        result['samples']+=1;step=r['episode_physics_step']
        if previous is not None and step!=previous+1:result['invalid_samples']+=1
        previous=step
        contacts=r['contacts'];valid=len(contacts)==4 and all(c.get('validation') is not None for c in contacts)
        if not valid:result['invalid_samples']+=1
        if valid and any(np.sum(c.get('counts') or [])>0 for c in contacts):result['valid_table_contact_samples']+=1
        if any(c['net']['value'] is not None and np.linalg.norm(c['net']['value'])>1e-4 for c in contacts):result['net_force_samples']+=1
        mode=r.get('dof_motions',{}).get('value')
        if mode not in result['modes']:result['modes'].append(mode)
        excess=r.get('limit_excess_rad')
        if excess is None:result['invalid_samples']+=1;continue
        for i,x in enumerate(excess):
            result['max_excess_rad'][i]=max(result['max_excess_rad'][i],x)
            if x>1e-4:
                result['outside_samples'][i]+=1
                if result['first_excess_step'][i] is None:result['first_excess_step'][i]=step
            rel=r['links'][i]['relative']
            if rel is None:result['invalid_samples']+=1
            else:result['max_link_angle_error_rad'][i]=max(result['max_link_angle_error_rad'][i],abs(rel['minus_direct_wrapped_rad']))
    result['outside_sample_time_s']=[None if dt is None else n*dt for n in result['outside_samples']]
    result['physics_dt']=dt
    result['note']='Outside sample time=sum of actual physics_dt samples, not continuous-time interpolation; force is last-step normal resultant, not drive torque.'
    return result

class ReplayContactAudit:
    def __init__(self,env,directory,dataset,candidate):
        self.env=env;self.path=Path(directory);self.probe=None;self.episode=None;self.expected=0;self.frames=0
        from slave_gain_experiment import readback
        self.gain_initial=readback(env,self.path/'runtime_gains.jsonl','after_gym_make_before_episode_reset')
        self.file=(self.path/'state_metrics.jsonl').open('x',buffering=1)
        self.report=dict(dataset=str(dataset),dataset_sha256=hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),candidate_position_iterations=candidate,
            task=str(env.cfg.env_name),physics_dt=env.physics_dt,decimation=env.cfg.decimation,render_interval=env.cfg.sim.render_interval,
            robot_spawn_config=str(env.cfg.scene.robot.spawn),solver_config=str(env.cfg.sim.physx),
            note='Initial reset_to once per episode only. States are comparison inputs. Original recorder read order with EXPORT_NONE. No VR or wrist target generation.')
        (self.path/'provenance.json').write_text(json.dumps(self.report,indent=2))
    def start(self,name,episode):
        if self.probe is not None:raise ValueError('One named episode only')
        from slave_gain_experiment import readback
        readback(self.env,self.path/'runtime_gains.jsonl','after_episode_reset_and_initial_state_restore',self.gain_initial)
        self.name=name;self.episode=episode;self.expected=len(episode.data['actions'])
        self.probe=ContactProbe(self.env,self.path/'contact.jsonl','action_replay_'+name)
        v=self.env.scene['robot'].root_physx_view
        from pxr import UsdPhysics
        settings=dict(phase='after_initial_state_restore_before_action_0',masses=value(lambda:v.get_masses()),inertias=value(lambda:v.get_inertias()),limits=value(lambda:v.get_dof_limits()),motions=value(lambda:v.get_dof_motions()),root_properties={str(p.GetPath()):{a.GetName():str(a.Get()) for a in p.GetAttributes() if 'solver' in a.GetName().lower()} for p in self.env.sim.stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)},joint_names=list(self.env.scene['robot'].joint_names))
        (self.path/'initial_runtime.json').write_text(json.dumps(settings,indent=2))
    def begin(self,index,actions):
        self.probe.begin(dict(episode_number=1,episode_name=self.name,control_index=index,action=actions[0].detach().cpu().tolist(),phase='action_replay',recording=False,expected_demo=self.name))
    def end(self):
        if self.probe:self.probe.end()
    def validation(self,index,metrics):
        import torch
        actual=torch.cat([self.env.action_manager.get_term(n).processed_actions[0] for n in self.env.action_manager.active_terms]).detach().cpu().numpy()
        expected=self.episode.data['processed_actions'][index].detach().cpu().numpy()
        if expected.shape!=actual.shape or not np.isfinite(actual).all():raise ValueError('processed action shape/nonfinite')
        self.file.write(json.dumps(dict(action_index=index,fields=metrics,processed_action_max_abs=float(np.max(np.abs(expected-actual)))))+'\n');self.frames+=1
    def close(self,checked,mismatched,expected):
        self.file.close()
        if self.probe:self.probe.close()
        summary=contact_metrics(self.path/'contact.jsonl') if self.probe else {'samples':0}
        summary.update(checked=checked,mismatched=mismatched,expected=expected,frames_compared=self.frames,
            complete_actions=self.expected>0 and self.frames==self.expected and summary['samples']==self.expected*self.env.cfg.decimation)
        if hasattr(self,'free_report'):
            if summary.get('invalid_samples') or summary.get('net_force_samples') or summary.get('valid_table_contact_samples'):
                self.free_report.update(completed=False,no_contact_rejected=True)
            summary.update(mode='free_gripper_check',complete_actions=False,free_check=self.free_report)
        (self.path/'physical_summary.json').write_text(json.dumps(summary,indent=2));print('CONTACT_REPLAY_PHYSICS '+json.dumps(summary),flush=True)
        if hasattr(self,'free_report') and not self.free_report['completed']:raise RuntimeError('Free gripper check incomplete/contact-contaminated; see saved physical summary')


def half_timestep(cfg):
    """Exactly halve recorded 10ms physics steps; preserve 40ms input/render periods."""
    if abs(cfg.sim.dt-.01)>1e-12 or cfg.decimation!=4 or cfg.sim.render_interval!=4:
        raise ValueError('half-dt experiment requires original .01/4/4 timing')
    cfg.sim.dt=.005;cfg.decimation=8;cfg.sim.render_interval=8


def free_schedule():
    # Same 40ms action hold for both dt variants. No new arm path.
    return [(name,value) for name,value in [('open',1.),('half_close',0.),('closed',-1.),('half_open',0.),('open_again',1.)] for _ in range(50)]


def free_gripper_check(audit,episode,name):
    import torch
    env=audit.env;audit.start(name,episode);audit.free_report=dict(completed=False,schedule='five 2s holds: +1,0,-1,0,+1; right gripper only; original action mapping',steps=0,max_wrist_drift_m=0.,max_pair_difference_rad=[0.,0.],phase_last_q={})
    fixed={k:env.get_robot_eef_pose(k)[0].clone() for k in ('left','right','body')}
    for i,(phase,command) in enumerate(free_schedule()):
        drift=float(torch.linalg.vector_norm(env.get_robot_eef_pose('right')[0,:3,3]-fixed['right'][:3,3]))
        if drift>.005:raise RuntimeError('free check wrist drift >5mm; not accepted as isolated gripper test')
        action=env.target_eef_pose_to_action(fixed,{'left':1.,'right':command}).unsqueeze(0)
        audit.begin(i,action)
        audit.probe.context.update(phase='free_'+phase,gripper_command=command)
        try:result=env.step(action)
        finally:audit.end()
        audit.free_report['steps']=i+1
        audit.free_report['max_wrist_drift_m']=max(audit.free_report['max_wrist_drift_m'],drift)
        row=audit.probe.latest
        if row is None or any(c['validation'] is None for c in row['contacts']):raise RuntimeError('free check contact measurement invalid')
        if any(np.sum(c['counts'])>0 or np.linalg.norm(c['net']['value'])>1e-4 for c in row['contacts']):raise RuntimeError('free check finger contact detected; no-contact interpretation rejected')
        if bool(result[2].any() or result[3].any()):raise RuntimeError('free check original termination')
        q=row['direct_q']['value'];pairs=[abs(q[0]-q[2]),abs(q[1]-q[3])]
        audit.free_report['max_pair_difference_rad']=np.maximum(audit.free_report['max_pair_difference_rad'],pairs).tolist()
        audit.free_report['phase_last_q'][phase]=q
    audit.free_report['completed']=True
