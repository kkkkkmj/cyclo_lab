"""CPU tests; synthetic inputs are never represented as physical observations."""
import ast
import argparse
import unittest
import tempfile
import json
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from control import BoundedTeleop
from test_control import sample, POSES
from free_gripper import command, metrics, VelocityCondition
from summarize_free_gripper import compare
from practice_options import add_arguments, options, configure


class FreeGripperTests(unittest.TestCase):
    def fake_robot(self):
        # Deliberately shuffled PhysX order; includes the other hand and arm.
        names=['gripper_r_joint4','arm_r_joint1','gripper_l_joint3','gripper_r_joint3','gripper_r_joint1','gripper_r_joint2']
        values={k:np.ones((1,len(names))) for k in VelocityCondition.GETTERS}
        values['velocity']=np.array([[6.5,15.,6.5,6.5,2.2,6.5]])
        values['limits']=np.array([[[-1.,1.]]*len(names)])
        view=SimpleNamespace(**{getter:(lambda key=key:values[key].copy()) for key,getter in VelocityCondition.GETTERS.items()})
        calls=[]
        def write(value,joint_ids):
            calls.append((value,joint_ids));values['velocity'][:,joint_ids]=value
        robot=SimpleNamespace(joint_names=names,root_physx_view=view,write_joint_velocity_limit_to_sim=write)
        return robot,values,calls

    def test_candidate_writes_only_named_j3_and_preserves_all_other_properties(self):
        robot,values,calls=self.fake_robot();c=VelocityCondition(robot,True)
        self.assertEqual(calls,[(2.2,[3])]);c.check(c.snapshot())
        self.assertEqual(c.named(c.snapshot())['velocity']['gripper_l_joint3'],[6.5])
        values['velocity'][0,0]=2.2
        with self.assertRaises(ValueError):c.check(c.snapshot())

    def test_default_has_no_write_and_rejects_gain_changes_or_reset_reversion(self):
        robot,values,calls=self.fake_robot();c=VelocityCondition(robot)
        self.assertEqual(calls,[]);c.check(c.snapshot())
        values['effort'][0,2]=20
        with self.assertRaises(ValueError):c.check(c.snapshot())
        robot,values,calls=self.fake_robot();c=VelocityCondition(robot,True)
        values['velocity'][0,3]=6.5
        with self.assertRaises(ValueError):c.check({'velocity':c.read('get_dof_max_velocities')})

    def test_candidate_refuses_unexpected_original_limit(self):
        robot,values,calls=self.fake_robot();values['velocity'][0,3]=3.
        with self.assertRaises(ValueError):VelocityCondition(robot,True)
        self.assertEqual(calls,[])

    def test_comparison_rejects_wrong_endpoint_commands_and_extra_change(self):
        robot,values,calls=self.fake_robot();condition=VelocityCondition(robot,True)
        settings=dict(event='runtime_settings',candidate=True,verified=True,
                      before=condition.named(condition.before),actual=condition.named(condition.snapshot()))
        import copy
        provenance={k:1 for k in ('task','scenario','seed','usd_sha256','dt','physics_dt','protocol','actuators','command_source')}
        provenance.update(close_angle=1.,code_sha256={'source/model.py':'unchanged'})
        common=dict(phases={},samples=1,command_sha256='same',resets=[dict(episode=i,q=[0]*4,velocity=[0]*4) for i in (1,2)],
                    errors=[],reported_contact_samples=0,invalid_contact_samples=0,right_settings=[['same']],
                    provenance=provenance,outcome=dict(status='completed',app_close_completed=True))
        a=copy.deepcopy(common);b=copy.deepcopy(common)
        a['velocity_limits']=[[2.2,6.5,6.5,6.5]];b['velocity_limits']=[[2.2,6.5,2.2,6.5]]
        b['provenance']['velocity_condition']='right_j3_2p2'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'runtime_settings.jsonl'
            path.write_text('\n'.join(json.dumps(settings) for _ in range(5)))
            def run():
                with patch('summarize_free_gripper.comparison_data',side_effect=[a,b]):return compare('baseline',tmp)
            self.assertTrue(run()['comparison_valid'])
            b['provenance']['close_angle']=1.1
            self.assertFalse(run()['comparison_valid']);b['provenance']['close_angle']=1.
            b['command_sha256']='changed'
            self.assertFalse(run()['comparison_valid']);b['command_sha256']='same'
            settings['actual']['velocity']['gripper_l_joint3']=[2.2]
            path.write_text('\n'.join(json.dumps(settings) for _ in range(5)))
            self.assertFalse(run()['comparison_valid'])

    def test_actual_practice_trigger_and_action_for_all_four_joints(self):
        root=Path(__file__).resolve().parents[2]
        file=root/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/gripper_action.py'
        tree=ast.parse(file.read_text())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='process_actions')
        scope={}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(file),'exec'),scope)
        parser=argparse.ArgumentParser();add_arguments(parser)
        c=configure(BoundedTeleop(POSES,1,True),options(parser.parse_args(['--control-profile','practice'])))
        s=sample();c.update(s,measured=POSES)
        for h in s['packet']['controllers'].values():h['buttons'][1]['value']=1
        c.update(s,measured=POSES)
        obj=SimpleNamespace(_raw_actions=torch.zeros(1,1),_processed_actions=torch.zeros(1,4),
                            _open_command=torch.zeros(1,4),_close_command=torch.full((1,4),1.1))
        for i in range(601):
            phase, trigger=command(i*.04)
            s['packet']['controllers']['right']['buttons'][0]['value']=trigger
            c.update(s,measured=POSES)
            a=c.action(POSES,.04)
            self.assertAlmostEqual(a[13],1-2*trigger)
            scope['process_actions'](obj,torch.tensor([[a[13]]]))
            torch.testing.assert_close(obj._processed_actions,torch.full((1,4),1.1*trigger))
            self.assertEqual(float(torch.max(obj._processed_actions)-torch.min(obj._processed_actions)),0)
        self.assertEqual(command(0),command(12))
        self.assertEqual(command(0),command(24))

    def test_response_difference_distinct_from_target_difference(self):
        row={k:{'value':v} for k,v in dict(direct_q=[.2,.3,.5,.6],direct_velocity=[1,2,3,4],target=[1]*4).items()}
        m=metrics(row)
        self.assertEqual(m['target_spread_rad'],0)
        self.assertAlmostEqual(m['proximal_error_rad'],-.3)
        self.assertAlmostEqual(m['distal_error_rad'],-.3)
        row['target']['value']=[1,1,0,1]
        self.assertEqual(metrics(row)['target_spread_rad'],1)
        row['direct_q']['value']=None
        with self.assertRaises(ValueError):metrics(row)

    def test_schedule_is_bounded_repeatable(self):
        for t in np.arange(0,24,.01):
            phase,x=command(float(t))
            self.assertTrue(0<=x<=1)
            self.assertAlmostEqual(x,command(float(t+24))[1])


if __name__=='__main__':unittest.main()
