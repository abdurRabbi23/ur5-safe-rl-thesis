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
                                        # Valid only at episode_length_s = 5.0 (250 steps @ 50 Hz): the budget is
                                        # EPISODIC over a per-step cost, so any change to episode length rescales
                                        # the constraint and voids this calibration. Day 19 tried 7.0 s and reverted.
                                        # RECHECKED Day 23 (cont.), Step 4: `cost_probe_v2_ctrl` (1500-iter
                                        # `ctrl` agent -- pure-PPO behaviour, so this is the genuine unconstrained
                                        # natural cost -- against the fully recalibrated env: MANIP_FLOOR=0.06,
                                        # JOINT_LIMIT_MARGIN=0.175, COLLISION_Z_FLOOR=0.05). Natural episodic cost
                                        # is now ~105 (cost_singularity ~15, cost_joint_limit ~90, cost_collision 0
                                        # -- per-step means x250 steps), NOT the 7-29 the 2026-07-30 matrix saw and
                                        # NOT the ~70 Day-9's probe assumed. Composition has flipped: joint-limit is
                                        # now ~86% of natural cost, singularity only ~14% -- a direct consequence of
                                        # JOINT_LIMIT_MARGIN going from inactive to active (see ur5e_lift_env.py).
                                        # cost_limit is therefore no longer plausibly slack (the audit's §A2 caveat
                                        # inherited into this batch's task brief no longer applies): 25 against a
                                        # natural cost of 105 is a ~76% cut, tighter than Day-9's ~65% design target.
                                        # KEPT AT 25 (Touhid's call, Day 23 cont.) -- not retuned further before
                                        # this batch, to avoid stacking a second calibration decision under
                                        # schedule pressure. Let the real cppo-vs-ctrl run be the test: if cppo's
                                        # reward tail-mean comes out meaningfully worse than ctrl's/ppo's (not just
                                        # different), that is a reportable limitation of this batch, not a bug --
                                        # see run_log.md and MATRIX_V2_PARTIAL_3ARM.md, Day 23 (cont.).
    lambda_lr: float = 0.035            # dual-ascent step for the Lagrange multiplier
    lambda_init: float = 0.0
    lambda_max: float = 100.0
    cost_value_loss_coef: float = 1.0
    gamma_cost: float = 0.98
    lam_cost: float = 0.95
    normalize_cost_advantage: bool = True
    penalty_advantage_normalize: bool = True
    cost_buffer_size: int = 4096        # Jc estimator window; = num_envs, so one full wave
                                        # of simultaneously-terminating episodes. Was an
                                        # implicit 100 before the Day-23 audit (finding A3).


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


# =====================================================================================
# Day-23 audit arms. Both are IDENTICAL to UR5eLiftCPPORunnerCfg above except for the one
# field named in each class. Do not add a second difference to either of them -- the whole
# point is that each isolates exactly one variable.
# =====================================================================================


@configclass
class UR5eLiftCPPO10RunnerCfg(UR5eLiftCPPORunnerCfg):
    """cPPO with a TIGHT cost budget (10 instead of 25).

    Why this arm exists. On the 2026-07-30 matrix `Loss/cost_lambda` sat at 0.0 for
    essentially the whole run on all three seeds: cPPO's natural episodic cost is 7-27,
    so a budget of 25 is above the unconstrained operating point and the dual update
    correctly never activated. A constraint that never binds cannot produce a
    constrained-RL result. 10 sits below the natural cost on every observed seed, so
    lambda must climb and the Lagrangian must actually trade reward for safety.

    Day-9's calibration of cost_limit = 25 is NOT wrong -- it was calibrated from a 50-iter
    probe against the then-unconstrained cost of ~70. The full 1500-iter runs simply land
    much lower than that probe suggested. Report both budgets as a sensitivity analysis;
    do not silently replace 25 with 10.

    Still valid only at episode_length_s = 5.0 -- the budget is episodic over a per-step
    cost, so episode length rescales it. Same caveat as the parent.
    """

    experiment_name = "ur5e_lift_cppo10"
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
        cost_limit=10.0,          # <-- THE ONLY DIFFERENCE FROM THE PARENT
    )


@configclass
class UR5eLiftCPPO15RunnerCfg(UR5eLiftCPPORunnerCfg):
    """cPPO with cost_limit = 15, REPLACING the registered `cppo10` arm (Day 24, cont.).

    Why 15 and not the registered 10. `ALGORITHM_AUDIT.md` §A2 justified cost_limit=10 as
    "below the natural cost on every observed seed" -- true against the 3-seed 2026-07-30
    data it was written from, but NOT true against the 10-seed `ctrl` data in
    MATRIX_V2_PARTIAL_3ARM.md §4.1 (natural cost 1.8-162.3 across seeds 1-5/50-54). Checked
    directly (2026-08-01, Day 24 cont. session) before this class was written:
        budget 15 binds (natural cost > budget) on seeds 1, 3, 4, 5, 52, 53 -- slack on 2, 50, 51, 54
        budget 10 binds on the SAME six seeds -- slack on the same four
    The partition is identical: 10 would not have met its own "binds on every seed" criterion
    either. Only a budget below 1.8 (seed 51's natural cost, the minimum across all ten seeds)
    binds on every seed, which is far below any achievable operating point for this task. 15
    and 10 therefore differ only in DEPTH of bind on the same six seeds, not in which seeds
    bind -- making 15 a substitution for the registered arm, not a weakening of it. Full
    reasoning: logbook/NEXT_SESSION_cppo15.md.

    Still valid only at episode_length_s = 5.0 -- the budget is episodic over a per-step
    cost, so episode length rescales it. Same caveat as the parent.
    """

    experiment_name = "ur5e_lift_cppo15"
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
        cost_limit=15.0,          # <-- THE ONLY DIFFERENCE FROM THE PARENT
    )


@configclass
class UR5eLiftCtrlRunnerCfg(UR5eLiftCPPORunnerCfg):
    """CONTROL ARM: the cost critic, with the constraint switched off (lambda_max = 0).

    `lambda` is updated as clip(lambda + lr*(Jc - d), 0, lambda_max); with lambda_max = 0
    that expression is identically 0 forever, so the combined advantage stays
    (A_reward - 0*A_cost)/(1+0) = A_reward. The policy update is therefore stock PPO --
    but this arm still carries everything ELSE cPPO carries: the second critic in the
    optimiser, its own gradient clip, and the RNG offset its construction causes.

    That makes it the missing control in the 2026-07-30 comparison:

        ctrl  vs  PPO    -> the cost of merely ATTACHING a cost critic (should now be ~0
                            after the Day-23 gradient-clipping fix; if it is not, something
                            else is still coupling the two heads and the audit is incomplete)
        cPPO  vs  ctrl   -> the effect of the CONSTRAINT alone. This difference, and only
                            this difference, is what the thesis may attribute to safe RL.

    If cPPO-vs-ctrl is null while cPPO-vs-PPO is large, the Day-22 headline was an
    artifact. That is a publishable finding and must be reported as one, not buried.
    """

    experiment_name = "ur5e_lift_ctrl"
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
        lambda_max=0.0,           # <-- THE ONLY DIFFERENCE FROM THE PARENT
    )
