# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e lift env with a proximity-weld grasp abstraction (Layer 1 escape hatch).

The Robotiq 2f-85 is a closed-loop linkage whose passive finger joints transmit
no normal force to the pads in Isaac Lab, so contact-based grasping does not hold
a cube (verified with scripts/grasp_hold_test.py: cube falls through regardless of
clamp force). Since the Layer 1 safe-RL result (cPPO vs PPO) is gripper-agnostic,
we replace contact grasping with a proximity weld:

  * when the policy commands CLOSE (gripper action < 0) AND the cube is within
    GRASP_TOL of the reach frame (between the fingers), the cube latches to the
    gripper — its pose tracks the reach frame each control step (velocity zeroed),
  * when the policy commands OPEN, the cube releases and physics resumes.

This makes "grasp + lift" reliable so PPO (and then cPPO) can learn the task.
Realistic finger contact is deferred to the Layer 3 sim-to-real window.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch

from isaaclab.envs import ManagerBasedRLEnv

from ur5_grasp.safe_rl.costs import SafetyCostComputer


class UR5eCubeLiftEnv(ManagerBasedRLEnv):
    """Manager-based lift env with a latch-on-close proximity weld.

    Also emits a per-step safety cost on ``self.extras["cost"]`` (used by the cPPO
    Lagrangian agent; ignored by the stock PPO baseline). Cost is computed for BOTH
    agents so the benchmark can report the baseline's violation rate too.
    """

    # cube-to-reach-frame distance (m) at which a close command latches a grasp
    GRASP_TOL: float = 0.06

    # ---- safety-cost config (Layer 1 constraints) ----------------------------------
    COST_ENABLED: bool = True
    ARM_JOINTS = [
        "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
        "wrist_1_joint", "wrist_2_joint", "wrist_3_joint",
    ]
    EE_BODY: str = "wrist_3_link"
    MONITORED_BODIES = ["forearm_link", "wrist_1_link", "wrist_3_link"]
    COLLISION_Z_FLOOR: float = 0.0    # table-plane height (m); VERIFY vs the table prim
    JOINT_LIMIT_MARGIN: float = 0.10  # rad (~5.7 deg) before a soft joint limit
    MANIP_FLOOR: float = 0.045        # calibrated Day 9 (baseline w: min .021/mean .055/max .114;
                                      # floor ~p10-p25 -> ~20% baseline violation). THE active constraint.
    W_COLLISION: float = 1.0
    W_JOINT: float = 1.0
    W_MANIP: float = 1.0

    def __init__(self, cfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode=render_mode, **kwargs)
        # per-env latch: True while the cube is welded to the gripper
        self._grasped = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self._cost_computer: SafetyCostComputer | None = None  # built lazily on first step

    def step(self, action: torch.Tensor):
        out = super().step(action)
        self._apply_weld()
        self._apply_cost()
        return out

    def _reset_idx(self, env_ids: Sequence[int]):
        super()._reset_idx(env_ids)
        # guard: super().__init__ triggers a reset before _grasped exists
        if hasattr(self, "_grasped"):
            self._grasped[env_ids] = False

    def _apply_weld(self):
        obj = self.scene["object"]
        ee = self.scene["ee_frame"]

        # gripper CLOSE command == last raw action < 0 (BinaryJointPositionAction)
        closing = self.action_manager.action[:, -1] < 0.0
        tcp = ee.data.target_pos_w[:, 0, :]                       # (N, 3) reach frame
        dist = torch.norm(obj.data.root_pos_w - tcp, dim=-1)      # (N,)

        # latch on close+near, release on open
        self._grasped = torch.where(closing & (dist < self.GRASP_TOL),
                                    torch.ones_like(self._grasped), self._grasped)
        self._grasped = torch.where(~closing, torch.zeros_like(self._grasped), self._grasped)

        ids = self._grasped.nonzero(as_tuple=False).squeeze(-1)
        if ids.numel() > 0:
            pose = obj.data.root_pose_w[ids].clone()             # (k, 7) pos+quat
            pose[:, 0:3] = tcp[ids]                              # snap position to reach frame
            obj.write_root_pose_to_sim(pose, env_ids=ids)
            obj.write_root_velocity_to_sim(
                torch.zeros((ids.numel(), 6), device=self.device), env_ids=ids
            )

    def _apply_cost(self):
        """Compute the per-step safety cost and publish it on extras (for cPPO)."""
        if not self.COST_ENABLED:
            return
        if self._cost_computer is None:
            self._cost_computer = SafetyCostComputer(
                robot=self.scene["robot"],
                arm_joint_names=self.ARM_JOINTS,
                ee_body_name=self.EE_BODY,
                monitored_body_names=self.MONITORED_BODIES,
                z_floor=self.COLLISION_Z_FLOOR,
                joint_margin=self.JOINT_LIMIT_MARGIN,
                manip_floor=self.MANIP_FLOOR,
                w_collision=self.W_COLLISION,
                w_joint=self.W_JOINT,
                w_manip=self.W_MANIP,
            )
        total, info = self._cost_computer.compute()
        # channel consumed by the cPPO agent (process_env_step reads extras["cost"])
        self.extras["cost"] = total
        # per-term diagnostics -> TensorBoard (runner averages extras["log"] each rollout)
        log = self.extras.setdefault("log", {})
        log.update(info)
