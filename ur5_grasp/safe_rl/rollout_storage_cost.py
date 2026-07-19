# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""RolloutStorage + a parallel cost stream and cost-GAE.

Stores per-step cost and cost-value predictions alongside the reward buffers, computes
GAE returns/advantages for the cost signal (same recursion as reward, own gamma/lambda),
and yields the cost tensors in the mini-batch generator so PPO-Lagrangian can form the
combined advantage. Feed-forward only (our policy is an MLP).
"""

from __future__ import annotations

import torch

from rsl_rl.storage import RolloutStorage


class RolloutStorageCost(RolloutStorage):
    class Transition(RolloutStorage.Transition):
        def __init__(self):
            super().__init__()
            self.costs = None
            self.cost_values = None

    def __init__(self, training_type, num_envs, num_transitions_per_env, obs, actions_shape, device="cpu"):
        super().__init__(training_type, num_envs, num_transitions_per_env, obs, actions_shape, device)
        if training_type != "rl":
            raise ValueError("RolloutStorageCost only supports training_type='rl'.")
        shape = (num_transitions_per_env, num_envs, 1)
        self.costs = torch.zeros(*shape, device=self.device)
        self.cost_values = torch.zeros(*shape, device=self.device)
        self.cost_returns = torch.zeros(*shape, device=self.device)
        self.cost_advantages = torch.zeros(*shape, device=self.device)

    def add_transitions(self, transition: "RolloutStorageCost.Transition"):
        step = self.step  # capture before super() increments it
        super().add_transitions(transition)
        self.costs[step].copy_(transition.costs.view(-1, 1))
        self.cost_values[step].copy_(transition.cost_values)

    def compute_cost_returns(self, last_cost_values, gamma, lam, normalize: bool = True):
        advantage = 0
        for step in reversed(range(self.num_transitions_per_env)):
            next_values = last_cost_values if step == self.num_transitions_per_env - 1 else self.cost_values[step + 1]
            next_is_not_terminal = 1.0 - self.dones[step].float()
            delta = self.costs[step] + next_is_not_terminal * gamma * next_values - self.cost_values[step]
            advantage = delta + next_is_not_terminal * gamma * lam * advantage
            self.cost_returns[step] = advantage + self.cost_values[step]
        self.cost_advantages = self.cost_returns - self.cost_values
        if normalize:
            self.cost_advantages = (self.cost_advantages - self.cost_advantages.mean()) / (
                self.cost_advantages.std() + 1e-8
            )

    def mini_batch_generator(self, num_mini_batches, num_epochs=8):
        """Feed-forward generator; yields the stock 10-tuple + (cost_values, cost_adv, cost_returns)."""
        batch_size = self.num_envs * self.num_transitions_per_env
        mini_batch_size = batch_size // num_mini_batches
        indices = torch.randperm(num_mini_batches * mini_batch_size, requires_grad=False, device=self.device)

        observations = self.observations.flatten(0, 1)
        actions = self.actions.flatten(0, 1)
        values = self.values.flatten(0, 1)
        returns = self.returns.flatten(0, 1)
        old_actions_log_prob = self.actions_log_prob.flatten(0, 1)
        advantages = self.advantages.flatten(0, 1)
        old_mu = self.mu.flatten(0, 1)
        old_sigma = self.sigma.flatten(0, 1)
        # cost tensors
        cost_values = self.cost_values.flatten(0, 1)
        cost_advantages = self.cost_advantages.flatten(0, 1)
        cost_returns = self.cost_returns.flatten(0, 1)

        for epoch in range(num_epochs):
            for i in range(num_mini_batches):
                start = i * mini_batch_size
                end = (i + 1) * mini_batch_size
                batch_idx = indices[start:end]

                obs_batch = observations[batch_idx]
                actions_batch = actions[batch_idx]
                target_values_batch = values[batch_idx]
                returns_batch = returns[batch_idx]
                old_actions_log_prob_batch = old_actions_log_prob[batch_idx]
                advantages_batch = advantages[batch_idx]
                old_mu_batch = old_mu[batch_idx]
                old_sigma_batch = old_sigma[batch_idx]
                cost_target_values_batch = cost_values[batch_idx]
                cost_advantages_batch = cost_advantages[batch_idx]
                cost_returns_batch = cost_returns[batch_idx]

                yield (
                    obs_batch,
                    actions_batch,
                    target_values_batch,
                    advantages_batch,
                    returns_batch,
                    old_actions_log_prob_batch,
                    old_mu_batch,
                    old_sigma_batch,
                    (None, None),
                    None,
                    cost_target_values_batch,
                    cost_advantages_batch,
                    cost_returns_batch,
                )
