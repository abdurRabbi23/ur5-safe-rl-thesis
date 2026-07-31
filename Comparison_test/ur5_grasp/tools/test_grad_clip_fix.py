# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Regression test for AUDIT finding A1 — the gradient-clipping asymmetry.

Pure torch. No Isaac, no GPU, no env. Runs in ~2 seconds:

    cd ~/Abdur_Rabbi_THESIS/Comparison_test
    ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/test_grad_clip_fix.py

WHAT IT PROVES

  Test 1  The bug was real and is quantified.
          One global clip_grad_norm_ over (actor + reward critic + cost critic) does NOT
          leave the actor's gradients equal to what a two-group clip gives them. The test
          prints the actual shrink factor the actor suffered. This is the mechanism by
          which cPPO ran a smaller effective step size than PPO on every update, including
          the ~100% of updates where lambda was exactly 0.

  Test 2  The fix restores baseline-identical treatment.
          With the two-group clip, the actor's post-clip gradients are bitwise identical to
          what stock PPO would produce for the same actor loss -- i.e. the presence of the
          cost critic no longer perturbs the baseline half of the network.

  Test 3  The Lagrangian surrogate collapses to PPO at lambda = 0.
          adv = (A_r - lambda*A_c)/(1 + lambda) == A_r exactly when lambda == 0.
          This is the algebraic step the whole audit rests on, checked numerically rather
          than asserted.

If any test FAILS, do not launch the matrix -- the arms are not comparable.
"""

from __future__ import annotations

import torch
import torch.nn as nn

torch.manual_seed(0)

PASS = "PASS"
FAIL = "FAIL"
failures = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global failures
    if not ok:
        failures += 1
    print(f"  [{PASS if ok else FAIL}] {name}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {line}")


def make_heads():
    """Actor + reward critic + cost critic, sized like the real policy ([256,128,64])."""
    obs, act = 31, 7
    actor = nn.Sequential(nn.Linear(obs, 256), nn.ELU(), nn.Linear(256, 128), nn.ELU(),
                          nn.Linear(128, 64), nn.ELU(), nn.Linear(64, act))
    critic = nn.Sequential(nn.Linear(obs, 256), nn.ELU(), nn.Linear(256, 128), nn.ELU(),
                           nn.Linear(128, 64), nn.ELU(), nn.Linear(64, 1))
    cost_critic = nn.Sequential(nn.Linear(obs, 256), nn.ELU(), nn.Linear(256, 128), nn.ELU(),
                                nn.Linear(128, 64), nn.ELU(), nn.Linear(64, 1))
    return actor, critic, cost_critic


def build_grads(scale_cost: float = 1.0):
    """Populate .grad on all three heads from a single backward, as the real update does."""
    actor, critic, cost_critic = make_heads()
    obs = torch.randn(4096, 31)

    surrogate = -actor(obs).mean()
    value_loss = (critic(obs) - torch.randn(4096, 1)).pow(2).mean()
    # scale_cost stands in for "how badly the cost critic is currently fitting". Early in
    # training the cost returns are large and unfitted, so this term dominates.
    cost_value_loss = scale_cost * (cost_critic(obs) - torch.randn(4096, 1) * 10.0).pow(2).mean()

    loss = surrogate + value_loss + cost_value_loss
    loss.backward()
    return actor, critic, cost_critic


def grad_vector(module) -> torch.Tensor:
    return torch.cat([p.grad.detach().reshape(-1) for p in module.parameters()])


MAX_GRAD_NORM = 1.0

print("=" * 78)
print("AUDIT A1 regression test — gradient clipping across the cost critic")
print("=" * 78)

# --------------------------------------------------------------------------------------
# Test 1: the old behaviour perturbs the actor.
# --------------------------------------------------------------------------------------
print("\nTest 1 — one global clip DOES shrink the actor (the bug)")

a_old, c_old, cc_old = build_grads(scale_cost=1.0)
a_new, c_new, cc_new = build_grads(scale_cost=1.0)   # same seed path -> same raw grads
assert torch.allclose(grad_vector(a_old), grad_vector(a_new)), "test harness is not deterministic"

actor_raw = grad_vector(a_old).clone()

# OLD: one clip over everything, exactly as the pre-fix line did.
nn.utils.clip_grad_norm_(
    list(a_old.parameters()) + list(c_old.parameters()) + list(cc_old.parameters()), MAX_GRAD_NORM
)
actor_after_global = grad_vector(a_old).clone()

# NEW: two independent clips, exactly as the fixed code does.
nn.utils.clip_grad_norm_(list(a_new.parameters()) + list(c_new.parameters()), MAX_GRAD_NORM)
nn.utils.clip_grad_norm_(list(cc_new.parameters()), MAX_GRAD_NORM)
actor_after_split = grad_vector(a_new).clone()

shrink = (actor_after_global.norm() / actor_after_split.norm()).item()
report(
    "global clip and split clip give the actor DIFFERENT gradients",
    not torch.allclose(actor_after_global, actor_after_split, atol=1e-9),
    f"raw actor grad norm      : {actor_raw.norm():.6f}\n"
    f"after ONE global clip    : {actor_after_global.norm():.6f}\n"
    f"after TWO split clips    : {actor_after_split.norm():.6f}\n"
    f"actor step shrink factor : {shrink:.4f}x   <-- cPPO's actor was scaled by this,\n"
    f"                            every update, relative to the PPO baseline.",
)

# The effect grows with how badly the cost critic fits -- i.e. it is worst early in training,
# which is exactly when the policy's trajectory is decided.
_, _, _ = None, None, None
for s in (0.1, 1.0, 10.0):
    a1, c1, cc1 = build_grads(scale_cost=s)
    a2, c2, cc2 = build_grads(scale_cost=s)
    nn.utils.clip_grad_norm_(list(a1.parameters()) + list(c1.parameters()) + list(cc1.parameters()), MAX_GRAD_NORM)
    nn.utils.clip_grad_norm_(list(a2.parameters()) + list(c2.parameters()), MAX_GRAD_NORM)
    nn.utils.clip_grad_norm_(list(cc2.parameters()), MAX_GRAD_NORM)
    print(f"         cost-loss scale {s:5.1f}  ->  actor shrink "
          f"{(grad_vector(a1).norm() / grad_vector(a2).norm()).item():.4f}x")

# --------------------------------------------------------------------------------------
# Test 2: after the fix, the baseline half is untouched by the cost critic's presence.
# --------------------------------------------------------------------------------------
print("\nTest 2 — with the split clip, the actor matches a cost-critic-free PPO exactly")

a_ppo, c_ppo, _cc_unused = build_grads(scale_cost=1.0)
# Stock PPO: clip over actor + reward critic only, with no cost critic in the module at all.
nn.utils.clip_grad_norm_(list(a_ppo.parameters()) + list(c_ppo.parameters()), MAX_GRAD_NORM)

report(
    "split-clip actor gradients == stock-PPO actor gradients (bitwise)",
    torch.equal(grad_vector(a_ppo), actor_after_split),
    f"max abs difference: {(grad_vector(a_ppo) - actor_after_split).abs().max().item():.3e}",
)

# --------------------------------------------------------------------------------------
# Test 3: the surrogate collapses to PPO at lambda = 0.
# --------------------------------------------------------------------------------------
print("\nTest 3 — Lagrangian advantage reduces to the PPO advantage at lambda = 0")

A_r = torch.randn(4096, 1)
A_c = torch.randn(4096, 1)


def lagrangian_adv(lam: float) -> torch.Tensor:
    adv = A_r - lam * A_c
    return adv / (1.0 + lam)


report("lambda = 0    -> adv == A_reward exactly", torch.equal(lagrangian_adv(0.0), A_r))
report(
    "lambda = 0.2  -> adv != A_reward (the constraint is doing something)",
    not torch.allclose(lagrangian_adv(0.2), A_r, atol=1e-6),
    f"mean |adv - A_r| at lambda=0.20 : {(lagrangian_adv(0.2) - A_r).abs().mean().item():.4f}\n"
    f"mean |adv - A_r| at lambda=1.00 : {(lagrangian_adv(1.0) - A_r).abs().mean().item():.4f}\n"
    "For reference, the 2026-07-30 runs sat at lambda = 0.000 for essentially every\n"
    "iteration, so the top line is what the 'constrained' arm was actually computing.",
)

print("\n" + "=" * 78)
if failures:
    print(f" {failures} TEST(S) FAILED — do not launch the matrix.")
    raise SystemExit(1)
print(" ALL TESTS PASSED — the actor is no longer coupled to the cost critic by clipping.")
print("=" * 78)
