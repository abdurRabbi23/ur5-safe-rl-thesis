# Copyright (c) 2025, Touhid — UR5 Safe RL Grasping thesis.
# SPDX-License-Identifier: BSD-3-Clause
"""Per-step safety cost for the UR5e grasp env (Layer 1 constraints).

Three geometric/kinematic cost terms, each a *soft* non-negative penalty that is 0
while safe and grows smoothly as the arm enters a danger zone (smoothness gives the
cost critic a usable learning signal):

  1. collision keep-out  -- any monitored arm link dropping below the table plane.
                            Self-collisions are OFF in sim and there are no contact
                            sensors, so this geometric proxy is the honest cheap choice.
  2. joint-limit margin  -- any arm joint entering the last `joint_margin` rad before
                            its (soft) limit, normalised to [0, 1] per joint.
  3. singularity floor   -- Yoshikawa manipulability w = sqrt(det(J Jᵀ)) of the 6-DOF
                            arm Jacobian dropping below `manip_floor`, normalised.

`total` = w_collision*c1 + w_joint*c2 + w_manip*c3 (one aggregate cost -> one Lagrange
multiplier). Per-term means and *violation rates* (0/1 indicators) are returned for
logging so the thesis can report each constraint separately.

NOTE (calibrate on the lab PC before trusting): `manip_floor` and the table-plane
`z_floor` are scale/scene-specific. Use `scripts/calibrate_manipulability.py` to pick
`manip_floor` from a baseline rollout, and confirm `z_floor` against the table prim.
"""

from __future__ import annotations

import torch


class SafetyCostComputer:
    """Computes the aggregate per-step safety cost for a batch of envs.

    Indices (arm joints, monitored bodies, EE body, Jacobian layout) are resolved once
    on the first call and cached. All math is batched over envs; nothing syncs to CPU.
    """

    def __init__(
        self,
        robot,
        arm_joint_names: list[str],
        ee_body_name: str,
        monitored_body_names: list[str],
        z_floor: float,
        joint_margin: float,
        manip_floor: float,
        w_collision: float,
        w_joint: float,
        w_manip: float,
    ):
        self.robot = robot
        self.device = robot.device
        self.z_floor = float(z_floor)
        self.joint_margin = float(joint_margin)
        self.manip_floor = float(manip_floor)
        self.w_collision = float(w_collision)
        self.w_joint = float(w_joint)
        self.w_manip = float(w_manip)

        # --- resolve & cache indices (find_* returns (ids, names)) ---
        self.arm_joint_ids = list(robot.find_joints(arm_joint_names)[0])
        self.monitored_body_ids = list(robot.find_bodies(monitored_body_names)[0])
        self.ee_body_id = robot.find_bodies(ee_body_name)[0][0]

        # Jacobian body-axis index. For a fixed-base articulation PhysX omits the root
        # from the Jacobian body axis, so jac_body = ee_body - 1. Detect at runtime by
        # comparing the Jacobian's body-dim to the number of bodies.
        self._jac_body_id = None  # resolved lazily on first compute (needs a live jacobian)

    def _manipulability(self) -> torch.Tensor:
        """Yoshikawa manipulability w = sqrt(det(J Jᵀ)) for the 6-DOF arm, per env."""
        jac = self.robot.root_physx_view.get_jacobians()  # (N, nbodies[-1], 6, ndof)
        if self._jac_body_id is None:
            num_bodies = self.robot.num_bodies
            if jac.shape[1] == num_bodies:
                self._jac_body_id = self.ee_body_id          # floating base / root included
            else:
                self._jac_body_id = self.ee_body_id - 1       # fixed base / root omitted
        # (N, 6, 6): EE spatial rows x arm-joint columns. Column order is irrelevant to
        # w because J Jᵀ is invariant to column permutation.
        J = jac[:, self._jac_body_id, :, :][:, :, self.arm_joint_ids]
        JJt = J @ J.transpose(-2, -1)                         # (N, 6, 6)
        det = torch.linalg.det(JJt).clamp(min=0.0)
        return torch.sqrt(det + 1e-12)                        # (N,)

    # --- raw per-env quantities (used by the threshold-calibration script) ---
    def manipulability(self) -> torch.Tensor:
        """Public alias: Yoshikawa w per env."""
        return self._manipulability()

    def joint_limit_min_distance(self) -> torch.Tensor:
        """Smallest distance (rad) from any arm joint to its nearer soft limit, per env."""
        q = self.robot.data.joint_pos[:, self.arm_joint_ids]
        lim = self.robot.data.soft_joint_pos_limits[:, self.arm_joint_ids, :]
        dist = torch.minimum(q - lim[..., 0], lim[..., 1] - q)
        return dist.min(dim=-1).values

    def min_link_height(self) -> torch.Tensor:
        """Lowest z (world) among monitored arm links, per env."""
        return self.robot.data.body_pos_w[:, self.monitored_body_ids, 2].min(dim=-1).values

    def compute(self):
        """Returns (total_cost (N,), info dict of 0-dim tensors for logging)."""
        robot = self.robot
        data = robot.data

        # 1) collision keep-out: penetration depth below the table plane, summed over links
        z = data.body_pos_w[:, self.monitored_body_ids, 2]              # (N, L) absolute height
        penetration = torch.clamp(self.z_floor - z, min=0.0)           # (N, L)
        c_collision = penetration.sum(dim=-1)                           # (N,)
        collide_violation = (penetration > 0.0).any(dim=-1).float()    # (N,)

        # 2) joint-limit margin: normalised encroachment into the last `margin` rad
        q = data.joint_pos[:, self.arm_joint_ids]                      # (N, 6)
        lim = data.soft_joint_pos_limits[:, self.arm_joint_ids, :]     # (N, 6, 2)
        dist = torch.minimum(q - lim[..., 0], lim[..., 1] - q)         # dist to nearer limit
        encroach = torch.clamp(1.0 - dist / self.joint_margin, min=0.0, max=1.0)
        c_joint = encroach.sum(dim=-1)                                 # (N,)
        joint_violation = (dist < self.joint_margin).any(dim=-1).float()

        # 3) singularity: normalised drop of manipulability below the floor
        w = self._manipulability()                                     # (N,)
        c_manip = torch.clamp(1.0 - w / self.manip_floor, min=0.0, max=1.0)
        manip_violation = (w < self.manip_floor).float()

        total = self.w_collision * c_collision + self.w_joint * c_joint + self.w_manip * c_manip

        info = {
            "safety/cost_total": total.mean().detach(),
            "safety/cost_collision": c_collision.mean().detach(),
            "safety/cost_joint_limit": c_joint.mean().detach(),
            "safety/cost_singularity": c_manip.mean().detach(),
            "safety/viol_collision": collide_violation.mean().detach(),
            "safety/viol_joint_limit": joint_violation.mean().detach(),
            "safety/viol_singularity": manip_violation.mean().detach(),
            "safety/manipulability_mean": w.mean().detach(),
            "safety/manipulability_min": w.min().detach(),
        }
        return total, info
