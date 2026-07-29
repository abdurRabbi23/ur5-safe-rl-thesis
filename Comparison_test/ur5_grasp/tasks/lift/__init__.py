# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Gym registration for the UR5e cube-lift task."""

import gymnasium as gym

from . import agents

gym.register(
    id="Isaac-Lift-Cube-UR5e-v0",
    entry_point=f"{__name__}.ur5e_lift_env:UR5eCubeLiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_lift_env_cfg:UR5eCubeLiftEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        # cPPO (PPO-Lagrangian) agent — same env, select with `--agent rsl_rl_cppo_cfg_entry_point`
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Lift-Cube-UR5e-Play-v0",
    entry_point=f"{__name__}.ur5e_lift_env:UR5eCubeLiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_lift_env_cfg:UR5eCubeLiftEnvCfg_PLAY",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

# --- Contact-grasp variant (post-Layer-1): real finger contact, no weld ------------
gym.register(
    id="Isaac-Lift-Cube-UR5e-Contact-v0",
    entry_point=f"{__name__}.ur5e_contact_env:UR5eCubeContactEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_contact_env_cfg:UR5eCubeContactEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Lift-Cube-UR5e-Contact-Play-v0",
    entry_point=f"{__name__}.ur5e_contact_env:UR5eCubeContactEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_contact_env_cfg:UR5eCubeContactEnvCfg_PLAY",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

# --- Simple two-finger gripper variant (Day 20 replacement for the Robotiq 2f-85
# contact-grasp attempt) — real contact grasp, no linkage, no weld. Reuses the same
# UR5eCubeContactEnv class (its only job is "no weld", which is gripper-agnostic);
# only the cfg differs (new robot, new gripper action, resized EE offset). See
# ur5e_simple_gripper_env_cfg.py for why this subclasses UR5eCubeLiftEnvCfg directly
# rather than UR5eCubeContactEnvCfg. -------------------------------------------------
gym.register(
    id="Isaac-Lift-Cube-UR5e-SimpleGripper-v0",
    entry_point=f"{__name__}.ur5e_contact_env:UR5eCubeContactEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_simple_gripper_env_cfg:UR5eSimpleGripperLiftEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Lift-Cube-UR5e-SimpleGripper-Play-v0",
    entry_point=f"{__name__}.ur5e_contact_env:UR5eCubeContactEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_simple_gripper_env_cfg:UR5eSimpleGripperLiftEnvCfg_PLAY",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)
