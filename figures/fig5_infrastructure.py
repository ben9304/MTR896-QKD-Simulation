"""Montreal fibre infrastructure zones — CONTEXT, not simulation.

Shows where carrier fibre actually concentrates, which is what constrains
where an intermediate node can physically be sited. No value on this
figure is a simulation output.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrow

Z1, Z2, Z3, Z4 = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8a84"
SURF = "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": SURF, "axes.facecolor": SURF})

P = {
    # 1 downtown core
    "Square-Victoria": (45.5017, -73.5614), "Griffintown": (45.4920, -73.5590),
    # 2 island ring
    "Pointe-Claire": (45.4486, -73.8200), "Dorval": (45.4500, -73.7500),
    "Saint-Laurent": (45.5100, -73.6800), "Anjou": (45.6100, -73.5600),
    # 3 south shore
    "Longueuil": (45.5300, -73.5100), "Boucherville": (45.6100, -73.4360),
    "Brossard (DIX30)": (45.4490, -73.4320),
    # 4 gateways
    "Laval": (45.5600, -73.7450), "Vaudreuil-Dorion": (45.4000, -74.0300),
    "St-Jean-sur-Richelieu": (45.3070, -73.2620),
}
BRIDGE = {"Jacques-Cartier": (45.5250, -73.5350),
          "Victoria": (45.4800, -73.5250),
          "Samuel-De Champlain": (45.4650, -73.5200)}
ZONE = {"Square-Victoria": Z1, "Griffintown": Z1,
        "Pointe-Claire": Z2, "Dorval": Z2, "Saint-Laurent": Z2, "Anjou": Z2,
        "Longueuil": Z3, "Boucherville": Z3, "Brossard (DIX30)": Z3,
        "Laval": Z4, "Vaudreuil-Dorion": Z4, "St-Jean-sur-Richelieu": Z4}

LAT0 = 45.50; K = math.cos(math.radians(LAT0))
def xy(n):
    la, lo = (P.get(n) or BRIDGE[n]); return lo*K, la

fig, ax = plt.subplots(figsize=(9.6, 6.4))

# zone 2: island ring corridors (Hwy 40 north arc, Hwy 20 south arc)
H40 = ["Pointe-Claire", "Saint-Laurent", "Anjou"]
H20 = ["Pointe-Claire", "Dorval", "Griffintown", "Square-Victoria"]
for seq, lab in ((H40, "Hwy 40"), (H20, "Hwy 20")):
    xs = [xy(n)[0] for n in seq]; ys = [xy(n)[1] for n in seq]
    ax.plot(xs, ys, color=Z2, lw=3.0, alpha=0.85, zorder=3,
            solid_capstyle="round")
    _mx = (xs[0]+xs[1])/2; _my = (ys[0]+ys[1])/2
    ax.text(_mx, _my+0.014, lab, fontsize=6.8, color=Z2,
            ha="center", weight="bold", zorder=9)
ax.plot([xy("Anjou")[0], xy("Square-Victoria")[0]],
        [xy("Anjou")[1], xy("Square-Victoria")[1]], color=Z2, lw=3.0,
        alpha=0.85, zorder=3, solid_capstyle="round")

# zone 1: downtown core halo
cx = sum(xy(n)[0] for n in ("Square-Victoria", "Griffintown"))/2
cy = sum(xy(n)[1] for n in ("Square-Victoria", "Griffintown"))/2
ax.add_patch(Circle((cx, cy), 0.030, color=Z1, alpha=0.13, zorder=1))
ax.text(cx, cy+0.034, "Downtown core", fontsize=7.4, color=Z1,
        ha="center", va="bottom", weight="bold", zorder=9)

# zone 3: the three bridge crossings
for br, dest in (("Jacques-Cartier", "Longueuil"),
                 ("Victoria", "Boucherville"),
                 ("Samuel-De Champlain", "Brossard (DIX30)")):
    bx, by = xy(br); dx, dy = xy(dest)
    ax.plot([cx, bx, dx], [cy, by, dy], color=Z3, lw=2.4, zorder=3,
            solid_capstyle="round")
    ax.plot(bx, by, "o", ms=8, mfc="white", mec=Z3, mew=1.8, zorder=7)
    BOFF = {"Jacques-Cartier": (0.007, 0.007, "left"),
            "Victoria": (0.009, -0.002, "left"),
            "Samuel-De Champlain": (0.004, -0.011, "left")}
    _dx, _dy, _ha = BOFF[br]
    ax.text(bx+_dx, by+_dy, br, fontsize=6.2, color=Z3, ha=_ha,
            va="center", style="italic", zorder=9)

# zone 4: long-haul gateways, with direction arrows off-map
GATE = {"Laval": ("Hwy 15 / 13 / 25", (0.0, 0.055)),
        "Vaudreuil-Dorion": ("→ Ottawa / Toronto", (-0.055, 0.0)),
        "St-Jean-sur-Richelieu": ("→ New York / US", (0.0, -0.055))}
ax.plot([xy("Saint-Laurent")[0], xy("Laval")[0]],
        [xy("Saint-Laurent")[1], xy("Laval")[1]], color=Z4, lw=2.4, zorder=3)
ax.plot([xy("Pointe-Claire")[0], xy("Vaudreuil-Dorion")[0]],
        [xy("Pointe-Claire")[1], xy("Vaudreuil-Dorion")[1]], color=Z4,
        lw=2.4, zorder=3)
ax.plot([xy("Brossard (DIX30)")[0], xy("St-Jean-sur-Richelieu")[0]],
        [xy("Brossard (DIX30)")[1], xy("St-Jean-sur-Richelieu")[1]],
        color=Z4, lw=2.4, zorder=3)
ax.plot([xy("Anjou")[0], xy("Anjou")[0]+0.075],
        [xy("Anjou")[1], xy("Anjou")[1]+0.030], color=Z4, lw=2.4, zorder=3)
ax.annotate("→ Québec City", (xy("Anjou")[0]+0.078, xy("Anjou")[1]+0.032),
            fontsize=7.0, color=Z4, weight="bold", va="center")
for nm, (lab, off) in GATE.items():
    x, y = xy(nm)
    ax.annotate(lab, (x+off[0], y+off[1]), fontsize=7.0, color=Z4,
                ha="center", va="center", weight="bold", zorder=9)

LOFF = {"Square-Victoria": (0.012, 0.009, "left"),
        "Griffintown": (0.004, -0.013, "left"),
        "Saint-Laurent": (0.0, -0.014, "center"),
        "Dorval": (0.0, -0.014, "center"),
        "Pointe-Claire": (0.0, -0.014, "center"),
        "Anjou": (0.008, 0.010, "left"),
        "Longueuil": (0.012, 0.0, "left"),
        "Boucherville": (0.012, 0.0, "left"),
        "Brossard (DIX30)": (0.0, -0.014, "center"),
        "Laval": (0.0, 0.013, "center"),
        "Vaudreuil-Dorion": (0.0, -0.014, "center"),
        "St-Jean-sur-Richelieu": (0.0, -0.014, "center")}
for nm, p in P.items():
    x, y = xy(nm)
    dx, dy, ha = LOFF[nm]
    ax.plot(x, y, "s", ms=9, mfc=ZONE[nm], mec="white", mew=1.3, zorder=8)
    ax.text(x+dx, y+dy, nm, fontsize=7.0, color=INK, ha=ha, va="center",
            weight="bold", zorder=9)

h = [Line2D([], [], marker="s", ls="", mfc=Z1, mec="white", ms=9,
            label="1  Downtown core hub — Cologix · eStruxture · QIX"),
     Line2D([], [], color=Z2, lw=3.0,
            label="2  Island ring corridors — Hwy 40 / Hwy 20"),
     Line2D([], [], color=Z3, lw=2.4,
            label="3  South-shore crossings — three bridges"),
     Line2D([], [], color=Z4, lw=2.4,
            label="4  North & long-haul gateways")]
ax.legend(handles=h, loc="lower left", fontsize=7.4, frameon=True,
          facecolor="white", edgecolor=MUTED, framealpha=0.96,
          borderpad=0.7, labelspacing=0.5)
ax.set_title("Montréal fibre infrastructure zones — "
             "where a node can physically be sited",
             loc="left", fontsize=10.5, weight="bold", color=INK, pad=22)
ax.text(0.0, 1.006, "Infrastructure context. No value on this figure is a "
        "simulation output.", transform=ax.transAxes, fontsize=7.4,
        color=INK2, va="bottom")
ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
ax.margins(0.10)
for s in ax.spines.values(): s.set_edgecolor(MUTED)
fig.tight_layout()
fig.savefig("fig5_infrastructure.png", dpi=300, facecolor=SURF)
fig.savefig("fig5_infrastructure.pdf", facecolor=SURF)
print("ok")
