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
        # --- Day-23 audit arms (see rsl_rl_cppo_cfg.py for why each exists) -------------
        # cppo10: cost_limit 10 instead of 25, so the constraint actually binds.
        # ctrl  : cost critic present, lambda pinned to 0 — isolates the implementation
        #         artifact from the constraint. THIS IS THE CONTROL; do not drop it.
        "rsl_rl_cppo10_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPO10RunnerCfg",
        "rsl_rl_ctrl_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCtrlRunnerCfg",
        # cppo15: cost_limit 15, REPLACES cppo10 as the binding-budget arm (Day 24, cont.) --
        # see UR5eLiftCPPO15RunnerCfg's docstring in rsl_rl_cppo_cfg.py for why. cppo10 stays
        # registered (harmless, unused) rather than being torn out.
        "rsl_rl_cppo15_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPO15RunnerCfg",
        # --- skrl agents (4-algorithm comparison) -------------------------------------
        # Selected by ur5_grasp/scripts/train_skrl.py via --algorithm: PPO maps to
        # "skrl_cfg_entry_point", anything else to "skrl_<algorithm>_cfg_entry_point".
        # These are YAML resources inside the agents package, not config classes.
        "skrl_cfg_entry_point": f"{agents.__name__}:skrl_ppo_cfg.yaml",
        # TODO(Day 23+): the yaml below is NOT AUTHORED YET. Registered ahead of time so
        # the wiring is in one place; running --algorithm SAC before the file exists fails
        # with FileNotFoundError on the yaml, which is the intended, readable failure.
        # No SAC skrl config exists anywhere in this IsaacLab checkout — it must be
        # written from skrl's own docs.
        # TD3 CUT 2026-07-31 (Day 23), Touhid's call, ahead of the Aug 6 hard-cut date.
        # The benchmark is now THREE algorithms: PPO / cPPO / SAC. Do not re-add the
        # skrl_td3_cfg_entry_point without a matching decision-record entry in
        # logbook/03c_multialgo_benchmark.md.
        "skrl_sac_cfg_entry_point": f"{agents.__name__}:skrl_sac_cfg.yaml",
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
        # Day-23 audit arms — also registered on -Play-v0 so eval_policy.py can load their
        # checkpoints (it resolves the agent cfg through whichever task id it is given).
        "rsl_rl_cppo10_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPO10RunnerCfg",
        "rsl_rl_ctrl_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCtrlRunnerCfg",
        "rsl_rl_cppo15_cfg_entry_point": f"{agents.__name__}.rsl_rl_cppo_cfg:UR5eLiftCPPO15RunnerCfg",
        # --- skrl agents: same entry points as -v0, needed by skrl's play.py ----------
        "skrl_cfg_entry_point": f"{agents.__name__}:skrl_ppo_cfg.yaml",
        "skrl_sac_cfg_entry_point": f"{agents.__name__}:skrl_sac_cfg.yaml",  # not authored yet
        # TD3 CUT 2026-07-31 (Day 23) — see the note on -v0 above.
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
