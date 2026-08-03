#!/bin/bash
# Pull the 15 matrix-v2 run directories that back the thesis (ctrl/cppo/cppo15 x seeds
# 1,3,4,52,54) from the lab PC to this laptop, full directories including checkpoints.
# Run this FROM THE LAPTOP TERMINAL (not through Cowork/Claude — this sandbox has no network
# path to the lab PC). Run it from the repo root (the folder containing this script's parent,
# Comparison_test/), or adjust LOCAL_BASE.
#
# What gets committed to git afterward is narrower than what this script pulls: .gitignore
# tracks the raw TensorBoard event files (+ small params/*.yaml) for exactly these 15 run dirs,
# but still excludes *.pt/*.pth/*.ckpt everywhere. So this script's checkpoints land on disk for
# your own local use (re-eval, re-play) but won't get pushed to GitHub. See .gitignore's
# "Exception (2026-08-02)" block if you need to change that.
#
# VERIFY BEFORE RUNNING: the lab PC's Tailscale address below (100.109.10.66) is the one
# recorded in run_log.md Day 5/9 for TensorBoard access — it may have changed since. Run
# `tailscale status` (or check however you normally reach the lab PC) and edit LAB_HOST if
# needed. Username "mte" and the remote path are taken directly from the checkpoint paths
# recorded in ur5_grasp/tools/eval_policy_results.csv, not guessed.

set -euo pipefail

LAB_HOST="mte@100.109.10.66"
REMOTE_BASE="Abdur_Rabbi_THESIS/Comparison_test/logs/rsl_rl"
LOCAL_BASE="Comparison_test/logs/rsl_rl"

RUNS=(
  "ur5e_lift_ctrl/2026-08-01_00-58-26_ctrl_s1"
  "ur5e_lift_ctrl/2026-08-01_01-21-49_ctrl_s3"
  "ur5e_lift_ctrl/2026-08-01_01-33-16_ctrl_s4"
  "ur5e_lift_ctrl/2026-08-01_05-30-34_ctrl_s52"
  "ur5e_lift_ctrl/2026-08-01_05-53-18_ctrl_s54"
  "ur5e_lift_cppo/2026-08-01_01-56-53_cppo_s1"
  "ur5e_lift_cppo/2026-08-01_02-19-58_cppo_s3"
  "ur5e_lift_cppo/2026-08-01_02-31-28_cppo_s4"
  "ur5e_lift_cppo/2026-08-01_06-28-07_cppo_s52"
  "ur5e_lift_cppo/2026-08-01_06-51-10_cppo_s54"
  "ur5e_lift_cppo15/2026-08-01_17-41-46_cppo15_s1"
  "ur5e_lift_cppo15/2026-08-01_18-05-05_cppo15_s3"
  "ur5e_lift_cppo15/2026-08-01_18-18-01_cppo15_s4"
  "ur5e_lift_cppo15/2026-08-01_19-04-15_cppo15_s52"
  "ur5e_lift_cppo15/2026-08-01_19-27-01_cppo15_s54"
)

for run in "${RUNS[@]}"; do
  echo "== $run =="
  mkdir -p "$LOCAL_BASE/$(dirname "$run")"
  rsync -avz --progress "$LAB_HOST:$REMOTE_BASE/$run/" "$LOCAL_BASE/$run/"
done

echo
echo "Done. Sizes:"
du -sh "$LOCAL_BASE"/* 2>/dev/null || true
echo
echo "Next: check what git would stage (should be tfevents/params only, no .pt):"
echo "  git add -n -A Comparison_test/logs"
echo "Then commit and push from here:"
echo "  git add Comparison_test/logs .gitignore"
echo "  git commit -m 'Add raw TensorBoard logs for the 5 selected-seed matrix-v2 runs'"
echo "  git push origin main"
