"""Figures 2-3: simulated QBER and key rate vs node count."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C = {"modest": "#eb6834", "good": "#2a78d6", "advanced": "#1baf7a"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a84", "#e3e2dd"
SURF = "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2,
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.spines.top": False, "axes.spines.right": False,
})

# ---- measured data (pooled rounds as noted) ------------------------------
D25 = {  # 25 km hops, 8000 pooled rounds
 "advanced": (range(1,15),
   [1.79,2.56,3.69,5.07,5.23,5.90,7.14,7.43,8.03,9.03,9.94,10.64,11.59,11.71],
   [.21,.25,.30,.34,.35,.38,.41,.41,.43,.46,.48,.49,.50,.51],
   [61.5,50.8,45.7,42.7,40.4,38.3,37.7,38.2,36.7,35.1,33.9,34.2,34.1,33.8]),
 "good": (range(1,4), [5.46,7.78,10.40], [.36,.42,.48], [53.7,42.5,37.0]),
 "modest": (range(1,2), [11.70], [.50], [46.6]),
}
D10 = {  # 10 km hops, 2000 rounds
 "advanced": (range(1,12),
   [1.48,2.15,2.65,4.91,4.25,5.65,5.56,6.35,7.65,8.91,9.72],
   [.38,.45,.50,.70,.63,.72,.73,.76,.85,.91,.94],
   [102,97.5,93.8,84.4,88.5,87.8,83.9,86.2,80.6,80.0,79.8]),
 "good": (range(1,5), [5.13,8.36,9.03,11.16], [.69,.87,.91,.99],
          [96.1,87.6,81.1,78.8]),
 "modest": (range(1,2), [13.21], [1.06], [86.1]),
}
ORDER = ["advanced", "good", "modest"]

def qpanel(ax, D, title, note):
    ax.axhspan(11, 15, color="#f2f1ec", zorder=0)
    ax.axhline(11, color=MUTED, lw=1.1, ls=(0, (4, 3)), zorder=1)
    for k in ORDER:
        n, q, e, _ = D[k]
        n = list(n)
        ax.errorbar(n, q, yerr=[2*x for x in e], color=C[k], lw=2.0,
                    marker="o", ms=4.2, mfc=C[k], mec=SURF, mew=0.9,
                    capsize=2.2, elinewidth=1.0, zorder=3, label=k)
        ax.annotate(k, (n[-1], q[-1]), textcoords="offset points",
                    xytext=(7, -1), fontsize=7.4, color=C[k],
                    weight="bold", va="center")
    ax.set_xlabel("intermediate nodes (Charlies), $N$")
    ax.set_ylabel("QBER  (%)")
    ax.set_ylim(0, 14.5); ax.set_xlim(0.3, 16.4)
    ax.set_xticks(range(1, 15, 1))
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=10.5, weight="bold", color=INK,
                 pad=12)
    ax.text(0, 1.015, note, transform=ax.transAxes, fontsize=6.8,
            color=INK2, va="bottom")

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9))
qpanel(axes[0], D25, "a",
       "25 km spacing · 8 000 pooled rounds/point · error bars 95% CI")
qpanel(axes[1], D10, "b",
       "10 km spacing · 2 000 rounds/point · error bars 95% CI")
from matplotlib.lines import Line2D
hs = [Line2D([], [], color=C[k], lw=2.0, marker="o", ms=4.2, mfc=C[k],
             mec=SURF, mew=0.9, label=k) for k in ORDER]
hs.append(Line2D([], [], color=MUTED, lw=1.1, ls=(0, (4, 3)),
                 label="BB84 threshold (11%)"))
axes[0].legend(handles=hs, loc="lower right", fontsize=7.2, frameon=False,
               handlelength=1.9, labelspacing=0.38)
fig.tight_layout()
fig.savefig("fig2_qber_vs_nodes.png", dpi=300, facecolor=SURF)
fig.savefig("fig2_qber_vs_nodes.pdf", facecolor=SURF)

# ---- figure 3: key rate + component sensitivity --------------------------
fig3, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.9))
for k in ORDER:
    n, _, _, r = D25[k]; n = list(n)
    a1.plot(n, r, color=C[k], lw=2.0, marker="o", ms=4.2, mfc=C[k],
            mec=SURF, mew=0.9, label=k, zorder=3)
    a1.annotate(k, (n[-1], r[-1]), textcoords="offset points",
                xytext=(7, 0), fontsize=7.4, color=C[k], weight="bold",
                va="center")
a1.set_xlabel("intermediate nodes (Charlies), $N$")
a1.set_ylabel("sifted key rate  (bit s$^{-1}$)")
a1.set_xlim(0.3, 16.4); a1.set_ylim(0, 70)
a1.set_xticks(range(1, 15))
a1.grid(axis="y", color=GRID, lw=0.7); a1.set_axisbelow(True)
a1.set_title("a", loc="left", fontsize=10.5, weight="bold", color=INK, pad=12)
a1.text(0, 1.015, "25 km spacing — rate falls with chain length",
        transform=a1.transAxes, fontsize=6.8, color=INK2, va="bottom")
a1.legend(loc="upper right", fontsize=7.2, frameon=False, handlelength=1.6)

labels = ["baseline\n(advanced)", "visibility\nerror ×2",
          "gate error\n×2", "gate error\n×4", "node loss\n+20%"]
vals = [11, 8, 7, 5, 10]
cols = ["#1baf7a", "#9a9890", "#9a9890", "#9a9890", "#9a9890"]
bars = a2.bar(range(5), vals, color=cols, width=0.62, zorder=3)
for i, v in enumerate(vals):
    a2.text(i, v + 0.22, str(v), ha="center", fontsize=8.6, color=INK,
            weight="bold")
a2.axhline(11, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=2)
a2.set_xticks(range(5)); a2.set_xticklabels(labels, fontsize=6.9)
a2.set_ylabel("node ceiling  (Charlies)")
a2.set_ylim(0, 13)
a2.text(0, 11.25, "baseline ceiling", fontsize=6.6, color=INK2,
        va="bottom", ha="left")
a2.grid(axis="y", color=GRID, lw=0.7); a2.set_axisbelow(True)
a2.set_title("b", loc="left", fontsize=10.5, weight="bold", color=INK, pad=12)
a2.text(0, 1.015, "Single-parameter perturbations from the advanced profile, "
        "25 km spacing", transform=a2.transAxes, fontsize=6.8, color=INK2,
        va="bottom")
fig3.tight_layout()
fig3.savefig("fig3_rate_and_sensitivity.png", dpi=300, facecolor=SURF)
fig3.savefig("fig3_rate_and_sensitivity.pdf", facecolor=SURF)
print("ok")
