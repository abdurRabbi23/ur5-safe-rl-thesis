# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + RH-P12-RN cube-lift env cfg (real contact grasp).

Mirrors `ur5e_lift_env_cfg.py` exactly except for the four things the gripper swap
forces to change:

  1. robot cfg          -> UR5E_RHP12_CFG
  2. gripper action     -> all FOUR finger joints on one binary open/close command
  3. ee_frame offset    -> TCP_OFFSET (0.130) instead of the Robotiq's 0.16
  4. env class          -> UR5eRHP12LiftEnv (weld disabled)
  5. lifting_object     -> dense `object_lift_progress` instead of the 0.04 m step

(5) is the one deliberate departure from "change only the grasp mechanism". Without the
weld, `object_is_lifted` is a cliff a random policy cannot cross, so the run would be
measuring exploration failure rather than grasp mechanics. The replacement is a strict
superset — identical (1.0) at and above 0.04 m, a gated ramp below — so the reward
landscape past the threshold is untouched. It makes raw episode reward NON-comparable
with Layer 1; compare on lift-success % and safety-violation % instead. Rationale in
`rhp12_rewards.py`.

Everything else — arm action, cube, observations, obs clamps — is inherited unchanged.
"""

from isaaclab.assets import RigidObjectCfg
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.sensors import FrameTransformerCfg
from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

from isaaclab_tasks.manager_based.manipulation.lift import mdp
from isaaclab_tasks.manager_based.manipulation.lift.lift_env_cfg import LiftEnvCfg

from ur5_grasp.tasks.lift import rhp12_rewards

from isaaclab.markers.config import FRAME_MARKER_CFG  # isort: skip
from ur5_grasp.robots.ur5e_rhp12 import (  # isort: skip
    UR5E_RHP12_CFG,
    GRIPPER_CLOSE,
    GRIPPER_JOINT_NAMES,
    GRIPPER_OPEN,
    TCP_OFFSET,
)


@configclass
class UR5eRHP12LiftEnvCfg(LiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = UR5E_RHP12_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # Arm: joint-position control over the 6 arm joints only (same as Layer 1).
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
        # Gripper: ONE binary command driving all four finger joints to the same target.
        # The action space is unchanged from Layer 1 (still a single open/close scalar),
        # so policies and network shapes stay comparable.
        self.actions.gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=GRIPPER_JOINT_NAMES,
            open_command_expr={j: GRIPPER_OPEN for j in GRIPPER_JOINT_NAMES},
            close_command_expr={j: GRIPPER_CLOSE for j in GRIPPER_JOINT_NAMES},
        )

        self.commands.object_pose.body_name = "wrist_3_link"

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

        # EE frame: wrist_3_link + TCP_OFFSET along wrist +z to the point between the pads.
        # 0.130, not the Robotiq's 0.16 — the RH-P12-RN is a shorter hand, but its fingers
        # CURL FORWARD as they close, so the grasp centre is not the open-pose midpoint.
        # 0.130 is calibrated by contact (scripts/rhp12_grasp_sweep.py, 2026-07-26): it is
        # the offset whose pad FACES close to 0.0413 m on a 0.0412 m cube. Do not "correct"
        # it toward the open-pose value without re-running that sweep.
        marker_cfg = FRAME_MARKER_CFG.copy()
        marker_cfg.markers["frame"].scale = (0.1, 0.1, 0.1)
        marker_cfg.prim_path = "/Visuals/FrameTransformer"
        self.scene.ee_frame = FrameTransformerCfg(
            prim_path="{ENV_REGEX_NS}/Robot/base_link",
            debug_vis=True,
            visualizer_cfg=marker_cfg,
            target_frames=[
                FrameTransformerCfg.FrameCfg(
                    prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link",
                    name="end_effector",
                    offset=OffsetCfg(pos=[0.0, 0.0, TCP_OFFSET]),
                ),
            ],
        )

        # ---- reward: dense lift progress instead of the 0.04 m step ----------------
        # The weld made the step crossable for free. Without it, a random policy never
        # reaches 0.04 m, so `object_is_lifted` pays nothing and the only live gradient
        # is `object_ee_distance`, which saturates near the cube. This keeps the value at
        # and above 0.04 m EXACTLY as before (1.0, weight 15.0, so `object_goal_distance`
        # still switches on at the same point) and only adds a slope underneath it.
        # `rest_height` is measured, not assumed: results/rhp12_geometry_check.txt puts
        # the resting cube centre at z = 0.021 m. `near_tol` stops the ramp being farmed
        # by batting the cube upward — see rhp12_rewards.py.
        self.rewards.lifting_object = RewTerm(
            func=rhp12_rewards.object_lift_progress,
            params={"minimal_height": 0.04, "rest_height": 0.021, "near_tol": 0.05},
            weight=15.0,
        )

        # Same NaN/inf firewall as Layer 1.
        for _term in ("joint_pos", "joint_vel", "object_position", "target_object_position", "actions"):
            getattr(self.observations.policy, _term).clip = (-100.0, 100.0)


@configclass
class UR5eRHP12LiftEnvCfg_PLAY(UR5eRHP12LiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 50
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False


@configclass
class UR5eRHP12LiftEnvCfg_STOCK(UR5eRHP12LiftEnvCfg):
    """ABLATION: the contact-grasp env with Layer 1's ORIGINAL sparse lift reward.

    Exists so the weld comparison can be made with the reward function held constant.
    Identical to `UR5eRHP12LiftEnvCfg` in every respect except that `lifting_object`
    reverts to the stock 0.04 m step, which makes raw episode reward directly comparable
    with the frozen Layer 1 numbers (cPPO 166.3 / PPO 167.2).

    Run BOTH. This one answers "is the task learnable without the weld and without help?";
    the shaped one answers "and how much help does it need?". The gap between them IS the
    exploration cost of removing the weld.
    """

    def __post_init__(self):
        super().__post_init__()
        self.rewards.lifting_object = RewTerm(
            func=mdp.object_is_lifted,
            params={"minimal_height": 0.04},
            weight=15.0,
        )


@configclass
class UR5eRHP12LiftEnvCfg_STOCK_PLAY(UR5eRHP12LiftEnvCfg_STOCK):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 50
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False
