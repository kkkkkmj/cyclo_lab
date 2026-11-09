import unittest,tempfile,json,copy,ast
from pathlib import Path
from replay_contact_audit import contact_metrics
from compare_contact_replay import compare
from contact_repro_compare import baseline_gate
class ContactReplayTests(unittest.TestCase):
 def rows(self):
  config=dict(event='configuration',physics_dt=.01,decimation=4,usd_sha256='asset',frames=[{'name':f'j{i}'} for i in range(4)])
  c=dict(validation={},counts=[[1]],net={'value':[[0,0,1]]})
  r=dict(event='physics',episode_physics_step=1,context={'control_index':0,'action':[0]*15},substep=1,contacts=[c]*4,dof_motions={'value':[1]*4},direct_q={'value':[.1]*4},limit_excess_rad=[.1,0,0,0],links=[{'relative':{'minus_direct_wrapped_rad':0},'parent':[0,0,1,0,0,0,1]}]*4)
  return [config,r,dict(event='closed')]
 def test_metrics_and_missing_samples(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'c';r=self.rows();p.write_text(''.join(json.dumps(x)+'\n' for x in r));s=contact_metrics(p)
   self.assertEqual(s['outside_sample_time_s'],[.01,0,0,0]);self.assertEqual(s['valid_table_contact_samples'],1)
   late=copy.deepcopy(r[1]);late['episode_physics_step']=3;r.insert(2,late);p.write_text(''.join(json.dumps(x)+'\n' for x in r));self.assertEqual(contact_metrics(p)['invalid_samples'],1)
 def test_substep_alignment_and_actions(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';q=Path(d)/'b';r=self.rows();p.write_text(''.join(json.dumps(x)+'\n' for x in r));q.write_text(p.read_text());self.assertEqual(compare(p,q)['pairs'],1)
   r[1]['context']['action'][0]=1;r[1]['direct_q']['value'][0]=.2;q.write_text(''.join(json.dumps(x)+'\n' for x in r));s=compare(p,q);self.assertEqual(s['action_differences'],1);self.assertEqual(s['first_q_difference_over_1e5']['control_index'],0)
   r[1]['substep']=2;q.write_text(''.join(json.dumps(x)+'\n' for x in r));self.assertGreater(compare(p,q)['alignment_errors'],0)
 def test_baseline_gate(self):
  s=dict(complete_actions=True,checked=1586,expected=1586,mismatched=0,invalid_samples=0,modes=[[1]*4],max_excess_rad=[.1]*4,max_link_angle_error_rad=[0]*4,valid_table_contact_samples=1)
  self.assertIsNone(baseline_gate(s))
  for key,val in [('complete_actions',False),('mismatched',1),('invalid_samples',1),('valid_table_contact_samples',0),('max_excess_rad',[0]*4)]:
   x=copy.deepcopy(s);x[key]=val;self.assertIsNotNone(baseline_gate(x))
 def test_initial_restore_only_no_video_route(self):
  tree=ast.parse(Path(__file__).with_name('replay_demos.py').read_text())
  resets=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='reset_to'];self.assertEqual(len(resets),2) # one episode restore, one separate free-check restore
  helper=Path(__file__).with_name('replay_contact_audit.py').read_text()
  self.assertNotIn('write_joint_state',helper);self.assertNotIn('reset_to(',helper)
 def test_half_dt_preserves_periods(self):
  from types import SimpleNamespace
  from replay_contact_audit import half_timestep,free_schedule
  c=SimpleNamespace(sim=SimpleNamespace(dt=.01,render_interval=4),decimation=4)
  half_timestep(c);self.assertEqual(c.sim.dt*c.decimation,.04);self.assertEqual(c.sim.dt*c.sim.render_interval,.04)
  with self.assertRaises(ValueError):half_timestep(c)
  s=free_schedule();self.assertEqual(len(s),250);self.assertEqual([s[i*50][1] for i in range(5)],[1,0,-1,0,1])
 def test_common_time_not_zip_of_fine_substeps(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'coarse';q=Path(d)/'fine';r=self.rows();p.write_text(''.join(json.dumps(x)+'\n' for x in r))
   fine=copy.deepcopy(r);fine[0].update(physics_dt=.005,decimation=8);extra=copy.deepcopy(fine[1]);extra['direct_q']['value']=[9]*4;fine[1]['substep']=2;fine.insert(1,extra)
   q.write_text(''.join(json.dumps(x)+'\n' for x in fine));s=compare(p,q)
   self.assertEqual(s['pairs'],1);self.assertEqual(s['extra_fine_samples'],1);self.assertEqual(s['max_q_difference_rad'],[0]*4)
if __name__=='__main__':unittest.main()
