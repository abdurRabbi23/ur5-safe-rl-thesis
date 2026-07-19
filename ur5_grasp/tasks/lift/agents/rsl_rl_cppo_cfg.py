# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""rsl_rl PPO-Lagrangian (cPPO) runner config for the UR5e lift task.

Mirrors the PPO baseline cfg exactly (same nets, same hyperparameters) and only adds
the constrained-RL machinery, so cPPO-vs-PPO differs by the safety constraint alone.
Logs under experiment `ur5e_lift_cppo`; keep the PPO baseline under `ur5e_lift` and point
TensorBoard at `logs/rsl_rl` to overlay both.
"""

from isaaclab.utils import configclass

from isaaclab_rl.rsl_rl import RslRlOnPolicyRunnerCfg, RslRlPpoActorCriticCfg, RslRlPpoAlgorithmCfg


@configclass
class RslRlCppoActorCriticCfg(RslRlPpoActorCriticCfg):
    class_name: str = "ActorCriticCost"


@configclass
class RslRlCppoAlgorithmCfg(RslRlPpoAlgorithmCfg):
    class_name: str = "PPOLagrangian"
    # --- constrained-RL knobs ---
    cost_limit: float = 25.0            # CALIBRATED Day 9 (undiscounted episodic-cost budget).
                                        # 50-iter probe: ~65% cost cut vs natural ~70+, ~17% reward dip, lambda controlled.
    lambda_lr: float = 0.035            # dual-ascent step for the Lagrange multiplier
    lambda_init: float = 0.0
    lambda_max: float = 100.0
    cost_value_loss_coef: float = 1.0
    gamma_cost: float = 0.98
    lam_cost: float = 0.95
    normalize_cost_advantage: bool = True
    penalty_advantage_normalize: bool = True


@configclass
class UR5eLiftCPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    num_steps_per_env = 24
    max_iterations = 1500
    save_interval = 50
    experiment_name = "ur5e_lift_cppo"
    class_name = "LagrangianRunner"
    obs_groups = {"policy": ["policy"], "critic": ["policy"]}
    policy = RslRlCppoActorCriticCfg(
        init_noise_std=1.0,
        actor_obs_normalization=False,
        critic_obs_normalization=False,
        actor_hidden_dims=[256, 128, 64],
        critic_hidden_dims=[256, 128, 64],
        activation="elu",
    )
    algorithm = RslRlCppoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.2,
        entropy_coef=0.006,
        num_learning_epochs=5,
        num_mini_batches=4,
        learning_rate=1.0e-4,
        schedule="adaptive",
        gamma=0.98,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=1.0,
    )
