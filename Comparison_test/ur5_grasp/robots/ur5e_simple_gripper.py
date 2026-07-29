# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + simple two-finger prismatic gripper articulation config.

Points at `ur5_grasp/assets/ur5e_simple_gripper.usd`, built by
`tools/make_ur5e_simple_gripper_usd.py`. Replaces `ur5e_robotiq.py` for the grasp env —
see that file's docstring history / `logbook/03c_multialgo_benchmark.md` Day 20 for why
the Robotiq 2f-85 asset was dropped (degenerate gripper body positions + missing finger
colliders, both traced to folding a closed 4-bar linkage into a foreign articulation).

Arm joints (6, UNCHANGED from the frozen env): shoulder_pan_joint, shoulder_lift_joint,
                elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint
Gripper joints (2, NEW): left_finger_joint, right_finger_joint — two independent
                prismatic joints, no linkage, no mimic constraint. Driven directly and
                symmetrically: same magnitude, opposite sign (see GRIPPER_OPEN_L/R,
                GRIPPER_CLOSE_L/R below and the env's `gripper_action` term).
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

# Local built USD (repo-relative so it works on any machine that has this repo).
_USD_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "ur5e_simple_gripper.usd")
)

# Each finger's own local frame shares the SAME "+X = base_link's +X" convention (see
# make_ur5e_simple_gripper_usd.py — no per-joint frame rotation). So "open" means:
#   left_finger_joint  -> +TRAVEL   (moves further in +X, away from center)
#   right_finger_joint -> -TRAVEL   (moves further in -X, away from center)
# and "closed" means both back at 0 (their rest position, 2*HALF_GAP apart — not touching;
# a real cube sits between them at that gap, which is the point).
#
# Day 21: these used to be defined here with a "must match TRAVEL in
# make_ur5e_simple_gripper_usd.py" comment — i.e. hand-kept in sync with the asset. They
# now come from robots/gripper_geometry.py, the single source of truth that the USD
# builder, the env cfg and the live demo all read. Re-exported under the same names so
# every existing import keeps working.
from ur5_grasp.robots.gripper_geometry import (  # noqa: E402
    GRIPPER_CLOSE_L,
    GRIPPER_CLOSE_R,
    GRIPPER_OPEN_L,
    GRIPPER_OPEN_R,
)

UR5E_SIMPLE_GRIPPER_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=_USD_PATH,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            max_depenetration_velocity=5.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=16,
            solver_velocity_iteration_count=1,
        ),
        activate_contact_sensors=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        # Ready pose reaching forward over the table (base at origin, table at x=0.5).
        # UNCHANGED from the frozen env — only the gripper joints below are new.
        joint_pos={
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.2,
            "elbow_joint": 1.4,
            "wrist_1_joint": -1.75,
            "wrist_2_joint": -1.57,
            "wrist_3_joint": 0.0,
            # gripper starts open
            "left_finger_joint": GRIPPER_OPEN_L,
            "right_finger_joint": GRIPPER_OPEN_R,
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
            # DO NOT LOWER. See ur5e_robotiq.py / logbook/03c — 1.0 rad/s erases the
            # Layer-1 safety signal (viol_singularity -> ~0 because a slow arm can't
            # reach ill-conditioned configurations, so lambda never activates).
            velocity_limit_sim=3.14,
            stiffness=800.0,
            damping=40.0,
            armature=0.01,
        ),
        # Both fingers driven directly — no passive/coupled joints needed. There is no
        # closed-loop linkage to fight, so straightforward PD gains should hold a light
        # cube without the instability the 2f-85's passive bodies risked.
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=["left_finger_joint", "right_finger_joint"],
            effort_limit_sim=50.0,
            velocity_limit_sim=2.0,
            stiffness=400.0,
            damping=20.0,
            armature=0.01,
            friction=0.1,
        ),
    },
)
"""UR5e arm with a simple two-finger prismatic gripper (single articulation, no linkage)."""
