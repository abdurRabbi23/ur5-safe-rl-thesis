# Module 03 — Safety Constraints + cPPO vs PPO (Layer 1 deliverable)

Status: ▶ next (not started)
Chat type: safe-RL / benchmarking
Last updated: 2026-07-12 (Day 7)

## Goal
The must-pass Layer 1 contribution: add hard safety constraints to the grasp env and
train constrained PPO (Lagrangian CMDP), then benchmark **cPPO vs unconstrained PPO** —
showing cPPO respects safety limits while still learning to grasp.

## Scope (to define at the start of this work)
- Constraints to encode as costs: self/table collision, joint-limit proximity, Jacobian
  singularity (manipulability floor), and — once IBVS is in — field-of-view loss.
- cPPO via **OmniSafe** (Lagrangian) or an skrl/rsl_rl constrained variant — decide and
  justify.
- Metrics: success rate, sample efficiency, and constraint-violation rate/cost. Overlay
  cPPO vs PPO curves in TensorBoard (same `--logdir` parent).

## Starting point
- Working PPO baseline + env from Module 02 (checkpoint + curves to compare against).
- Add cost terms to the env; keep the PPO baseline unchanged as the control.

## Open questions
- Which constrained-RL library integrates cleanest with Isaac Lab 2.3 (OmniSafe vs skrl)?
- Constraint thresholds (joint-limit margin, manipulability floor) — pick defensible values.

## Next steps
1. Decide constrained-RL library + define the cost/constraint set.
2. Implement cost terms in the env; add a cPPO agent config.
3. Run cPPO vs PPO; collect success + violation metrics; write up.

## run_log.md refs
(to be added)
