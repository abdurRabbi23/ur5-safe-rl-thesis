# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Config for the real-contact UR5e cube-lift variant (post-Layer-1).

Subclasses the FROZEN Layer-1 cfg (`UR5eCubeLiftEnvCfg`) and applies only the two
fixes found on 2026-07-28. Nothing else about the MDP changes.

  Bug 1 — open/close inverted. Measured pad gap vs finger_joint:
            finger_joint 0.0 -> pads touching  (CLOSED)
            finger_joint 0.8 -> pads ~85 mm     (OPEN, the 2f-85's full stroke)
          Layer 1 had GRIPPER_OPEN=0.0 / CLOSE=0.8, i.e. swapped, so a 'close'
          command drove the hand fully OPEN. Corrected in the gripper action below.

  Bug 2 — reach frame 16 cm off. FrameTransformer used wrist_3 + [0,0,0.16]; the
          real pad midpoint sits only ~1.3 cm from wrist_3. Offset corrected below.
          NOTE: `_TCP_OFFSET` is provisional (world delta at ready pose). Replace it
          with the exact LOCAL offset printed by `scripts/grasp_lift_test.py`.
"""

from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.lift import mdp

from ur5_grasp.tasks.lift.ur5e_lift_env_cfg import UR5eCubeLiftEnvCfg

# physically-correct finger targets (measured 2026-07-28)
GRIPPER_OPEN_TRUE = 0.8   # pads ~85 mm apart
GRIPPER_CLOSE_TRUE = 0.0  # pads touching

# provisional corrected TCP offset; update from grasp_lift_test.py's [local offset] line.
_TCP_OFFSET = (-0.013, 0.0, 0.0)


@configclass
class UR5eCubeContactEnvCfg(UR5eCubeLiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # --- Bug 1: correct the open/close convention -------------------------------
        self.actions.gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["finger_joint"],
            open_command_expr={"finger_joint": GRIPPER_OPEN_TRUE},
            close_command_expr={"finger_joint": GRIPPER_CLOSE_TRUE},
        )

        # Spawn the hand OPEN so a contact grasp starts from a sensible state.
        # (Re-author init_state without mutating the shared Layer-1 robot cfg.)
        robot_cfg = self.scene.robot
        new_joint_pos = dict(robot_cfg.init_state.joint_pos)
        new_joint_pos["finger_joint"] = GRIPPER_OPEN_TRUE
        robot_cfg.init_state = robot_cfg.init_state.replace(joint_pos=new_joint_pos)

        # --- Bug 2: correct the reach-frame offset ----------------------------------
        self.scene.ee_frame.target_frames[0].offset = OffsetCfg(pos=list(_TCP_OFFSET))


@configclass
class UR5eCubeContactEnvCfg_PLAY(UR5eCubeContactEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # smaller scene for play / visual debugging
        self.scene.num_envs = 50
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False
