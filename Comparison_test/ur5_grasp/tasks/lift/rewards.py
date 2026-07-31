# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Custom lift-reward terms for the UR5e lift task.

Isaac Lab's stock `object_is_lifted` / `object_goal_distance` (isaaclab_tasks.manager_based.
manipulation.lift.mdp.rewards) gate their reward on a FIXED scalar `minimal_height` (0.04 m in
the inherited Franka defaults) -- the object counts as "lifted" once it clears an absolute
height, regardless of where this episode's goal actually is.

Day 23 (cont.): Touhid wants "lifted" to instead mean *50% of the way from the table to this
episode's goal height*, so the gate scales with how far the sampled goal actually is above the
table (relevant now that the goal-pose box's pos_z spans 0.10-0.50 m, not a narrow band). These
two functions are drop-in replacements for the stock ones, same signatures plus `fraction` /
`spawn_height` in place of `minimal_height`, so `RewTerm(func=...)` swaps cleanly in
`ur5e_lift_env_cfg.py`. Written here (project-owned) rather than editing the vendored Isaac Lab
source, same rule as the goal-pose range override.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.assets import RigidObject
from isaaclab.managers import SceneEntityCfg
from isaaclab.utils.math import combine_frame_transforms

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def _lift_threshold_z(
    env: ManagerBasedRLEnv,
    fraction: float,
    spawn_height: float,
    command_name: str,
    robot_cfg: SceneEntityCfg,
) -> torch.Tensor:
    """Per-env world-frame height that counts as "lifted": `spawn_height` plus `fraction` of
    the vertical gap up to this episode's commanded goal height. Mirrors the world-frame
    transform `object_goal_distance` uses for the goal position (command is base-frame)."""
    robot: RigidObject = env.scene[robot_cfg.name]
    command = env.command_manager.get_command(command_name)
    des_pos_b = command[:, :3]
    des_pos_w, _ = combine_frame_transforms(robot.data.root_pos_w, robot.data.root_quat_w, des_pos_b)
    goal_z = des_pos_w[:, 2]
    return spawn_height + fraction * (goal_z - spawn_height)


def object_lifted_toward_goal(
    env: ManagerBasedRLEnv,
    fraction: float,
    spawn_height: float,
    command_name: str,
    robot_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
    object_cfg: SceneEntityCfg = SceneEntityCfg("object"),
) -> torch.Tensor:
    """Drop-in replacement for `object_is_lifted`: 1.0 once the object has climbed `fraction`
    of the way from `spawn_height` to this episode's goal height, else 0.0."""
    object: RigidObject = env.scene[object_cfg.name]
    threshold = _lift_threshold_z(env, fraction, spawn_height, command_name, robot_cfg)
    return torch.where(object.data.root_pos_w[:, 2] > threshold, 1.0, 0.0)


def object_goal_distance_relative_lift(
    env: ManagerBasedRLEnv,
    std: float,
    fraction: float,
    spawn_height: float,
    command_name: str,
    robot_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
    object_cfg: SceneEntityCfg = SceneEntityCfg("object"),
) -> torch.Tensor:
    """Drop-in replacement for `object_goal_distance`: identical tanh-kernel distance reward,
    but gated on `object_lifted_toward_goal`'s goal-relative height instead of a fixed
    `minimal_height`."""
    robot: RigidObject = env.scene[robot_cfg.name]
    object: RigidObject = env.scene[object_cfg.name]
    command = env.command_manager.get_command(command_name)
    des_pos_b = command[:, :3]
    des_pos_w, _ = combine_frame_transforms(robot.data.root_pos_w, robot.data.root_quat_w, des_pos_b)
    threshold = spawn_height + fraction * (des_pos_w[:, 2] - spawn_height)
    distance = torch.norm(des_pos_w - object.data.root_pos_w, dim=1)
    return (object.data.root_pos_w[:, 2] > threshold) * (1 - torch.tanh(distance / std))
