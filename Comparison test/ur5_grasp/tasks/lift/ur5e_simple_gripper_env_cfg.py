# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Config for the UR5e + simple two-finger gripper lift variant (Day 20 replacement
for the Robotiq 2f-85 contact-grasp attempt).

Subclasses the FROZEN Layer-1 cfg (`UR5eCubeLiftEnvCfg`) directly — NOT
`UR5eCubeContactEnvCfg` (that class's TCP offset / finger_joint assumptions were built
on the now-superseded "~1.3 cm" theory from before the Day 18 diagnosis; this gripper
has different geometry entirely, so start clean from the frozen base).

Reuses the existing `UR5eCubeContactEnv` class UNCHANGED (`ur5e_contact_env.py`) — that
class only does one thing, override `_apply_weld` to a no-op, which is exactly what a
real-contact grasp needs regardless of which gripper is attached. Nothing in it is
Robotiq-specific.

Overrides vs. the frozen base, both required because the gripper is physically
different, not because anything else about the MDP changed:
  - `scene.robot`: UR5E_ROBOTIQ_CFG -> UR5E_SIMPLE_GRIPPER_CFG
  - `actions.gripper_action`: single `finger_joint` -> two independent joints
    (`left_finger_joint`, `right_finger_joint`), open/close values from
    `robots/ur5e_simple_gripper.py`
  - `scene.ee_frame` offset: the grasp point between the finger tips, imported from
    `robots/gripper_geometry.py` (TCP_OFFSET_POS / TCP_OFFSET_ROT) rather than written
    out by hand. NOT the old 0.16 m — that was sized for the much longer real 2f-85 body.

Day 21 — why the offset now carries a ROTATION as well as a translation. It used to be
`OffsetCfg(pos=[0, 0, 0.075])`: a distance along `wrist_3_link`'s local +Z, on the
assumption that +Z is the arm's tool axis. It is not — the GUI showed the gripper sticking
out of the SIDE of the wrist. That assumption was inherited from the frozen weld env's
`OffsetCfg(pos=[0, 0, 0.16])` (commented "approx, tune") and could never have been caught
there, because a weld env teleports the cube to whatever point the TCP names: a TCP hanging
in mid-air off the side of the wrist trains to 100% success exactly like a correct one.
The real axis is now MEASURED by `tools/check_wrist_frame.py`, and `TCP_OFFSET_ROT` aligns
the TCP frame's own +Z with the true approach direction — which matters because anything
that reasons about approach direction (the IK in the live demo, and Layer 2's IBVS later)
reads that frame's orientation, not just its position.
"""

from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.lift import mdp

from ur5_grasp.robots.gripper_geometry import TCP_OFFSET_POS, TCP_OFFSET_ROT
from ur5_grasp.robots.ur5e_simple_gripper import (
    GRIPPER_CLOSE_L,
    GRIPPER_CLOSE_R,
    GRIPPER_OPEN_L,
    GRIPPER_OPEN_R,
    UR5E_SIMPLE_GRIPPER_CFG,
)
from ur5_grasp.tasks.lift.ur5e_lift_env_cfg import UR5eCubeLiftEnvCfg


@configclass
class UR5eSimpleGripperLiftEnvCfg(UR5eCubeLiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # New robot: UR5e + simple two-finger prismatic gripper (no linkage).
        self.scene.robot = UR5E_SIMPLE_GRIPPER_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # Gripper: two independent joints, driven directly and symmetrically.
        self.actions.gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["left_finger_joint", "right_finger_joint"],
            open_command_expr={"left_finger_joint": GRIPPER_OPEN_L, "right_finger_joint": GRIPPER_OPEN_R},
            close_command_expr={"left_finger_joint": GRIPPER_CLOSE_L, "right_finger_joint": GRIPPER_CLOSE_R},
        )

        # Reach-frame offset: the grasp point between the finger tips, on the MEASURED
        # tool axis, with the TCP frame's +Z aligned to the approach direction. Both
        # values are derived in robots/gripper_geometry.py — change the geometry there,
        # not here.
        self.scene.ee_frame.target_frames[0].offset = OffsetCfg(
            pos=TCP_OFFSET_POS, rot=TCP_OFFSET_ROT
        )


@configclass
class UR5eSimpleGripperLiftEnvCfg_PLAY(UR5eSimpleGripperLiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # smaller scene for play / visual debugging
        self.scene.num_envs = 50
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False
