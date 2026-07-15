# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + Robotiq 2f-85 articulation config for the grasp env.

Points at the locally-built single-articulation USD produced by
`tools/make_ur5e_robotiq_usd.py` (arm root kept, gripper's nested articulation
root disabled). Joint / body names below are the exact names Isaac Lab reported
when loading that USD — see `ur5_grasp/CONTEXT.md`.

Arm joints (6): shoulder_pan_joint, shoulder_lift_joint, elbow_joint,
                wrist_1_joint, wrist_2_joint, wrist_3_joint
Gripper joints (6): finger_joint (drive) + right_outer_knuckle_joint,
                left_inner_finger_joint, right_inner_finger_joint,
                left_inner_finger_knuckle_joint, right_inner_finger_knuckle_joint
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

# Local corrected USD (repo-relative so it works on any machine that has this repo).
_USD_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "ur5e_robotiq_2f85.usd")
)

# Robotiq 2f-85 finger_joint travel: 0.0 = open, ~0.8 rad = closed.
GRIPPER_OPEN = 0.0
GRIPPER_CLOSE = 0.8

UR5E_ROBOTIQ_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=_USD_PATH,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            max_depenetration_velocity=5.0,
        ),
        # Self-collisions OFF: the 2f-85 has many closely-packed finger bodies; leaving
        # this on blows up GPU contact-pair buffers at high num_envs and hangs physics
        # init. Matches Isaac Lab's manipulation-env convention.
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=16,
            solver_velocity_iteration_count=1,
        ),
        activate_contact_sensors=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        # Ready pose reaching forward over the table (base at origin, table at x=0.5).
        # NOTE: likely needs a small tune after the first visual/play check.
        joint_pos={
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.2,
            "elbow_joint": 1.4,
            "wrist_1_joint": -1.75,
            "wrist_2_joint": -1.57,
            "wrist_3_joint": 0.0,
            # gripper starts open
            "finger_joint": GRIPPER_OPEN,
            "right_outer_knuckle_joint": 0.0,
            "left_inner_finger_joint": 0.0,
            "right_inner_finger_joint": 0.0,
            "left_inner_finger_knuckle_joint": 0.0,
            "right_inner_finger_knuckle_joint": 0.0,
        },
    ),
    actuators={
        "arm": ImplicitActuatorCfg(
            joint_names_expr=[
                "shoulder_pan_joint",
                "shoulder_lift_joint",
                "elbow_joint",
                "wrist_1_joint",
                "wrist_2_joint",
                "wrist_3_joint",
            ],
            effort_limit_sim=150.0,
            velocity_limit_sim=3.14,
            stiffness=800.0,
            damping=40.0,
            armature=0.01,  # effective inertia — improves solver stability
        ),
        # The 2f-85 is a CLOSED-LOOP 4-bar linkage. Drive ONLY finger_joint; leave the
        # coupled joints PASSIVE (stiffness/damping 0) so the mechanical loop makes them
        # follow. Actively holding all of them fights the loop constraint and diverges to
        # NaN (mirrors Isaac Lab's UR10e Robotiq drive/passive split).
        "gripper_drive": ImplicitActuatorCfg(
            joint_names_expr=["finger_joint"],
            # TOUHID: clamp force was ~100x softer than Isaac Lab's Franka gripper
            # (stiffness 2000 / effort 200), which is why the cube fell straight
            # through. Drive finger_joint much harder so the linkage presses the pads.
            effort_limit_sim=200.0,
            velocity_limit_sim=2.0,
            stiffness=400.0,
            damping=20.0,
            armature=0.01,
            friction=0.1,
        ),
        "gripper_passive": ImplicitActuatorCfg(
            joint_names_expr=[
                "right_outer_knuckle_joint",
                "left_inner_finger_joint",
                "right_inner_finger_joint",
                "left_inner_finger_knuckle_joint",
                "right_inner_finger_knuckle_joint",
            ],
            effort_limit_sim=10.0,
            velocity_limit_sim=2.0,
            stiffness=0.0,
            damping=0.5,  # bleed loop-constraint energy so the linkage can't blow up
            armature=0.01,
            friction=0.1,
        ),
    },
)
"""UR5e arm with a Robotiq 2f-85 parallel-jaw gripper (single articulation)."""
