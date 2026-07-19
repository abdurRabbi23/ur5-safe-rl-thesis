# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""OnPolicyRunner that builds the cost critic + PPO-Lagrangian.

Only `_construct_algorithm` changes: the stock runner resolves class names with eval()
in its own module namespace (where our subclasses aren't visible), so we build them
directly. Everything else — rollout loop, logging, checkpointing — is inherited, so the
extra `cost_lambda` / `mean_episode_cost` / cost losses land in TensorBoard under Loss/
automatically, and the env's per-step `safety/*` diagnostics under Episode/.
"""

from __future__ import annotations

from rsl_rl.runners import OnPolicyRunner

from .actor_critic_cost import ActorCriticCost
from .ppo_lagrangian import PPOLagrangian


class LagrangianRunner(OnPolicyRunner):
    def _construct_algorithm(self, obs):
        policy_cfg = dict(self.policy_cfg)
        policy_cfg.pop("class_name", None)
        actor_critic = ActorCriticCost(
            obs, self.cfg["obs_groups"], self.env.num_actions, **policy_cfg
        ).to(self.device)

        alg_cfg = dict(self.alg_cfg)
        alg_cfg.pop("class_name", None)
        alg = PPOLagrangian(
            actor_critic, device=self.device, **alg_cfg, multi_gpu_cfg=self.multi_gpu_cfg
        )
        alg.init_storage("rl", self.env.num_envs, self.num_steps_per_env, obs, [self.env.num_actions])
        return alg
