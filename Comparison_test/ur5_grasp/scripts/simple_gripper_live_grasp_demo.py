# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Live, GUI, closed-loop pick-and-place demo for the simple two-finger gripper
(`robots/ur5e_simple_gripper.py`, built by `tools/make_ur5e_simple_gripper_usd.py`).

What this proves, visually, with your own eyes in the Isaac Sim viewport — NOT a
pinned/teleported cube like `simple_gripper_grasp_test.py` (that script exists to
isolate contact-vs-passthrough as a diagnostic; this one is the real thing):

  1. The arm reaches down to a cube resting on the table under its own IK-driven
     motion (no teleporting the arm or the cube).
  2. The two fingers physically close via their real PD drives (ImplicitActuatorCfg
     in `robots/ur5e_simple_gripper.py`) until they contact the cube and stall —
     you will SEE the fingers stop short of fully closed, same signature
     `simple_gripper_grasp_test.py` used to confirm real contact.
  3. The arm then lifts the cube into the air and holds it there for a few seconds
     purely by grip friction (no weld, no pin) — cube visibly leaves the table and
     stays up.
  4. It lowers, releases, retracts, and repeats — runs until YOU close the viewport
     window or Ctrl+C. No fixed episode count, no auto-reset.

Two things added specifically for this validation pass, neither touches physics:
  - The gripper (base_link, left_finger, right_finger) is painted black
    (UsdPreviewSurface, bound to the default/visual material purpose — the
    friction material stays bound separately to the "physics" purpose, so grip
    behavior is unaffected).
  - The TCP — the same grasp point used everywhere else in this project, imported from
    `robots/gripper_geometry.py` (`TCP_OFFSET_POS` / `TCP_OFFSET_ROT`: between the finger
    tips, on the MEASURED tool axis, with the frame's +Z along the real approach
    direction) — is marked live with an RGB axis-arrow marker
    (`isaaclab.markers.FRAME_MARKER_CFG`, the same marker IsaacLab's own
    `05_controllers/run_diff_ik.py` tutorial uses) that tracks the real TCP pose
    every physics step, so you can see exactly where the code thinks the grasp
    point is relative to where the fingers actually close on the cube.

Why this is a standalone InteractiveScene script and not the registered gym task
(`Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0`): that task's `episode_length_s = 5.0`
plus its `time_out` / `object_dropping` terminations (`lift_env_cfg.py`) would
auto-reset mid-demo — the opposite of "hold it in the air until I decide to quit."
This script drives the same robot/object/EE-frame configuration directly with
`sim.step()`, so nothing times out.

Run on the lab PC, WITH the GUI (do not pass --headless):

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/simple_gripper_live_grasp_demo.py

Optional flags:
    --num_envs N        spawn N side-by-side copies (default 1)
    --lift_height H      meters to lift above the grasp height (default 0.25)
    --device cpu|cuda    passed straight to AppLauncher / SimulationContext

Close the viewport window (or Ctrl+C in the terminal) to stop.
"""

import argparse
import os
import sys

from isaaclab.app import AppLauncher

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

parser = argparse.ArgumentParser(description="Live GUI grasp-and-lift demo for the simple gripper.")
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--lift_height", type=float, default=0.25, help="Meters to lift the cube above grasp height.")
parser.add_argument("--marker_scale", type=float, default=0.05,
                    help="Length (m) of the TCP axis arrows. Default 0.05 = 5 cm, deliberately "
                         "shorter than the gripper's own 0.10 m reach so the marker reads as a "
                         "frame ON the gripper rather than dominating the scene.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

if args_cli.headless:
    print("[WARN] --headless was passed, but the whole point of this script is to watch it in the "
          "GUI. Re-run without --headless to actually see the grasp.")

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# --- everything below needs the app running -----------------------------------------
import torch

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg, RigidObjectCfg
from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg
from isaaclab.managers import SceneEntityCfg
from isaaclab.markers import VisualizationMarkers
from isaaclab.markers.config import FRAME_MARKER_CFG
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sensors import FrameTransformerCfg
from isaaclab.sensors.frame_transformer.frame_transformer_cfg import OffsetCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import GroundPlaneCfg, UsdFileCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR
from isaaclab.utils.math import quat_apply, quat_inv, quat_mul, subtract_frame_transforms

from isaacsim.core.utils.stage import get_current_stage  # noqa: E402

from ur5_grasp.robots import gripper_geometry as G  # noqa: E402
from ur5_grasp.robots.ur5e_simple_gripper import (  # noqa: E402
    GRIPPER_CLOSE_L,
    GRIPPER_CLOSE_R,
    GRIPPER_OPEN_L,
    GRIPPER_OPEN_R,
    UR5E_SIMPLE_GRIPPER_CFG,
)

# Day 21: this used to be a hand-copied `_EE_OFFSET_Z = 0.075` with a comment asking whoever
# changed the asset to remember to change it here too. It now comes from
# robots/gripper_geometry.py, the single source of truth shared with the USD builder and the
# training env cfg. `_TCP_FORWARD` is the distance from wrist_3_link to the grasp point
# measured ALONG THE TCP FRAME'S OWN +Z, which the geometry module guarantees is the real
# approach direction — so `wrist_target_for_tcp` below can keep rotating a plain [0, 0, d]
# by the TCP quaternion, and it is now correct rather than accidentally correct.
_TCP_FORWARD = G.TCP_Z

ARM_JOINTS = [
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint", "wrist_2_joint", "wrist_3_joint",
]
GRIPPER_JOINTS = ["left_finger_joint", "right_finger_joint"]

# --- flushed report file, same pattern every tool/ script in this project uses ---------
# Day 21: the first attempt to capture this script's output with `| tee` produced a 162 KB
# log containing the entire Isaac Sim startup and NOT ONE line from this script. Cause:
# piping makes Python's stdout block-buffered instead of line-buffered, and Isaac's
# `simulation_app.close()` tears the process down without flushing it, so every print was
# lost. (Isaac's own startup logs survived because they are written from the C++ side.)
# stderr stays line-buffered, which is how we could tell there had been no traceback.
# A flushed file removes the whole class of problem and lets the report be read back
# afterwards instead of scrolled past in a terminal.
_REPORT_PATH = os.path.normpath(os.path.join(_HERE, "..", "tools", "demo_run_report.txt"))
_FH = open(_REPORT_PATH, "w")


def log(msg: str = "") -> None:
    print(msg, flush=True)
    _FH.write(msg + "\n")
    _FH.flush()


# ----------------------------------------------------------------------------------
# Scene: same robot / object / table / ee_frame as ur5e_simple_gripper_env_cfg.py,
# built directly (no gym wrapper, no episode timeout) so we can run indefinitely.
# ----------------------------------------------------------------------------------

# Marker cfg for the TCP tracker. MUST live at module level, NOT inside the configclass
# body below.
#
# Day 21: this is what actually stopped the demo from ever running — including on Day 20,
# where it was written this way and the failure was never seen because the run was never
# reported back. `InteractiveScene._add_entities_from_cfg()` walks EVERY field of the scene
# cfg and dispatches on its type, with a final `else: raise ValueError("Unknown asset config
# type")`. It does not skip underscore-prefixed names. So a `_marker_cfg` declared in the
# class body is not a private helper — it is a scene entity as far as InteractiveScene is
# concerned, and a `VisualizationMarkersCfg` is not a spawnable asset type, so scene
# construction died before a single frame rendered.
#
# The training env cfg gets away with the identical three lines because it builds its marker
# inside `__post_init__`, where it is an ordinary local variable rather than a class field.
_S = args_cli.marker_scale
_TCP_MARKER_CFG = FRAME_MARKER_CFG.copy()
_TCP_MARKER_CFG.markers["frame"].scale = (_S, _S, _S)
_TCP_MARKER_CFG.prim_path = "/Visuals/TCPFrame"
# The connecting line is a 1 m cylinder that FrameTransformer stretches from the source frame
# to each target. It is unscaled by the above (different marker key) and, in a scene this
# size, reads as a yellow beam across the whole viewport. Thin it right down; with
# ee_frame.debug_vis off (below) it should not draw at all, but leave it correct in case
# debug_vis is ever turned back on.
_TCP_MARKER_CFG.markers["connecting_line"].radius = 0.0005


@configclass
class GraspDemoSceneCfg(InteractiveSceneCfg):
    plane = AssetBaseCfg(
        prim_path="/World/GroundPlane",
        init_state=AssetBaseCfg.InitialStateCfg(pos=[0, 0, -1.05]),
        spawn=GroundPlaneCfg(),
    )
    light = AssetBaseCfg(
        prim_path="/World/light",
        spawn=sim_utils.DomeLightCfg(color=(0.75, 0.75, 0.75), intensity=3000.0),
    )
    table = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        init_state=AssetBaseCfg.InitialStateCfg(pos=[0.5, 0, 0], rot=[0.707, 0, 0, 0.707]),
        spawn=UsdFileCfg(usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Mounts/SeattleLabTable/table_instanceable.usd"),
    )
    robot = UR5E_SIMPLE_GRIPPER_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
    object = RigidObjectCfg(
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
    # Real TCP tracker — same offset used by the training env cfg. Note the marker cfg is
    # referenced from module level; declaring it here would make it a scene entity (see the
    # note above _TCP_MARKER_CFG).
    ee_frame = FrameTransformerCfg(
        prim_path="{ENV_REGEX_NS}/Robot/base_link",
        # debug_vis OFF on purpose. FrameTransformer's own debug draw puts a frame marker at
        # the SOURCE (the arm's base_link) as well as at each target, plus a yellow line
        # joining them — so with it on, the viewport showed a second, differently-scaled axis
        # triad sitting out in space near the robot base and a beam running across the scene,
        # neither of which is the grasp point. The live `tcp_marker` in run_demo() is the one
        # that tracks the TCP, and it is now the only frame drawn.
        debug_vis=False,
        visualizer_cfg=_TCP_MARKER_CFG,
        target_frames=[
            FrameTransformerCfg.FrameCfg(
                prim_path="{ENV_REGEX_NS}/Robot/wrist_3_link",
                name="tcp",
                # Same offset the training env uses — position AND rotation, so the marker's
                # +Z arrow points along the real approach direction.
                offset=OffsetCfg(pos=G.TCP_OFFSET_POS, rot=G.TCP_OFFSET_ROT),
            ),
        ],
    )


# ----------------------------------------------------------------------------------
# Visual only: paint the gripper black. Physics/friction material (bound separately
# to the "physics" material purpose in make_ur5e_simple_gripper_usd.py) is untouched.
# ----------------------------------------------------------------------------------
def paint_gripper_black(stage) -> int:
    mat_path = "/World/Looks/GripperBlack"
    mat = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, mat_path + "/PBRShader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.02, 0.02, 0.02))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.15)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    # Day 21: the gripper links are now rigid-body Xforms with their box geometry on a
    # CHILD `collision` prim (see tools/make_ur5e_simple_gripper_usd.py, "Fix, round 3"),
    # so the link prim itself is no longer a Gprim. Bind the material on the link (USD
    # material bindings inherit down to descendant gprims) and set displayColor on
    # whichever descendants are actually geometry.
    painted = 0
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        if "/SimpleGripper/" in path and prim.GetName() in ("base_link", "left_finger", "right_finger"):
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)
            for gprim in [prim, *Usd.PrimRange(prim)]:
                if gprim.IsA(UsdGeom.Gprim):
                    UsdGeom.Gprim(gprim).CreateDisplayColorAttr([Gf.Vec3f(0.02, 0.02, 0.02)])
            painted += 1
    return painted


# ----------------------------------------------------------------------------------
# State machine: HOME -> DESCEND -> CLOSE -> LIFT -> HOLD -> LOWER -> OPEN -> RETRACT
# -> PAUSE -> back to DESCEND. Runs forever (until the viewport is closed).
# ----------------------------------------------------------------------------------
STEPS = dict(SETTLE=100, DESCEND=200, CLOSE=150, LIFT=200, HOLD=300, LOWER=200, OPEN=100, RETRACT=200, PAUSE=100)


def run_demo(sim: sim_utils.SimulationContext, scene: InteractiveScene, lift_height: float) -> None:
    robot = scene["robot"]
    obj = scene["object"]
    ee_frame = scene["ee_frame"]
    device = scene.device
    N = scene.num_envs

    arm_cfg = SceneEntityCfg("robot", joint_names=ARM_JOINTS, body_names=["wrist_3_link"])
    arm_cfg.resolve(scene)
    grip_cfg = SceneEntityCfg("robot", joint_names=GRIPPER_JOINTS)
    grip_cfg.resolve(scene)
    ee_jacobi_idx = arm_cfg.body_ids[0] - 1 if robot.is_fixed_base else arm_cfg.body_ids[0]

    ik_cfg = DifferentialIKControllerCfg(command_type="pose", use_relative_mode=False, ik_method="dls")
    ik = DifferentialIKController(ik_cfg, num_envs=N, device=device)
    ik_command = torch.zeros(N, ik.action_dim, device=device)

    # THE marker — the only frame drawn in the scene. Note it uses _TCP_MARKER_CFG, i.e. the
    # SAME scale as everything else here. It previously used a bare `FRAME_MARKER_CFG.copy()`,
    # which carries IsaacLab's default 0.5 m axes: half-metre arrows on a 0.10 m gripper, which
    # is what filled the viewport.
    tcp_marker = VisualizationMarkers(_TCP_MARKER_CFG.copy().replace(prim_path="/Visuals/tcp_live"))

    gripper_target = torch.zeros(N, 2, device=device)

    def set_gripper(open_: bool) -> None:
        if open_:
            gripper_target[:, 0] = GRIPPER_OPEN_L
            gripper_target[:, 1] = GRIPPER_OPEN_R
        else:
            gripper_target[:, 0] = GRIPPER_CLOSE_L
            gripper_target[:, 1] = GRIPPER_CLOSE_R

    # Inverse of the gripper->wrist mount rotation, needed to turn a desired TCP
    # ORIENTATION back into the wrist orientation the IK actually drives.
    mount_quat_inv = quat_inv(
        torch.tensor([float(v) for v in G.MOUNT_QUAT], device=device).unsqueeze(0)
    ).expand(N, 4)

    def wrist_target_for_tcp(tcp_pos_w: torch.Tensor, tcp_quat_w: torch.Tensor):
        """Convert a desired world-frame TCP pose into the wrist_3_link pose (in the
        robot base frame) that the IK controller actually drives.

        Two corrections, not one:
          - POSITION: subtract the tool offset. `_TCP_FORWARD` is measured along the TCP
            frame's own +Z, which gripper_geometry guarantees is the true approach
            direction, so rotating [0, 0, d] by the TCP quaternion gives the right vector
            in world frame.
          - ORIENTATION: the TCP frame is no longer parallel to wrist_3_link. Day 21 gave
            the `ee_frame` offset a rotation (`TCP_OFFSET_ROT`) so the TCP's +Z lies on the
            arm's real tool axis, and FrameTransformer applies it as
            `tcp_quat = wrist_quat (x) MOUNT_QUAT`. Feeding `tcp_quat` straight to the IK —
            which is what this function used to do, correctly, back when the offset was
            pure translation — would now command the WRIST to take the GRIPPER's
            orientation, i.e. ask the arm to rotate by the mount transform. Undo it.
        """
        offset_w = quat_apply(tcp_quat_w, torch.tensor([0.0, 0.0, _TCP_FORWARD], device=device).expand(N, 3))
        wrist_pos_w = tcp_pos_w - offset_w
        wrist_quat_w = quat_mul(tcp_quat_w, mount_quat_inv)
        root_pose_w = robot.data.root_pose_w
        pos_b, quat_b = subtract_frame_transforms(
            root_pose_w[:, 0:3], root_pose_w[:, 3:7], wrist_pos_w, wrist_quat_w
        )
        return pos_b, quat_b

    def set_ik_goal(pos_b: torch.Tensor, quat_b: torch.Tensor) -> None:
        ik_command[:, 0:3] = pos_b
        ik_command[:, 3:7] = quat_b
        ik.reset()
        ik.set_command(ik_command)

    def step_ik_and_apply() -> None:
        jacobian = robot.root_physx_view.get_jacobians()[:, ee_jacobi_idx, :, arm_cfg.joint_ids]
        ee_pose_w = robot.data.body_pose_w[:, arm_cfg.body_ids[0]]
        root_pose_w = robot.data.root_pose_w
        joint_pos = robot.data.joint_pos[:, arm_cfg.joint_ids]
        ee_pos_b, ee_quat_b = subtract_frame_transforms(
            root_pose_w[:, 0:3], root_pose_w[:, 3:7], ee_pose_w[:, 0:3], ee_pose_w[:, 3:7]
        )
        joint_pos_des = ik.compute(ee_pos_b, ee_quat_b, jacobian, joint_pos)
        robot.set_joint_position_target(joint_pos_des, joint_ids=arm_cfg.joint_ids)

    def do_step(phase: str) -> None:
        step_ik_and_apply()
        robot.set_joint_position_target(gripper_target, joint_ids=grip_cfg.joint_ids)
        scene.write_data_to_sim()
        sim.step()
        scene.update(sim.get_physics_dt())
        tcp_pos = ee_frame.data.target_pos_w[:, 0]
        tcp_quat = ee_frame.data.target_quat_w[:, 0]
        tcp_marker.visualize(tcp_pos, tcp_quat)
        return tcp_pos, tcp_quat

    # ---- settle ------------------------------------------------------------------
    default_joint_pos = robot.data.default_joint_pos.clone()
    for _ in range(STEPS["SETTLE"]):
        if not simulation_app.is_running():
            return
        robot.set_joint_position_target(default_joint_pos[:, arm_cfg.joint_ids], joint_ids=arm_cfg.joint_ids)
        robot.set_joint_position_target(default_joint_pos[:, grip_cfg.joint_ids], joint_ids=grip_cfg.joint_ids)
        scene.write_data_to_sim()
        sim.step()
        scene.update(sim.get_physics_dt())
        tcp_marker.visualize(ee_frame.data.target_pos_w[:, 0], ee_frame.data.target_quat_w[:, 0])

    home_tcp_pos = ee_frame.data.target_pos_w[:, 0].clone()
    home_tcp_quat = ee_frame.data.target_quat_w[:, 0].clone()
    hover_z = home_tcp_pos[:, 2].clone()
    log(f"[demo] home TCP (pad midpoint) world pos: {home_tcp_pos[0].tolist()}  "
          f"quat(wxyz): {home_tcp_quat[0].tolist()}")

    cycle = 0
    while simulation_app.is_running():
        cycle += 1
        cube_pos = obj.data.root_pos_w.clone()
        grasp_pos = torch.stack([cube_pos[:, 0], cube_pos[:, 1], cube_pos[:, 2]], dim=1)
        lift_pos = grasp_pos.clone()
        lift_pos[:, 2] += lift_height
        retract_pos = torch.stack([cube_pos[:, 0], cube_pos[:, 1], hover_z], dim=1)

        log(f"\n[demo] === cycle {cycle} === cube at "
              f"({cube_pos[0,0]:.3f}, {cube_pos[0,1]:.3f}, {cube_pos[0,2]:.3f})")

        set_gripper(open_=True)

        # DESCEND onto the cube
        pos_b, quat_b = wrist_target_for_tcp(grasp_pos, home_tcp_quat)
        set_ik_goal(pos_b, quat_b)
        for i in range(STEPS["DESCEND"]):
            if not simulation_app.is_running():
                return
            do_step("DESCEND")

        # CLOSE the fingers for real (PD drive, real contact) — arm holds position
        log("[demo] closing fingers...")
        set_gripper(open_=False)
        for i in range(STEPS["CLOSE"]):
            if not simulation_app.is_running():
                return
            do_step("CLOSE")
            if i % 30 == 0:
                lj = robot.data.joint_pos[0, grip_cfg.joint_ids[0]].item()
                rj = robot.data.joint_pos[0, grip_cfg.joint_ids[1]].item()
                log(f"    close step {i:3d}  left={lj:+.4f} right={rj:+.4f} "
                      f"(both ~0.0350/-0.0350 = fully open/no contact; "
                      f"stalled well short = real contact on the cube)")

        # LIFT the cube into the air
        log("[demo] lifting...")
        pos_b, quat_b = wrist_target_for_tcp(lift_pos, home_tcp_quat)
        set_ik_goal(pos_b, quat_b)
        for i in range(STEPS["LIFT"]):
            if not simulation_app.is_running():
                return
            do_step("LIFT")

        # HOLD in the air — the actual validation moment
        cz0 = obj.data.root_pos_w[0, 2].item()
        for i in range(STEPS["HOLD"]):
            if not simulation_app.is_running():
                return
            do_step("HOLD")
            if i % 50 == 0:
                cz = obj.data.root_pos_w[0, 2].item()
                held = "HELD" if (cz > grasp_pos[0, 2].item() - 0.05) else "DROPPED"
                log(f"    hold step {i:3d}  cube z={cz:+.3f} (table z~{grasp_pos[0,2].item():+.3f}) -> {held}")
        cz1 = obj.data.root_pos_w[0, 2].item()
        result = "GRIP HOLDS -- cube lifted and held in the air" if cz1 > cz0 - 0.05 else "grip slipped"
        log(f"[demo] cycle {cycle} result: {result} (start-of-hold z={cz0:+.3f}, end-of-hold z={cz1:+.3f})")

        # LOWER back down before releasing (gentle place, not a drop)
        pos_b, quat_b = wrist_target_for_tcp(grasp_pos, home_tcp_quat)
        set_ik_goal(pos_b, quat_b)
        for i in range(STEPS["LOWER"]):
            if not simulation_app.is_running():
                return
            do_step("LOWER")

        # OPEN / release
        set_gripper(open_=True)
        for i in range(STEPS["OPEN"]):
            if not simulation_app.is_running():
                return
            do_step("OPEN")

        # RETRACT back to hover
        pos_b, quat_b = wrist_target_for_tcp(retract_pos, home_tcp_quat)
        set_ik_goal(pos_b, quat_b)
        for i in range(STEPS["RETRACT"]):
            if not simulation_app.is_running():
                return
            do_step("RETRACT")

        for i in range(STEPS["PAUSE"]):
            if not simulation_app.is_running():
                return
            do_step("PAUSE")


def main() -> None:
    # Progress is logged at every stage below, not just at the end. The Day-21 run that
    # produced no output at all could not be diagnosed precisely because there was no way to
    # tell "died during scene construction" from "ran fine and the window was closed after
    # three seconds". Now the report says how far it got.
    log("=" * 78)
    log("LIVE GRASP DEMO — simple two-finger gripper")
    log("=" * 78)
    log(G.summary())
    log("")

    log("[demo] creating simulation context...")
    sim_cfg = sim_utils.SimulationCfg(dt=0.01, device=args_cli.device)
    sim = sim_utils.SimulationContext(sim_cfg)
    sim.set_camera_view([1.7, 1.7, 1.2], [0.5, 0.0, 0.25])

    log("[demo] building scene (downloads table + DexCube from the Isaac asset server on a "
        "cold cache — this is the slow step)...")
    scene_cfg = GraspDemoSceneCfg(num_envs=args_cli.num_envs, env_spacing=2.5)
    scene = InteractiveScene(scene_cfg)
    log("[demo] scene built. resetting sim...")
    sim.reset()
    log("[demo] sim reset done.")

    robot = scene["robot"]
    log(f"[demo] body names : {list(robot.body_names)}")
    log(f"[demo] joint names: {list(robot.joint_names)}")

    stage = get_current_stage()
    n_painted = paint_gripper_black(stage)
    log(f"[demo] painted {n_painted} gripper prims black "
        f"(expected {3 * args_cli.num_envs}: base_link + left_finger + right_finger per env)")

    log("[demo] setup complete. Close the viewport window or Ctrl+C to stop.")
    run_demo(sim, scene, lift_height=args_cli.lift_height)
    log("[demo] simulation window closed — exiting normally.")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback

        log("!! demo failed — traceback below:")
        log(traceback.format_exc())
    finally:
        log(f"[report saved to {_REPORT_PATH}]")
        _FH.close()
        simulation_app.close()
