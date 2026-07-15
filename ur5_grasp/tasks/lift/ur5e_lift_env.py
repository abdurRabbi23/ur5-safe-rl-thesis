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


class UR5eCubeLiftEnv(ManagerBasedRLEnv):
    """Manager-based lift env with a latch-on-close proximity weld."""

    # cube-to-reach-frame distance (m) at which a close command latches a grasp
    GRASP_TOL: float = 0.06

    def __init__(self, cfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode=render_mode, **kwargs)
        # per-env latch: True while the cube is welded to the gripper
        self._grasped = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)

    def step(self, action: torch.Tensor):
        out = super().step(action)
        self._apply_weld()
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
