#!/usr/bin/env bash
# =====================================================================================
# Evaluation sweep: every checkpoint x every eval seed, with SAFETY COUNTED.
#
# Replaces run_eval_success.sh (Day 22). Two things changed and both matter for the thesis:
#
#   1. Safety is now measured HERE, on the frozen deterministic policy, instead of being
#      read off the training TensorBoard scalars. The old singularity / joint-limit numbers
#      in LAYER1_RESULTS_3seed.md were tail-means over the last 10% of TRAINING iterations
#      — a still-learning policy with exploration noise on. They cannot support a claim
#      about the final policy. Everything reported from here does.
#
#   2. Three eval seeds (101/102/103 — deliberately disjoint from the training seeds 1/2/3)
#      instead of one, 1000 episodes each. The old protocol was a single
#      eval seed, so "PPO seed 2 scored 0.00%" had no error bar of its own — there was no
#      way to tell a bad policy from a bad exam. Three seeds x 1000 episodes gives a
#      mean +- sd per checkpoint over the EVAL draw, separately from the sd over the
#      three TRAINING seeds. Those are two different sources of variance and the thesis
#      needs them apart.
#
#   3. Harder, better-posed success rules (Touhid, Day 23):
#        goal-reach bound  = 1 cm          (was 5 cm)
#        lift success      = cube reaches >= 50% of the episode's COMMANDED goal height
#                            (was a flat 4 cm, which sits ~2 cm above the cube's resting
#                            height and so read 100% for every policy in the Day-22 table)
#      Both are defaults inside eval_policy.py; they are restated here so this file alone
#      documents the protocol. Change them in ONE place — the script — not here.
#
# Cost: 18 launches (6 ckpt x 3 seeds) at ~1 min each, dominated by Isaac startup, not by
# the rollouts (1000 episodes at 128 envs is ~2000 sim steps).
#
# Results land in (all APPENDED, so re-runs accumulate rather than overwrite):
#   ur5_grasp/tools/eval_policy_report.txt     <- readable
#   ur5_grasp/tools/eval_policy_results.csv    <- one row per (checkpoint, eval seed)
#   ur5_grasp/tools/eval_episodes/*.csv        <- one row per EPISODE (the distribution)
#
# Usage:
#   ./run_eval_policy.sh                 # rsl_rl only: PPO x3 + cPPO x3
#   ./run_eval_policy.sh skrl            # also score skrl runs, once they exist
# =====================================================================================

set -uo pipefail          # NOT -e: one bad checkpoint must not cancel the other 23.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EPISODES=1000
readonly NUM_ENVS=128
readonly EVAL_SEEDS=(101 102 103)
# DELIBERATELY DISJOINT FROM THE TRAINING SEEDS (1/2/3). These fix the cube SPAWNS during
# evaluation; every eval seed scores ALL six checkpoints. An earlier draft used 1/2/3 here
# and that was a mistake: "ppo_s1 @ seed 1" invites reading a pairing that does not exist,
# and it also puts the eval draw on the same RNG stream the policy was trained against.
# Three digits, no overlap, no ambiguity. If you change these, keep them >= 100.

WITH_SKRL="${1:-}"
fail=0
ran=0

# --- PREFLIGHT -----------------------------------------------------------------------
# Added after the Day-23 first sweep reported "18 of 18 EVALS FAILED" with NO report file
# and no error text anywhere. Cause: a duplicate --checkpoint argparse declaration, which
# raises at IMPORT time — before eval_policy.py opens its flushed report — so all 18
# launches died identically and invisibly. The standing "always write a flushed report"
# rule cannot cover a crash that happens before the report exists. This does.
#
# `--help` exits inside argparse, before AppLauncher, so Isaac never boots: ~2 s.
# stderr is redirected to a FILE, not a pipe. That is safe here precisely because no
# simulation_app is ever created, so there is no close() to discard the buffer.
PREFLIGHT_LOG="ur5_grasp/tools/eval_policy_preflight.txt"
mkdir -p "$(dirname "$PREFLIGHT_LOG")"
echo "=== preflight: importing eval_policy.py (no Isaac) ==="
if ! ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py --help > "$PREFLIGHT_LOG" 2>&1; then
    echo "!! PREFLIGHT FAILED — eval_policy.py cannot even be imported. Sweep aborted."
    echo "!! Last 30 lines of $PREFLIGHT_LOG:"
    tail -n 30 "$PREFLIGHT_LOG"
    exit 1
fi
echo "   preflight 1/2 OK (imports)"

# Preflight 2: the InferenceMode accumulator contract.
# The first successful launch ran ~128 episodes and then died on
#   "Inplace update to inference tensor outside InferenceMode is not allowed"
# because an accumulator was REBOUND inside torch.inference_mode() (`min_w = torch.minimum(
# min_w, w)`), which silently turns a normal tensor into an inference tensor; the
# episode-reset line outside the block then cannot write to it. This reproduces the exact
# pattern eval_policy.py uses — in-place accumulate inside the block, reset outside — in
# ~2 s of pure torch, no Isaac. If this passes, that class of bug is gone.
echo "=== preflight: torch InferenceMode accumulator contract ==="
if ! ../IsaacLab/isaaclab.sh -p - >> "$PREFLIGHT_LOG" 2>&1 <<'PYEOF'
import torch

n = 4
ep_len = torch.zeros(n)
sing_ct = torch.zeros(n)
min_w = torch.full((n,), float("inf"))
max_z = torch.full((n,), -float("inf"))

for _ in range(3):
    with torch.inference_mode():
        w = torch.rand(n)               # stands in for cost_computer.manipulability()
        z = torch.rand(n)
        sing_ct += (w < 0.5).float()    # proven-safe idiom
        ep_len += 1.0
        min_w.copy_(torch.minimum(min_w, w))   # the fixed idiom
        max_z.copy_(torch.maximum(max_z, z))   # the fixed idiom
    # episode reset, OUTSIDE inference mode — this is where the crash used to happen
    done = torch.tensor([0, 2])
    ep_len[done] = 0.0
    sing_ct[done] = 0.0
    min_w[done] = float("inf")
    max_z[done] = -float("inf")

assert not min_w.is_inference(), "min_w became an inference tensor"
assert not max_z.is_inference(), "max_z became an inference tensor"
assert not sing_ct.is_inference(), "sing_ct became an inference tensor"
print("[preflight] InferenceMode accumulator contract OK")
PYEOF
then
    echo "!! PREFLIGHT FAILED — the InferenceMode accumulator pattern is still broken."
    echo "!! Last 30 lines of $PREFLIGHT_LOG:"
    tail -n 30 "$PREFLIGHT_LOG"
    exit 1
fi
echo "   preflight 2/2 OK (InferenceMode contract)"
# --------------------------------------------------------------------------------------

# eval_one <log_root> <experiment_dir> <label> <ckpt_glob> <backend> [extra args...]
eval_one() {
    local root="$1"; shift
    local exp="$1"; shift
    local label="$1"; shift
    local glob="$1"; shift
    local backend="$1"; shift

    # newest run dir whose name ENDS in this label
    local dir; dir=$(ls -1dt "logs/$root/$exp/"*"$label" 2>/dev/null | head -n1)
    if [[ -z "$dir" ]]; then
        echo "!! SKIP $label — no run directory under logs/$root/$exp/"
        fail=$((fail + 1)); return
    fi
    # skrl keeps checkpoints in a checkpoints/ subdir; rsl_rl writes them at the top level
    local ckpt; ckpt=$(ls -1v "$dir"/$glob "$dir"/checkpoints/$glob 2>/dev/null | tail -n1)
    if [[ -z "$ckpt" ]]; then
        echo "!! SKIP $label — no checkpoint matching '$glob' in $dir"
        fail=$((fail + 1)); return
    fi

    for s in "${EVAL_SEEDS[@]}"; do
        echo "=== eval $label  seed $s  ($(basename "$ckpt")) ==="
        # Not piped — see the standing rule; the script writes its own flushed report.
        ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py \
            --task "$TASK" --headless --num_envs "$NUM_ENVS" \
            --episodes "$EPISODES" --seed "$s" \
            --backend "$backend" --checkpoint "$ckpt" --label "$label" "$@"
        local rc=$?
        ran=$((ran + 1))
        [[ $rc -ne 0 ]] && { echo "!! $label seed $s exited $rc"; fail=$((fail + 1)); }
    done
}

for s in 1 2 3; do
    eval_one rsl_rl ur5e_lift      "ppo_s${s}"  "model_*.pt" rsl_rl
done
for s in 1 2 3; do
    eval_one rsl_rl ur5e_lift_cppo "cppo_s${s}" "model_*.pt" rsl_rl \
        --agent rsl_rl_cppo_cfg_entry_point
done

if [[ "$WITH_SKRL" == "skrl" ]]; then
    # The skrl PPO bridge. SAC joins here once skrl_sac_cfg.yaml is authored.
    # TD3 was CUT on 2026-07-31 (Day 23) — the benchmark is PPO / cPPO / SAC.
    for s in 1 2 3; do
        eval_one skrl ur5e_lift_skrl "skrl_ppo_s${s}" "agent_*.pt" skrl \
            --agent skrl_cfg_entry_point
    done
fi

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL $ran EVALS OK"; else echo " $fail of $ran EVALS FAILED"; fi
echo " report       : ur5_grasp/tools/eval_policy_report.txt"
echo " summary csv  : ur5_grasp/tools/eval_policy_results.csv"
echo " episode csvs : ur5_grasp/tools/eval_episodes/"
echo "======================================================================"
exit "$fail"
