# 01 — Environment Setup & RL Validation

**Status:** ✅ Done · **Layer:** foundation (needed for everything) · **Roadmap:** Weeks 1–4

**Goal of this section:** get a working Isaac simulation stack on the machine, and prove the
reinforcement-learning training loop works end-to-end — *before* touching any robot task. When you
finish this page you will have trained a toy robot (a cartpole and a reaching arm) and watched the
learning curves from another computer.

---

## 0. Before you start — the mental model

We are stacking four things on top of each other. Each layer depends on the one below it:

```
  Your RL task code  (ur5_grasp/ — comes later)
        |
  Isaac Lab 2.3      (RL-friendly wrapper: environments, PPO trainer, sensors)
        |
  Isaac Sim 5.0      (the physics simulator + renderer)
        |
  GPU + driver + CUDA + PyTorch   (the hardware and math layer)
```

If a lower layer is wrong (e.g. PyTorch can't see the GPU), nothing above it will work. That is
why we validate bottom-up and don't move on until each layer is proven.

---

## 1. Hardware and OS (the machine)

The thesis runs on a lab PC:

- **CPU:** Intel i9 · **RAM:** 64 GB · **GPU:** NVIDIA RTX 5090 (Blackwell architecture,
  compute capability `sm_120`) · **OS:** Ubuntu Linux.
- Accessed remotely via **NoMachine** (a remote-desktop tool). You get a full Linux desktop over
  the network.

> **Beginner note — why the GPU matters so much.** RL here trains *thousands of robots in
> parallel* on the GPU. A weaker GPU still works but is slower and needs fewer parallel
> environments. The RTX 5090 is a *Blackwell* card, which is new enough that it forces specific
> driver/PyTorch versions — this is the single biggest setup gotcha, covered next.

---

## 2. NVIDIA driver

**Why:** the GPU needs a driver new enough to understand a Blackwell card.

**Requirement:** driver **570 or newer**. The thesis machine runs **580.159.03**.

Check what you have:

```bash
nvidia-smi
```

**Expected output:** a table showing the driver version (top row), the RTX 5090, its memory, and
temperature. If the version is below 570, update the driver before doing anything else.

---

## 3. Conda + the Python environment

**Why:** we isolate everything in one conda environment named `isaaclab` so system Python is never
touched, and versions can't drift.

```bash
# create the environment (Python 3.11 is required by this Isaac Lab release)
conda create -n isaaclab python=3.11 -y

# activate it — you must do this in EVERY new terminal
conda activate isaaclab
```

**Expected:** your shell prompt changes from `(base)` to `(isaaclab)`.

> **Gotcha (you WILL hit this):** every fresh NoMachine terminal opens in `(base)`. If a command
> fails with "module not found", the first thing to check is whether the prompt says
> `(isaaclab)`. Running `conda activate isaaclab` fixes it.

---

## 4. PyTorch (the Blackwell-critical step)

**Why:** PyTorch is the math engine RL runs on. Blackwell (`sm_120`) is only supported by CUDA
12.8 builds, so you must install the **`cu128`** wheels — the default PyTorch install will *not*
drive a 5090 correctly.

```bash
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
    --index-url https://download.pytorch.org/whl/cu128
```

Also pin NumPy (Isaac Lab expects the 1.x series here):

```bash
pip install "numpy==1.26.0"
```

**Verify PyTorch actually sees the GPU** — this is the make-or-break check:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.get_device_name(0))"
```

**Expected output:**

```
2.7.0+cu128
NVIDIA GeForce RTX 5090
```

**Pass condition:** it prints the 5090 name **with no `sm_120 is not compatible` warning**. If you
see that warning, you installed a non-cu128 build — reinstall with the `--index-url` above.

---

## 5. Isaac Sim 5.0.0

**Why:** this is the simulator — it provides the physics (PhysX) and the renderer. Isaac Lab sits
on top of it.

Install Isaac Sim **5.0.0** (frozen — do not upgrade mid-thesis) following NVIDIA's official
instructions for a pip/binary install into the `isaaclab` env. The exact installer command depends
on NVIDIA's current distribution, so follow their 5.0.0 docs, but the **frozen version is
non-negotiable**: 5.0.0.

> **Gotcha — `TiledCamera` hangs on Blackwell.** Under Isaac Sim on the 5090, the `TiledCamera`
> sensor freezes. Use the plain **`Camera`** sensor instead — at `num_envs=1` the output is
> identical. This matters in Layer 2 (vision); note it now so it doesn't surprise you later.

**Smoke test Isaac Sim by itself** (before adding Isaac Lab):

```bash
# from the Isaac Sim install, run the empty-scene sample, headless
python create_empty.py --headless
```

**Expected output:** it prints `Setup complete` and exits with **no traceback**. The GUI is not
needed here — headless means "no window", which is how we train.

---

## 6. Isaac Lab 2.3.0 (pin the TAG, not the branch)

**Why:** Isaac Lab gives us ready-made RL environments, the PPO trainer, and sensor/robot helpers.
We build the thesis task by retargeting one of its environments.

```bash
cd ~/Abdur_Rabbi_THESIS
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
```

**Critically — check out the v2.3.0 _tag_, not the release branch:**

```bash
git checkout -b frozen/2.3.0 v2.3.0
```

> **Hard-won lesson (Day 8 bug).** The `release/2.3.0` *branch* silently advanced to 2.3.1, which
> exact-pinned a URDF importer version (`2.4.31`) that the installed Isaac Sim doesn't ship
> (`2.4.19`). Result: training crashed at startup. The **v2.3.0 tag** pins that importer to "any",
> so it works. **Always pin Isaac Lab to the tag `v2.3.0`, never the moving branch.**

Install Isaac Lab into the env and let it pull `rsl_rl`:

```bash
./isaaclab.sh -i          # installs Isaac Lab + RL dependencies (rsl_rl 3.0.1)
```

**Expected:** install completes with no error; `rsl_rl` version **3.0.1** ends up in the env. This
trainer is shared by both the PPO baseline and our custom cPPO, which keeps the later comparison
fair.

---

## 7. Validate the RL loop — Test A: Cartpole

**Why:** before trusting the stack on a hard robot task, prove the whole training loop works on the
simplest possible task (balancing a pole on a cart). If Cartpole won't train, nothing will.

```bash
cd ~/Abdur_Rabbi_THESIS/IsaacLab
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless
```

**Expected output / pass condition:**

- Converges in about **150 iterations** (~17 seconds on the 5090).
- **Mean episode length reaches 300** (the episode cap) — i.e. the pole stays balanced the whole
  time.
- Termination breakdown: `time_out ≈ 0.999`, `cart_out_of_bounds ≈ 0.001` — it almost never falls,
  so it *learned*.

---

## 8. Validate the RL loop — Test B: Franka reaching arm

**Why:** Cartpole proves the loop; a reaching arm proves the loop works on an actual **manipulator**
with a reward that must climb over time — much closer to our grasping task.

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Reach-Franka-v0 --headless
```

**Expected:** reward **climbs sharply then plateaus around 400 iterations**; episode length stays
stable. No NaN.

---

## 9. Watch training from another computer (TensorBoard)

**Why:** we train **headless** (no window) on the lab PC, so we monitor progress through
**TensorBoard**, a web dashboard of the learning curves. You open it from your laptop.

On the lab PC, point TensorBoard at the logs and bind it to all network interfaces:

```bash
tensorboard --logdir logs/rsl_rl --port 6006 --bind_all
```

Then on your laptop, open the lab PC's address in a browser, e.g.:

```
http://100.109.10.66:6006
```

(That address is the lab PC over **Tailscale**, a private VPN; use whatever address reaches your
machine.)

**Expected:** the reward/length curves render and update live.

> **Debug lesson (memorise this).** If the browser says **"connection refused"**, the TensorBoard
> *process is down* — restart it. If the page just **hangs**, it's a *network/firewall* issue — the
> process is fine but traffic isn't reaching it. Two different problems, two different fixes.

---

## 10. How big to make training (num_envs)

**Why:** `num_envs` is how many robots train in parallel. More = faster learning per wall-clock
second, up to a point, then GPU memory and overhead push back. We measured the trade-off on the
Franka reach task (100 iterations each):

| num_envs | wall time | iters/s | throughput (env·it/s) | peak VRAM |
|:--------:|:---------:|:-------:|:---------------------:|:---------:|
| 4096 (default) | 40.9 s | 2.44 | ~10.0k | 4600 MiB |
| 8192 | 50.5 s | 1.98 | ~16.2k | 5059 MiB |
| 16384 | 74.1 s | 1.35 | ~22.1k | 7554 MiB |

**Takeaway:** ~**8192** was the sweet spot for the light reaching task. The UR5e grasping env is
*heavier per environment*, so re-time it before committing to a training budget (in practice we run
the grasp env at **4096**, which fits comfortably in VRAM).

---

## 11. Session-start checklist (do this every time)

Every new NoMachine session, before any training:

```bash
conda activate isaaclab                              # fresh terminals start in (base)
sudo cpupower frequency-set -g performance           # CPU governor resets on every reboot
tmux new -s thesis_abrabbi                           # run training inside tmux (survives disconnects)
```

- **`conda activate`** — otherwise imports fail.
- **`cpupower ... performance`** — keeps the CPU at full speed so it doesn't bottleneck the GPU.
- **`tmux`** — if your NoMachine connection drops, a bare training run dies with it; a run started
  *inside* tmux keeps going. Detach with **Ctrl-b** then **d**; reattach with
  `tmux attach -t thesis_abrabbi`.

---

## What "done" looks like for this section

- `nvidia-smi` shows driver ≥ 570 and the RTX 5090.
- PyTorch prints `2.7.0+cu128` and the 5090 name, no `sm_120` warning.
- Isaac Sim `create_empty.py --headless` prints `Setup complete`.
- Isaac Lab is on the **v2.3.0 tag**; `rsl_rl` is 3.0.1.
- Cartpole converges (~150 iters); Franka-Reach reward climbs.
- TensorBoard curves are visible from your laptop.

If all six hold, the foundation is solid — move on to `02_Grasp_Environment.md`.
