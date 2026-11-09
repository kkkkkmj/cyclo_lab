"""Opt-in post-physics audit. No setters, extra render or physical parameter changes."""
import json, math, time, hashlib
from pathlib import Path
import numpy as np
from contact_filter import exact_targets,NativePhysicsErrors,read_contact,validate_view

class DiagnosticStop(RuntimeError):
    """Stop before another physics substep; evidence is already flushed."""



def stop_reason(row,threshold,require_contact):
    if threshold is not None:
        if row['dof_motions']['value']!=[1,1,1,1]:return 'dof_motion_not_confirmed_limited'
        if row['limit_excess_rad'] is None or any(l['relative'] is None for l in row['links']):return 'joint_measurement_invalid'
        if max(row['limit_excess_rad'])>threshold:return 'joint_limit_excess'
    if require_contact and any(c['validation'] is None for c in row['contacts']):return 'contact_measurement_invalid'
    return None

def rotation(q):
    q=np.asarray(q,dtype=float);q=q/np.linalg.norm(q);w,x,y,z=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def relative_angle(parent_xyzw,child_xyzw,local0_wxyz,local1_wxyz,axis):
    """Signed twist of J0^-1 * parent^-1 * child * J1; principal [-pi,pi]."""
    def r(p):return rotation([p[6],*p[3:6]])
    m=rotation(local0_wxyz).T @ r(parent_xyzw).T @ r(child_xyzw) @ rotation(local1_wxyz)
    i='XYZ'.index(axis);j,k=[(1,2),(2,0),(0,1)][i]
    angle=math.atan2(m[k,j]-m[j,k],m[j,j]+m[k,k])
    c,s=math.cos(angle),math.sin(angle);expected=np.eye(3)
    expected[j,j]=expected[k,k]=c;expected[k,j]=s;expected[j,k]=-s
    residual=math.acos(float(np.clip((np.trace(expected.T@m)-1)/2,-1,1)))
    return {'angle_rad':angle,'angle_deg':math.degrees(angle),'off_axis_residual_rad':residual,
            'branch':'principal [-pi,pi]; not unwrapped'}


def value(fn):
    try:
        x=fn()
        if hasattr(x,'detach'):x=x.detach().cpu().numpy()
        x=np.asarray(x)
        if not np.isfinite(x).all():raise ValueError('nonfinite measurement')
        return {'value':x.tolist(),'reason':None}
    except Exception as e:return {'value':None,'reason':repr(e)}


class ContactProbe:
    def __init__(self,env,path,run_id,stop_on_excess=None,require_contact=False):
        from pxr import UsdPhysics
        self.env=env;self.robot=env.scene['robot'];self.context=None;self.total=0;self.substep=0;self.last_counter=-1
        self.file=Path(path).open('x',buffering=1);self.original=env.scene.update
        self.names=[f'gripper_r_joint{i}' for i in range(1,5)]
        self.ids=[self.robot.joint_names.index(n) for n in self.names]
        self.frames=[];self.contacts=[];self.contact_setup=[]
        self.stop_on_excess=stop_on_excess;self.require_contact=require_contact;self.latest=None;self.control_contact=False
        self.native=NativePhysicsErrors()
        stage=env.sim.stage
        table=env.cfg.scene.table.prim_path.replace('{ENV_REGEX_NS}','/World/envs/env_0').replace('env_.*','env_0')
        try:self.table_setup=exact_targets(stage,table)
        except Exception as e:self.table_setup=dict(colliders=[],targets=[],reason=repr(e))
        def quat(v):return [float(v.GetReal()),*[float(z) for z in v.GetImaginary()]]
        for name in self.names:
            matches=[p for p in stage.Traverse() if p.GetName()==name and '/env_0/' in str(p.GetPath())]
            if len(matches)!=1:raise ValueError(f'{name}: expected one env_0 joint, found {len(matches)}')
            p=matches[0];j=UsdPhysics.RevoluteJoint(p)
            bodies=[str(j.GetBody0Rel().GetTargets()[0]),str(j.GetBody1Rel().GetTargets()[0])]
            frame=dict(name=name,path=str(p.GetPath()),bodies=bodies,
                body_indices=[self.robot.body_names.index(Path(b).name) for b in bodies],
                local_pos=[list(j.GetLocalPos0Attr().Get()),list(j.GetLocalPos1Attr().Get())],
                local_rot=[quat(j.GetLocalRot0Attr().Get()),quat(j.GetLocalRot1Attr().Get())],axis=j.GetAxisAttr().Get(),
                usd_limits_deg=[j.GetLowerLimitAttr().Get(),j.GetUpperLimitAttr().Get()])
            self.frames.append(frame)
            filters=self.table_setup['targets']
            try:
                if not filters:raise ValueError(self.table_setup.get('reason','No exact filters'))
                cv=self.robot._physics_sim_view.create_rigid_contact_view([bodies[1]],filter_patterns=[filters],max_contact_data_count=128)
                validated=validate_view(cv,bodies[1],filters)
                self.contacts.append(cv);self.contact_setup.append(dict(body=bodies[1],filters=filters,reason=None,initial_validation=validated))
            except Exception as e:
                self.contacts.append(None);self.contact_setup.append(dict(body=bodies[1],filters=filters,reason=repr(e)))
        table_collision_paths=self.table_setup['colliders']
        usd=Path(env.cfg.scene.robot.spawn.usd_path)
        self.emit(dict(event='configuration',run_id=run_id,joint_names=list(self.robot.joint_names),indices=self.ids,
            native_monitor_reason=self.native.reason,table_setup=self.table_setup,frames=self.frames,table_collision_paths=table_collision_paths,contact_setup=self.contact_setup,physics_dt=env.physics_dt,decimation=env.cfg.decimation,
            usd=str(usd),usd_sha256=hashlib.sha256(usd.read_bytes()).hexdigest(),
            sampling='after scene.update for each physics substep inside explicit env.step; reset updates excluded',
            force_semantics='PhysX contact impulse / physics_dt (N); last physics step, world frame. Net normal contact force vs table-filtered normal force; not drive torque or full friction wrench. Zero resultant does not prove absence of contact. No new contact reporter settings applied.',
            overhead='opt-in synchronous small GPU readbacks each physics step; may slow wall time'))
        def update(*a,**kw):
            result=self.original(*a,**kw)
            if self.context is not None and int(env._sim_step_counter)!=self.last_counter:
                self.last_counter=int(env._sim_step_counter)
                self.substep+=1;self.total+=1
                self.latest=None
                try:self.sample()
                except DiagnosticStop as e:
                    self.emit(dict(event='automatic_stop',context=self.context,substep=self.substep,
                                   reason=str(e),physics_step=int(env._sim_step_counter)))
                    raise
                except Exception as e:
                    self.emit(dict(event='sample_error',context=self.context,substep=self.substep,reason=repr(e)))
                    if self.stop_on_excess is not None:raise DiagnosticStop('diagnostic_sample_error') from e
                if self.latest is not None:
                    self.control_contact |= any(c.get('counts') is not None and np.any(np.asarray(c['counts'])>0) for c in self.latest['contacts'])
                    reason=stop_reason(self.latest,self.stop_on_excess,self.require_contact)
                    if reason:
                        self.emit(dict(event='automatic_stop',reason=reason,physics_step=int(env._sim_step_counter)))
                        raise DiagnosticStop(reason)
            return result
        env.scene.update=update
    def emit(self,row):self.file.write(json.dumps(row,allow_nan=False)+'\n')
    def begin(self,context):self.context=context;self.substep=0;self.control_contact=False;self.last_counter=int(self.env._sim_step_counter)
    def end(self):
        self.emit(dict(event='control_end',context=self.context,observed_substeps=self.substep,expected=self.env.cfg.decimation))
        self.context=None
    def sample(self):
        r=self.robot;v=r.root_physx_view;ids=self.ids;started=time.monotonic()
        row=dict(event='physics',context=self.context,substep=self.substep,physics_step_global=int(self.env._sim_step_counter),
            episode_physics_step=self.context['control_index']*self.env.cfg.decimation+self.substep,
            simulation_time_s=(self.context['control_index']*self.env.cfg.decimation+self.substep)*self.env.physics_dt,
            host_monotonic=started)
        for key,fn in {'direct_q':lambda:v.get_dof_positions()[0,ids],'cache_q':lambda:r.data.joint_pos[0,ids],
            'direct_velocity':lambda:v.get_dof_velocities()[0,ids],'cache_velocity':lambda:r.data.joint_vel[0,ids],
            'dof_motions':lambda:v.get_dof_motions()[0,ids],'hard_limits':lambda:v.get_dof_limits()[0,ids],'soft_limits':lambda:r.data.soft_joint_pos_limits[0,ids],
            'target':lambda:r.data.joint_pos_target[0,ids],
            'processed_action':lambda:self.env.action_manager.get_term('right_gripper').processed_actions[0],
            'stiffness':lambda:v.get_dof_stiffnesses()[0,ids],'damping':lambda:v.get_dof_dampings()[0,ids],
            'effort_limit':lambda:v.get_dof_max_forces()[0,ids],
            'velocity_limit':lambda:v.get_dof_max_velocities()[0,ids]}.items():row[key]=value(fn)
        # Isaac Lab implicit actuator applied_torque is a PD estimate, NOT measured motor torque.
        row['estimated_pd_effort']=value(lambda:r.data.applied_torque[0,ids])
        row['estimated_pd_effort']['meaning']='Isaac Lab implicit actuator PD estimate, Nm; not measured drive/constraint torque'
        row['measured_drive_effort']={'value':None,'reason':'No verified drive-only measured torque API in installed path'}
        row['joint_reaction']={'value':None,'reason':'Not collected: spatial joint reaction is not drive torque'}
        q=row['direct_q']['value'];limits=row['hard_limits']['value']
        row['limit_excess_rad']=None if q is None or limits is None else np.maximum(np.maximum(np.array(limits)[:,0]-q,np.array(q)-np.array(limits)[:,1]),0).tolist()
        # Same kinematic refresh as ArticulationData.body_link_pose_w, no physics advancement.
        r._physics_sim_view.update_articulations_kinematic()
        transforms=value(lambda:v.get_link_transforms()[0]);row['links']=[]
        for f in self.frames:
            item={'joint':f['name'],'parent':None,'child':None,'relative':None,'reason':transforms['reason']}
            if transforms['value'] is not None:
                parent,child=[transforms['value'][i] for i in f['body_indices']]
                relative=relative_angle(parent,child,*f['local_rot'],f['axis'])
                if q is not None:
                    delta=relative['angle_rad']-q[len(row['links'])]
                    relative['minus_direct_wrapped_rad']=math.atan2(math.sin(delta),math.cos(delta))
                def pivot(pose,local):return np.asarray(pose[:3])+rotation([pose[6],*pose[3:6]])@local
                item.update(parent=parent,child=child,relative=relative,
                    pivot_separation_m=float(np.linalg.norm(pivot(parent,f['local_pos'][0])-pivot(child,f['local_pos'][1]))))
            row['links'].append(item)
        row['contacts']=[read_contact(cv,setup,self.env.physics_dt,self.native) for cv,setup in zip(self.contacts,self.contact_setup)]
        row['native_physics_errors']=list(self.native.errors)
        row['units']={'position':'rad','velocity':'rad/s','limits':'rad','link_translation':'m','link_quaternion':'xyzw','force':'N','effort':'Nm'}
        row['read_complete_monotonic']=time.monotonic();self.emit(row);self.latest=row
    def preview(self,frame_id,captured,cameras):
        self.emit(dict(event='preview',frame_id=frame_id,captured_monotonic=captured,
            physics_step_global=int(self.env._sim_step_counter),camera_frames={k:value(lambda c=c:c.frame) for k,c in cameras.items()},
            note='existing render/camera output; publication time is not exposure time; no additional render'))
    def close(self):
        self.env.scene.update=self.original
        self.native.close()
        self.emit(dict(event='closed',physics_samples=self.total,monotonic=time.monotonic()));self.file.close()
