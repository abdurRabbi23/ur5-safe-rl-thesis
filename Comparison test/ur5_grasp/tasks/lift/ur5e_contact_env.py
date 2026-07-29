# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e lift env with REAL finger contact (no proximity weld) — post-Layer-1 variant.

Layer 1 (`ur5e_lift_env.py`) uses a proximity weld because the grasp never physically
closed. That was diagnosed on 2026-07-28 as two *config* bugs — not a physics limit:

  1. gripper open/close inverted (finger_joint 0.0 = pads touching/CLOSED, 0.8 = 85 mm/OPEN);
  2. reach frame 16 cm off the pads (pads sit ~1.3 cm from wrist_3, cfg used 0.16 m).

The fingers already carry enabled convex-hull colliders, so once the two bugs are fixed
the 2f-85 can grip with contact forces. This class fixes them via `ur5e_contact_env_cfg`
and drops the weld. Layer 1 (weld) is left FROZEN as the passed baseline; this is the
`-Contact-v0` variant used for the post-Layer-1 contact-grasp study.
"""

from __future__ import annotations

from ur5_grasp.tasks.lift.ur5e_lift_env import UR5eCubeLiftEnv


class UR5eCubeContactEnv(UR5eCubeLiftEnv):
    """Lift env that keeps the Layer-1 safety-cost machinery but removes the weld.

    Inherits everything from the Layer-1 env — including the per-step safety cost
    published on ``extras['cost']`` for the cPPO agent — but overrides the proximity
    weld to a no-op, so the cube is held only by genuine finger contact.
    """

    def _apply_weld(self) -> None:
        # Real contact physics: no latch-on-close teleport weld.
        return
