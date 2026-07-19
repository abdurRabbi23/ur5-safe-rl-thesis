# 08 — Glossary (plain-English terms)

Terms a beginner needs to follow this thesis, in plain language. Roughly grouped, not alphabetical.

---

## Robotics

**UR5 / UR5e** — a 6-joint industrial robot arm made by Universal Robots. "e" is the e-Series.

**End-effector (EE) / TCP** — the "hand" of the arm: the tool tip that grabs the object. TCP =
Tool Center Point.

**Gripper** — the hand mechanism. This project uses a **Robotiq 2f-85** (2-finger, 85 mm) in
simulation and a **ROBOTIS RH-P12-RN** on the real robot.

**Joint limit** — how far a joint can rotate before it physically can't go further. Driving into a
limit is unsafe.

**Jacobian** — the matrix that translates "how the joints move" into "how the hand moves". Central
to both singularity detection and IBVS.

**Singularity** — an arm pose where it momentarily loses the ability to move in some direction (like
a fully-stretched arm). Near a singularity, small hand motions demand huge joint speeds — jerky and
dangerous.

**Manipulability (Yoshikawa `w`)** — a single number measuring how "well-conditioned" the current
pose is. High = far from a singularity and free to move; near 0 = near a singularity. Computed as
`w = sqrt(det(J·Jᵀ))`.

---

## Simulation

**Isaac Sim** — NVIDIA's physics simulator + renderer; where the virtual robot lives.

**Isaac Lab** — a framework on top of Isaac Sim that provides ready-made RL environments, a PPO
trainer, and robot/sensor helpers.

**USD** — Universal Scene Description; the 3D file format Isaac uses to describe robots and scenes.

**Articulation** — one connected chain of rigid bodies and joints the physics engine treats as a
single robot.

**Headless** — running the simulator with **no visible window** (faster; how we train). The opposite
is opening the GUI to watch.

**num_envs** — how many copies of the robot train **in parallel** on the GPU. More = faster
learning, up to memory/overhead limits.

**Domain randomization** — randomly varying sim details (friction, lighting, timing) during training
so the learned policy survives the messiness of the real world.

---

## Reinforcement learning

**Reinforcement learning (RL)** — teaching a policy by trial and error: it acts, gets a **reward**,
and adjusts to earn more reward over time.

**Policy** — the trained "brain": a neural network mapping what the robot senses (observations) to
what it does (actions).

**Reward** — the score the policy is trying to maximise (e.g. lifting the cube to a goal).

**Reward hacking** — the policy finds a loophole that scores high without doing the intended task
(e.g. *throwing* the cube to collect height reward instead of holding it).

**PPO (Proximal Policy Optimization)** — a popular, stable RL algorithm. Our **baseline**.

**Critic** — a network that predicts future return; used to judge whether an action was
better/worse than expected. cPPO adds a **second critic** that predicts future *cost*.

**Checkpoint** — a saved snapshot of a trained policy (a `.pt` file) you can reload and watch or
deploy.

**Privileged information** — extra data the policy is allowed to read *in simulation only* (e.g. the
exact cube position) that a real robot wouldn't have. Used in Layer 1; removed in Layer 2 (camera).

---

## Safe RL (the core of this thesis)

**Constrained RL / CMDP** — RL where the policy must maximise reward **subject to** keeping some
**cost** under a budget. CMDP = Constrained Markov Decision Process.

**Cost** — the "unsafe-ness" signal, separate from reward (e.g. how close the arm got to a
singularity). 0 when safe, growing as danger increases.

**cost_limit / budget** — the maximum total cost the policy is allowed. cPPO tries to stay under it.

**cPPO (constrained PPO / PPO-Lagrangian)** — PPO plus a mechanism that enforces the cost budget.
Our safe algorithm.

**Lagrange multiplier (λ / `cost_lambda`)** — an automatically-tuned "safety tax". Rises when the
policy is over budget (penalising unsafe acts more), falls when safely under budget. It tunes
itself — you don't hand-set it.

**Violation rate** — the fraction of steps that broke a given constraint (e.g. dipped below the
manipulability floor). The key safety metric for the benchmark.

---

## Vision (Layer 2)

**IBVS (Image-Based Visual Servoing)** — controlling the arm directly from what the **camera** sees
(pixel positions of features) so the image reaches a target view, without computing 3D pose.

**Image Jacobian** — the matrix linking "change in pixel features" to "how to move the arm". The
thesis learns a correction to it with RL.

**YOLOv8** — a fast object detector used to find the object/features in the camera image.

**Eye-in-hand** — the camera is mounted on the arm's wrist (moves with the hand), as opposed to a
fixed external camera.

**Field of view (FOV)** — what the camera can see; losing the object off-frame is an IBVS failure
mode and a monitored constraint.

---

## Tools / workflow

**NoMachine** — remote-desktop software used to control the lab PC from a laptop.

**tmux** — a terminal multiplexer; a training run started inside tmux survives a dropped connection.

**TensorBoard** — a web dashboard that plots training curves live.

**Tailscale** — a private VPN used to reach the lab PC from the laptop.

**conda** — a Python environment manager; keeps the project's versions isolated in the `isaaclab`
env.

**ROS 2 (Humble)** — the robotics middleware used to talk to the *real* UR5e in Layer 3.
