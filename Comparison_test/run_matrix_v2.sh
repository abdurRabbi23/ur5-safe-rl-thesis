#!/usr/bin/env bash
# =====================================================================================
# LAYER 1 RUN MATRIX v2 — the post-audit rerun.   Authored 2026-07-31 (Day 23).
#
# Supersedes run_ppo_cppo_seeds.sh, which produced the CONFOUNDED 2026-07-30 matrix.
# Do not run that script again and do not quote its numbers. Why, in one paragraph:
#
#   `Loss/cost_lambda` was 0.0 for essentially the whole of every cPPO run in that matrix
#   (cppo_s2: 0.0 at every single iteration). At lambda = 0 the PPO-Lagrangian update is
#   algebraically stock PPO. So the constraint cannot explain why cPPO beat PPO on every
#   seed — something non-algorithmic did. The prime suspect was a single global
#   clip_grad_norm_ over actor + reward critic + cost critic, which let the cost critic's
#   gradients shrink the actor's step. That is fixed in safe_rl/ppo_lagrangian.py, and this
#   matrix adds the CONTROL ARM that can prove or disprove the explanation.
#
# THE FIVE ARMS AND WHAT EACH ONE IS FOR
# -------------------------------------------------------------------------------------
#   ppo      PPO, 4096 envs      the unconstrained baseline
#   ctrl     lambda_max = 0      cost critic present, constraint OFF.
#                                ctrl vs ppo  = the cost of merely attaching a second critic.
#                                Should now be ~null. If it is NOT, the audit is incomplete
#                                and something still couples the two heads — stop and say so.
#   cppo     cost_limit = 25     the Day-9 budget. Expected to stay near lambda = 0 again;
#                                that is a RESULT (the constraint does not bind), not a bug.
#   cppo10   cost_limit = 10     a budget below the natural operating point, so lambda MUST
#                                activate. This is where a real constrained-RL result lives.
#                                cppo10 vs ctrl = the effect of the constraint alone.
#   sac      skrl, 128 envs      the off-policy third algorithm. Cut this arm first if time
#                                runs short — it is the only one whose config has never run.
#
# COST: 20 rsl_rl runs at ~11 min = ~3h40m, plus 5 SAC runs of unknown duration (first
# execution ever). Budget 5-6 hours and start it when you can leave the machine alone.
# Today is Day 23; writing is due 2026-08-11. Running all 25 in one night is the plan;
# if SAC misbehaves, kill it and ship the 20-run rsl_rl matrix, which is self-sufficient.
#
# USAGE (from inside Comparison_test/, on the GPU workstation):
#   ./run_matrix_v2.sh              # all five arms
#   ./run_matrix_v2.sh rsl_rl       # the 20 rsl_rl runs only, skip SAC
#   ./run_matrix_v2.sh sac          # SAC only (e.g. after fixing its config)
#
# Design carried over from run_ppo_cppo_seeds.sh and deliberately kept:
#   * NOT `set -e` — one failed run must not cancel the other 24.
#   * training runs are NEVER piped — piping causes the block buffering that
#     simulation_app.close() then discards. Verification reads artefacts off disk instead.
#   * per-run exit code, wall clock, and checkpoint count go into a flushed report.
# =====================================================================================

set -uo pipefail          # NOT -e. See above.
cd "$(dirname "$0")"

readonly TASK="Isaac-Lift-Cube-UR5e-v0"
readonly NUM_ENVS_ONPOLICY=4096
readonly NUM_ENVS_OFFPOLICY=128     # SAC. See skrl_sac_cfg.yaml gotcha 3.
readonly SEEDS=(1 2 3 4 5)          # 5, not 3. PPO's goal-reach across the old 3 seeds was
                                    # 0 / 58.6 / 100 % (sd 50.25) — a bimodal outcome that
                                    # 3 samples cannot characterise. 5 is the minimum that
                                    # lets you report "k of 5 converged" honestly.
readonly REPORT="logs/batch_report_v2.txt"

WHICH="${1:-all}"

mkdir -p logs
log() { printf '%s\n' "$*" | tee -a "$REPORT"; }

: > "$REPORT"
log "======================================================================"
log " LAYER 1 MATRIX v2 (post-audit)   task: $TASK"
log " arms    : ppo, ctrl, cppo(25), cppo10(10), sac    x 5 seeds"
log " selected: $WHICH"
log " started : $(date -Is)"
log " host    : $(hostname)"
log " cwd     : $(pwd)"
log " git     : $(git rev-parse --short HEAD 2>/dev/null || echo '(not a git repo)')"
log " dirty   : $(git status --porcelain 2>/dev/null | wc -l) modified/untracked path(s)"
log "======================================================================"
log ""

# A dirty tree is not fatal, but the fairness protocol requires the env frozen and stamped
# BEFORE run 1, so an uncommitted change here means the provenance line in the results table
# is a lie. Warn loudly rather than block — you may legitimately be mid-debug.
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    log "!! WARNING: working tree is DIRTY. Commit + tag before the run you intend to REPORT."
    log "!!          (git add -A && git commit -m 'Day 23: matrix v2 freeze' && git tag matrix-v2)"
    log ""
fi

fail_count=0
run_index=0
total_runs=0
[[ "$WHICH" == "all" || "$WHICH" == "rsl_rl" ]] && total_runs=$((total_runs + 20))
[[ "$WHICH" == "all" || "$WHICH" == "sac" ]]    && total_runs=$((total_runs + 5))

# ---------------------------------------------------------------------------------
# verify_run <run_dir_glob> <ckpt_glob> <label> <rc> <started_epoch>
# Shared tail of both run_* helpers: turn "the process exited" into "the artefacts exist".
# ---------------------------------------------------------------------------------
verify_run() {
    local dir_glob="$1" ckpt_glob="$2" label="$3" rc="$4" started="$5"
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
        log "             (check experiment_name in the agent cfg)"
        fail_count=$((fail_count + 1)); return
    fi

    local n_ckpt; n_ckpt=$(ls -1 "$dir"/$ckpt_glob "$dir"/checkpoints/$ckpt_glob 2>/dev/null | wc -l)
    local last;   last=$(ls -1v "$dir"/$ckpt_glob "$dir"/checkpoints/$ckpt_glob 2>/dev/null | tail -n1)
    local n_ev;   n_ev=$(ls -1 "$dir"/events.out.tfevents.* 2>/dev/null | wc -l)

    if [[ "$n_ckpt" -eq 0 ]]; then
        log "    RESULT: FAILED — run dir exists but holds no checkpoint"
        log "             dir: $dir"
        fail_count=$((fail_count + 1)); return
    fi

    log "    RESULT: OK   ${mins} min   checkpoints: $n_ckpt   tb event files: $n_ev"
    log "    dir      : $dir"
    log "    last ckpt: ${last:-none}"
}

# ---------------------------------------------------------------------------------
# run_rsl <experiment_name> <run_name> <seed> [extra args...]
# ---------------------------------------------------------------------------------
run_rsl() {
    local exp="$1"; shift
    local run_name="$1"; shift
    local seed="$1"; shift

    run_index=$((run_index + 1))
    local started; started=$(date +%s)
    log "--- [$run_index/$total_runs] $run_name  (exp=$exp, seed=$seed)  start $(date -Is)"

    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS_ONPOLICY" \
        --seed "$seed" --run_name "$run_name" "$@"
    local rc=$?

    verify_run "logs/rsl_rl/$exp/*_$run_name" "model_*.pt" "$run_name" "$rc" "$started"
}

# ---------------------------------------------------------------------------------
# run_sac <seed>
# skrl's log dir is logs/skrl/<directory>/<timestamp>_<algorithm>_<framework>[_<expname>].
# train_skrl.py appends the experiment_name, so --run_name equivalents come through
# agent.experiment.experiment_name; the hydra override below is how that is set per seed.
# ---------------------------------------------------------------------------------
run_sac() {
    local seed="$1"
    local run_name="sac_s${seed}"

    run_index=$((run_index + 1))
    local started; started=$(date +%s)
    log "--- [$run_index/$total_runs] $run_name  (skrl SAC, seed=$seed, num_envs=$NUM_ENVS_OFFPOLICY)  start $(date -Is)"

    ../IsaacLab/isaaclab.sh -p ur5_grasp/scripts/train_skrl.py \
        --task "$TASK" --headless --num_envs "$NUM_ENVS_OFFPOLICY" \
        --algorithm SAC --seed "$seed" \
        agent.experiment.experiment_name="$run_name"
    local rc=$?

    verify_run "logs/skrl/ur5e_lift_sac/*_$run_name" "agent_*.pt" "$run_name" "$rc" "$started"
}

# =================================================================================
# THE MATRIX. Order matters: the two arms that settle the audit question (ppo, ctrl)
# run FIRST, so that if the night dies halfway you still have the finding.
# =================================================================================
if [[ "$WHICH" == "all" || "$WHICH" == "rsl_rl" ]]; then

    log "=== ARM 1/5: PPO — unconstrained baseline ==="
    for s in "${SEEDS[@]}"; do run_rsl "ur5e_lift" "ppo_s${s}" "$s"; done
    log ""

    log "=== ARM 2/5: CTRL — cost critic present, lambda pinned to 0 (THE CONTROL) ==="
    for s in "${SEEDS[@]}"; do
        run_rsl "ur5e_lift_ctrl" "ctrl_s${s}" "$s" --agent rsl_rl_ctrl_cfg_entry_point
    done
    log ""

    log "=== ARM 3/5: cPPO, cost_limit = 25 (the Day-9 budget) ==="
    for s in "${SEEDS[@]}"; do
        run_rsl "ur5e_lift_cppo" "cppo_s${s}" "$s" --agent rsl_rl_cppo_cfg_entry_point
    done
    log ""

    log "=== ARM 4/5: cPPO, cost_limit = 10 (a budget that actually binds) ==="
    for s in "${SEEDS[@]}"; do
        run_rsl "ur5e_lift_cppo10" "cppo10_s${s}" "$s" --agent rsl_rl_cppo10_cfg_entry_point
    done
    log ""
fi

if [[ "$WHICH" == "all" || "$WHICH" == "sac" ]]; then
    log "=== ARM 5/5: SAC — skrl, off-policy, 128 envs ==="
    log "    First execution of skrl_sac_cfg.yaml anywhere. If run 1 fails, kill the batch"
    log "    (Ctrl-C) rather than burning four more launches on the same config error."
    for s in "${SEEDS[@]}"; do run_sac "$s"; done
    log ""
fi

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
log "   2. check Loss/cost_lambda for the cppo10 arm — if it is still 0.0 the budget is"
log "      STILL not binding and the constraint arm has to be retuned again before eval."
log "   3. ./run_eval_policy_v2.sh"
log "======================================================================"

exit "$fail_count"
