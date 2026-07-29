#!/usr/bin/env bash
# =====================================================================================
# Layer 1 comparative benchmark — PPO x3 + cPPO x3 on the FROZEN WELD env.
#
# Target task: Isaac-Lift-Cube-UR5e-v0  (UR5e + Robotiq 2f-85, proximity-weld grasp).
#
#   Day 22 (2026-07-30) decision: the matrix runs on -v0, NOT on -SimpleGripper-v0.
#   -v0 is the frozen, tagged, already-validated Layer-1 env; the SimpleGripper is
#   kept as a separate demonstrated contact-grasp result, smoke-trained only.
#   See logbook/09_comparison_test.md.
#
# Run this ON THE GPU WORKSTATION (Isaac Sim + CUDA), from inside "Comparison test/"
# as cwd. The folder name contains a space — every path here is quoted.
#
# -------------------------------------------------------------------------------------
# WHY THIS IS NOT `set -e` AROUND THE LOOP  (changed 2026-07-30, Day 22)
# -------------------------------------------------------------------------------------
# The previous version had `set -euo pipefail` covering the whole file. In a six-run
# overnight batch that means one bad run silently cancels the five that follow, and you
# come back to a third of a matrix with no record of which run died or why. Exit codes
# are now captured per run and the batch always continues. Failures are counted and
# reported at the end, and the exit status of the SCRIPT reflects whether all six passed.
#
# -------------------------------------------------------------------------------------
# WHY IT VERIFIES CHECKPOINTS INSTEAD OF CAPTURING STDOUT
# -------------------------------------------------------------------------------------
# Standing rule in this project (four demonstrated failures, run_log_new.md Day 21-22):
# piping an Isaac script's stdout causes block-buffering that `simulation_app.close()`
# then discards, so `| tee` LOSES the output it was added to capture. This script
# therefore never pipes a training run. It checks the artefacts rsl_rl writes to disk
# continuously — the run directory and the final checkpoint — which is evidence that
# cannot be buffered away.
#
# Read the result afterwards from:
#   logs/batch_report.txt                       <- written by this script
#   ur5_grasp/tools/summarize_runs_report.txt   <- written by summarize_runs.py
# =====================================================================================

set -uo pipefail          # NOT -e: see the note above.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly NUM_ENVS=4096
readonly SEEDS=(1 2 3)
readonly REPORT="logs/batch_report.txt"

mkdir -p logs

# --- flushed logging: every line hits disk immediately -------------------------------
log() {
    printf '%s\n' "$*" | tee -a "$REPORT"
}

# `tee` is safe HERE (plain bash echo, no Isaac process, nothing to block-buffer);
# it is training runs specifically that must never be piped.

: > "$REPORT"
log "======================================================================"
log " PPO x3 + cPPO x3  ---  task: $TASK   num_envs: $NUM_ENVS"
log " started : $(date -Is)"
log " host    : $(hostname)"
log " cwd     : $(pwd)"
log " git     : $(git rev-parse --short HEAD 2>/dev/null || echo '(not a git repo)')"
log " dirty   : $(git status --porcelain 2>/dev/null | wc -l) modified/untracked path(s)"
log "======================================================================"
log ""

fail_count=0
run_index=0

# ---------------------------------------------------------------------------------
# run_one <experiment_name> <run_name> <seed> [extra args ...]
#   experiment_name must match the agent cfg's `experiment_name`, because that is the
#   directory rsl_rl creates:  logs/rsl_rl/<experiment_name>/<timestamp>_<run_name>/
# ---------------------------------------------------------------------------------
run_one() {
    local exp="$1"; shift
    local run_name="$1"; shift
    local seed="$1"; shift

    run_index=$((run_index + 1))
    local started_epoch; started_epoch=$(date +%s)

    log "--- [$run_index/6] $run_name  (exp=$exp, seed=$seed)  start $(date -Is)"

    # NOT piped. See the header note.
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS" \
        --seed "$seed" --run_name "$run_name" "$@"
    local rc=$?

    local elapsed=$(( $(date +%s) - started_epoch ))
    local mins=$(( elapsed / 60 ))

    # Newest run directory whose name ends in this run_name.
    local dir
    dir=$(ls -1dt "logs/rsl_rl/$exp/"*"_$run_name" 2>/dev/null | head -n1)

    if [[ $rc -ne 0 ]]; then
        log "    RESULT: FAILED (train.py exit code $rc) after ${mins} min"
        [[ -n "$dir" ]] && log "    partial run dir: $dir"
        fail_count=$((fail_count + 1))
        return
    fi

    if [[ -z "$dir" ]]; then
        log "    RESULT: FAILED — exit code 0 but no run directory under logs/rsl_rl/$exp/"
        log "             (expected a dir matching '*_$run_name'; check experiment_name)"
        fail_count=$((fail_count + 1))
        return
    fi

    local n_ckpt; n_ckpt=$(ls -1 "$dir"/model_*.pt 2>/dev/null | wc -l)
    local last_ckpt; last_ckpt=$(ls -1v "$dir"/model_*.pt 2>/dev/null | tail -n1)
    local n_events; n_events=$(ls -1 "$dir"/events.out.tfevents.* 2>/dev/null | wc -l)

    if [[ "$n_ckpt" -eq 0 ]]; then
        log "    RESULT: FAILED — run dir exists but holds no checkpoint"
        log "             dir: $dir"
        fail_count=$((fail_count + 1))
        return
    fi

    log "    RESULT: OK   ${mins} min   checkpoints: $n_ckpt   tb event files: $n_events"
    log "    dir      : $dir"
    log "    last ckpt: ${last_ckpt:-none}"
}

# ---------------------------------------------------------------------------------
# PPO x3 — stock rsl_rl PPO, experiment_name "ur5e_lift"
# ---------------------------------------------------------------------------------
log "=== PPO (unconstrained baseline) ==="
for seed in "${SEEDS[@]}"; do
    run_one "ur5e_lift" "ppo_s${seed}" "$seed"
done
log ""

# ---------------------------------------------------------------------------------
# cPPO x3 — PPO-Lagrangian. `--agent rsl_rl_cppo_cfg_entry_point` also switches the
# runner to LagrangianRunner via agent_cfg.class_name. experiment_name "ur5e_lift_cppo".
# ---------------------------------------------------------------------------------
log "=== cPPO (PPO-Lagrangian, the contribution) ==="
for seed in "${SEEDS[@]}"; do
    run_one "ur5e_lift_cppo" "cppo_s${seed}" "$seed" --agent rsl_rl_cppo_cfg_entry_point
done
log ""

log "======================================================================"
log " finished: $(date -Is)"
if [[ $fail_count -eq 0 ]]; then
    log " ALL 6 RUNS OK"
else
    log " $fail_count of 6 RUNS FAILED — see the RESULT lines above"
fi
log ""
log " Next: ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py"
log "======================================================================"

exit "$fail_count"
