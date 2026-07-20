import csv, os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# ---- Times New Roman look (Liberation Serif = metric-identical substitute) ----
for p in glob.glob("/usr/share/fonts/truetype/liberation*/LiberationSerif-*.ttf"):
    fm.fontManager.addfont(p)
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "font.size": 13,
    "axes.titlesize": 15,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 13,
    "axes.linewidth": 0.9,
    "figure.dpi": 120,
})

# ---- purposeful palette ----
C_CPPO = "#1B7F5C"   # teal-green  -> safe / constrained
C_PPO  = "#C1442E"   # warm red    -> unconstrained baseline
C_REF  = "#555555"   # grey dashed -> reference lines / budgets

DATA = "/sessions/compassionate-relaxed-sagan/mnt/Abdur_Rabbi_THESIS/results/tb_csv"
OUT  = "/sessions/compassionate-relaxed-sagan/mnt/outputs/fig_out"
os.makedirs(OUT, exist_ok=True)

def load(rel):
    xs, ys = [], []
    with open(os.path.join(DATA, rel)) as fh:
        for row in csv.DictReader(fh):
            xs.append(float(row["Step"])); ys.append(float(row["Value"]))
    return xs, ys

def ema(y, a=0.06):
    out=[]; s=y[0]
    for v in y:
        s = a*v + (1-a)*s; out.append(s)
    return out

def caption(fig, text):
    fig.text(0.5, 0.15, text, ha="center", va="top",
             fontsize=11.5, style="italic")

def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"),
                    dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)

# ======================= FIG 1 — reward overlay =======================
fig, ax = plt.subplots(figsize=(7.2, 4.5))
for rel, col, lab in [("ppo/ppo_mean_reward.csv",  C_PPO,  "PPO (unconstrained)"),
                      ("cppo/cppo_mean_reward.csv", C_CPPO, "cPPO (cost_limit = 25)")]:
    x, y = load(rel)
    ax.plot(x, y, color=col, alpha=0.22, lw=1.0)
    ax.plot(x, ema(y), color=col, lw=2.2, label=lab)
ax.set_xlabel("Training iteration"); ax.set_ylabel("Mean reward")
ax.set_title("Task Reward: cPPO vs. PPO", fontweight="bold")
ax.grid(True, ls=":", lw=0.6, alpha=0.6); ax.legend(loc="lower right", frameon=False)
ax.margins(x=0)
fig.subplots_adjust(bottom=0.32)
caption(fig, "Figure 1. Mean reward over training on the UR5e cube-lift task. cPPO and unconstrained\n"
             "PPO converge to essentially identical reward (166.3 vs. 167.2) — the safety constraint\n"
             "costs no task performance.")
save(fig, "fig_reward_ppo_vs_cppo")

# ================== FIG 2 — episodic cost vs budget ===================
fig, ax = plt.subplots(figsize=(7.2, 4.5))
x, y = load("cppo/cppo_mean_episode_cost.csv")
ax.plot(x, y, color=C_CPPO, alpha=0.25, lw=1.0)
ax.plot(x, ema(y), color=C_CPPO, lw=2.2, label="cPPO mean episodic cost")
ax.axhline(25, color=C_REF, ls="--", lw=1.6, label="cost budget (cost_limit = 25)")
ax.annotate("peak ≈ 80.2", xy=(x[y.index(max(y))], max(y)),
            xytext=(0.30, 0.86), textcoords="axes fraction",
            fontsize=11.5, color=C_CPPO,
            arrowprops=dict(arrowstyle="->", color=C_CPPO, lw=1.2))
ax.annotate("final = 2.24", xy=(x[-1], y[-1]), xytext=(0.62, 0.30),
            textcoords="axes fraction", fontsize=11.5, color=C_CPPO,
            arrowprops=dict(arrowstyle="->", color=C_CPPO, lw=1.2))
ax.set_xlabel("Training iteration"); ax.set_ylabel("Mean episodic safety cost")
ax.set_title("Constraint Satisfaction: Episodic Cost vs. Budget", fontweight="bold")
ax.grid(True, ls=":", lw=0.6, alpha=0.6); ax.legend(loc="upper right", frameon=False)
ax.margins(x=0)
fig.subplots_adjust(bottom=0.32)
caption(fig, "Figure 2. cPPO mean episodic safety cost over training against the cost budget\n"
             "(cost_limit = 25, dashed). Cost peaks ≈ 80 as the policy first grasps through singular\n"
             "poses, then is driven to 2.24 — well under budget.")
save(fig, "fig_cost_vs_budget")

# ==================== FIG 3 — lambda dynamics =========================
fig, ax = plt.subplots(figsize=(7.2, 4.5))
x, y = load("cppo/cppo_cost_lambda.csv")
ax.plot(x, y, color=C_CPPO, alpha=0.25, lw=1.0)
ax.plot(x, ema(y), color=C_CPPO, lw=2.2, label="cost_lambda (λ)")
peak = max(y)
ax.annotate(f"peak ≈ {peak:.1f}", xy=(x[y.index(peak)], peak),
            xytext=(0.42, 0.80), textcoords="axes fraction",
            fontsize=11.5, color=C_CPPO,
            arrowprops=dict(arrowstyle="->", color=C_CPPO, lw=1.2))
ax.axhline(0, color=C_REF, ls="--", lw=1.2, alpha=0.7)
ax.set_xlabel("Training iteration"); ax.set_ylabel("Lagrange multiplier  λ")
ax.set_title("Lagrangian Self-Tuning (λ) over Training", fontweight="bold")
ax.grid(True, ls=":", lw=0.6, alpha=0.6); ax.legend(loc="upper right", frameon=False)
ax.margins(x=0)
fig.subplots_adjust(bottom=0.32)
caption(fig, "Figure 3. Self-tuning of the dual variable λ (cost_lambda). λ rises to a 16.7 peak to\n"
             "penalise near-singular poses, then relaxes to zero once the constraint is satisfied —\n"
             "never approaching its cap of 100.")
save(fig, "fig_lambda_dynamics")

# ==================== FIG 4 — violation bars ==========================
fig, ax = plt.subplots(figsize=(6.4, 4.6))
_, vp = load("ppo/ppo_viol_singularity.csv")
_, vc = load("cppo/cppo_viol_singularity.csv")
vals = [vp[-1]*100, vc[-1]*100]
bars = ax.bar(["PPO\n(unconstrained)", "cPPO\n(cost_limit = 25)"], vals,
              color=[C_PPO, C_CPPO], width=0.55, edgecolor="black", lw=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x()+b.get_width()/2, v+0.4, f"{v:.2f}%",
            ha="center", va="bottom", fontsize=13, fontweight="bold")
ax.set_ylabel("Singularity violation rate (%)")
ax.set_title("Safety Outcome: Time Spent Near Singularities", fontweight="bold")
ax.set_ylim(0, max(vals)*1.25)
ax.grid(True, axis="y", ls=":", lw=0.6, alpha=0.6)
ax.text(0.5, 0.92, "violation ≡  manipulability  w < MANIP_FLOOR = 0.045",
        transform=ax.transAxes, ha="center", fontsize=11.5, color=C_REF, style="italic")
fig.subplots_adjust(bottom=0.34)
caption(fig, "Figure 4. Final singularity violation rate (a violation is w < MANIP_FLOOR = 0.045).\n"
             "cPPO more than halves the time spent near kinematic singularities versus\n"
             "unconstrained PPO (6.65% vs. 16.86%).")
save(fig, "fig_violation_rates")

print("done:", sorted(os.listdir(OUT)))
