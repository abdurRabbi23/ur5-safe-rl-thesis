#!/usr/bin/env bash
# =====================================================================================
# skrl seed batch — <ALGO> x3 on the FROZEN WELD env, Isaac-Lift-Cube-UR5e-v0.
#
# The skrl half of the 4-algorithm comparison. Deliberately the same shape as
# run_ppo_cppo_seeds.sh (per-run exit codes, wall clock, verification by artefact on
# disk, never pipes a training run, does not abort the batch on one failure, exit code
# = number of failures). Read that script's header for WHY on each of those points;
# they are not repeated here.
#
#   Usage, from inside Comparison_test/ :
#       ./run_skrl_seeds.sh                    # PPO bridge, 4096 envs, 1500 iters
#       ./run_skrl_seeds.sh PPO 4096 1500
#       ./run_skrl_seeds.sh SAC  256  1500     (TD3 CUT 2026-07-31, Day 23)
#
# TWO DIFFERENCES FROM THE rsl_rl SCRIPT, both forced by how skrl's train.py works:
#
#  1. There is no --run_name. skrl builds its run directory as
#         logs/skrl/<experiment.directory>/<timestamp>_<algorithm>_<ml_framework>
#     and appends experiment_name only if it is non-empty. So the per-seed label is
#     injected through hydra: agent.agent.experiment.experiment_name=<label>.
#     Resulting dir: logs/skrl/ur5e_lift_skrl/<stamp>_ppo_torch_skrl_ppo_s1
#     Without this every seed lands in a near-identical directory name and the seeds
#     become impossible to tell apart after the fact.
#
#  2. Checkpoints are agent_*.pt (plus best_agent.pt), not model_*.pt.
#
# WHY LABELLING MATTERS MORE HERE THAN IT LOOKS: on Day 22 the same smoke was launched
# twice and produced two bit-identical run directories. Nothing warns you. A later glob
# over logs/skrl/ would happily average them as if they were independent seeds and
# report a fake sd of 0. Distinct labels make an accidental repeat visible.
# =====================================================================================

set -uo pipefail          # NOT -e: one failed run must not cancel the rest of the batch.
cd "$(dirname "$0")"

readonly ALGO="${1:-PPO}"
readonly NUM_ENVS="${2:-4096}"
readonly MAX_ITERS="${3:-1500}"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly SEEDS=(1 2 3)
readonly EXPDIR="ur5e_lift_skrl"          # must match experiment.directory in the yaml
readonly ALGO_LC="$(echo "$ALGO" | tr '[:upper:]' '[:lower:]')"
readonly REPORT="logs/batch_report_skrl_${ALGO_LC}.txt"

mkdir -p logs

log() { printf '%s\n' "$*" | tee -a "$REPORT"; }

: > "$REPORT"
log "======================================================================"
log " skrl $ALGO x3  ---  task: $TASK   num_envs: $NUM_ENVS   iters: $MAX_ITERS"
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
# run_one <label> <seed>
# ---------------------------------------------------------------------------------
run_one() {
    local label="$1"; shift
    local seed="$1"; shift

    run_index=$((run_index + 1))
    local started_epoch; started_epoch=$(date +%s)

    log "--- [$run_index/${#SEEDS[@]}] $label  (algo=$ALGO, seed=$seed)  start $(date -Is)"

    # NOT piped — see run_ppo_cppo_seeds.sh header.
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train_skrl.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS" \
        --algorithm "$ALGO" --seed "$seed" --max_iterations "$MAX_ITERS" \
        agent.agent.experiment.experiment_name="$label" "$@"
    local rc=$?

    local elapsed=$(( $(date +%s) - started_epoch ))
    local mins=$(( elapsed / 60 ))

    # Newest run directory ending in this label.
    local dir
    dir=$(ls -1dt "logs/skrl/$EXPDIR/"*"_$label" 2>/dev/null | head -n1)

    if [[ $rc -ne 0 ]]; then
        log "    RESULT: FAILED (train_skrl.py exit code $rc) after ${mins} min"
        [[ -n "$dir" ]] && log "    partial run dir: $dir"
        fail_count=$((fail_count + 1))
        return
    fi

    if [[ -z "$dir" ]]; then
        log "    RESULT: FAILED — exit code 0 but no run dir under logs/skrl/$EXPDIR/"
        log "             (expected a dir matching '*_$label'; check experiment.directory)"
        fail_count=$((fail_count + 1))
        return
    fi

    local n_ckpt;   n_ckpt=$(ls -1 "$dir"/checkpoints/agent_*.pt 2>/dev/null | wc -l)
    local last_ckpt; last_ckpt=$(ls -1v "$dir"/checkpoints/agent_*.pt 2>/dev/null | tail -n1)
    local n_events; n_events=$(ls -1 "$dir"/events.out.tfevents.* 2>/dev/null | wc -l)

    if [[ "$n_ckpt" -eq 0 ]]; then
        log "    RESULT: FAILED — run dir exists but holds no checkpoint"
        log "             dir: $dir"
        fail_count=$((fail_count + 1))
        return
    fi

    # Guard against the duplicate-run trap described in the header.
    local n_same; n_same=$(ls -1d "logs/skrl/$EXPDIR/"*"_$label" 2>/dev/null | wc -l)
    if [[ "$n_same" -gt 1 ]]; then
        log "    WARNING: $n_same run dirs now carry the label '$label'."
        log "             Only the newest is this run. Delete or rename the others"
        log "             before summarising, or they will be averaged as extra seeds."
    fi

    log "    RESULT: OK   ${mins} min   checkpoints: $n_ckpt   tb event files: $n_events"
    log "    dir      : $dir"
    log "    last ckpt: ${last_ckpt:-none}"
}

log "=== skrl $ALGO ==="
for seed in "${SEEDS[@]}"; do
    run_one "skrl_${ALGO_LC}_s${seed}" "$seed"
done
log ""

log "======================================================================"
log " finished: $(date -Is)"
if [[ $fail_count -eq 0 ]]; then
    log " ALL ${#SEEDS[@]} RUNS OK"
else
    log " $fail_count of ${#SEEDS[@]} RUNS FAILED — see the RESULT lines above"
fi
log "======================================================================"

exit "$fail_count"
