#!/usr/bin/env bash
# =====================================================================================
# cppo15 TRAINING — the binding-budget arm (cost_limit = 15), replaces registered cppo10.
# Authored 2026-08-01 (Day 24, cont. 2). Modeled tightly on run_matrix_v2.sh's run_rsl
# helper (same verify-by-checkpoint pattern, same non-piped invocation) — only the arm
# and seed list differ.
#
# WHY THIS ARM: see UR5eLiftCPPO15RunnerCfg's docstring in
# ur5_grasp/tasks/lift/agents/rsl_rl_cppo_cfg.py and logbook/NEXT_SESSION_cppo15.md.
# Short version: cost_limit=15 binds on seeds 1/3/4/5/52/53 (natural cost > budget under
# ctrl), slack on 2/50/51/54 — same partition cost_limit=10 would have hit.
#
# BEFORE RUNNING THIS SCRIPT:
#   1. Run the Step-1 resolve check (see logbook/NEXT_SESSION_cppo15.md / RUN_CHECKLIST_v2.md
#      Step 1, substitute rsl_rl_cppo15_cfg_entry_point) — confirms the entry point actually
#      loads and reports cost_limit=15.0 before spending any GPU time.
#   2. Run the Step-3 smoke test below (50 iters, seed 1) and confirm Loss/cost_lambda departs
#      from 0. Seed 1's ctrl natural cost is 102.1, far above 15, so this should be an easy
#      pass — but it is exactly the check that catches a mis-wired entry point.
#
# USAGE (from inside Comparison_test/, on the GPU workstation):
#   ./run_cppo15_seeds.sh smoke      # single 50-iter seed-1 smoke run only
#   ./run_cppo15_seeds.sh            # all 10 full seeds (1500 iters each)
# =====================================================================================

set -uo pipefail          # NOT -e — one failed seed must not cancel the other nine.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly NUM_ENVS=4096
readonly SEEDS=(1 2 3 4 5 50 51 52 53 54)   # matches the existing ppo/ctrl/cppo batch exactly
readonly AGENT="rsl_rl_cppo15_cfg_entry_point"
readonly EXP="ur5e_lift_cppo15"
readonly REPORT="logs/batch_report_cppo15.txt"

MODE="${1:-full}"

mkdir -p logs
log() { printf '%s\n' "$*" | tee -a "$REPORT"; }

: > "$REPORT"
log "======================================================================"
log " cppo15 TRAINING   task: $TASK   agent: $AGENT   exp: $EXP"
log " mode    : $MODE"
log " started : $(date -Is)"
log " host    : $(hostname)"
log " cwd     : $(pwd)"
log " git     : $(git rev-parse --short HEAD 2>/dev/null || echo '(not a git repo)')"
log " tag     : $(git describe --tags --exact-match 2>/dev/null || echo '(HEAD is not exactly a tag)')"
log " dirty   : $(git status --porcelain 2>/dev/null | wc -l) modified/untracked path(s)"
log "======================================================================"
log ""

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    log "!! WARNING: working tree is DIRTY. This run's provenance line will not be trustworthy"
    log "!!          unless HEAD is exactly tag matrix-v2-cppo15. Check before trusting results."
    log ""
fi

fail_count=0
run_index=0

verify_run() {
    local dir_glob="$1" label="$2" rc="$3" started="$4"
    local elapsed=$(( $(date +%s) - started ))
    local mins=$(( elapsed / 60 ))
    local dir; dir=$(ls -1dt $dir_glob 2>/dev/null | head -n1)

    if [[ $rc -ne 0 ]]; then
        log "    RESULT: FAILED (exit code $rc) after ${mins} min"
        [[ -n "$dir" ]] && log "    partial run dir: $dir"
        fail_count=$((fail_count + 1)); return
    fi
    if [[ -z "$dir" ]]; then
        log "    RESULT: FAILED — exit 0 but no run directory matched: $dir_glob"
        fail_count=$((fail_count + 1)); return
    fi
    local n_ckpt; n_ckpt=$(ls -1 "$dir"/model_*.pt 2>/dev/null | wc -l)
    local last;   last=$(ls -1v "$dir"/model_*.pt 2>/dev/null | tail -n1)
    if [[ "$n_ckpt" -eq 0 ]]; then
        log "    RESULT: FAILED — run dir exists but holds no checkpoint"
        log "             dir: $dir"
        fail_count=$((fail_count + 1)); return
    fi
    log "    RESULT: OK   ${mins} min   checkpoints: $n_ckpt"
    log "    dir      : $dir"
    log "    last ckpt: ${last:-none}"
}

if [[ "$MODE" == "smoke" ]]; then
    log "=== SMOKE: cppo15, seed 1, 50 iterations ==="
    started=$(date +%s)
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
        --task "$TASK" --headless --num_envs 512 \
        --max_iterations 50 --seed 1 --run_name "cppo15_smoke_$(date +%H%M%S)" --agent "$AGENT"
    rc=$?
    verify_run "logs/rsl_rl/$EXP/*cppo15_smoke*" "cppo15_smoke" "$rc" "$started"
    log ""
    log "NEXT: read Loss/cost_lambda from this run's TB scalars (or wait for"
    log "  ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py to pick it up)."
    log "  It MUST depart from 0 — seed 1's ctrl natural cost is 102.1 against budget 15."
    log "  If it stays at 0, STOP. Something is wrong with the entry point; do not launch"
    log "  the full 10-seed run."
    exit "$fail_count"
fi

log "=== cppo15, all 10 seeds, 1500 iterations, num_envs=$NUM_ENVS ==="
total_runs=${#SEEDS[@]}
for s in "${SEEDS[@]}"; do
    run_index=$((run_index + 1))
    run_name="cppo15_s${s}"
    started=$(date +%s)
    log "--- [$run_index/$total_runs] $run_name  (seed=$s)  start $(date -Is)"
    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS" \
        --seed "$s" --run_name "$run_name" --agent "$AGENT"
    rc=$?
    verify_run "logs/rsl_rl/$EXP/*_$run_name" "$run_name" "$rc" "$started"
    log ""
done

log "======================================================================"
log " finished: $(date -Is)"
if [[ $fail_count -eq 0 ]]; then
    log " ALL $run_index RUNS OK"
else
    log " $fail_count of $run_index RUNS FAILED — see the RESULT lines above"
fi
log ""
log " Next, in order:"
log "   1. ../IsaacLab/isaaclab.sh -p ur5_grasp/tools/summarize_runs.py"
log "   2. Check Loss/cost_lambda for EVERY cppo15 seed in results/tb_csv/ — this script"
log "      already writes the full per-iteration trajectory (confirmed this session for the"
log "      existing cppo(25) runs), so read it directly rather than only the tail-mean."
log "   3. ./run_eval_cppo15.sh"
log "======================================================================"
exit "$fail_count"
