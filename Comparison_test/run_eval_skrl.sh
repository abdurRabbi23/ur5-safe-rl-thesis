#!/usr/bin/env bash
# =====================================================================================
# Evaluate lift / goal-reach success for the three skrl checkpoints of one algorithm.
#
# The skrl twin of run_eval_success.sh, and it follows the SAME fairness protocol:
#   - 512 episodes per checkpoint
#   - frozen policies, deterministic (mean) actions
#   - FIXED eval seed 42 for every policy, so all of them are graded on identical cube
#     spawns; the training seed only labels the run.
# Results append to the same two files as the rsl_rl evals, so one table holds both:
#   ur5_grasp/tools/eval_success_report.txt
#   ur5_grasp/tools/eval_success_results.csv
#
#   Usage, from inside Comparison_test/ :
#       ./run_eval_skrl.sh            # PPO bridge
#       ./run_eval_skrl.sh SAC
# =====================================================================================

set -uo pipefail          # NOT -e: one bad checkpoint must not cancel the others.
cd "$(dirname "$0")"

readonly ALGO="${1:-PPO}"
readonly ALGO_LC="$(echo "$ALGO" | tr '[:upper:]' '[:lower:]')"
readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly EXPDIR="ur5e_lift_skrl"
readonly EPISODES=512
readonly EVAL_SEED=42
readonly NUM_ENVS=64

fail=0

eval_one() {
    local label="$1"; shift

    local dir; dir=$(ls -1dt "logs/skrl/$EXPDIR/"*"_$label" 2>/dev/null | head -n1)
    if [[ -z "$dir" ]]; then
        echo "!! SKIP $label — no run directory under logs/skrl/$EXPDIR/"
        fail=$((fail + 1)); return
    fi
    # Highest-numbered agent_*.pt = end of training. Deliberately NOT best_agent.pt:
    # the rsl_rl side was scored on its final checkpoint, and "best" is selected on
    # training reward, which is a different and more flattering criterion.
    local ckpt; ckpt=$(ls -1v "$dir"/checkpoints/agent_*.pt 2>/dev/null | tail -n1)
    if [[ -z "$ckpt" ]]; then
        echo "!! SKIP $label — no agent_*.pt in $dir/checkpoints/"
        fail=$((fail + 1)); return
    fi

    echo "=== eval $label  ($(basename "$ckpt")) ==="
    # Not piped — the script writes its own flushed report.
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/eval_success_skrl.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS" \
        --algorithm "$ALGO" --episodes "$EPISODES" --seed "$EVAL_SEED" \
        --checkpoint "$ckpt" --label "$label" "$@"
    local rc=$?
    [[ $rc -ne 0 ]] && { echo "!! $label exited $rc"; fail=$((fail + 1)); }
}

for s in 1 2 3; do eval_one "skrl_${ALGO_LC}_s${s}"; done

echo
echo "======================================================================"
if [[ $fail -eq 0 ]]; then echo " ALL 3 EVALS OK"; else echo " $fail of 3 EVALS FAILED"; fi
echo " report : ur5_grasp/tools/eval_success_report.txt"
echo " csv    : ur5_grasp/tools/eval_success_results.csv"
echo "======================================================================"
exit "$fail"
