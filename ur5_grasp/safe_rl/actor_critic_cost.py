# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""ActorCritic + a separate cost-value head (textbook PPO-Lagrangian).

Adds a second critic that predicts the discounted *cost*-to-go, reusing the same
critic observation set as the reward critic. Everything else is inherited unchanged
from rsl_rl's ActorCritic, so the actor/reward-critic are identical to the PPO baseline.
"""

from __future__ import annotations

import torch

from rsl_rl.modules import ActorCritic
from rsl_rl.networks import MLP, EmpiricalNormalization


class ActorCriticCost(ActorCritic):
    def __init__(
        self,
        obs,
        obs_groups,
        num_actions,
        actor_obs_normalization: bool = False,
        critic_obs_normalization: bool = False,
        actor_hidden_dims=(256, 256, 256),
        critic_hidden_dims=(256, 256, 256),
        activation: str = "elu",
        init_noise_std: float = 1.0,
        noise_std_type: str = "scalar",
        cost_critic_hidden_dims=None,
        **kwargs,
    ):
        super().__init__(
            obs,
            obs_groups,
            num_actions,
            actor_obs_normalization=actor_obs_normalization,
            critic_obs_normalization=critic_obs_normalization,
            actor_hidden_dims=list(actor_hidden_dims),
            critic_hidden_dims=list(critic_hidden_dims),
            activation=activation,
            init_noise_std=init_noise_std,
            noise_std_type=noise_std_type,
            **kwargs,
        )

        # cost critic: same input as the reward critic, mirrors its architecture unless overridden
        if cost_critic_hidden_dims is None:
            cost_critic_hidden_dims = list(critic_hidden_dims)
        num_critic_obs = sum(obs[g].shape[-1] for g in self.obs_groups["critic"])
        self.cost_critic = MLP(num_critic_obs, 1, list(cost_critic_hidden_dims), activation)

        self.cost_critic_obs_normalization = critic_obs_normalization
        if critic_obs_normalization:
            self.cost_critic_obs_normalizer = EmpiricalNormalization(num_critic_obs)
        else:
            self.cost_critic_obs_normalizer = torch.nn.Identity()
        print(f"Cost Critic MLP: {self.cost_critic}")

    def evaluate_cost(self, obs, **kwargs):
        obs = self.get_critic_obs(obs)
        obs = self.cost_critic_obs_normalizer(obs)
        return self.cost_critic(obs)

    def update_normalization(self, obs):
        super().update_normalization(obs)
        if self.cost_critic_obs_normalization:
            self.cost_critic_obs_normalizer.update(self.get_critic_obs(obs))
