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

# --- RH-P12-RN variant: the REAL hardware gripper, real contact grasp (no weld) -------
# Additive. The two ids above are the frozen Layer 1 benchmark and must not change.
gym.register(
    id="Isaac-Lift-Cube-UR5e-RHP12-v0",
    entry_point=f"{__name__}.ur5e_rhp12_env:UR5eRHP12LiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_rhp12_env_cfg:UR5eRHP12LiftEnvCfg",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Lift-Cube-UR5e-RHP12-Play-v0",
    entry_point=f"{__name__}.ur5e_rhp12_env:UR5eRHP12LiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_rhp12_env_cfg:UR5eRHP12LiftEnvCfg_PLAY",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

# --- RH-P12-RN ABLATION: same contact env, Layer 1's ORIGINAL sparse lift reward -------
# Run alongside -RHP12-v0 (dense lift shaping). Same env, same physics, same action space;
# ONLY the lift reward differs, so raw episode reward stays comparable with Layer 1 and the
# gap between the two runs measures the exploration cost of removing the weld.
gym.register(
    id="Isaac-Lift-Cube-UR5e-RHP12-Stock-v0",
    entry_point=f"{__name__}.ur5e_rhp12_env:UR5eRHP12LiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_rhp12_env_cfg:UR5eRHP12LiftEnvCfg_STOCK",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)

gym.register(
    id="Isaac-Lift-Cube-UR5e-RHP12-Stock-Play-v0",
    entry_point=f"{__name__}.ur5e_rhp12_env:UR5eRHP12LiftEnv",
    kwargs={
        "env_cfg_entry_point": f"{__name__}.ur5e_rhp12_env_cfg:UR5eRHP12LiftEnvCfg_STOCK_PLAY",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:UR5eLiftPPORunnerCfg",
        "rsl_rl_cppo_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPORunnerCfg",
    },
    disable_env_checker=True,
)
