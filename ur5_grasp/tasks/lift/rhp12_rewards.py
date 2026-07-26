# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Reward shaping for the RH-P12-RN CONTACT-grasp env (Layer 3 weld validation).

WHY THIS EXISTS
---------------
Layer 1 grasps via a proximity weld: the instant the policy commands CLOSE near the
cube, the cube latches on. Grasping is free, so the stock lift reward works — the only
sparsity (`object_is_lifted`, a step function at 0.04 m) is trivially crossed once the
latch fires.

Remove the weld and that step becomes a cliff. A random policy must discover a pad
alignment precise enough for two flat faces to hold the cube BEFORE it sees a single
unit of lift reward. Below 0.04 m the only gradient is `object_ee_distance`, which
saturates once the arm is near the cube and then goes flat. That is a hard-exploration
failure, and it is the weld's real cost.

WHAT THIS CHANGES — and deliberately what it does NOT
-----------------------------------------------------
`object_lift_progress` replaces `object_is_lifted` on the RH-P12-RN task only. It is a
strict SUPERSET of the stock term:

    cube height >= minimal_height  ->  1.0   (IDENTICAL to object_is_lifted)
    cube height <  minimal_height  ->  gated linear ramp in [0, 1)

So the reward landscape above the threshold is untouched — `object_goal_distance` still
switches on at exactly the same point, and the term's magnitude at success is unchanged,
which keeps the weight of 15.0 meaningful. All that is added is a slope where there was
a cliff.

WHY NOT REWARD THE GRASP DIRECTLY: the obvious shaping is "bonus when the gripper is
commanded closed and the cube is within tolerance of the TCP". That predicate is
literally `UR5eCubeLiftEnv._apply_weld`'s latch condition. Rewarding it would reinstate
the weld in reward-space and would be open to exactly the criticism this whole run
exists to answer. This term instead rewards only the OUTCOME (cube off the table) and
says nothing about how to achieve it — and a UR5e cannot raise a cube without holding it.

THE GATE: an ungated height ramp is farmable — the arm can bat the cube upward and
collect transient height without ever grasping. `near_tol` blocks that by paying the
ramp only while the cube stays within reach of the TCP. Batting sends the cube away from
the TCP, so the flick earns nothing.

CAVEAT FOR THE WRITE-UP: this is a training-time aid and it makes the raw episode reward
NON-comparable with the Layer 1 numbers (cPPO 166.3 / PPO 167.2). Compare on
`scripts/eval_success.py` lift-success % and on the safety-violation % from
`_apply_cost` instead — neither depends on the reward function.
"""

from __future__ import annotations

import torch
from typing import TYPE_CHECKING

from isaaclab.assets import RigidObject
from isaaclab.managers import SceneEntityCfg
from isaaclab.sensors import FrameTransformer

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def object_lift_progress(
    env: ManagerBasedRLEnv,
    minimal_height: float,
    rest_height: float,
    near_tol: float,
    object_cfg: SceneEntityCfg = SceneEntityCfg("object"),
    ee_frame_cfg: SceneEntityCfg = SceneEntityCfg("ee_frame"),
) -> torch.Tensor:
    """Dense drop-in for :func:`object_is_lifted`.

    Args:
        minimal_height: height at which the cube counts as lifted. Above this the
            return is exactly 1.0, matching ``object_is_lifted``.
        rest_height: cube centre height while sitting on the table (0 progress point).
            Measured, not assumed — see ``results/rhp12_geometry_check.txt``.
        near_tol: the ramp only pays while the cube is within this distance of the TCP.
            Stops the policy farming height by batting the cube.

    Returns:
        (num_envs,) in [0, 1].
    """
    obj: RigidObject = env.scene[object_cfg.name]
    ee_frame: FrameTransformer = env.scene[ee_frame_cfg.name]

    z = obj.data.root_pos_w[:, 2]
    lifted = z > minimal_height

    span = max(minimal_height - rest_height, 1e-6)
    ramp = torch.clamp((z - rest_height) / span, 0.0, 1.0)

    tcp = ee_frame.data.target_pos_w[..., 0, :]
    near = torch.norm(obj.data.root_pos_w - tcp, dim=1) < near_tol

    return torch.where(lifted, torch.ones_like(ramp), ramp * near.float())
