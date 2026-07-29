# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Build + validate a UR5e + SIMPLE two-finger prismatic gripper USD.

Why this exists (Day 20 decision): the stock Robotiq 2f-85 path
(`make_ur5e_robotiq_usd.py`) has TWO independent, confirmed problems, not one:
  1. Its gripper bodies report degenerate [0,0,0] local positions after the nested-
     articulation-root surgery (Day 18 `check_gripper_mount.py` diagnosis).
  2. Its finger/pad prims have no working collider at all — `check_gripper_colliders.py`
     showed mesh-only geometry with no `UsdPhysics.CollisionAPI`, which is why physics-only
     grasp tests showed the pads closing straight through the cube with no contact.
Both stem from the same root cause: the 2f-85 is a closed 4-bar linkage authored as its
OWN articulation, and folding a foreign closed-loop mechanism into the arm's articulation
is inherently fragile. Rebuilding the real 2f-85 asset would mean debugging both bugs in
someone else's USD. Instead: don't import a gripper at all. Select `Gripper=None` on the
stock ur5e.usd (confirmed available — see `ur5_grasp/CONTEXT.md`, "Variant sets on
ur5e.usd"), giving a clean arm-only articulation, then author two independent prismatic
finger joints ourselves, with colliders and friction WE control from the start.

Design (deliberately the simplest thing that can hold an object with real contact physics):
  - base_link  — small plate, fixed-jointed onto the arm's wrist_3_link (single articulation,
    no nested root to disable — nothing to fold, we never created a second root).
  - left_finger / right_finger — two identical boxes, each on its own INDEPENDENT prismatic
    joint along the gripper's local +-X, resting at +-HALF_GAP. No mimic joint, no 4-bar
    linkage: driven directly and symmetrically at the Python action-term level (RL side,
    see `robots/ur5e_simple_gripper.py`). This is the same "two independent prismatic
    joints, no linkage" pattern Isaac Lab's own Franka gripper uses, which is why it has
    never had this class of bug.
  - Both fingers get UsdPhysics.CollisionAPI + an explicit friction material (this is the
    part the stock asset was silently missing).

ALL geometry numbers live in `robots/gripper_geometry.py`, not here. That module is also
what the training env cfg and the live demo import, so the plate/finger/TCP distances can
no longer drift apart between the three files (they used to be hand-copied).

--- Fix, round 1 (2026-07-29) ---
First build produced a structurally correct single articulation (8 joints, 10 bodies) but
the fingers never moved under either the open or close command. Root cause:
`UsdPhysics.PrismaticJoint` only declares the joint's kinematics (axis, limits, body0/1) —
it does NOT give PhysX a drive to act on. The stock arm joints already carry
`UsdPhysics.DriveAPI` authored by NVIDIA (that's what `ImplicitActuatorCfg` writes its
stiffness/damping/target into at runtime); the two hand-built finger joints never had that
schema applied, so there was nothing for the actuator to drive. Fixed by explicitly
applying `UsdPhysics.DriveAPI.Apply(joint_prim, "linear")` to both finger joints below
(`add_linear_drive`), with placeholder gains that `ImplicitActuatorCfg` overwrites at spawn.

--- Fix, round 2 (2026-07-29) — SUPERSEDED, see round 3 ---
After the drive fix the fingers moved and genuinely stalled against a cube, but the
measured wrist_3 -> pad offset came out ~0.031 m against a designed ~0.075 m, even though
the raw USD held the intended `physics:localPos0` of `(0.015, 0, 0.045)`. The `FixedJoint`
mount, using the identical mechanism, measured correctly — so PhysX resolves a
`PrismaticJoint`'s off-axis (Y/Z) anchor component differently from a `FixedJoint`'s.
Round 2 routed around that by moving the ENTIRE forward reach into the fixed mount joint
and zeroing the finger joints' own Z offset. That restored the 0.075 m number but left the
finger boxes centred on the mounting plate — flagged at the time as "cosmetic". It was not
cosmetic: it put the grasp point at the middle of the fingers, level with the plate.

--- Fix, round 3 (2026-07-30) — orientation + grasp point ---
Two problems reported from the GUI, with two different causes:

  (a) THE GRIPPER STUCK OUT SIDEWAYS. It was mounted along `wrist_3_link`'s local +Z, a
      number inherited from the frozen weld env's `OffsetCfg(pos=[0, 0, 0.16])` — commented
      "approx, tune" and never once validated, because a weld env teleports the cube to
      whatever point the TCP names. A TCP pointing out of the side of the wrist welds the
      cube to a point in mid-air and still trains to 100% success, so that env could never
      have caught this. Fixed by MEASURING the tool axis instead of inheriting it:
      `tools/check_wrist_frame.py` identifies which local axis of `wrist_3_link` is the one
      `wrist_3_joint` rotates about (the tool axis, by definition) and which sign points out
      of the flange, writes `assets/wrist_frame.json`, and `robots/gripper_geometry.py`
      turns that into `MOUNT_QUAT`, authored here as the mount joint's `localRot0`. The
      gripper's own +Z is now rotated onto the real flange direction rather than assumed to
      be it.

  (b) THE CUBE WAS NOT GRASPED BETWEEN THE FINGER TIPS — see the round-2 note above. Fixed
      without reintroducing the PrismaticJoint anchor bug: each finger is now a rigid-body
      Xform whose ORIGIN sits exactly at its joint anchor (so the prismatic joint still
      carries zero off-axis offset — the buggy path is never taken) with its collision box
      as a CHILD prim translated forward by `FINGER_GEOM_OFFSET_Z`. A collider offset inside
      a rigid body is ordinary USD, the way nearly every robot link is authored, and it never
      reaches the joint solver. This is the "joint-anchor + offset-visual-child split" the
      round-2 note deferred. The plate now sits flush on the flange, the fingers project
      forward from its front face, and the TCP is derived as `TIP_Z - GRASP_INSET`.

Run on the lab PC (isaaclab env), headless. `check_wrist_frame.py` MUST have been run once
first — this script reads the JSON it writes and will refuse to build without it:

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/check_wrist_frame.py --headless
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/make_ur5e_simple_gripper_usd.py --headless

Output: ur5_grasp/assets/ur5e_simple_gripper.usd  +  tools/make_simple_gripper_report.txt

Read the printed report before doing anything else. It tells you:
  - the resolved geometry (measured tool axis, plate/finger/TCP distances),
  - whether the wrist_3_link mount prim was found (search-based, not hardcoded),
  - the final joint/body list Isaac Lab will see (6 arm joints + 2 finger joints = 8 DOF,
    10 bodies),
  - whether it validated as ONE articulation, and — new in round 3 — a POST-SPAWN
    MEASUREMENT of where `left_finger` actually ended up relative to `wrist_3_link`,
    compared against where the geometry says it should be. That check is what would have
    caught both the round-2 offset bug and the sideways mount immediately.
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Build + validate UR5e + simple gripper USD.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- after app is up -------------------------------------------------------------
import os
import sys

import torch

from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR
from isaaclab.utils.math import quat_apply, quat_apply_inverse

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

HERE = _HERE
ASSETS_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))
OUT_USD = os.path.join(ASSETS_DIR, "ur5e_simple_gripper.usd")
REPORT_PATH = os.path.join(HERE, "make_simple_gripper_report.txt")

# Geometry module import is guarded: it deliberately REFUSES to load without the measured
# assets/wrist_frame.json (see robots/gripper_geometry.py). Fail with that module's
# instructions and shut the app down cleanly, rather than dumping a bare traceback and
# leaving Isaac Sim running.
try:
    from ur5_grasp.robots import gripper_geometry as G  # noqa: E402
except FileNotFoundError as _exc:
    print(f"\n{_exc}\n", flush=True)
    simulation_app.close()
    sys.exit(1)

SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"
MOUNT_BODY_NAME = "wrist_3_link"  # confirmed arm body name, ur5_grasp/CONTEXT.md

# Placeholder drive gains — just need the DriveAPI to exist so PhysX exposes a
# drivable DOF; ImplicitActuatorCfg (robots/ur5e_simple_gripper.py) overwrites these
# with the real stiffness/damping/effort_limit_sim at spawn time.
DRIVE_STIFFNESS = 400.0
DRIVE_DAMPING = 20.0
DRIVE_MAX_FORCE = 50.0

_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def find_prim_by_name(stage: Usd.Stage, name: str):
    """Search the whole stage for a prim whose name matches exactly. Avoids hardcoding
    a guessed prim path — the arm's structure is trusted by name only (CONTEXT.md)."""
    return [prim for prim in stage.Traverse() if prim.GetName() == name]


def add_body(stage, path, size_xyz, geom_offset_z, mass_kg):
    """Author a rigid body as an Xform (the BODY frame / joint anchor) with its box
    geometry as a CHILD prim, optionally pushed forward along the body's +Z.

    This split is the round-3 fix. Putting the offset in the child geometry keeps the
    prismatic joint's anchor purely on its own free axis, so PhysX never has to resolve an
    off-axis anchor component on a prismatic joint — the case that silently produced a
    0.031 m reach where 0.075 m was authored (round 2). A collider offset inside a rigid
    body is completely ordinary USD and goes nowhere near the joint solver.

    Returns (body_prim, collision_prim).
    """
    body = UsdGeom.Xform.Define(stage, path).GetPrim()
    UsdPhysics.RigidBodyAPI.Apply(body)
    mass_api = UsdPhysics.MassAPI.Apply(body)
    mass_api.CreateMassAttr(float(mass_kg))

    cube = UsdGeom.Cube.Define(stage, f"{path}/collision")
    cube.CreateSizeAttr(1.0)  # unit cube spans -0.5..0.5; the scale op gives real dims
    xf = UsdGeom.Xformable(cube)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, float(geom_offset_z)))
    xf.AddScaleOp().Set(Gf.Vec3f(*size_xyz))

    collision = cube.GetPrim()
    UsdPhysics.CollisionAPI.Apply(collision)
    return body, collision


def add_friction_material(stage, path):
    mat = UsdShade.Material.Define(stage, path)
    mat_api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    mat_api.CreateStaticFrictionAttr(G.FRICTION)
    mat_api.CreateDynamicFrictionAttr(G.FRICTION)
    mat_api.CreateRestitutionAttr(0.0)
    return mat


def bind_material(prim, material):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, materialPurpose="physics")


def add_linear_drive(joint_prim, target_pos: float) -> None:
    """Apply a linear (prismatic) position drive to a joint prim. Without this, the
    joint has kinematics (axis/limits) but no motor — PhysX will never move it toward
    a commanded target, regardless of what any ImplicitActuatorCfg tries to write."""
    drive_api = UsdPhysics.DriveAPI.Apply(joint_prim, "linear")
    drive_api.CreateTypeAttr("force")
    drive_api.CreateStiffnessAttr(DRIVE_STIFFNESS)
    drive_api.CreateDampingAttr(DRIVE_DAMPING)
    drive_api.CreateMaxForceAttr(DRIVE_MAX_FORCE)
    drive_api.CreateTargetPositionAttr(float(target_pos))


def _gf_quat(q) -> Gf.Quatf:
    """numpy (w, x, y, z) -> Gf.Quatf."""
    w, x, y, z = (float(v) for v in q)
    return Gf.Quatf(w, Gf.Vec3f(x, y, z))


def build_usd() -> bool:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.exists(OUT_USD):
        os.remove(OUT_USD)

    stage = Usd.Stage.CreateNew(OUT_USD)
    robot = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    robot.GetReferences().AddReference(SRC_USD)
    stage.SetDefaultPrim(robot)

    # Arm only. Gripper=None avoids the nested-articulation-root problem entirely —
    # there is no gripper subtree to disable, because we never composed one in.
    vsets = robot.GetVariantSets()
    for name, sel in {"Physics": "PhysX", "Gripper": "None", "Sensor": "None"}.items():
        if name in vsets.GetNames():
            opts = vsets.GetVariantSet(name).GetVariantNames()
            if sel in opts:
                vsets.GetVariantSet(name).SetVariantSelection(sel)
                log(f"    variant {name} -> {sel}")
            else:
                log(f"    !! variant {name} has no '{sel}' option (available: {opts}); left unset")

    # Find the wrist mount point by name, not by a guessed path.
    matches = find_prim_by_name(stage, MOUNT_BODY_NAME)
    if not matches:
        log(f"    !! could not find a prim named '{MOUNT_BODY_NAME}' anywhere on the stage.")
        log("       Aborting build — dumping all prim paths under /Robot for debugging:")
        for prim in stage.Traverse():
            log(f"         {prim.GetPath()}")
        return False
    if len(matches) > 1:
        log(f"    !! found {len(matches)} prims named '{MOUNT_BODY_NAME}': "
            f"{[str(p.GetPath()) for p in matches]} — using the first. Verify this is correct.")
    wrist_path = matches[0].GetPath()
    log(f"    mount body found: {wrist_path}")

    grip_root = "/Robot/SimpleGripper"
    UsdGeom.Xform.Define(stage, grip_root)

    # --- mounting plate: body frame at the plate's centre, geometry centred on it ----
    base_path = f"{grip_root}/base_link"
    _, base_col = add_body(stage, base_path, G.BASE_SIZE, 0.0, G.BASE_MASS)

    # --- friction material, shared by both fingers ----------------------------------
    mat = add_friction_material(stage, f"{grip_root}/GripperFrictionMat")
    bind_material(base_col, mat)

    # --- fingers: body origin AT the joint anchor, box pushed forward as a child -----
    left_path = f"{grip_root}/left_finger"
    right_path = f"{grip_root}/right_finger"
    _, left_col = add_body(stage, left_path, G.FINGER_SIZE, G.FINGER_GEOM_OFFSET_Z, G.FINGER_MASS)
    _, right_col = add_body(stage, right_path, G.FINGER_SIZE, G.FINGER_GEOM_OFFSET_Z, G.FINGER_MASS)
    bind_material(left_col, mat)
    bind_material(right_col, mat)

    # --- fixed joint: base_link welded onto wrist_3_link -----------------------------
    # localPos0 places the plate centre half a plate-thickness out along the MEASURED tool
    # axis (flush on the flange). localRot0 rotates the gripper's own +Z onto that axis —
    # this is the round-3 orientation fix. Without it the gripper inherits wrist_3_link's
    # raw frame and points wherever that frame's +Z happens to go, which is sideways.
    mount_joint = UsdPhysics.FixedJoint.Define(stage, f"{grip_root}/mount_joint")
    mount_joint.CreateBody0Rel().SetTargets([wrist_path])
    mount_joint.CreateBody1Rel().SetTargets([base_path])
    mount_joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*G.MOUNT_POS))
    mount_joint.CreateLocalRot0Attr().Set(_gf_quat(G.MOUNT_QUAT))
    mount_joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    mount_joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, Gf.Vec3f(0.0, 0.0, 0.0)))

    # --- left finger prismatic joint: axis X, rest +HALF_GAP, opens toward +X ---------
    # NOTE the Z component of localPos0 is deliberately ZERO on both finger joints: the
    # forward reach lives in the fixed mount (proven correct) plus the fingers' own child
    # geometry offset, never in a prismatic joint's off-axis anchor. See round 2/3 above.
    left_joint = UsdPhysics.PrismaticJoint.Define(stage, f"{grip_root}/left_finger_joint")
    left_joint.CreateBody0Rel().SetTargets([base_path])
    left_joint.CreateBody1Rel().SetTargets([left_path])
    left_joint.CreateAxisAttr("X")
    left_joint.CreateLocalPos0Attr().Set(Gf.Vec3f(+G.HALF_GAP, 0.0, 0.0))
    left_joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    left_joint.CreateLowerLimitAttr(0.0)
    left_joint.CreateUpperLimitAttr(G.TRAVEL)
    add_linear_drive(left_joint.GetPrim(), target_pos=G.GRIPPER_OPEN_L)

    # --- right finger prismatic joint: SAME axis convention (local X of base_link),
    # rest -HALF_GAP, opens toward -X by taking a NEGATIVE joint value. No frame
    # trickery needed — the sign flip lives in the Python action term, not in USD.
    right_joint = UsdPhysics.PrismaticJoint.Define(stage, f"{grip_root}/right_finger_joint")
    right_joint.CreateBody0Rel().SetTargets([base_path])
    right_joint.CreateBody1Rel().SetTargets([right_path])
    right_joint.CreateAxisAttr("X")
    right_joint.CreateLocalPos0Attr().Set(Gf.Vec3f(-G.HALF_GAP, 0.0, 0.0))
    right_joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    right_joint.CreateLowerLimitAttr(-G.TRAVEL)
    right_joint.CreateUpperLimitAttr(0.0)
    add_linear_drive(right_joint.GetPrim(), target_pos=G.GRIPPER_OPEN_R)

    stage.GetRootLayer().Save()
    log(f"    wrote {OUT_USD}")
    return True


def validate_usd() -> None:
    """Spawn the built USD, confirm a single articulation, and MEASURE where the fingers
    actually ended up relative to wrist_3_link.

    The measurement is the point. Rounds 2 and 3 were both "the USD says X, PhysX resolved
    Y" bugs, and neither was visible in a joint/body name dump. Gravity is off so the arm
    holds its spawn pose exactly and nothing sags between spawn and read.
    """
    sim = sim_utils.SimulationContext(
        sim_utils.SimulationCfg(dt=0.01, device=args_cli.device, gravity=(0.0, 0.0, 0.0))
    )
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=OUT_USD),
            actuators={"all": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=None, damping=None)},
        )
    )
    sim.reset()

    # Park EVERY joint at zero and let the drives actually settle there before measuring.
    #
    # This is not cosmetic. First run of this check (Day 21) reported a 26.43 mm error and
    # cried "PhysX did not resolve the mount as authored" — which was WRONG, and the check's
    # fault, not the asset's. The finger joints' `UsdPhysics.DriveAPI` carries an OPEN target
    # (authored deliberately, so the asset spawns open), and `ImplicitActuatorCfg(stiffness=
    # None, damping=None)` inherits the USD gains rather than overriding them. So over those
    # first 5 steps the drives were actively hauling the fingers out toward +TRAVEL, and the
    # read caught them mid-travel at 0.0264 m of the 0.035 m stroke. The tell was in the
    # numbers all along: the error was ENTIRELY in X, the fingers' own free axis, while Z —
    # the mount offset, the thing being checked — was exact to five decimals.
    zeros = torch.zeros_like(robot.data.joint_pos)
    robot.write_joint_state_to_sim(zeros, torch.zeros_like(zeros))
    robot.set_joint_position_target(zeros)
    robot.write_data_to_sim()
    for _ in range(60):
        sim.step(render=False)
        robot.update(sim.get_physics_dt())

    log("    SUCCESS: loaded as a single articulation.")
    log(f"    num joints : {robot.num_joints}")
    log(f"    joint names: {list(robot.joint_names)}")
    log(f"    num bodies : {robot.num_bodies}")
    log(f"    body names : {list(robot.body_names)}")
    log("")
    log("    Expected: 8 joints (6 arm + left_finger_joint + right_finger_joint),")
    log("    10 bodies (7 arm + base_link + left_finger + right_finger). The fixed")
    log("    mount_joint has no DOF so it will not appear in joint_names.")
    log("    NOTE: the gripper plate is reported as 'base_link_0' — the arm already has a")
    log("    'base_link', so Isaac Lab de-duplicates the name. Cosmetic, but do not use")
    log("    body_names=['base_link'] anywhere expecting the gripper.")
    log("")

    # ---- post-spawn geometry check --------------------------------------------------
    names = list(robot.body_names)
    if MOUNT_BODY_NAME not in names or "left_finger" not in names:
        log("    !! cannot run the geometry check — expected bodies missing from body_names.")
        return
    i_w3 = names.index(MOUNT_BODY_NAME)
    i_lf = names.index("left_finger")

    w3_pos = robot.data.body_pos_w[0, i_w3]
    w3_quat = robot.data.body_quat_w[0, i_w3]
    lf_pos = robot.data.body_pos_w[0, i_lf]

    # left_finger's origin, expressed in wrist_3_link's own frame.
    measured = quat_apply_inverse(w3_quat, lf_pos - w3_pos)

    # Where the authored geometry says it should be: the mount translation, plus the
    # finger's offset along the gripper's X, rotated into wrist_3_link's frame.
    #
    # The X term uses the finger joint's ACTUAL position, read back from sim, not an assumed
    # 0. That makes this a check of the MOUNT TRANSFORM AND THE JOINT KINEMATICS — "given the
    # joint is here, is the body where the geometry says it should be" — instead of a check
    # that silently also assumes the drive has not moved. See the parking note above for the
    # false alarm that assumption produced on the first run.
    dev = robot.device
    jnames = list(robot.joint_names)
    lj = float(robot.data.joint_pos[0, jnames.index("left_finger_joint")])
    mount_pos = torch.tensor(G.MOUNT_POS, dtype=torch.float32, device=dev)
    mount_quat = torch.tensor([float(v) for v in G.MOUNT_QUAT], dtype=torch.float32, device=dev)
    finger_local = torch.tensor([G.HALF_GAP + lj, 0.0, 0.0], dtype=torch.float32, device=dev)
    expected = mount_pos + quat_apply(mount_quat, finger_local)

    err = float(torch.linalg.norm(measured - expected))
    log("--- 3. post-spawn geometry check (left_finger origin in wrist_3_link's frame) ---")
    log(f"    left_finger_joint at read time : {lj:+.5f} m (parked target 0.0; "
        f"open would be {G.TRAVEL:+.3f})")
    log(f"    expected : {[round(v, 5) for v in expected.tolist()]}")
    log(f"    measured : {[round(v, 5) for v in measured.tolist()]}")
    log(f"    error    : {err * 1000:.2f} mm")
    if err < 2e-3:
        log("    -> OK. The mount transform PhysX resolved matches what was authored.")
    else:
        log("    -> !! MISMATCH. PhysX did not resolve the mount the way it was authored.")
        log("       This is the same class of bug as round 2 (a joint anchor component being")
        log("       reinterpreted). Do NOT proceed to a grasp test — the TCP would be wrong.")
        log("       READ THE PER-AXIS ERROR BEFORE PANICKING: an error confined to X is about")
        log("       the FINGER JOINTS (X is their free axis); an error in Z is about the mount.")
        deltas = (measured - expected).tolist()
        log(f"       per-axis error (mm): x {deltas[0]*1000:+.2f}  y {deltas[1]*1000:+.2f}  "
            f"z {deltas[2]*1000:+.2f}")

    # Finger tip position, the number that actually answers "is the cube between the tips?"
    tip_local = torch.tensor([G.HALF_GAP, 0.0, G.FINGER_GEOM_OFFSET_Z + G.FINGER_LEN / 2.0],
                             dtype=torch.float32, device=dev)
    tip = mount_pos + quat_apply(mount_quat, tip_local)
    tcp = torch.tensor(G.TCP_OFFSET_POS, dtype=torch.float32, device=dev)
    log("")
    log(f"    finger tip (wrist_3 frame) : {[round(v, 5) for v in tip.tolist()]}")
    log(f"    TCP        (wrist_3 frame) : {[round(v, 5) for v in tcp.tolist()]}")
    log(f"    TCP sits {G.GRASP_INSET * 1000:.0f} mm back from the tips, between the fingers.")


def main() -> None:
    log("=" * 78)
    log("BUILD + VALIDATE  ur5e_simple_gripper.usd")
    log("=" * 78)
    log(f"source USD : {SRC_USD}")
    log(f"output USD : {OUT_USD}")
    log("")
    log("--- 0. Resolved geometry (robots/gripper_geometry.py) ---")
    log(G.summary())
    log("")
    log("--- 1. Authoring local USD (arm-only reference + custom finger joints) ---")
    if not build_usd():
        log("    build aborted; skipping validation.")
        return
    log("")
    log("--- 2. Validating single articulation ---")
    try:
        validate_usd()
    except Exception:  # noqa: BLE001
        import traceback

        log("    !! validation failed — traceback below:")
        log(traceback.format_exc())
    log("")
    log(f"[report saved to {REPORT_PATH}]")


if __name__ == "__main__":
    try:
        main()
    finally:
        _FH.close()
        simulation_app.close()
