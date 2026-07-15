# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + Robotiq 2f-85 cube-lift env (Layer 1 grasp task).

Retargets Isaac Lab's Franka lift env (privileged object-pose observations,
reach/grasp/lift reward shaping) onto the UR5e. Only the robot, actions, EE frame
and command body change; the base LiftEnvCfg supplies the rest of the MDP.
"""

from isaaclab.assets import RigidObjectCfg
from isaaclab.sensors import FrameTransformerCfg
from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

from isaaclab_tasks.manager_based.manipulation.lift import mdp
from isaaclab_tasks.manager_based.manipulation.lift.lift_env_cfg import LiftEnvCfg

from isaaclab.markers.config import FRAME_MARKER_CFG  # isort: skip
from ur5_grasp.robots.ur5e_robotiq import UR5E_ROBOTIQ_CFG, GRIPPER_CLOSE, GRIPPER_OPEN  # isort: skip


@configclass
class UR5eCubeLiftEnvCfg(LiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # UR5e + Robotiq 2f-85 as the robot
        self.scene.robot = UR5E_ROBOTIQ_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # Arm: joint-position control over the 6 arm joints only.
        self.actions.arm_action = mdp.JointPositionActionCfg(
            asset_name="robot",
            joint_names=[
                "shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
            ],
            scale=0.5,
            use_default_offset=True,
        )
        # Gripper: binary open/close on the Robotiq drive joint.
        self.actions.gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["finger_joint"],
            open_command_expr={"finger_joint": GRIPPER_OPEN},
            close_command_expr={"finger_joint": GRIPPER_CLOSE},
        )

        # End-effector body used by the pose command.
        self.commands.object_pose.body_name = "wrist_3_link"

        # Cube to grasp.
        self.scene.object = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/Object",
            init_state=RigidObjectCfg.InitialStateCfg(pos=[0.5, 0, 0.055], rot=[1, 0, 0, 0]),
            spawn=UsdFileCfg(
                usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd",
                scale=(0.8, 0.8, 0.8),
                rigid_props=RigidBodyPropertiesCfg(
                    solver_position_iteration_count=16,
                    solver_velocity_iteration_count=1,
                    max_angular_velocity=1000.0,
                    max_linear_velocity=1000.0,
                    max_depenetration_velocity=5.0,
                    disable_gravity=False,
                ),
            ),
        )

        # EE frame for the reach/lift rewards: root at arm base, target at the wrist
        # with an offset down to the Robotiq TCP (between the fingers). Offset is
        # approximate — tune after the first visual check.
        marker_cfg = FRAME_MARKER_CFG.copy()
        marker_cfg.markers["frame"].scale = (0.1, 0.1, 0.1)
        marker_cfg.prim_path = "/Visuals/FrameTransformer"
        self.scene.ee_frame = FrameTransformerCfg(
            prim_path="{ENV_REGEX_NS}/Robot/base_link",
            debug_vis=True,  # TOUHID: show the reach-target frame for grasp-geometry check
            visualizer_cfg=marker_cfg,
            target_frames=[
                FrameTransformerCfg.FrameCfg(
                    prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link",
                    name="end_effector",
                    offset=OffsetCfg(pos=[0.0, 0.0, 0.16]),
                ),
            ],
        )

        # NaN/inf firewall: clamp policy observations to a finite range so a single
        # briefly-unstable env can't poison the PPO batch (guards against the
        # `std >= 0.0` crash).
        for _term in ("joint_pos", "joint_vel", "object_position", "target_object_position", "actions"):
            getattr(self.observations.policy, _term).clip = (-100.0, 100.0)


@configclass
class UR5eCubeLiftEnvCfg_PLAY(UR5eCubeLiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        # smaller scene for play / visual debugging
        self.scene.num_envs = 50
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False
