# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + Robotiq 2f-85 cube-lift env (Layer 1 grasp task).

Retargets Isaac Lab's Franka lift env (privileged object-pose observations,
reach/grasp/lift reward shaping) onto the UR5e. Only the robot, actions, EE frame
and command body change; the base LiftEnvCfg supplies the rest of the MDP.
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

from isaaclab.markers.config import FRAME_MARKER_CFG  # isort: skip
from ur5_grasp.robots.ur5e_robotiq import UR5E_ROBOTIQ_CFG, GRIPPER_CLOSE, GRIPPER_OPEN  # isort: skip
from ur5_grasp.tasks.lift import rewards as lift_rewards  # isort: skip


@configclass
class UR5eCubeLiftEnvCfg(LiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # episode_length_s stays at the base 5.0 s (250 control steps @ 50 Hz).
        # Day 19: tried 7.0 s alongside the 1.0 rad/s speed cap and REVERTED both — see
        # ur5e_robotiq.py. Note for anyone tempted again: `cost_limit` in
        # agents/rsl_rl_cppo_cfg.py is an undiscounted EPISODIC budget over a per-step
        # cost, so changing episode length silently rescales the constraint and voids the
        # Day-9 calibration. Change the two together or not at all.

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

        # Goal-pose sampling box, widened Day 23 (cont.) from Isaac Lab's inherited Franka
        # defaults (pos_x=(0.4,0.6), pos_y=(-0.25,0.25), pos_z=(0.25,0.5) -- never previously
        # overridden here). Touhid's call: the old box felt too narrow; widened once, then
        # widened again the same session (still before any run against either version).
        #
        # Kept reach-limited on purpose. The UR5e base sits at the env origin
        # (ur5e_robotiq.py init_state) and its rated reach is ~0.85 m. The box's far corner
        # (max x, max |y|, max z) is what determines whether a sampled goal is physically
        # reachable -- distance history:
        #   Isaac Lab default   (0.60, 0.25, 0.50) -> 0.82 m  (already near full extension)
        #   first draft, REJECTED (0.70, 0.40, 0.62) -> 1.02 m  (unreachable)
        #   round 1              (0.60, 0.28, 0.50) -> 0.83 m
        #   round 2 (current)    (0.60, 0.30, 0.50) -> 0.84 m  (~13 mm under the 0.85 m spec)
        # x and z have a "cheap" direction -- extending the MIN bound toward the base doesn't
        # touch the far-corner distance at all, so most of round 2's extra width comes from
        # there (x_min 0.30->0.22, z_min 0.15->0.10); y has no cheap side (both bounds are
        # squared symmetrically in the distance), so it only got a small +/-0.28->+/-0.30 bump,
        # and x_max/z_max stayed put to protect the shrinking reach margin.
        # Near corner sanity check: (0.22, 0, 0.10) is 0.24 m from the base -- a normal working
        # distance, not a folded-arm degenerate pose, but still worth watching in the Step 4
        # recalibration probe (RUN_CHECKLIST_v2.md) since a 6-DOF arm can also go singular
        # reaching in close.
        #
        # CALIBRATION WARNING: MANIP_FLOOR (ur5e_lift_env.py) and cost_limit (agents/
        # rsl_rl_cppo_cfg.py) were both calibrated Day 9 against the OLD, narrower box. A
        # different goal region changes how often the arm nears joint limits / low
        # manipulability while reaching, which changes the natural cost distribution those
        # thresholds assume. Recalibrate (rerun calibrate_manipulability.py + a short cost probe)
        # BEFORE trusting RUN_CHECKLIST_v2.md Step 7's "did cost_limit=10 bind?" check. See
        # run_log.md, Day 23 (cont.).
        self.commands.object_pose.ranges = mdp.UniformPoseCommandCfg.Ranges(
            pos_x=(0.22, 0.60), pos_y=(-0.30, 0.30), pos_z=(0.10, 0.50),
            roll=(0.0, 0.0), pitch=(0.0, 0.0), yaw=(0.0, 0.0),
        )

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

        # Reward re-weighting + goal-relative lift condition, Day 23 (cont.). Isaac Lab's
        # inherited Franka defaults gate "lifted" on a FIXED height (minimal_height=0.04 m,
        # same number reused by all three of lifting_object / object_goal_tracking /
        # object_goal_tracking_fine_grained). Touhid's call: "lifted" should instead mean
        # 50% of the way from the table to THIS EPISODE's goal height, since pos_z now spans
        # 0.10-0.50 m rather than a narrow band. All three terms switch together so they keep
        # agreeing on what "lifted" means (see rewards.py for the two new functions; neither
        # touches vendored Isaac Lab source). spawn_height is read from the cube's own
        # init_state above rather than hardcoded a second time.
        spawn_height = self.scene.object.init_state.pos[2]  # 0.055 m, table rest height
        lift_fraction = 0.5

        self.rewards.lifting_object = RewTerm(
            func=lift_rewards.object_lifted_toward_goal,
            params={
                "fraction": lift_fraction,
                "spawn_height": spawn_height,
                "command_name": "object_pose",
            },
            weight=10.0,  # was 15.0
        )
        self.rewards.object_goal_tracking = RewTerm(
            func=lift_rewards.object_goal_distance_relative_lift,
            params={
                "std": 0.3,
                "fraction": lift_fraction,
                "spawn_height": spawn_height,
                "command_name": "object_pose",
            },
            weight=15.0,  # was 16.0
        )
        self.rewards.object_goal_tracking_fine_grained = RewTerm(
            func=lift_rewards.object_goal_distance_relative_lift,
            params={
                "std": 0.05,
                "fraction": lift_fraction,
                "spawn_height": spawn_height,
                "command_name": "object_pose",
            },
            weight=5.0,  # unchanged -- only the lift gate changed, to stay consistent with the
                        # other two terms above
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
