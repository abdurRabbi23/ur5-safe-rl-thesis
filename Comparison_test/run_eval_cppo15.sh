#!/usr/bin/env bash
# =====================================================================================
# EVALUATION — cppo15 arm only. Authored 2026-08-01 (Day 24, cont. 2).
#
# Scoped copy of run_eval_matrix_v2_3arm.sh's pattern, deliberately NOT reused unmodified
# (Touhid's instruction — that script is scoped to ppo/ctrl/cppo and has no cppo15 case).
# ctrl and cppo(25) are already evaluated in eval_policy_results.csv from the prior batch —
# this script only adds the 30 new (cppo15 x 10 seeds x 3 eval-seeds) rows. Do not re-run
# ctrl/cppo here; the comparison this arm licenses (cppo15 vs ctrl) reads the existing rows
# for ctrl and only needs fresh rows for cppo15.
#
# Same protocol as the prior batch, for direct comparability: eval seeds 101/102/103,
# 1000 episodes each, num_envs=128, deterministic policy.
#
# eval_policy_results.csv is APPEND-ONLY (confirmed the hard way once already — 20 stale
# rows from an old sweep). Filter any analysis by checkpoint path date
# (grep 2026-08-01.*cppo15), never by the "cppo15" label alone.
#
# USAGE (from inside Comparison_test/):
#   ./run_eval_cppo15.sh
# =====================================================================================

set -uo pipefail
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EPISODES=1000
readonly NUM_ENVS=128
readonly EVAL_SEEDS=(101 102 103)
readonly TRAIN_SEEDS=(1 2 3 4 5 50 51 52 53 54)

fail=0
ran=0

PREFLIGHT_LOG="ur5_grasp/tools/eval_policy_preflight_cppo15.txt"
mkdir -p "$(dirname "$PREFLIGHT_LOG")"
echo "=== preflight: importing eval_policy.py (no Isaac) ==="
if ! ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py --help > "$PREFLIGHT_LOG" 2>&1; then
    echo "!! PREFLIGHT FAILED — eval_policy.py cannot even be imported. Sweep aborted."
    tail -n 30 "$PREFLIGHT_LOG"
    exit 1
fi
echo "   OK"
echo

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
        ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_policy.py \
            --task "$TASK" --headless --num_envs "$NUM_ENVS" \
            --episodes "$EPISODES" --seed "$s" \
            --backend "$backend" --checkpoint "$ckpt" --label "$label" "$@"
        local rc=$?
        ran=$((ran + 1))
        [[ $rc -ne 0 ]] && { echo "!! $label eval-seed $s exited $rc"; fail=$((fail + 1)); }
    done
}

for s in "${TRAIN_SEEDS[@]}"; do
    eval_one rsl_rl ur5e_lift_cppo15 "cppo15_s${s}" "model_*.pt" rsl_rl \
        --agent rsl_rl_cppo15_cfg_entry_point
done

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL $ran EVALS OK"; else echo " $fail of $ran EVALS FAILED"; fi
echo " report       : ur5_grasp/tools/eval_policy_report.txt (appended)"
echo " summary csv  : ur5_grasp/tools/eval_policy_results.csv (appended — filter by date!)"
echo " episode csvs : ur5_grasp/tools/eval_episodes/cppo15_s*_seed*.csv"
echo
echo " ctrl's rows for the cppo15-vs-ctrl comparison already exist in eval_policy_results.csv"
echo " from the prior batch (checkpoint dates 2026-08-01, label ctrl_s*) — no need to re-eval."
echo "======================================================================"
exit "$fail"
