"""A simulated toaster latch, four-second timer, and contact-driven bread carriage."""

import torch

from . import mdp


class ToastCycle:
    # Idle, lowering, heating, rising, complete. Times are simulation seconds.
    STROKE = .045
    HEATING_SECONDS = 4.0
    LOWER_SECONDS = .60
    RISE_SECONDS = .80
    STATE_NAMES = ("phase", "elapsed", "command", "previous_pressed", "heating_time")

    BREAD_STATE_NAMES = ("heating_present", "heated_bread")

    def __init__(self, env):
        self.env = env
        self.toaster = env.scene["toaster"]
        self.carriage_id = self.toaster.joint_names.index("carriage_joint")
        self.lever_id = self.toaster.joint_names.index("joint_1")
        self.popup_height = getattr(env.cfg, "toast_popup_extra_height", 0.0)
        for name in self.STATE_NAMES:
            setattr(self, name, torch.zeros(env.num_envs, device=env.device))

        for name in self.BREAD_STATE_NAMES:
            setattr(self, name, torch.zeros((env.num_envs, 4), dtype=torch.bool, device=env.device))

    def reset(self, env_ids):
        for name in (*self.STATE_NAMES, *self.BREAD_STATE_NAMES):
            getattr(self, name)[env_ids] = 0
        self.apply_targets()

    def state(self, env_ids=None):
        ids = slice(None) if env_ids is None else env_ids
        result = {name: getattr(self, name)[ids, None].clone() for name in self.STATE_NAMES}
        result.update({name: getattr(self, name)[ids].clone() for name in self.BREAD_STATE_NAMES})
        return result

    def restore(self, state, env_ids):
        for name in self.STATE_NAMES:
            getattr(self, name)[env_ids] = state[name].reshape(-1)
        # Legacy recordings have no per-bread evidence: fail closed, never infer
        # cooked IDs from a global phase or timer alone.
        for name in self.BREAD_STATE_NAMES:
            value = state.get(name)
            getattr(self, name)[env_ids] = (False if value is None else
                torch.as_tensor(value, device=self.env.device, dtype=torch.bool).reshape(-1, 4))
        self.apply_targets()

    def apply_targets(self):
        self.toaster.set_joint_position_target(self.command[:, None], [self.carriage_id])
        # Leave the lever passive until a real press latches the mechanism.
        latched = (self.phase == 1) | (self.phase == 2)
        active = self.phase > 0
        stiffness = torch.where(active, 1500.0, 0.0)[:, None]
        self.toaster.write_joint_stiffness_to_sim(stiffness, [self.lever_id])
        limits = self.toaster.data.joint_pos_limits[:, self.lever_id]
        target = torch.where(latched, limits[:, 1], limits[:, 0])
        self.toaster.set_joint_position_target(target[:, None], [self.lever_id])

    def update(self, dt):
        from .bimanual_mdp import bread_in_slot

        ratio = mdp.lever_press_ratio(self.env)
        pressed = ratio >= .90
        # Appliance readiness includes all four slices; task success is separate.
        # Reuse the unchanged geometric predicate for each slice/slot pair.
        present = torch.stack([
            bread_in_slot(self.env, f"bread_{i}", 0) | bread_in_slot(self.env, f"bread_{i}", 1)
            for i in range(4)
        ], dim=-1)
        loaded = present.any(dim=-1)
        trigger = (self.phase == 0) & pressed & (self.previous_pressed == 0) & loaded
        self.phase[trigger] = 1
        self.elapsed[trigger] = 0
        self.previous_pressed.copy_(pressed.float())
        self.elapsed[self.phase > 0] += dt
        lowering = self.phase == 1
        u = (self.elapsed / self.LOWER_SECONDS).clamp(0, 1)
        self.command[lowering] = -self.STROKE * (u * u * (3 - 2 * u))[lowering]
        q = self.toaster.data.joint_pos[:, self.carriage_id]
        qd = self.toaster.data.joint_vel[:, self.carriage_id]
        lowered = lowering & (self.elapsed >= self.LOWER_SECONDS) & ((q + self.STROKE).abs() < .0015)
        lowered &= qd.abs() < .01
        # Eligibility begins at heating entry, not at the lever press. Any
        # observed absence/misalignment during heating permanently invalidates
        # that slice for this cycle, including removal followed by reinsertion.
        self.heating_present[lowered] = present[lowered]
        self.phase[lowered] = 2
        self.elapsed[lowered] = 0
        heating = self.phase == 2
        self.heating_present[heating] &= present[heating]
        self.command[heating] = -self.STROKE
        self.heating_time[heating] = self.elapsed[heating]
        finished = heating & (self.elapsed >= self.HEATING_SECONDS)
        self.heated_bread[finished] |= self.heating_present[finished]
        self.phase[finished] = 3
        self.elapsed[finished] = 0
        rising = self.phase == 3
        u = (self.elapsed / self.RISE_SECONDS).clamp(0, 1)
        self.command[rising] = -self.STROKE * (1 - u * u * (3 - 2 * u))[rising]
        self.command[rising] += self.popup_height * (u * u * (3 - 2 * u))[rising]
        # Position-drive constraint stabilization can report residual velocity
        # under gravity even once its measured position is stationary.
        raised = rising & (self.elapsed >= self.RISE_SECONDS + .12) & ((q - self.popup_height).abs() < .0015)
        self.phase[raised] = 4
        self.command[self.phase == 4] = self.popup_height
        self.apply_targets()
