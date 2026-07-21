# Methodology — Safe Reinforcement Learning for UR5e Precision Grasping (Layer 1)

**Status:** ✅ Draft (2026-07-19) · Thesis-book chapter prose · **Layer:** 1 (must-pass)
**Scope:** the safe-RL grasping method benchmarked in Chapter *Results* (cPPO vs. PPO).
Formatting note: prose draft for the thesis book (Times New Roman 14, justified, 1.25 spacing when
typeset; tables and figures centred with centred captions). Numbers verified against
`ur5_grasp/` source on 2026-07-19.

---

## 1. Problem formulation

The grasping task is posed as a constrained Markov decision process (CMDP). A standard MDP is the
tuple (S, A, P, r, γ) over states S, actions A, transition kernel P, reward r and discount γ; a CMDP
augments it with a cost function c and a budget d, and asks the policy to maximise expected return
while keeping expected cumulative cost bounded:

    maximise_π  E[ Σ γ^t r(s_t, a_t) ]   subject to   E[ Σ c(s_t, a_t) ]  ≤  d.

This framing separates *what the robot should achieve* (grasp and place the cube, encoded in r) from
*what it must not do* (enter unsafe configurations, encoded in c). The remainder of this chapter
defines the simulation environment and MDP (Section 2), the safety cost that instantiates c
(Section 3), the constrained optimisation algorithm that solves the CMDP (Section 4), the calibration
that makes the constraint meaningful (Section 5), and the training and evaluation protocol
(Sections 6–7).

## 2. Simulation environment and task

Experiments are carried out in NVIDIA Isaac Sim 5.0.0 with the Isaac Lab 2.3.0 manager-based
framework, using the `rsl_rl` 3.0.1 reinforcement-learning library, PyTorch 2.7 (CUDA 12.8) and a
single RTX 5090 GPU. The task is retargeted from Isaac Lab's Franka cube-lift environment onto a
Universal Robots UR5e equipped with a Robotiq 2F-85 gripper; only the robot, action space, and
end-effector frame are changed, so the reward shaping and task structure of the well-tested base
environment are preserved.

The manipulator is a six-degree-of-freedom arm controlled by joint-position commands on its six
revolute joints (shoulder pan, shoulder lift, elbow, and three wrist joints), with the action scaled
by 0.5 about the default configuration. The gripper is driven by a single binary open/close command
on the Robotiq actuation joint. The object is a rigid cube (Isaac's DexCube asset scaled to 0.8)
initialised on a table in front of the arm, and its target is a goal pose sampled once per episode.

Because the Robotiq 2F-85 is a closed-loop linkage whose passive finger joints transmit no normal
force to the pads in simulation, contact-based grasping does not hold the cube (verified with
`grasp_hold_test.py`: the cube falls through the fingers regardless of clamp force). Since the Layer 1
safe-RL result is independent of the specific grasp mechanism, contact grasping is replaced by a
*proximity-weld* abstraction: when the policy commands a close action while the cube lies within a
6 cm tolerance of the end-effector frame, the cube latches to the gripper and its pose tracks the
end-effector each control step (with its velocity zeroed); an open command releases it and physics
resumes. This makes "grasp-and-lift" reliable so that both the baseline and the constrained policy
can learn the task, and defers realistic finger contact to the Layer 3 sim-to-real work.

### 2.1 State, action, and reward

The policy receives a privileged observation comprising the arm joint positions and velocities
(relative to their defaults), the cube position expressed in the robot base frame, the commanded goal
position, and the previous action. Object pose is provided directly rather than through vision, which
isolates the safe-RL contribution from perception; closing the loop with an image-based estimate is
the subject of Layer 2. All observation terms are clamped to a finite range as a numerical
safeguard, preventing a single transiently-unstable environment from corrupting the on-policy batch.

The action is the six-dimensional vector of target arm-joint positions together with the binary
gripper command. Episodes last five simulated seconds with a control decimation of two physics steps
per action, and the goal pose is resampled once per episode from a uniform range over the workspace
(x ∈ [0.4, 0.6] m, y ∈ [−0.25, 0.25] m, z ∈ [0.25, 0.5] m). At reset the cube position is randomised
within a small planar region so the policy cannot memorise a fixed trajectory.

The reward is the shaped sum inherited from the base lift task: a reaching term that rewards reducing
the end-effector-to-object distance (tanh kernel, standard deviation 0.1, weight 1), a lifting term
that rewards raising the cube above 0.04 m (weight 15), and two goal-tracking terms that reward
bringing the lifted cube toward the commanded goal at coarse and fine scales (tanh kernels with
standard deviations 0.3 and 0.05, weights 16 and 5). Small quadratic penalties on the action rate and
joint velocity (each weight −10⁻⁴) discourage jerky motion. Crucially, the reward contains **no
safety term** — safety is expressed entirely through the separate cost channel of Section 3, so that
the comparison in the Results chapter isolates the effect of the constraint.

## 3. The safety cost function

Safety is encoded by a per-step cost computed in `SafetyCostComputer` (`safe_rl/costs.py`) from three
geometric-kinematic terms. Each term is zero while the arm is safe and grows smoothly as the arm
enters a danger zone; smoothness matters because it gives the cost critic (Section 4) a usable
gradient. The three terms are summed into a single aggregate cost so that a single Lagrange multiplier
governs the whole constraint, and each term additionally exposes a mean value and a binary violation
indicator for reporting.

The first term is a **collision keep-out**. For each monitored arm link (forearm, wrist-1, wrist-3)
the penetration depth below the table plane, max(z_floor − z, 0), is summed across links, with the
table plane at z_floor = 0. Because self-collisions are disabled in simulation and no contact sensors
are present, this geometric proxy is the honest, inexpensive choice.

The second term is a **joint-limit margin**. For each arm joint the clearance to its nearer soft limit
is computed, and an encroachment penalty clamp(1 − clearance / margin, 0, 1) is summed over the six
joints, with a margin of 0.10 rad (about 5.7°). The penalty is zero until a joint enters the final
margin band and rises linearly to one at the limit.

The third term, and the operative constraint of this thesis, is a **singularity floor**. The Yoshikawa
manipulability measure w = √det(J Jᵀ) is computed from the 6×6 end-effector Jacobian J of the arm,
where a small w indicates a near-singular configuration in which the arm momentarily loses the ability
to move in some Cartesian direction and commands can produce large, jerky joint velocities. The
penalty clamp(1 − w / w_floor, 0, 1) activates as w falls below a floor of 0.045 and reaches one as w
approaches zero. The Jacobian body-axis index is resolved automatically to accommodate the
fixed-base articulation (for which PhysX omits the root body from the Jacobian), and correctness was
confirmed at calibration by a smooth, small-positive distribution of w.

The aggregate per-step cost is c = c_collision + c_joint + c_singularity (unit weights), and its
undiscounted sum over an episode is the quantity constrained against the budget d.

## 4. Constrained policy optimisation (cPPO)

The CMDP is solved with a Lagrangian formulation of Proximal Policy Optimisation, hereafter cPPO,
which converts the constrained problem into the saddle-point objective

    max_π  min_{λ ≥ 0}   J_reward(π) − λ ( J_cost(π) − d ),

where λ is a non-negative Lagrange multiplier acting as an automatically-tuned penalty on constraint
violation. The implementation (`safe_rl/ppo_lagrangian.py`, `actor_critic_cost.py`,
`rollout_storage_cost.py`, `lagrangian_runner.py`) follows the textbook separate-critic variant: in
addition to the usual value network that estimates future reward, a second critic estimates future
cost, so reward and cost advantages are learned independently. Cost advantages are computed by
generalised advantage estimation with its own discount and smoothing (γ_cost = 0.98, λ_GAE = 0.95).

At each policy-update step the reward and cost advantages are combined into a single Lagrangian
advantage,

    A = ( A_reward − λ · A_cost ) / ( 1 + λ ),

which is then used in the standard clipped PPO surrogate; the division by (1 + λ) keeps the effective
step size stable as λ grows. The multiplier itself is updated once per iteration by projected dual
ascent on the measured mean episodic cost of the just-collected rollout,

    λ ← clip( λ + η ( Ĵ_cost − d ), 0, λ_max ),

with dual step η = 0.035, initial λ = 0, and ceiling λ_max = 100. Intuitively, whenever the policy
exceeds its cost budget the multiplier rises and unsafe actions are penalised more heavily; once the
policy is comfortably under budget the multiplier decays back toward zero. The multiplier tunes
itself during training and is never hand-set.

The unconstrained baseline is exactly this algorithm with λ pinned at zero — that is, stock PPO on
the same `rsl_rl` trainer, with no cost critic. Building the constrained agent as a thin extension of
the baseline, rather than adopting a different safe-RL library, is a deliberate methodological choice:
it guarantees that the baseline and the constrained policy share an identical trainer, network
architecture, and hyperparameters, so any measured difference is attributable to the safety
constraint alone and not to two dissimilar PPO implementations.

Both agents use the same actor and critic multilayer perceptrons with hidden layers of 256, 128 and
64 units and ELU activations, and the same optimisation hyperparameters, summarised in Table M1.

**Table M1. Shared training hyperparameters (PPO baseline and cPPO).**

| Hyperparameter | Value |
|---|---|
| Parallel environments | 4096 |
| Rollout length (steps/env) | 24 |
| Iterations | 1500 |
| Actor / critic hidden layers | [256, 128, 64], ELU |
| Clip parameter | 0.2 |
| Entropy coefficient | 0.006 |
| Learning epochs / mini-batches | 5 / 4 |
| Learning rate (adaptive, target KL 0.01) | 1×10⁻⁴ |
| Discount γ / GAE λ | 0.98 / 0.95 |
| Max gradient norm | 1.0 |
| cPPO cost budget d (`cost_limit`) | 25 |
| cPPO dual step η / λ ceiling | 0.035 / 100 |
| cPPO cost discount / GAE λ | 0.98 / 0.95 |

## 5. Constraint calibration and cost budget

A safety benchmark is only meaningful if the unconstrained baseline actually violates the constraint;
otherwise the constrained policy has nothing to demonstrate. Both the singularity floor and the cost
budget were therefore calibrated from the real trained baseline rather than guessed.

The manipulability floor was set from a 25,600-sample rollout of the trained baseline. The measure w
was distributed with a minimum of 0.021, a mean of 0.055 and a maximum of 0.114; a floor of 0.045,
lying between the tenth and twenty-fifth percentiles, causes the unconstrained baseline to violate the
constraint roughly one fifth of the time, which makes it the single active constraint. The same
rollout showed a minimum joint-limit clearance of 1.39 rad and a minimum monitored-link height of
0.125 m above the table, meaning the arm never approaches its joint limits or the table surface in
this tabletop workspace. The joint-limit and collision terms are therefore inactive by construction;
they are retained and reported as monitored constraints that remain satisfied, which is a truthful and
defensible configuration for a first safe-RL benchmark.

The episodic cost budget d was set from a 50-iteration unconstrained probe, during which the natural
episodic cost of a grasping policy rose above 70 as it learned to reach through near-singular poses.
Setting d = 25 targets roughly a two-thirds reduction of that natural cost; the probe confirmed the
Lagrangian machinery behaved correctly, with the multiplier engaging in a controlled manner (rising to
about 6.9 without saturating) and the expected modest reward trade-off.

## 6. Training protocol

Each agent was trained for 1500 iterations at 4096 parallel environments (roughly 2×10⁵ environment
steps per second on the RTX 5090), headless, with progress monitored through TensorBoard. The
constrained and baseline agents are launched from the same script and differ only by an agent-config
flag, and they log to separate experiment directories so their curves overlay directly for comparison.
The healthy Lagrangian signature to be verified during training is that the mean episodic cost trends
down toward the budget, the multiplier rises while over budget and then settles without pinning at its
ceiling, the reward continues to improve, and the singularity-violation rate falls below the baseline.

## 7. Evaluation protocol

Task performance is measured after training by replaying each checkpoint over 512 held-out episodes
(64 parallel environments) with the evaluation utility `eval_success.py`, which reuses the
environment's own lift and goal definitions so the reported success is consistent with the reward. A
*lift success* is recorded when the cube is raised more than 0.1 m above the table, and a *goal-reach
success* when the lifted cube is additionally brought within 1 cm of the commanded goal pose, the
goal position being transformed into the world frame from the robot base frame exactly as in the
reward computation. Alongside success, the benchmark reports the final mean reward, the
singularity-violation rate and mean per-step safety cost logged by the environment for both agents,
and, for the constrained agent, the terminal multiplier and the episodic-cost trajectory that
document the Lagrangian dynamics. The resulting comparison is presented in the Results chapter.
