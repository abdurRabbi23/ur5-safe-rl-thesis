#!/usr/bin/env bash
# =====================================================================================
# EVALUATION SWEEP v2 — scores the post-audit matrix.   Authored 2026-07-31 (Day 23).
#
# Supersedes run_eval_policy.sh, which covered 2 arms x 3 seeds. This covers 5 arms x 5
# seeds. Everything else about the protocol is unchanged and deliberately so — read the
# header of run_eval_policy.sh for why safety is measured HERE (on the frozen deterministic
# policy) rather than read off training TensorBoard scalars, and why the eval seeds are
# >= 100 and disjoint from the training seeds.
#
# THE ARMS, AND THE COMPARISONS THEY LICENCE
# -------------------------------------------------------------------------------------
#   ppo     vs  ctrl     -> the cost of attaching a cost critic. SHOULD BE NULL after the
#                           Day-23 gradient-clipping fix. If it is not null, do not report
#                           any cPPO-vs-PPO number: something still couples the heads.
#   ctrl    vs  cppo     -> the effect of a constraint that (probably) never binds.
#   ctrl    vs  cppo10   -> the effect of a constraint that DOES bind. THIS IS THE THESIS
#                           CLAIM. Not cppo-vs-ppo, which mixes the constraint with
#                           whatever the extra critic does.
#   ppo/cppo vs sac      -> algorithm-family comparison. Matched on gradient steps, NOT on
#                           environment samples. Say so in the table caption.
#
# COST: 5 arms x 5 seeds x 3 eval seeds = 75 launches at ~1 min each (Isaac startup
# dominates, not the 1000 episodes). Budget ~90 minutes.
#
# USAGE (from inside Comparison_test/):
#   ./run_eval_policy_v2.sh            # rsl_rl arms only (20 checkpoints, 60 launches)
#   ./run_eval_policy_v2.sh sac        # also score SAC (adds 15 launches)
# =====================================================================================

set -uo pipefail          # NOT -e: one bad checkpoint must not cancel the other 74.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EPISODES=1000
readonly NUM_ENVS=128
readonly EVAL_SEEDS=(101 102 103)
readonly TRAIN_SEEDS=(1 2 3 4 5)

WITH_SKRL="${1:-}"
fail=0
ran=0

# --- PREFLIGHT (unchanged from v1 — see that file for the two failures it was added for)
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
        echo "=== eval $label  eval-seed $s  ($(basename "$ckpt")) ==="
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

# --- the four rsl_rl arms ------------------------------------------------------------
# NOTE the --agent flag on every non-PPO arm. It selects BOTH the runner class
# (LagrangianRunner) and the policy class (ActorCriticCost). Omit it and the checkpoint
# load fails on missing cost_critic.* keys — a loud failure, but an avoidable one.
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
for s in "${TRAIN_SEEDS[@]}"; do
    eval_one rsl_rl ur5e_lift_cppo10 "cppo10_s${s}" "model_*.pt" rsl_rl \
        --agent rsl_rl_cppo10_cfg_entry_point
done

# --- SAC -----------------------------------------------------------------------------
if [[ "$WITH_SKRL" == "sac" || "$WITH_SKRL" == "skrl" ]]; then
    for s in "${TRAIN_SEEDS[@]}"; do
        eval_one skrl ur5e_lift_sac "sac_s${s}" "agent_*.pt" skrl \
            --agent skrl_sac_cfg_entry_point
    done
fi

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL $ran EVALS OK"; else echo " $fail of $ran EVALS FAILED"; fi
echo " report       : ur5_grasp/tools/eval_policy_report.txt"
echo " summary csv  : ur5_grasp/tools/eval_policy_results.csv"
echo " episode csvs : ur5_grasp/tools/eval_episodes/"
echo
echo " FIRST THING TO READ, before any table: is ppo-vs-ctrl null?"
echo " If ctrl differs materially from ppo, the audit is incomplete — stop and report that."
echo "======================================================================"
exit "$fail"
