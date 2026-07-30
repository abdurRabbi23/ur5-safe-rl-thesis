#!/usr/bin/env bash
# =====================================================================================
# Evaluate lift / goal-reach success for all six matrix checkpoints.
#
# There is NO success scalar logged during training — the headline "100% lift" claim comes
# only from this script. Run it after run_ppo_cppo_seeds.sh.
#
# Protocol (03c "Fairness protocol"):
#   - 512 episodes per checkpoint
#   - frozen policies
#   - mean +- std reported over the three seeds
#
# FIXED EVAL SEED. Every policy is scored on the SAME cube spawns (--seed 42 for all six),
# not on its own training seed. Otherwise each policy would be graded on a different exam
# and the seed-to-seed spread would mix policy quality with luck of the draw. The training
# seed still distinguishes the runs; it is recorded in the CSV.
#
# Results land in (both APPENDED, so re-runs accumulate rather than overwrite):
#   ur5_grasp/tools/eval_success_report.txt    <- readable
#   ur5_grasp/tools/eval_success_results.csv   <- one row per checkpoint
# =====================================================================================

set -uo pipefail          # NOT -e: one bad checkpoint must not cancel the other five.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EPISODES=512
readonly EVAL_SEED=42
readonly NUM_ENVS=64

fail=0

# eval_one <experiment_dir> <run_name_suffix> [extra args...]
eval_one() {
    local exp="$1"; shift
    local label="$1"; shift

    # newest run dir ending in this label; then its final checkpoint
    local dir; dir=$(ls -1dt "logs/rsl_rl/$exp/"*"_$label" 2>/dev/null | head -n1)
    if [[ -z "$dir" ]]; then
        echo "!! SKIP $label — no run directory under logs/rsl_rl/$exp/"
        fail=$((fail + 1)); return
    fi
    local ckpt="$dir/model_1499.pt"
    if [[ ! -f "$ckpt" ]]; then
        ckpt=$(ls -1v "$dir"/model_*.pt 2>/dev/null | tail -n1)
    fi
    if [[ -z "$ckpt" ]]; then
        echo "!! SKIP $label — no checkpoint in $dir"
        fail=$((fail + 1)); return
    fi

    echo "=== eval $label  ($(basename "$ckpt")) ==="
    # Not piped — see the standing rule; the script writes its own flushed report.
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_success.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS" \
        --episodes "$EPISODES" --seed "$EVAL_SEED" \
        --checkpoint "$ckpt" --label "$label" "$@"
    local rc=$?
    [[ $rc -ne 0 ]] && { echo "!! $label exited $rc"; fail=$((fail + 1)); }
}

for s in 1 2 3; do eval_one "ur5e_lift"      "ppo_s${s}"; done
for s in 1 2 3; do eval_one "ur5e_lift_cppo" "cppo_s${s}" --agent rsl_rl_cppo_cfg_entry_point; done

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL 6 EVALS OK"; else echo " $fail of 6 EVALS FAILED"; fi
echo " report : ur5_grasp/tools/eval_success_report.txt"
echo " csv    : ur5_grasp/tools/eval_success_results.csv"
echo "======================================================================"
exit "$fail"
