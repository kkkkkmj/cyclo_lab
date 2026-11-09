"""Opt-in VR configuration only; no simulator reads, stepping or diagnostics."""
from copy import deepcopy


def configure_right_j3_speed(cfg, enabled=False):
    if not enabled:
        return
    # Clone the final task actuators, retaining the task's existing slave gains
    # and all USD-derived defaults. Do not alter the shared robot configuration.
    actuators = deepcopy(cfg.scene.robot.actuators)
    j3 = deepcopy(actuators['gripper_slave'])
    j3.joint_names_expr = ['gripper_r_joint3']
    j3.velocity_limit_sim = 2.2
    actuators['gripper_slave'].joint_names_expr = ['gripper_l_joint[2-4]', 'gripper_r_joint[24]']
    actuators['gripper_right_j3'] = j3
    cfg.scene.robot.actuators = actuators


def configure_right_j1_speed(cfg, enabled=False):
    if not enabled:
        return
    # Independent comparison C: split only the right master from the final
    # task config. Left master and every slave retain their existing settings.
    actuators = deepcopy(cfg.scene.robot.actuators)
    j1 = deepcopy(actuators['gripper_master'])
    j1.joint_names_expr = ['gripper_r_joint1']
    j1.velocity_limit_sim = 6.5
    actuators['gripper_master'].joint_names_expr = ['gripper_l_joint1']
    actuators['gripper_right_j1'] = j1
    cfg.scene.robot.actuators = actuators
