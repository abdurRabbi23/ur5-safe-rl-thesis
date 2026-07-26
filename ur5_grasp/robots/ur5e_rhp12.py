# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""UR5e + ROBOTIS RH-P12-RN articulation config — the REAL-hardware gripper.

Points at `assets/ur5e_rhp12.usd`, built + verified by `tools/make_ur5e_rhp12_usd.py`
(report: `tools/make_rhp12_report.txt`, 2026-07-26). Loads as ONE articulation:
10 joints / 12 bodies.

WHY THIS EXISTS (vs `ur5e_robotiq.py`)
-------------------------------------
The Robotiq 2f-85 is a closed-loop 4-bar. PhysX articulations are trees, so the loop is
never closed: the pad-carrying joints stay passive (stiffness 0) and NO force reaches the
contact surfaces. That is why `grasp_hold_test.py` reported GRIP TOO WEAK at any clamp
force, and why Layer 1 falls back to a proximity weld.

The RH-P12-RN URDF is a pure TREE — 5 links, 4 revolute joints, no loop:

    rh_p12_rn_base
      |-- rh_p12_rn (+x, 0..1.1) --> r1 --|-- rh_r2 (-x, 0..1.0) --> r2
      |-- rh_l1     (-x, 0..1.1) --> l1 --|-- rh_l2 (+x, 0..1.0) --> l2

Every joint is directly drivable, so there is a real force path to the pads. No PhysX
mimic joints and no loop-closure joint are needed.

COUPLING
--------
The opposed axis signs mean all four joints take the SAME scalar target q and the pads
stay parallel through the stroke. r1/l1 allow 1.1 rad but r2/l2 only 1.0, so the usable
stroke is q in [0, 1.0]. Measured pad separation (body origins, from the build report):

    q      0.00    0.20    0.40    0.60    0.80    1.00
    gap    .1145   .1012   .0844   .0656   .0442   .0216   (m)

Subtract ~0.0078 m for the pad inner faces -> ~107 mm clear opening when open. The
DexCube is ~0.041 m, so the pads reach it at q ~ 0.78; commanding q = 1.0 leaves a
position error the drive converts into clamping force (capped by `effort_limit_sim`).
"""

import os

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

_USD_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "ur5e_rhp12.usd")
)

# All four gripper joints take this same scalar target.
GRIPPER_JOINT_NAMES = ["rh_p12_rn", "rh_r2", "rh_l1", "rh_l2"]
GRIPPER_OPEN = 0.0
GRIPPER_CLOSE = 1.0

# Distance from wrist_3_link origin to the grasp point, ALONG WRIST +Z.
#
# CALIBRATED EMPIRICALLY, not guessed — `scripts/rhp12_grasp_sweep.py`, 2026-07-26.
# The naive value is wrong twice over:
#   * the TCP is not a fixed point (fingers curl forward as they close, so the pad
#     midpoint travels 0.0767 m open -> 0.1049 m closed), and
#   * a static hold test alone is not enough. Offsets 0.100-0.120 all "HELD", but with
#     the pad faces stopped 14-22 mm WIDER than the 0.0412 m cube — the cube was wedged
#     on the curved proximal r1/l1 links, which survives a static test and fails under
#     the accelerations of a real lift.
# At 0.130 the pad faces close to 0.0415 m against a 0.0412 m cube (delta +0.3 mm):
# a true flat-pad parallel grip, q stalling at 0.875 and z_drop of only 2.9 mm.
TCP_OFFSET = 0.130

UR5E_RHP12_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=_USD_PATH,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            max_depenetration_velocity=5.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            # Only 4 finger bodies here (vs the 2f-85's 10), but they never need to
            # collide with each other and leaving this on costs contact pairs at 4096 envs.
            enabled_self_collisions=False,
            solver_position_iteration_count=16,
            solver_velocity_iteration_count=1,
        ),
        activate_contact_sensors=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        # Same ready pose as the Robotiq env so the two are directly comparable.
        joint_pos={
            "shoulder_pan_joint": 0.0,
            "shoulder_lift_joint": -1.2,
            "elbow_joint": 1.4,
            "wrist_1_joint": -1.75,
            "wrist_2_joint": -1.57,
            "wrist_3_joint": 0.0,
            # gripper starts open
            "rh_p12_rn": GRIPPER_OPEN,
            "rh_r2": GRIPPER_OPEN,
            "rh_l1": GRIPPER_OPEN,
            "rh_l2": GRIPPER_OPEN,
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
            armature=0.01,
        ),
        # Drive ALL FOUR gripper joints. This is the whole point of switching grippers:
        # with a tree there is no loop constraint to fight, so holding every joint at the
        # commanded target is correct rather than divergent.
        #
        # `effort_limit_sim` — not stiffness — sets the grip force. The finger lever is
        # ~0.05 m, so 5 Nm caps the pad force near 100 N. Raise it if the cube slips
        # under load; lower it if closing launches the cube.
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=GRIPPER_JOINT_NAMES,
            effort_limit_sim=5.0,
            velocity_limit_sim=6.5,
            stiffness=200.0,
            damping=10.0,
            armature=0.01,
            friction=0.1,
        ),
    },
)
"""UR5e arm with a ROBOTIS RH-P12-RN two-finger gripper (single articulation)."""
