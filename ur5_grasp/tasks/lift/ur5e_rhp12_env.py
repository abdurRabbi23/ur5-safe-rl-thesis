# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + RH-P12-RN lift env — REAL CONTACT GRASP, no proximity weld.

`UR5eCubeLiftEnv` (the Layer 1 env) latches the cube to the gripper when the policy
commands CLOSE nearby, because the Robotiq 2f-85 cannot transmit grip force in PhysX.
The RH-P12-RN can, so this subclass switches the weld OFF and keeps everything else —
including the safety-cost channel used by cPPO — identical.

Keeping the cost computation matters: it means a cPPO-vs-PPO run on this env is directly
comparable with the Layer 1 numbers, with contact grasping as the only changed variable.

Layer 1 files are NOT modified. This is additive.
"""

from __future__ import annotations

from ur5_grasp.tasks.lift.ur5e_lift_env import UR5eCubeLiftEnv


class UR5eRHP12LiftEnv(UR5eCubeLiftEnv):
    """Lift env whose grasp comes from finger contact rather than a kinematic latch."""

    def _apply_weld(self):
        """Disabled. The RH-P12-RN holds the cube with real contact forces.

        Deliberately a no-op override rather than a config flag: if this env ever starts
        succeeding suspiciously fast, the first thing to check is that nothing has
        re-enabled a latch behind your back.
        """
        return
