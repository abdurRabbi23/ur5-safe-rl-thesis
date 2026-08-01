#!/usr/bin/env bash
# =====================================================================================
# EVALUATION SWEEP — matrix v2, 3-arm / 10-seed PARTIAL BATCH.   Authored 2026-08-01.
#
# Scoped copy of run_eval_policy_v2.sh for the ppo/ctrl/cppo batch trained against
# commit 567e4c0 (tag matrix-v2), seeds 1-5 and 50-54. Deliberately NOT a superset of
# run_eval_policy_v2.sh: this one skips cppo10 and sac, which have no checkpoints in
# this batch (running them would just produce spurious SKIP/FAILED noise). When the
# full 5-arm matrix is eventually trained, use run_eval_policy_v2.sh instead — do not
# extend this file to cover it.
#
# eval_policy.py itself is unchanged: it already records constraint violations
# PER EPISODE, PER STEP, for the whole evaluation -- not just a pass/fail summary.
# Each row of ur5_grasp/tools/eval_episodes/<label>_seed<seed>.csv is one episode:
#   sing_frac / joint_frac / coll_frac  -- FRACTION OF STEPS in that episode spent in
#                                          violation of the singularity / joint-limit /
#                                          collision constraint (0.0-1.0)
#   sing_any  / joint_any / coll_any    -- did the episode touch that constraint at all
#                                          (derived from the _frac columns: > 0.0)
#   min_w                                -- worst (lowest) manipulability reached
#   cost_sum                             -- total undiscounted episodic safety cost,
#                                          directly comparable to cost_limit=25
# So the full within-episode violation record survives to the CSV; nothing is lost to
# a single averaged number. See eval_policy.py's own docstring for the complete list.
#
# THE ARMS, AND THE COMPARISONS THEY LICENSE (unchanged from the audit, ALGORITHM_AUDIT.md §4)
# -------------------------------------------------------------------------------------
#   ppo   vs  ctrl   -> cost of merely attaching a cost critic. Confirmed NULL at the
#                       training-scalar level already (checkpoint-hash verified,
#                       MATRIX_V2_PARTIAL_3ARM report) -- this eval re-checks it on the
#                       frozen deterministic policy, where it matters for the thesis claim.
#   ctrl  vs  cppo   -> the effect of the cost_limit=25 constraint, everything else fixed.
#                       This is the only safe-RL reading this 3-arm batch licenses.
#                       cppo10 vs ctrl (an ACTIVELY binding budget) is NOT in this batch.
#
# COST: 3 arms x 10 seeds x 3 eval seeds = 90 launches at ~1 min startup each (Isaac
# boot dominates, not the 1000 episodes/launch). Budget ~1.5-2h.
#
# USAGE (from inside Comparison_test/):
#   ./run_eval_matrix_v2_3arm.sh
# =====================================================================================

set -uo pipefail          # NOT -e: one bad checkpoint must not cancel the rest.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EPISODES=1000         # Original audit Step-8 protocol (episodes scored per
                                # checkpoint x eval-seed). Note: eval_policy.py has no
                                # --max_iterations flag -- that's train.py's, training-loop-only.
readonly NUM_ENVS=128
readonly EVAL_SEEDS=(101 102 103)
readonly TRAIN_SEEDS=(1 2 3 4 5 50 51 52 53 54)

fail=0
ran=0

# --- PREFLIGHT (same two checks as run_eval_policy_v2.sh — see that file for the two
# failures each one was added for; not duplicating the explanation here)
PREFLIGHT_LOG="ur5_grasp/tools/eval_policy_preflight.txt"
mkdir -p "$(dirname "$PREFLIGHT_LOG")"
echo "=== preflight 1/2: importing eval_policy.py (no Isaac) ==="
if ! ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py --help > "$PREFLIGHT_LOG" 2>&1; then
    echo "!! PREFLIGHT FAILED — eval_policy.py cannot even be imported. Sweep aborted."
    tail -n 30 "$PREFLIGHT_LOG"
    exit 1
fi
echo "   OK"

echo "=== preflight 2/2: torch InferenceMode accumulator contract ==="
if ! ../IsaacLab/isaaclab.sh -p - >> "$PREFLIGHT_LOG" 2>&1 <<'PYEOF'
import torch
n = 4
ep_len, sing_ct = torch.zeros(n), torch.zeros(n)
min_w = torch.full((n,), float("inf"))
max_z = torch.full((n,), -float("inf"))
for _ in range(3):
    with torch.inference_mode():
        w, z = torch.rand(n), torch.rand(n)
        sing_ct += (w < 0.5).float()
        ep_len += 1.0
        min_w.copy_(torch.minimum(min_w, w))
        max_z.copy_(torch.maximum(max_z, z))
    done = torch.tensor([0, 2])
    ep_len[done] = 0.0; sing_ct[done] = 0.0
    min_w[done] = float("inf"); max_z[done] = -float("inf")
assert not min_w.is_inference() and not max_z.is_inference() and not sing_ct.is_inference()
print("[preflight] InferenceMode accumulator contract OK")
PYEOF
then
    echo "!! PREFLIGHT FAILED — the InferenceMode accumulator pattern is still broken."
    tail -n 30 "$PREFLIGHT_LOG"
    exit 1
fi
echo "   OK"
echo

# eval_one <log_root> <experiment_dir> <label> <ckpt_glob> <backend> [extra args...]
# NOTE on checkpoint selection: `ls -1dt ... | head -n1` sorts candidate run dirs by
# MODIFICATION TIME (newest first). ur5e_lift_cppo/ still contains 3 superseded
# pre-audit runs (2026-07-30, cppo_s1/s2/s3, gradient-clip-bug era) alongside the new
# ones under the SAME label. The -t sort means the newer (2026-08-01) run wins
# automatically -- verified this resolves correctly before relying on it. Still,
# archive the old 3 dirs out of logs/rsl_rl/ur5e_lift_cppo/ when convenient; don't
# keep depending on mtime ordering for correctness longer than necessary.
eval_one() {
    local root="$1"; shift
    local exp="$1"; shift
    local label="$1"; shift
    local glob="$1"; shift
    local backend="$1"; shift

    local dir; dir=$(ls -1dt "logs/$root/$exp/"*"$label" 2>/dev/null | head -n1)
    if [[ -z "$dir" ]]; then
        echo "!! SKIP $label — no run directory under logs/$root/$exp/"
        fail=$((fail + 1)); return
    fi
    local ckpt; ckpt=$(ls -1v "$dir"/$glob "$dir"/checkpoints/$glob 2>/dev/null | tail -n1)
    if [[ -z "$ckpt" ]]; then
        echo "!! SKIP $label — no checkpoint matching '$glob' in $dir"
        fail=$((fail + 1)); return
    fi

    for s in "${EVAL_SEEDS[@]}"; do
        echo "=== eval $label  eval-seed $s  (dir=$(basename "$dir")  ckpt=$(basename "$ckpt")) ==="
        # Never piped — the script writes its own flushed report.
        ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py \
            --task "$TASK" --headless --num_envs "$NUM_ENVS" \
            --episodes "$EPISODES" --seed "$s" \
            --backend "$backend" --checkpoint "$ckpt" --label "$label" "$@"
        local rc=$?
        ran=$((ran + 1))
        [[ $rc -ne 0 ]] && { echo "!! $label eval-seed $s exited $rc"; fail=$((fail + 1)); }
    done
}

# --- the three arms in this batch -----------------------------------------------------
# NOTE the --agent flag on ctrl/cppo. It selects BOTH the runner class (LagrangianRunner)
# and the policy class (ActorCriticCost). Omit it and the checkpoint load fails on
# missing cost_critic.* keys.
for s in "${TRAIN_SEEDS[@]}"; do
    eval_one rsl_rl ur5e_lift        "ppo_s${s}"    "model_*.pt" rsl_rl
done
for s in "${TRAIN_SEEDS[@]}"; do
    eval_one rsl_rl ur5e_lift_ctrl   "ctrl_s${s}"   "model_*.pt" rsl_rl \
        --agent rsl_rl_ctrl_cfg_entry_point
done
for s in "${TRAIN_SEEDS[@]}"; do
    eval_one rsl_rl ur5e_lift_cppo   "cppo_s${s}"   "model_*.pt" rsl_rl \
        --agent rsl_rl_cppo_cfg_entry_point
done

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL $ran EVALS OK"; else echo " $fail of $ran EVALS FAILED"; fi
echo " report       : ur5_grasp/tools/eval_policy_report.txt"
echo " summary csv  : ur5_grasp/tools/eval_policy_results.csv"
echo " episode csvs : ur5_grasp/tools/eval_episodes/  (per-episode violation record)"
echo
echo " FIRST THING TO READ, before any table: is ppo-vs-ctrl still null under eval?"
echo " (It was null at the training-scalar level, checkpoint-hash confirmed. This is"
echo " the frozen-policy re-check — it SHOULD also be null. If it is not, stop and"
echo " report that before trusting any cppo-vs-ctrl number.)"
echo "======================================================================"
exit "$fail"
