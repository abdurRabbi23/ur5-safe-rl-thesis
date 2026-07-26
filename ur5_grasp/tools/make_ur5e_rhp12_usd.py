# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Build + validate a single-articulation UR5e + ROBOTIS RH-P12-RN USD.

WHY THIS EXISTS
---------------
The Layer 1 env grasps via a proximity WELD because the Robotiq 2f-85 is a closed-loop
4-bar linkage whose passive joints transmit no normal force to the pads in PhysX (see
`logbook/02_grasp_env.md`, Day-8 correction). The RH-P12-RN — the gripper actually
bolted to the real UR5e — does NOT have that problem: its URDF is a pure TREE
(5 links / 4 revolute joints, no loop), so every joint is directly drivable and force
reaches the contact pads. This script builds that robot.

Layer 1 files are untouched. This produces a NEW asset for a NEW env.

WHAT IT DOES
------------
  1. Converts `assets/rh_p12_rn/rh_p12_rn.urdf` -> `assets/rh_p12_rn.usd`
     (Isaac Lab UrdfConverter; convex-decomposition colliders so the pad faces are
     represented properly instead of being swallowed by a convex hull).
  2. Authors `assets/ur5e_rhp12.usd`: references the stock ur5e.usd with variant
     Gripper=None, references the converted gripper under it, DISABLES the gripper's
     nested articulation root, and adds a fixed mount joint wrist_3_link -> base.
     Same USD-surgery pattern as `make_ur5e_robotiq_usd.py`.
  3. Validates: spawns it, confirms ONE articulation, prints joint/body names, then
     sweeps the gripper open -> closed and MEASURES the pad separation each step.
     That sweep is the real acceptance test — if the pads converge, the kinematics and
     the drives are correct and a grasp can physically hold.

RUN (lab PC, isaaclab env, headless):

    cd ~/Abdur_Rabbi_THESIS/IsaacLab
    ./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_rhp12_usd.py --headless

Add `--mount_pos "0 0 0.005"` / `--mount_rpy "0 0 0.7854"` to nudge the flange mount
if the visual check shows the gripper clocked or sunk into the wrist.

Output: ur5_grasp/assets/ur5e_rhp12.usd  +  tools/make_rhp12_report.txt
"""

import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Build + validate UR5e + RH-P12-RN USD.")
parser.add_argument(
    "--mount_pos",
    type=str,
    default="0 0 0",
    help="gripper base position in wrist_3_link frame, 'x y z' metres (default: flange origin)",
)
parser.add_argument(
    "--mount_rpy",
    type=str,
    default="0 0 0",
    help="gripper base orientation in wrist_3_link frame, 'r p y' radians",
)
parser.add_argument("--skip_convert", action="store_true", help="reuse an existing rh_p12_rn.usd")
parser.add_argument(
    "--gripper_color",
    type=str,
    default="0.02 0.02 0.02",
    help="linear RGB for the gripper visual material, 'r g b' in 0..1 (default: near-black)",
)
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- after app is up -------------------------------------------------------------
import math
import os

import torch
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(HERE, "..", "assets"))
URDF_PATH = os.path.join(ASSETS_DIR, "rh_p12_rn", "rh_p12_rn.urdf")
GRIPPER_USD = os.path.join(ASSETS_DIR, "rh_p12_rn.usd")
OUT_USD = os.path.join(ASSETS_DIR, "ur5e_rhp12.usd")
REPORT_PATH = os.path.join(HERE, "make_rhp12_report.txt")

SRC_USD = f"{ISAAC_NUCLEUS_DIR}/Robots/UniversalRobots/ur5e/ur5e.usd"

# All four joints take the same scalar target (opposed axis signs keep the pads
# parallel). r1/l1 allow 1.1 rad, r2/l2 only 1.0 -> the common safe stroke is 0..1.0.
GRIPPER_JOINTS = ["rh_p12_rn", "rh_r2", "rh_l1", "rh_l2"]
Q_OPEN = 0.0
Q_CLOSE = 1.0

_FH = open(REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


def colour_gripper(stage: Usd.Stage, root: str, rgb: list[float]) -> tuple[int, list[str]]:
    """Force a flat colour onto every renderable prim under `root`.

    Purely cosmetic — the RH-P12-RN and the UR5e both import light grey, so in the GUI
    the hand disappears into the wrist and you cannot see whether the fingers are open
    or closed. Colouring the hand makes visual debugging of grasps possible.

    WHY THIS IS FIDDLIER THAN IT LOOKS (first attempt failed, gripper stayed white):
    binding a material on each MESH is not enough. USD resolves material bindings by
    strength, and a binding authored on an ANCESTOR prim with `strongerThanDescendants`
    beats every binding below it. The URDF importer does exactly that, so per-mesh
    bindings were being ignored. The fix is to
      1. strip every existing binding in the subtree, then
      2. bind our material ONCE at the subtree root with `strongerThanDescendants`,
      3. and also write `displayColor`, which covers the case where a mesh had no
         material at all and was falling back to the renderer default.

    Authored on the MERGED stage, which references the converted gripper, so all of this
    lands on the stronger layer. Mass, inertia, colliders and joints are untouched.
    """
    UsdGeom.Scope.Define(stage, "/Robot/Looks")
    mat = UsdShade.Material.Define(stage, "/Robot/Looks/GripperColour")
    shader = UsdShade.Shader.Define(stage, "/Robot/Looks/GripperColour/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.45)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    start = stage.GetPrimAtPath(root)
    displaced: list[str] = []
    n = 0

    # 1 + 3: clear competing bindings, and set displayColor on every renderable prim.
    for prim in Usd.PrimRange(start):
        if prim.HasAPI(UsdShade.MaterialBindingAPI):
            api = UsdShade.MaterialBindingAPI(prim)
            path = api.GetDirectBinding().GetMaterialPath()
            if path:
                displaced.append(f"{prim.GetPath()} was bound to {path}")
            api.UnbindAllBindings()
        if prim.IsA(UsdGeom.Gprim):
            UsdGeom.Gprim(prim).CreateDisplayColorAttr().Set([Gf.Vec3f(*rgb)])
            n += 1

    # 2: single authoritative binding at the top of the gripper subtree.
    UsdShade.MaterialBindingAPI.Apply(start).Bind(
        mat, bindingStrength=UsdShade.Tokens.strongerThanDescendants
    )
    return n, displaced


def find_prim_by_name(stage: Usd.Stage, root: str, name: str) -> Usd.Prim | None:
    """Depth-first search for a prim whose name matches exactly (paths vary by importer)."""
    start = stage.GetPrimAtPath(root)
    if not start or not start.IsValid():
        return None
    for prim in Usd.PrimRange(start):
        if prim.GetName() == name:
            return prim
    return None


# ---------------------------------------------------------------------------------
# 1. URDF -> USD
# ---------------------------------------------------------------------------------
def convert_gripper() -> None:
    cfg = UrdfConverterCfg(
        asset_path=URDF_PATH,
        usd_dir=ASSETS_DIR,
        usd_file_name="rh_p12_rn.usd",
        force_usd_conversion=True,
        # The base link mounts to the UR5e flange, so it must NOT be world-fixed.
        fix_base=False,
        root_link_name="rh_p12_rn_base",
        # Keep every link: there are no fixed joints to merge, and merging risks
        # renaming bodies the env cfg refers to.
        merge_fixed_joints=False,
        # Convex HULL would fill the gap between the two pad faces and make the fingers
        # behave like solid blocks. Decomposition keeps the gripping surfaces real.
        collider_type="convex_decomposition",
        # Fingers are close-packed and never need to collide with each other.
        self_collision=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(
            drive_type="force",
            target_type="position",
            gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=200.0, damping=20.0),
        ),
    )
    converter = UrdfConverter(cfg)
    log(f"    converted -> {converter.usd_path}")


# ---------------------------------------------------------------------------------
# 2. Author the merged USD
# ---------------------------------------------------------------------------------
def build_usd() -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.exists(OUT_USD):
        os.remove(OUT_USD)

    mount_pos = [float(v) for v in args_cli.mount_pos.split()]
    mount_rpy = [float(v) for v in args_cli.mount_rpy.split()]
    log(f"    mount pos={mount_pos}  rpy={mount_rpy} (in wrist_3_link frame)")

    stage = Usd.Stage.CreateNew(OUT_USD)
    robot = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    robot.GetReferences().AddReference(SRC_USD)
    stage.SetDefaultPrim(robot)

    # Bare arm: NO Robotiq. We bolt our own gripper on below.
    vsets = robot.GetVariantSets()
    for name, sel in {"Physics": "PhysX", "Gripper": "None", "Sensor": "None"}.items():
        if name in vsets.GetNames():
            vsets.GetVariantSet(name).SetVariantSelection(sel)
            log(f"    variant {name} -> {sel}")

    # Reference the converted gripper under the arm prim.
    grip_root = UsdGeom.Xform.Define(stage, "/Robot/RHP12").GetPrim()
    grip_root.GetReferences().AddReference(GRIPPER_USD)

    # One articulation only: strip the gripper's own articulation root so PhysX folds
    # its bodies into the arm across the fixed mount joint we add next.
    for prim in Usd.PrimRange(grip_root):
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
            PhysxSchema.PhysxArticulationAPI.Apply(prim).CreateArticulationEnabledAttr(False)
            log(f"    disabled nested articulation root at {prim.GetPath()}")

    wrist = find_prim_by_name(stage, "/Robot", "wrist_3_link")
    base = find_prim_by_name(stage, "/Robot/RHP12", "rh_p12_rn_base")
    if wrist is None or base is None:
        log(f"    !! mount failed — wrist_3_link={wrist}, rh_p12_rn_base={base}; aborting")
        return
    log(f"    wrist prim : {wrist.GetPath()}")
    log(f"    base  prim : {base.GetPath()}")

    joint = UsdPhysics.FixedJoint.Define(stage, "/Robot/rhp12_mount_joint")
    joint.CreateBody0Rel().SetTargets([wrist.GetPath()])
    joint.CreateBody1Rel().SetTargets([base.GetPath()])
    joint.CreateLocalPos0Attr().Set(Gf.Vec3f(*mount_pos))
    joint.CreateLocalPos1Attr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    r, p, y = mount_rpy
    q = (
        Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(y))
        * Gf.Rotation(Gf.Vec3d(0, 1, 0), math.degrees(p))
        * Gf.Rotation(Gf.Vec3d(1, 0, 0), math.degrees(r))
    ).GetQuat()
    joint.CreateLocalRot0Attr().Set(Gf.Quatf(q))
    joint.CreateLocalRot1Attr().Set(Gf.Quatf(1.0, 0.0, 0.0, 0.0))
    log("    added fixed joint /Robot/rhp12_mount_joint (wrist_3_link -> rh_p12_rn_base)")

    # Cosmetic: make the hand visually distinct from the grey UR5e.
    rgb = [float(v) for v in args_cli.gripper_color.split()]
    n, displaced = colour_gripper(stage, "/Robot/RHP12", rgb)
    log(f"    gripper colour rgb={rgb} -> displayColor on {n} renderable prims")
    log(f"    bound /Robot/Looks/GripperColour at /Robot/RHP12 (strongerThanDescendants)")
    if displaced:
        log(f"    removed {len(displaced)} competing material binding(s) from the subtree:")
        for d in displaced[:12]:
            log(f"      - {d}")
    else:
        log("    no pre-existing material bindings found in the subtree")
    if n == 0:
        log("    !! WARNING: zero renderable prims found under /Robot/RHP12 — the colour")
        log("       cannot apply. The traversal, not the material, is the problem.")

    stage.GetRootLayer().Save()
    log(f"    wrote {OUT_USD}")


# ---------------------------------------------------------------------------------
# 3. Validate + measure the stroke
# ---------------------------------------------------------------------------------
def validate_usd() -> None:
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args_cli.device))
    sim_utils.GroundPlaneCfg().func("/World/ground", sim_utils.GroundPlaneCfg())
    sim_utils.DomeLightCfg(intensity=2000.0).func("/World/Light", sim_utils.DomeLightCfg(intensity=2000.0))

    robot = Articulation(
        ArticulationCfg(
            prim_path="/World/Robot",
            spawn=sim_utils.UsdFileCfg(usd_path=OUT_USD),
            actuators={
                "all": ImplicitActuatorCfg(
                    joint_names_expr=[".*"], stiffness=400.0, damping=40.0, armature=0.01
                )
            },
        )
    )
    sim.reset()

    log("    SUCCESS: loaded as a single articulation.")
    log(f"    num joints : {robot.num_joints}")
    log(f"    joint names: {list(robot.joint_names)}")
    log(f"    num bodies : {robot.num_bodies}")
    log(f"    body names : {list(robot.body_names)}")

    missing = [j for j in GRIPPER_JOINTS if j not in robot.joint_names]
    if missing:
        log(f"    !! expected gripper joints missing: {missing} — stop here and fix the mount.")
        return

    # --- acceptance test: does the stroke actually close the pads? ------------------
    gid, _ = robot.find_joints(GRIPPER_JOINTS)
    r2 = robot.find_bodies("rh_p12_rn_r2")[0][0]
    l2 = robot.find_bodies("rh_p12_rn_l2")[0][0]
    wid = robot.find_bodies("wrist_3_link")[0][0]

    log("")
    log("    --- gripper stroke sweep (pad separation should shrink monotonically) ---")
    log("      q(rad)   pad_gap(m)   tcp_offset_from_wrist(m)")
    targets = robot.data.default_joint_pos.clone()
    for q in [Q_OPEN + i * (Q_CLOSE - Q_OPEN) / 10.0 for i in range(11)]:
        targets[:, gid] = q
        for _ in range(60):  # let the drives settle at this target
            robot.set_joint_position_target(targets)
            robot.write_data_to_sim()
            sim.step()
            robot.update(1.0 / 120.0)
        pr = robot.data.body_pos_w[0, r2]
        pl = robot.data.body_pos_w[0, l2]
        pw = robot.data.body_pos_w[0, wid]
        gap = torch.norm(pr - pl).item()
        mid = (pr + pl) / 2.0
        tcp = torch.norm(mid - pw).item()
        log(f"      {q:5.2f}    {gap:7.4f}      {tcp:7.4f}")

    log("")
    log("    READ THIS TABLE:")
    log("      * pad_gap at q=0.00 should be ~0.10 m (RH-P12-RN opens ~106 mm).")
    log("      * pad_gap should fall smoothly to near 0 at q=1.00. If it does NOT move,")
    log("        the drives are not reaching the joints. If it jumps or oscillates,")
    log("        lower the drive stiffness.")
    log("      * tcp_offset_from_wrist is the number to put in the env's ee_frame")
    log("        OffsetCfg (replaces the Robotiq's 0.16). Use the value at q=0.")


def main() -> None:
    log("=" * 74)
    log("BUILD + VALIDATE  ur5e_rhp12.usd   (UR5e + ROBOTIS RH-P12-RN)")
    log("=" * 74)
    log(f"urdf       : {URDF_PATH}")
    log(f"arm USD    : {SRC_USD}")
    log(f"output USD : {OUT_USD}")
    log("")
    log("--- 1. Converting URDF -> USD ---")
    if args_cli.skip_convert and os.path.exists(GRIPPER_USD):
        log(f"    skipped (reusing {GRIPPER_USD})")
    else:
        try:
            convert_gripper()
        except Exception:  # noqa: BLE001
            import traceback

            log("    !! conversion failed — traceback below:")
            log(traceback.format_exc())
    log("")
    log("--- 2. Authoring merged USD ---")
    build_usd()
    log("")
    log("--- 3. Validating + measuring stroke ---")
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
