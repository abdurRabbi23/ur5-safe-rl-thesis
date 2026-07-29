# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Safe-RL layer for the UR5e grasp task (Layer 1 deliverable).

Constrained PPO (Lagrangian CMDP) built ON TOP of rsl_rl 3.0.1, as thin subclasses
so the PPO baseline stays byte-for-byte the control. Pieces:

  costs.py                -- per-step safety cost (collision / joint-limit / singularity)
  actor_critic_cost.py    -- ActorCritic + a second (cost) critic head
  rollout_storage_cost.py -- RolloutStorage + cost stream, cost-GAE
  ppo_lagrangian.py       -- PPO + combined advantage (A_r - lambda*A_c) + dual-ascent lambda
  lagrangian_runner.py    -- OnPolicyRunner that wires the three above together

The env emits the per-step cost on `env.extras["cost"]`; everything else rides the
stock rsl_rl data path (TensorDict obs, `extras` channel on process_env_step).
"""
