# 10 — Master Terminal Command Reference (whole thesis, in order)

**What this is:** every terminal command used across the thesis, listed in the order you actually run
them, each with a one-line *why / when*. Built from `run_log.md`, the `logbook/`, the
`Thesis_Documentation/` pages, the `ur5_grasp/` scripts, and the run logs. Use it as a checklist.

**Legend:** ✅ = already run/used · ♻️ = one-time setup (do once per machine) · 🔁 = every session ·
⏳ = planned, not run yet (Layer 2/3).

**Where you run things**
- Almost everything runs from `~/Abdur_Rabbi_THESIS/IsaacLab` (the `./isaaclab.sh` launcher lives
  there). The `../ur5_grasp/...` paths in commands are relative to that folder.
- Git and the figure script run from the repo root `~/Abdur_Rabbi_THESIS`.
- All training runs **inside `tmux`** so a dropped NoMachine connection can't kill a run.

---

## Table of contents
1. [Session start — every time](#1-session-start--every-time-)
2. [One-time stack setup](#2-one-time-stack-setup-)
3. [Validate the RL loop (Cartpole, Franka reach, TensorBoard)](#3-validate-the-rl-loop-)
4. [UR5e asset prep (inspect + build gripper USD)](#4-ur5e-asset-prep-)
5. [Grasp environment + PPO baseline](#5-grasp-environment--ppo-baseline-)
6. [Safety constraints + cost calibration + cPPO](#6-safety-constraints--cost-calibration--cppo-)
7. [Evaluation, benchmark & figures](#7-evaluation-benchmark--figures-)
8. [Git / end-of-session](#8-git--end-of-session-)
9. [Appendix A — planned Layer 2 / Layer 3 commands](#appendix-a--planned-layer-2--layer-3-)
10. [Appendix B — one-screen quick reference](#appendix-b--one-screen-quick-reference)

---

## 1. Session start — every time 🔁

Run this block at the start of **every** NoMachine session, before any training.

```bash
tmux new -s thesis_abrabbi          # or, if it already exists: tmux attach -t thesis_abrabbi
# --- everything below runs INSIDE that tmux session ---
conda activate isaaclab             # fresh terminals open in (base); this fixes "module not found"
sudo cpupower frequency-set -g performance   # CPU governor resets on reboot; keep CPU at full speed
cd ~/Abdur_Rabbi_THESIS/IsaacLab    # the launcher ./isaaclab.sh lives here
```

- **Why tmux first:** a bare training run dies with the connection; a run *inside* tmux survives.
  Detach with **Ctrl-b** then **d**; reattach with `tmux attach -t thesis_abrabbi`.
- **When:** once per session, before anything else.
- **Check:** the prompt must read `(isaaclab)`, not `(base)`.

---

## 2. One-time stack setup ♻️

Do this once per machine. The stack is **frozen** — do not upgrade mid-thesis.

**2.1 — Check the GPU driver.** Blackwell (RTX 5090) needs driver **≥ 570**.
```bash
nvidia-smi
```
*Why/when:* first thing on a new machine; confirms the driver version and that the 5090 is seen.

**2.2 — Create and activate the conda env** (Python 3.11 required by Isaac Lab 2.3).
```bash
conda create -n isaaclab python=3.11 -y
conda activate isaaclab
```
*Why/when:* isolates every dependency so versions can't drift. Activate in every new terminal.

**2.3 — Install the Blackwell-critical PyTorch** (`cu128` wheels — the default build won't drive a 5090).
```bash
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
    --index-url https://download.pytorch.org/whl/cu128
pip install "numpy==1.26.0"          # Isaac Lab expects the NumPy 1.x series
```
*Why/when:* right after the env is created; this is the single biggest setup gotcha.

**2.4 — Verify PyTorch sees the GPU** (make-or-break check).
```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.get_device_name(0))"
```
*Expected:* `2.7.0+cu128` then `NVIDIA GeForce RTX 5090`, with **no** `sm_120 is not compatible`
warning. If the warning appears, you installed a non-cu128 build — reinstall with 2.3.

**2.5 — Install Isaac Sim 5.0.0** (frozen) following NVIDIA's official 5.0.0 pip/binary docs, then
smoke-test it alone:
```bash
python create_empty.py --headless
```
*Expected:* prints `Setup complete`, no traceback. `--headless` = no window (how we train).

**2.6 — Clone Isaac Lab and pin the v2.3.0 TAG (not the branch).**
```bash
cd ~/Abdur_Rabbi_THESIS
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
git checkout -b frozen/2.3.0 v2.3.0     # the TAG — the branch drifted to 2.3.1 and broke the URDF importer
```
*Why/when:* the `release/2.3.0` branch advanced to 2.3.1 and exact-pinned a URDF importer the
installed Isaac Sim doesn't ship → startup crash. The **v2.3.0 tag** pins it to "any".

**2.7 — Install Isaac Lab + RL deps** (pulls `rsl_rl` 3.0.1, shared by PPO and cPPO).
```bash
./isaaclab.sh -i
```
*Why/when:* once, after checking out the tag. `rsl_rl` 3.0.1 is what keeps the later PPO-vs-cPPO
comparison fair (same trainer).

---

## 3. Validate the RL loop ✅

Prove the whole training loop works on toy tasks **before** touching the robot. Run from
`~/Abdur_Rabbi_THESIS/IsaacLab`.

**3.1 — Cartpole (simplest possible task).**
```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless
```
*Why/when:* first RL test. If Cartpole won't train, nothing will.
*Expected:* converges ~150 iters (~17 s on the 5090); mean episode length 300 (cap); `time_out ≈ 0.999`.

**3.2 — Franka reaching arm (a real manipulator with a climbing reward).**
```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless
```
*Why/when:* second RL test; closer to grasping than Cartpole.
*Expected:* reward climbs sharply, plateaus ~400 iters; episode length stable; no NaN.

**3.3 — `num_envs` scale test** (how many robots to train in parallel). Repeat with each value:
```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless --num_envs 8192 --max_iterations 100
# also run with --num_envs 4096 and --num_envs 16384 to compare
```
*Why/when:* once, to find the throughput sweet spot. Result: ~**8192** best for reach; the heavier
grasp env is run at **4096**.

**3.4 — Watch training from your laptop (TensorBoard).**
```bash
tensorboard --logdir logs/rsl_rl --port 6006 --bind_all
```
Then open the lab PC's address in a laptop browser, e.g. `http://100.109.10.66:6006` (Tailscale VPN).
*Why/when:* any time a run is training (we train headless, so this is how we monitor).
*Debug:* "connection refused" = TensorBoard process is down (restart it); page hangs = network/firewall.

---

## 4. UR5e asset prep ✅

Build the robot once. These launch Isaac Sim headless (they use `AppLauncher`), so run them with the
launcher too. Run from the repo root `~/Abdur_Rabbi_THESIS`.

**4.1 — Inspect the UR5e asset** (USD path, variants, joint/body names).
```bash
./isaaclab.sh -p ur5_grasp/tools/inspect_ur5e_asset.py
```
*Why/when:* once, before building the env — confirms the Nucleus `ur5e.usd`, its `Robotiq_2f_85`
gripper variant, and joint names. Writes `ur5_grasp/tools/ur5e_asset_report.txt`.

**4.2 — Build the merged single-articulation USD** (arm + Robotiq 2f-85 as one robot).
```bash
./isaaclab.sh -p ur5_grasp/tools/make_ur5e_robotiq_usd.py
```
*Why/when:* once. Stitches the gripper onto the flange and disables its nested articulation root so
it loads as **one** articulation (12 joints / 16 bodies). Output: `ur5_grasp/assets/ur5e_robotiq_2f85.usd`.

---

## 5. Grasp environment + PPO baseline ✅

Layer 1 foundation. Gym ids: `Isaac-Lift-Cube-UR5e-v0` (train) and `Isaac-Lift-Cube-UR5e-Play-v0`
(watch). Run from `~/Abdur_Rabbi_THESIS/IsaacLab`, inside tmux.

**5.1 — Tiny smoke test** (does the env load, do rewards compute).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 64 --max_iterations 10
```
*Why/when:* first thing after scaffolding the env; cheap check before spending hours on a full run.
*Expected:* one articulation loads, reach reward rises, episode length grows 20 → ~127, no crash.

**5.2 — Geometry probe** (reach-frame vs fingertips, EE-offset check).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/zero_agent.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1
```
*Why/when:* when checking the end-effector offset. The "offset = 0" hint is an artifact — **keep
`offset = 0.16 m`**, do not zero it.

**5.3 — Physics-only hold test** (can a closed gripper actually hold the cube?).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/grasp_hold_test.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 1
```
*Why/when:* used to diagnose the "cube falls through" problem and to verify the **proximity weld**
fix (cube then holds at pad level 210+ steps, no NaN).

**5.4 — Full PPO training run (on the weld env).**
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```
*Why/when:* trains the PPO grasping baseline (~1500 iters). **Retrain here after the weld fix** — the
pre-weld checkpoint reward-hacked (threw the cube) and is dead.
*Watch:* `Train/mean_reward` climbs 0.7 → ~8+; `Episode/...lifting_object` rises; no NaN /
`std >= 0.0`. Checkpoint lands in `logs/rsl_rl/ur5e_lift/`.

**5.5 — Visual verification gate (play the trained policy).**
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/play.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 9 --real-time
```
*Why/when:* always watch before trusting a checkpoint. Pass = real reach → close-near → lift-to-goal,
**no flinging**. `play.py` also exports the policy to **JIT/ONNX** (needed later for ROS 2 deploy).

> **Tip — save a run's console log to the right place.** Training is launched from inside `IsaacLab/`,
> so a *relative* `tee` path lands in `IsaacLab/…`, not the repo's `logbook/`. Use an absolute path:
> `... --num_envs 4096 2>&1 | tee ~/Abdur_Rabbi_THESIS/logbook/run.log`. (The real data is safe
> regardless — it lives in the TensorBoard event files under `logs/rsl_rl/`.)

---

## 6. Safety constraints + cost calibration + cPPO ✅

The Layer 1 deliverable. cPPO opts in with `--agent rsl_rl_cppo_cfg_entry_point`; the PPO baseline
path is byte-for-byte unchanged. Run from `~/Abdur_Rabbi_THESIS/IsaacLab`, inside tmux.

**6.1 — cPPO smoke test (5 iters, the cheap bug-catcher).**
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 64 --max_iterations 5
```
*Why/when:* first run of the new cPPO code, before any long run. *Pass:* startup prints
`Cost Critic MLP: Sequential(...)`; log shows `cost_value_function`, `cost_lambda`,
`mean_episode_cost`; `safety/cost_total`, `safety/viol_joint_limit`, `safety/manipulability_mean`
appear; `mean_reward` finite. (`cost_lambda = 0` at 5 iters is fine — plumbing, not learning, is
under test.)

**6.2 — Calibrate the manipulability floor** (needs the trained PPO checkpoint from 5.4).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/calibrate_manipulability.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 64 --steps 400
```
*Why/when:* once, to set the threshold so the constraint actually *bites*. Reports percentiles of
manipulability `w`, joint-limit clearance, min link height + baseline violation rates.
*Result:* `w` min .021 / mean .055 → **`MANIP_FLOOR = 0.045`** (~20% baseline violation, the ONE
active constraint). Joint-limit & collision came back inactive (monitored-but-satisfied).
*Sanity:* `w` should spread ≈0.01–0.1, not all-zero and not 1e6 (else the Jacobian index is wrong).
Set `MANIP_FLOOR` / `COLLISION_Z_FLOOR` in `ur5_grasp/tasks/lift/ur5e_lift_env.py`.

**6.3 — Cost-budget probe (50 iters) → set `cost_limit`.**
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 4096 --max_iterations 50
```
*Why/when:* once, to read the episodic cost a baseline-like policy incurs and pick the budget.
*Result:* `mean_episode_cost` climbs ~6.7 → 74, `cost_lambda` self-engages 0 → 6.85 (controlled) →
**`cost_limit = 25`** (set in `ur5_grasp/tasks/lift/agents/rsl_rl_cppo_cfg.py`; ~65% cost cut, ~17% reward dip).

**6.4 — Full cPPO training run** (the headline experiment).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 4096
```
*Why/when:* the safe-RL run (~1500 iters). *Watch the Lagrangian dynamics — this is the thesis story:*
`Loss/mean_episode_cost` trends down toward 25; `Loss/cost_lambda` rises then settles (must NOT pin at
100); `Train/mean_reward` still learns; `safety/viol_*` drop vs PPO. Logs → `logs/rsl_rl/ur5e_lift_cppo/`.

**6.5 — Matched PPO baseline at the SAME floor (0.045).**
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/train.py \
    --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096
```
*Why/when:* re-run unconstrained PPO at `MANIP_FLOOR = 0.045` so PPO and cPPO share the exact same
cost definition (the Day-7 checkpoint was at the old floor 0.02 and isn't comparable). Logs →
`logs/rsl_rl/ur5e_lift/`.

**6.6 — Overlay both runs in TensorBoard.**
```bash
tensorboard --logdir logs/rsl_rl --port 6006 --bind_all
```
*Why/when:* after both full runs. `ur5e_lift` (PPO) and `ur5e_lift_cppo` (cPPO) overlay automatically.

---

## 7. Evaluation, benchmark & figures ✅

Training logs reward and cost but **not** task success, so success is measured after training by
replaying each checkpoint.

**7.1 — Success rate, cPPO checkpoint** (512 episodes).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 --agent rsl_rl_cppo_cfg_entry_point \
    --headless --num_envs 64 --episodes 512 --min_height 0.1 --success_tol 0.01
```

**7.2 — Success rate, PPO baseline checkpoint** (default agent).
```bash
./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py \
    --task Isaac-Lift-Cube-UR5e-Play-v0 \
    --headless --num_envs 64 --episodes 512 --min_height 0.1 --success_tol 0.01
```
*Why/when:* after training, to fill the benchmark table. Scores **lift success** (cube > `--min_height`)
and **goal-reach** (lifted and within `--success_tol`). Each auto-loads the newest checkpoint for its
experiment. *Result:* cPPO 100% lift / 99.6% goal; PPO 100% / 100% — task success is a tie; cPPO cuts
singularity violations ~60% (6.65% vs 16.86%).

**7.3 — Generate the four Layer 1 figures** (from the archived TB CSVs). Run from the repo root:
```bash
python results/scripts/make_layer1_figs.py
```
*Why/when:* after the benchmark, to make the reward / cost-vs-budget / λ-dynamics / violation-rate
figures. Reads `results/tb_csv/`, writes 300-dpi PNG + vector PDF (Times-New-Roman style, centred
captions) to `Thesis_Documentation/assets/`. Reproducible — rerun any time.

> The CSVs in `results/tb_csv/` (ppo/ + cppo/) are exported from the TensorBoard event files; the
> figure script depends on them, so keep them in the repo.

---

## 8. Git / end-of-session ✅ 🔁

End-of-session commit + push. Run from the repo root; push from the **lab PC** (the SSH key lives
there). A nightly reminder (`thesis-git-push-reminder`, 23:00) nudges this.

```bash
cd ~/Abdur_Rabbi_THESIS
rm -f .git/index.lock              # clear any stray lock
git add -A
git status -s                      # sanity-check what's staged
git commit -m "<summary of today's work>"
git push origin main
```
*Why/when:* every session, **after** updating the module file + `run_log.md` + `09_Changelog.md`.
- Push asks for a password → the key isn't loaded: `ssh-add ~/.ssh/<key>`.
- Push rejected as "behind" → `git pull --rebase origin main`, then `git push origin main`.

*First-time git setup (Day 3, one-off):* `git init`, add `.gitignore` (excludes the IsaacLab clone +
`logs/`/checkpoints), first commit; SSH remote added on Day 8.

---

## Appendix A — planned Layer 2 / Layer 3 ⏳

Not run yet. Layer 2 starts only after Layer 1 is signed off; Layer 3 only if time allows. Listed so
nothing is missing — fill in exact commands when the work happens.

**Layer 2 — IBVS (vision).** Reuses the same launcher and the Layer 1 cPPO runner.
- Add an eye-in-hand **`Camera`** sensor (NOT `TiledCamera` — it hangs on Blackwell).
- Feature pixel `(u,v)` from RGB-D (colour-centroid in sim; YOLOv8 reserved for Layer 3 clutter).
- Classical IBVS baseline, then the RL-tuned image-Jacobian correction (fuzzy state coding + blend β).
- Add one **field-of-view** cost term to `SafetyCostComputer`, then train/eval exactly like §6–§7.
- Docs to fill: `04_Layer2_IBVS.md`.

**Layer 3 — sim-to-real (real UR5e).**
- ROS 2 Humble + `Universal_Robots_ROS2_Driver` bring-up (control the real arm).
- Load the JIT/ONNX export from `play.py` (§5.5) into a ROS 2 node.
- Import the real gripper **ROBOTIS RH-P12-RN**: URDF → USD via Isaac Lab's `UrdfConverter`, mount
  `rh_p12_rn_base` to `tool0`/`wrist_3_link`; then adapt the grasp.
- Zero-shot test on hardware; measure real grasp success + safety behaviour.
- Docs to fill: `05_Layer3_SimToReal.md`.

---

## Appendix B — one-screen quick reference

```bash
# ── every session ────────────────────────────────────────────────────────────
tmux new -s thesis_abrabbi            # or: tmux attach -t thesis_abrabbi
conda activate isaaclab
sudo cpupower frequency-set -g performance
cd ~/Abdur_Rabbi_THESIS/IsaacLab

# ── validate the stack (toy tasks) ───────────────────────────────────────────
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py --task Isaac-Cartpole-v0 --headless
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py --task Isaac-Reach-Franka-v0 --headless
tensorboard --logdir logs/rsl_rl --port 6006 --bind_all

# ── build the robot (once) ───────────────────────────────────────────────────
./isaaclab.sh -p ../ur5_grasp/tools/inspect_ur5e_asset.py       # (run from repo root as ur5_grasp/tools/...)
./isaaclab.sh -p ../ur5_grasp/tools/make_ur5e_robotiq_usd.py

# ── grasp env + PPO baseline ─────────────────────────────────────────────────
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 64 --max_iterations 10   # smoke
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096                     # full PPO
./isaaclab.sh -p ../ur5_grasp/scripts/play.py  --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 9 --real-time                  # verify

# ── safety + cPPO ────────────────────────────────────────────────────────────
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point --headless --num_envs 64 --max_iterations 5   # smoke
./isaaclab.sh -p ../ur5_grasp/scripts/calibrate_manipulability.py --task Isaac-Lift-Cube-UR5e-Play-v0 --num_envs 64 --steps 400                                  # MANIP_FLOOR
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point --headless --num_envs 4096 --max_iterations 50 # cost_limit probe
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --agent rsl_rl_cppo_cfg_entry_point --headless --num_envs 4096                      # full cPPO
./isaaclab.sh -p ../ur5_grasp/scripts/train.py --task Isaac-Lift-Cube-UR5e-v0 --headless --num_envs 4096                                                          # matched PPO @0.045

# ── evaluate + figures ───────────────────────────────────────────────────────
./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py --task Isaac-Lift-Cube-UR5e-Play-v0 --agent rsl_rl_cppo_cfg_entry_point --headless --num_envs 64 --episodes 512 --min_height 0.1 --success_tol 0.01
./isaaclab.sh -p ../ur5_grasp/scripts/eval_success.py --task Isaac-Lift-Cube-UR5e-Play-v0 --headless --num_envs 64 --episodes 512 --min_height 0.1 --success_tol 0.01
python ~/Abdur_Rabbi_THESIS/results/scripts/make_layer1_figs.py

# ── commit ───────────────────────────────────────────────────────────────────
cd ~/Abdur_Rabbi_THESIS && git add -A && git status -s && git commit -m "..." && git push origin main
```

*Sources: `run_log.md`, `logbook/01–07`, `logbook/03b_cppo_runbook.md`, `Thesis_Documentation/01–07`,
and the `ur5_grasp/` scripts.*
