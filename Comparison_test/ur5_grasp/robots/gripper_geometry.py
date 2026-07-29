# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""SINGLE SOURCE OF TRUTH for the simple two-finger gripper's geometry.

Before this file existed, the pad-plane distance `0.075` was written out by hand in three
separate places — `tools/make_ur5e_simple_gripper_usd.py` (which authors it),
`tasks/lift/ur5e_simple_gripper_env_cfg.py` (whose reward geometry depends on it) and
`scripts/simple_gripper_live_grasp_demo.py` (whose IK subtracts it) — each carrying a
comment begging whoever changed one to remember the other two. Day 21 changed the geometry
and that is exactly the moment that arrangement breaks. Everything is derived here now;
the other three files import.

--------------------------------------------------------------------------------------
FRAME CONVENTION
--------------------------------------------------------------------------------------
Everything below is expressed in the GRIPPER's own frame, where:

    +Z  = the approach / tool direction (fingers point this way, cube is approached
          along it)
    +-X = the open/close direction (the two fingers separate along X)
     Y  = the free axis (finger width)

That frame is then rotated onto the arm by `MOUNT_QUAT` so the gripper's +Z lands on the
arm's REAL tool axis. Which local axis of `wrist_3_link` that is, is NOT assumed here — it
is read from `assets/wrist_frame.json`, written by `tools/check_wrist_frame.py`.

Day 21 background: the previous build hardcoded the mount along wrist_3_link's local +Z and
the gripper came out 90 degrees off, sticking out of the side of the wrist. The +Z figure was
inherited from the frozen weld env's `OffsetCfg(pos=[0, 0, 0.16])`, which is commented
"approx, tune" and was never validated — a weld env teleports the cube to whatever point the
TCP names, so a TCP pointing out of the side of the wrist trains to 100% success just as
happily as a correct one. Hence: measure it, don't inherit it.

--------------------------------------------------------------------------------------
GEOMETRY ALONG +Z (all distances from wrist_3_link's origin, in metres)
--------------------------------------------------------------------------------------

    0.000  wrist_3_link origin / flange
    |
    |  <-- BASE_THICK: mounting plate, sits FLUSH on the flange
    |
    0.030  plate front face, fingers start here
    |
    |  <-- FINGER_LEN
    |
    0.075  TCP  (= TIP_Z - GRASP_INSET)  <-- cube centre sits HERE, between the fingers
    |
    0.100  finger tips (TIP_Z)

The second Day-21 complaint was "the grasp should be between the tips of the gripper." The
old build could not do that: its "Fix, round 2" workaround pushed the ENTIRE 0.075 m reach
into the fixed mount joint and set `FINGER_Z_OFFSET = 0.0`, which left the finger boxes
centred on the plate — spanning 0.045..0.105 while the plate spanned 0.060..0.090. The
fingers were buried in their own mounting plate, half of each sticking out BACKWARDS toward
the wrist, and the TCP sat at 0.075 = the finger MIDPOINT, level with the plate. So the cube
was being pinched at the middle of the fingers, inside the plate.

That workaround existed for a real reason: PhysX resolves an off-axis (Y/Z) anchor offset on
a `PrismaticJoint` differently from the identical offset on a `FixedJoint` (Day 20 measured
0.031 m where 0.075 m was authored). The fix here does NOT reintroduce that offset. Instead
each finger is authored as a rigid-body Xform whose ORIGIN sits at the joint anchor (zero Z
offset in the prismatic joint, so the buggy path is never taken) with its collision box as a
CHILD prim translated forward by `FINGER_GEOM_OFFSET_Z`. A collider offset inside a rigid
body is ordinary USD — it is how essentially every robot link is authored — and it goes
nowhere near the joint solver. This is the "joint-anchor + offset-visual-child split" the old
builder's docstring flagged as deferred.

`TCP_Z` lands on 0.075 again, the same number as before, but now for a reason instead of by
accident: it is derived as `TIP_Z - GRASP_INSET`, i.e. a fixed inset back from the finger
tips. Change `FINGER_LEN` or `BASE_THICK` and the TCP follows automatically.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

# --------------------------------------------------------------------------------------
# Measured input: which local axis of wrist_3_link the flange actually faces along.
# --------------------------------------------------------------------------------------
_WRIST_FRAME_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "wrist_frame.json")
)

_MISSING_MSG = f"""
Missing measured wrist frame: {_WRIST_FRAME_JSON}

The gripper mount direction is MEASURED, not assumed (see this module's docstring — the
old hardcoded +Z is what produced the sideways gripper). Run the measurement once on the
lab PC before anything that imports this module:

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_wrist_frame.py --headless

That writes the JSON this module reads. It only needs re-running if the source arm asset
changes.

HEADS UP on the blast radius: this failure blocks EVERY task import in the package, including
the frozen weld env `Isaac-Lift-Cube-UR5e-v0`, because `tasks/lift/__init__.py` registers the
SimpleGripper cfg alongside it. That is deliberate — a silent fallback to a guessed axis is
what produced the sideways gripper in the first place — but if `train.py` or `play.py` dies on
this and the gripper is not what you were working on, the one command above is the whole fix.
""".strip()


def _load_tool_axis() -> np.ndarray:
    if not os.path.exists(_WRIST_FRAME_JSON):
        raise FileNotFoundError(_MISSING_MSG)
    with open(_WRIST_FRAME_JSON) as fh:
        data = json.load(fh)
    axis = np.asarray(data["tool_axis_wrist3_link"], dtype=float)
    norm = float(np.linalg.norm(axis))
    if not math.isclose(norm, 1.0, abs_tol=1e-6):
        raise ValueError(
            f"{_WRIST_FRAME_JSON} holds a non-unit tool axis {axis.tolist()} (|a| = {norm}). "
            "Re-run tools/check_wrist_frame.py."
        )
    return axis


#: Unit vector, in `wrist_3_link`'s local frame, pointing OUT of the flange. Measured.
TOOL_AXIS: np.ndarray = _load_tool_axis()

# --------------------------------------------------------------------------------------
# Authored geometry (the numbers a human tunes)
# --------------------------------------------------------------------------------------

#: Mounting plate, x/y/z in the gripper frame. Z is its thickness along the tool axis.
BASE_SIZE = (0.06, 0.08, 0.03)
BASE_THICK = BASE_SIZE[2]

#: One finger box, x/y/z in the gripper frame. Z is the finger LENGTH along the tool axis.
#: 0.07 m is long enough to reach past the centre of the 0.8-scaled DexCube so the pads
#: bracket it rather than clipping a corner.
FINGER_SIZE = (0.015, 0.02, 0.07)
FINGER_LEN = FINGER_SIZE[2]

#: Half the rest separation between the two finger centres, along the gripper's X.
HALF_GAP = 0.015

#: Each finger's prismatic travel from its rest (closed) position, outward along +-X.
TRAVEL = 0.035

#: How far back from the finger TIPS the grasp point sits. The cube's centre is placed
#: here, so the tips reach past it and the pads contact flat faces rather than a corner.
GRASP_INSET = 0.025

#: Roll of the gripper about the tool axis, degrees. `MOUNT_QUAT` uses the shortest-arc
#: rotation from the gripper's +Z onto TOOL_AXIS, which fixes the APPROACH direction but
#: leaves the roll arbitrary — i.e. which way round the fingers open. Set this from the
#: GUI: run the live demo, look down the tool axis, and if the fingers close diagonally
#: across the cube's faces instead of squarely onto two opposite faces, put the correction
#: here (90 is the usual answer) and rebuild the USD. Nothing else needs to change.
MOUNT_ROLL_DEG = 0.0

#: Per-finger mass (kg), plate mass (kg), and pad friction (static == dynamic).
FINGER_MASS = 0.03
BASE_MASS = 0.05
FRICTION = 1.0

# --------------------------------------------------------------------------------------
# Derived geometry — do not hand-edit; change the authored values above instead.
# --------------------------------------------------------------------------------------

#: Plate centre along +Z. Half its thickness => the plate's back face sits FLUSH on the
#: flange, with no floating gap (the old build put this at 0.075 and the plate hung in
#: mid-air 7.5 cm off the wrist).
MOUNT_CENTER_Z = BASE_THICK / 2.0

#: Finger box centre along +Z: starts at the plate's front face, extends forward.
FINGER_CENTER_Z = BASE_THICK + FINGER_LEN / 2.0

#: Finger tip plane along +Z.
TIP_Z = BASE_THICK + FINGER_LEN

#: THE GRASP POINT — the TCP, between the finger tips. Everything downstream (the env's
#: `ee_frame` offset, the demo's IK tool offset) uses this.
TCP_Z = TIP_Z - GRASP_INSET

#: Offset of a finger's collision/visual box from its own rigid-body origin, along +Z.
#: The body origin sits at the prismatic joint's anchor (same Z as the plate centre), so
#: the joint itself carries NO off-axis offset — see the docstring for why that matters.
FINGER_GEOM_OFFSET_Z = FINGER_CENTER_Z - MOUNT_CENTER_Z

#: Binary gripper action targets. Both fingers are driven directly and symmetrically:
#: same magnitude, opposite sign. "Closed" is 0 on both, i.e. the rest separation
#: (2 * HALF_GAP = 30 mm) — a cube wider than that stalls the fingers, which is the
#: real-contact signature the Day-20 grasp test looks for.
GRIPPER_OPEN_L = +TRAVEL
GRIPPER_OPEN_R = -TRAVEL
GRIPPER_CLOSE_L = 0.0
GRIPPER_CLOSE_R = 0.0


# --------------------------------------------------------------------------------------
# Mount rotation: gripper frame -> wrist_3_link frame
# --------------------------------------------------------------------------------------
def _quat_mul(a, b):
    """Hamilton product, both (w, x, y, z)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return np.array([
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ])


def _shortest_arc(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Unit quaternion (w, x, y, z) rotating unit vector `a` onto unit vector `b` by the
    shortest path. Handles the antiparallel case explicitly (where the shortest arc is
    undefined and the naive formula divides by zero)."""
    d = float(np.dot(a, b))
    if d > 1.0 - 1e-9:
        return np.array([1.0, 0.0, 0.0, 0.0])
    if d < -1.0 + 1e-9:
        # 180 degrees about any axis perpendicular to `a`.
        perp = np.cross(a, np.array([1.0, 0.0, 0.0]))
        if np.linalg.norm(perp) < 1e-6:
            perp = np.cross(a, np.array([0.0, 1.0, 0.0]))
        perp = perp / np.linalg.norm(perp)
        return np.array([0.0, *perp])
    v = np.cross(a, b)
    q = np.array([1.0 + d, v[0], v[1], v[2]])
    return q / np.linalg.norm(q)


def _axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    h = angle_rad / 2.0
    s = math.sin(h)
    return np.array([math.cos(h), axis[0] * s, axis[1] * s, axis[2] * s])


_GRIPPER_FORWARD = np.array([0.0, 0.0, 1.0])

#: Rotation taking the gripper's own frame into `wrist_3_link`'s frame, (w, x, y, z).
#: Applied as the fixed mount joint's `localRot0`, and as the `ee_frame` offset rotation so
#: the TCP marker's +Z is the true approach direction (which is what the demo's IK assumes
#: when it subtracts the tool offset).
MOUNT_QUAT: np.ndarray = _quat_mul(
    _axis_angle(TOOL_AXIS, math.radians(MOUNT_ROLL_DEG)),
    _shortest_arc(_GRIPPER_FORWARD, TOOL_AXIS),
)
MOUNT_QUAT = MOUNT_QUAT / np.linalg.norm(MOUNT_QUAT)

#: Mount-joint translation in `wrist_3_link`'s frame: plate centre, along the measured axis.
MOUNT_POS = tuple(float(v) for v in (MOUNT_CENTER_Z * TOOL_AXIS))

#: TCP offset from `wrist_3_link`, in `wrist_3_link`'s frame — feeds `OffsetCfg`.
TCP_OFFSET_POS = tuple(float(v) for v in (TCP_Z * TOOL_AXIS))
TCP_OFFSET_ROT = tuple(float(v) for v in MOUNT_QUAT)


def summary() -> str:
    """One-screen dump of the resolved geometry. Printed by the builder and the demo so
    every run's log records exactly which numbers it used."""
    ax = TOOL_AXIS.tolist()
    return "\n".join([
        "gripper geometry (all distances from wrist_3_link origin, metres):",
        f"    TOOL_AXIS (measured)   : {ax}",
        f"    MOUNT_ROLL_DEG         : {MOUNT_ROLL_DEG}",
        f"    MOUNT_QUAT (w,x,y,z)   : {[round(v, 6) for v in MOUNT_QUAT.tolist()]}",
        f"    plate  (BASE_THICK)    : 0.000 -> {BASE_THICK:.3f}  (centre {MOUNT_CENTER_Z:.3f}, flush on flange)",
        f"    fingers (FINGER_LEN)   : {BASE_THICK:.3f} -> {TIP_Z:.3f}  (centre {FINGER_CENTER_Z:.3f})",
        f"    TCP / grasp point      : {TCP_Z:.3f}  (= TIP_Z {TIP_Z:.3f} - GRASP_INSET {GRASP_INSET:.3f})",
        f"    finger geom offset     : {FINGER_GEOM_OFFSET_Z:.3f}  (inside the body, NOT in the joint)",
        f"    finger rest gap        : {2 * HALF_GAP:.3f}   travel each: {TRAVEL:.3f}",
        f"    TCP_OFFSET_POS (w3)    : {[round(v, 6) for v in TCP_OFFSET_POS]}",
    ])
