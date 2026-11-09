"""CPU-only configuration contract; never starts Isaac Sim or imports teleop."""
import ast
import argparse
import contextlib
import copy
import io
import re
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from teleop_gripper_options import configure_right_j3_speed,configure_right_j1_speed

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2'


def config():
    tree=ast.parse((ROOT/'source/cyclo_lab/cyclo_lab/assets/robots/FFW_BG2.py').read_text())
    robot=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FFW_BG2_CFG' for t in n.targets))
    actuators=next(k.value for k in robot.keywords if k.arg=='actuators')
    # Evaluate actual config literals with an inert constructor. No simulator import.
    scope={'ImplicitActuatorCfg':lambda **kw:NS(**({'velocity_limit_sim':None}|kw))}
    groups=eval(compile(ast.Expression(actuators),'actual_robot_config','eval'),scope)
    cfg=NS(scene=NS(robot=NS(actuators=groups,spawn=NS(collision='unchanged')),camera='unchanged'),
           seed=1,scenario_id='batch02_toast_001',solver='unchanged',actions='unchanged')
    task=ast.parse((TASK/'bimanual_env_cfg.py').read_text())
    for n in ast.walk(task):
        if isinstance(n,ast.Assign) and len(n.targets)==1 and ast.unparse(n.targets[0]) in (
            "self.scene.robot.actuators['gripper_slave'].stiffness",
            "self.scene.robot.actuators['gripper_slave'].damping",
            "self.scene.robot.actuators['gripper_master'].velocity_limit_sim"):
            exec(compile(ast.fix_missing_locations(ast.Module(body=[n],type_ignores=[])),'actual_task_override','exec'),{'self':cfg})
    return cfg


def per_joint(cfg):
    names=['lift_joint','head_joint1','head_joint2']+[f'arm_{s}_joint{i}' for s in ('l','r') for i in range(1,8)]+[f'gripper_{s}_joint{i}' for s in ('l','r') for i in range(1,5)]
    result={}
    for name in names:
        matches=[a for a in cfg.scene.robot.actuators.values() if any(re.fullmatch(p,name) for p in a.joint_names_expr)]
        if len(matches)!=1:raise AssertionError((name,len(matches)))
        result[name]={k:v for k,v in vars(matches[0]).items() if k!='joint_names_expr'}
    return result


class TeleopGripperOptionsTests(unittest.TestCase):
    def test_default_is_exact_noop(self):
        cfg=config();before=copy.deepcopy(cfg);groups=cfg.scene.robot.actuators
        configure_right_j3_speed(cfg)
        configure_right_j1_speed(cfg)
        self.assertIs(cfg.scene.robot.actuators,groups)
        self.assertEqual(cfg,before)

    def test_actual_final_task_j1_option_keeps_6p5_no_overlap(self):
        cfg=config();before=copy.deepcopy(cfg);old_groups=cfg.scene.robot.actuators
        configure_right_j1_speed(cfg,True)
        left=per_joint(before);right=per_joint(cfg)
        delta=[(name,k,left[name].get(k),v) for name,values in right.items() for k,v in values.items() if left[name].get(k)!=v]
        self.assertEqual(delta,[])
        self.assertEqual(right['gripper_l_joint1']['velocity_limit_sim'],6.5)
        self.assertEqual(right['gripper_r_joint1']['velocity_limit_sim'],6.5)
        self.assertEqual(right['gripper_r_joint1']['stiffness'],100.)
        self.assertEqual(right['gripper_r_joint1']['damping'],4.)
        self.assertEqual(right['gripper_r_joint1']['effort_limit_sim'],30.)
        self.assertEqual(old_groups,before.scene.robot.actuators)
        cfg.scene.robot.actuators=before.scene.robot.actuators
        self.assertEqual(cfg,before)

    def test_actual_cli_abc_and_mutual_exclusion(self):
        tree=ast.parse(Path(__file__).with_name('teleop_toast.py').read_text())
        # Execute only the actual argparse group statements, never teleop imports.
        nodes=[n for n in tree.body if
               (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='gripper_speed_options' for t in n.targets)) or
               (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='gripper_speed_options.add_argument')]
        self.assertEqual(len(nodes),3)
        parser=argparse.ArgumentParser()
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_cli','exec'),{'parser':parser})
        for flags,expected in (([],[6.5,None,None,None]),
                               (['--right-gripper-j3-speed-2p2'],[6.5,None,2.2,None]),
                               (['--right-gripper-j1-speed-6p5'],[6.5,None,None,None])):
            args=parser.parse_args(flags);cfg=config()
            configure_right_j3_speed(cfg,args.right_gripper_j3_speed_2p2)
            configure_right_j1_speed(cfg,args.right_gripper_j1_speed_6p5)
            # None means preserve the authored USD speed, not override it.
            values=per_joint(cfg)
            self.assertEqual([values[f'gripper_r_joint{i}']['velocity_limit_sim'] for i in range(1,5)],expected)
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as exc:
            parser.parse_args(['--right-gripper-j3-speed-2p2','--right-gripper-j1-speed-6p5'])
        self.assertEqual(exc.exception.code,2)

    def test_actual_final_task_only_j3_speed_changes_no_overlap(self):
        cfg=config();before=copy.deepcopy(cfg);old_groups=cfg.scene.robot.actuators
        configure_right_j3_speed(cfg,True)
        left=per_joint(before);right=per_joint(cfg)
        delta=[(name,k,left[name].get(k),v) for name,values in right.items() for k,v in values.items() if left[name].get(k)!=v]
        self.assertEqual(delta,[('gripper_r_joint3','velocity_limit_sim',None,2.2)])
        self.assertEqual(right['gripper_r_joint3']['stiffness'],100.)
        self.assertEqual(right['gripper_r_joint3']['damping'],4.)
        self.assertEqual(right['gripper_r_joint3']['effort_limit_sim'],20.)
        self.assertEqual(old_groups,before.scene.robot.actuators)
        cfg.scene.robot.actuators=before.scene.robot.actuators
        self.assertEqual(cfg,before)

    def test_cfg_has_no_runtime_or_reset_mutation_path(self):
        tree=ast.parse(Path(__file__).with_name('teleop_gripper_options.py').read_text())
        calls=[ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)]
        self.assertEqual(set(calls),{'deepcopy'})
        tree=ast.parse((ROOT/'third_party/IsaacLab/source/isaaclab/isaaclab/assets/articulation/articulation.py').read_text())
        reset=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='reset')
        self.assertNotIn('velocity_limit',ast.unparse(reset))

    def test_teleop_startup_config_and_readback_outside_loop(self):
        tree=ast.parse(Path(__file__).with_name('teleop_toast.py').read_text())
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        configure_calls=[n for n in calls if ast.unparse(n.func)=='configure_right_j3_speed']
        make=next(n for n in calls if ast.unparse(n.func)=='gym.make')
        self.assertEqual(len(configure_calls),1);self.assertLess(configure_calls[0].lineno,make.lineno)
        configure_c=[n for n in calls if ast.unparse(n.func)=='configure_right_j1_speed']
        self.assertEqual(len(configure_c),1);self.assertLess(configure_c[0].lineno,make.lineno)
        reads=[n for n in calls if ast.unparse(n.func).endswith('get_dof_max_velocities')]
        self.assertEqual(len(reads),1)
        loop=next(n for n in ast.walk(tree) if isinstance(n,ast.While) and 'app.is_running' in ast.unparse(n.test))
        self.assertLess(reads[0].lineno,loop.lineno)
        option=next(n for n in calls if n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='--right-gripper-j3-speed-2p2')
        self.assertEqual(next(k.value.value for k in option.keywords if k.arg=='action'),'store_true')


if __name__=='__main__':unittest.main()
