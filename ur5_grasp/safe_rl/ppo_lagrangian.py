# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""PPO-Lagrangian (constrained PPO) on top of rsl_rl 3.0.1.

Solves the CMDP  max_pi J_reward(pi)  s.t.  J_cost(pi) <= d  via the Lagrangian
    max_pi  min_{lambda>=0}  J_reward - lambda*(J_cost - d).

Concretely, on top of stock PPO:
  * a separate cost critic (ActorCriticCost) + cost-GAE (RolloutStorageCost),
  * the surrogate uses the combined advantage  A = (A_reward - lambda*A_cost)/(1+lambda),
  * the Lagrange multiplier lambda is updated once per iteration by projected dual
    ascent on the measured mean episodic cost:  lambda <- clip(lambda + eta*(Jc - d), 0, max).

Baseline PPO == this with lambda pinned at 0 (achieved by simply using the stock PPO
runner instead). RND/symmetry are intentionally unsupported here to keep the math auditable.
"""

from __future__ import annotations

import statistics
from collections import deque

import torch
import torch.nn as nn

from rsl_rl.algorithms import PPO

from .rollout_storage_cost import RolloutStorageCost


class PPOLagrangian(PPO):
    def __init__(
        self,
        policy,
        cost_limit: float = 25.0,
        lambda_lr: float = 0.035,
        lambda_init: float = 0.0,
        lambda_max: float = 100.0,
        cost_value_loss_coef: float = 1.0,
        gamma_cost: float | None = None,
        lam_cost: float | None = None,
        normalize_cost_advantage: bool = True,
        penalty_advantage_normalize: bool = True,
        **kwargs,
    ):
        super().__init__(policy, **kwargs)  # PPO params (+ multi_gpu_cfg) flow through kwargs
        if self.rnd is not None or self.symmetry is not None:
            raise NotImplementedError("PPOLagrangian does not support RND or symmetry.")

        self.cost_limit = float(cost_limit)
        self.lambda_lr = float(lambda_lr)
        self.cost_lambda = float(lambda_init)
        self.lambda_max = float(lambda_max)
        self.cost_value_loss_coef = float(cost_value_loss_coef)
        self.gamma_cost = self.gamma if gamma_cost is None else float(gamma_cost)
        self.lam_cost = self.lam if lam_cost is None else float(lam_cost)
        self.normalize_cost_advantage = bool(normalize_cost_advantage)
        self.penalty_advantage_normalize = bool(penalty_advantage_normalize)

        # episodic-cost accounting for the dual update
        self._cur_cost_sum = None
        self._cost_buffer = deque(maxlen=100)

    # -- storage with the cost stream --
    def init_storage(self, training_type, num_envs, num_transitions_per_env, obs, actions_shape):
        self.storage = RolloutStorageCost(
            training_type, num_envs, num_transitions_per_env, obs, actions_shape, self.device
        )
        self.transition = RolloutStorageCost.Transition()
        self._cur_cost_sum = torch.zeros(num_envs, device=self.device)

    # -- rollout: also record the cost-value prediction --
    def act(self, obs):
        actions = super().act(obs)
        self.transition.cost_values = self.policy.evaluate_cost(obs).detach()
        return actions

    # -- rollout: record cost, bootstrap on timeout, track episodic cost --
    def process_env_step(self, obs, rewards, dones, extras):
        self.policy.update_normalization(obs)

        self.transition.rewards = rewards.clone()
        self.transition.dones = dones

        if "cost" in extras:
            cost = extras["cost"].to(self.device).float()
        else:
            cost = torch.zeros_like(rewards)
        self.transition.costs = cost.clone()

        # bootstrap reward AND cost on timeouts (infinite-horizon correction)
        if "time_outs" in extras:
            t = extras["time_outs"].unsqueeze(1).to(self.device)
            self.transition.rewards += self.gamma * torch.squeeze(self.transition.values * t, 1)
            self.transition.costs += self.gamma_cost * torch.squeeze(self.transition.cost_values * t, 1)

        # accumulate undiscounted episodic cost; on episode end push to the buffer
        self._cur_cost_sum += cost
        done_b = dones.bool()
        if torch.any(done_b):
            self._cost_buffer.extend(self._cur_cost_sum[done_b].detach().cpu().numpy().tolist())
            self._cur_cost_sum[done_b] = 0.0

        self.storage.add_transitions(self.transition)
        self.transition.clear()
        self.policy.reset(dones)

    # -- reward returns (super) + cost returns --
    def compute_returns(self, obs):
        super().compute_returns(obs)
        last_cost_values = self.policy.evaluate_cost(obs).detach()
        self.storage.compute_cost_returns(
            last_cost_values, self.gamma_cost, self.lam_cost, normalize=self.normalize_cost_advantage
        )

    def update(self):  # noqa: C901
        # ---- dual ascent on lambda (once per iteration, on the just-collected rollout) ----
        jc = statistics.mean(self._cost_buffer) if len(self._cost_buffer) > 0 else 0.0
        self.cost_lambda = float(
            min(self.lambda_max, max(0.0, self.cost_lambda + self.lambda_lr * (jc - self.cost_limit)))
        )

        mean_value_loss = 0.0
        mean_cost_value_loss = 0.0
        mean_surrogate_loss = 0.0
        mean_entropy = 0.0

        generator = self.storage.mini_batch_generator(self.num_mini_batches, self.num_learning_epochs)
        for (
            obs_batch,
            actions_batch,
            target_values_batch,
            advantages_batch,
            returns_batch,
            old_actions_log_prob_batch,
            old_mu_batch,
            old_sigma_batch,
            _hid_states_batch,
            _masks_batch,
            cost_target_values_batch,
            cost_advantages_batch,
            cost_returns_batch,
        ) in generator:
            if self.normalize_advantage_per_mini_batch:
                with torch.no_grad():
                    advantages_batch = (advantages_batch - advantages_batch.mean()) / (advantages_batch.std() + 1e-8)
                    cost_advantages_batch = (cost_advantages_batch - cost_advantages_batch.mean()) / (
                        cost_advantages_batch.std() + 1e-8
                    )

            # recompute log-prob / values for the current params
            self.policy.act(obs_batch)
            actions_log_prob_batch = self.policy.get_actions_log_prob(actions_batch)
            value_batch = self.policy.evaluate(obs_batch)
            cost_value_batch = self.policy.evaluate_cost(obs_batch)
            mu_batch = self.policy.action_mean
            sigma_batch = self.policy.action_std
            entropy_batch = self.policy.entropy

            # adaptive LR via KL (identical to stock PPO)
            if self.desired_kl is not None and self.schedule == "adaptive":
                with torch.inference_mode():
                    kl = torch.sum(
                        torch.log(sigma_batch / old_sigma_batch + 1.0e-5)
                        + (torch.square(old_sigma_batch) + torch.square(old_mu_batch - mu_batch))
                        / (2.0 * torch.square(sigma_batch))
                        - 0.5,
                        axis=-1,
                    )
                    kl_mean = torch.mean(kl)
                    if self.is_multi_gpu:
                        torch.distributed.all_reduce(kl_mean, op=torch.distributed.ReduceOp.SUM)
                        kl_mean /= self.gpu_world_size
                    if self.gpu_global_rank == 0:
                        if kl_mean > self.desired_kl * 2.0:
                            self.learning_rate = max(1e-5, self.learning_rate / 1.5)
                        elif kl_mean < self.desired_kl / 2.0 and kl_mean > 0.0:
                            self.learning_rate = min(1e-2, self.learning_rate * 1.5)
                    if self.is_multi_gpu:
                        lr_tensor = torch.tensor(self.learning_rate, device=self.device)
                        torch.distributed.broadcast(lr_tensor, src=0)
                        self.learning_rate = lr_tensor.item()
                    for param_group in self.optimizer.param_groups:
                        param_group["lr"] = self.learning_rate

            # ---- combined (Lagrangian) advantage ----
            adv = advantages_batch - self.cost_lambda * cost_advantages_batch
            if self.penalty_advantage_normalize:
                adv = adv / (1.0 + self.cost_lambda)

            ratio = torch.exp(actions_log_prob_batch - torch.squeeze(old_actions_log_prob_batch))
            surrogate = -torch.squeeze(adv) * ratio
            surrogate_clipped = -torch.squeeze(adv) * torch.clamp(
                ratio, 1.0 - self.clip_param, 1.0 + self.clip_param
            )
            surrogate_loss = torch.max(surrogate, surrogate_clipped).mean()

            # reward value loss
            if self.use_clipped_value_loss:
                value_clipped = target_values_batch + (value_batch - target_values_batch).clamp(
                    -self.clip_param, self.clip_param
                )
                value_loss = torch.max(
                    (value_batch - returns_batch).pow(2), (value_clipped - returns_batch).pow(2)
                ).mean()
            else:
                value_loss = (returns_batch - value_batch).pow(2).mean()

            # cost value loss (same clipping scheme)
            if self.use_clipped_value_loss:
                cost_value_clipped = cost_target_values_batch + (
                    cost_value_batch - cost_target_values_batch
                ).clamp(-self.clip_param, self.clip_param)
                cost_value_loss = torch.max(
                    (cost_value_batch - cost_returns_batch).pow(2),
                    (cost_value_clipped - cost_returns_batch).pow(2),
                ).mean()
            else:
                cost_value_loss = (cost_returns_batch - cost_value_batch).pow(2).mean()

            loss = (
                surrogate_loss
                + self.value_loss_coef * value_loss
                + self.cost_value_loss_coef * cost_value_loss
                - self.entropy_coef * entropy_batch.mean()
            )

            self.optimizer.zero_grad()
            loss.backward()
            if self.is_multi_gpu:
                self.reduce_parameters()
            nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
            self.optimizer.step()

            mean_value_loss += value_loss.item()
            mean_cost_value_loss += cost_value_loss.item()
            mean_surrogate_loss += surrogate_loss.item()
            mean_entropy += entropy_batch.mean().item()

        num_updates = self.num_learning_epochs * self.num_mini_batches
        mean_value_loss /= num_updates
        mean_cost_value_loss /= num_updates
        mean_surrogate_loss /= num_updates
        mean_entropy /= num_updates
        self.storage.clear()

        return {
            "value_function": mean_value_loss,
            "cost_value_function": mean_cost_value_loss,
            "surrogate": mean_surrogate_loss,
            "entropy": mean_entropy,
            "cost_lambda": self.cost_lambda,
            "mean_episode_cost": jc,
        }
