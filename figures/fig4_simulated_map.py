"""Figure: the SIMULATED configurations placed on Quebec geography.

Every node shown is an actual simulated node: uniform 25 km hops, which is
exactly what qline_chain.py ran. QBER values are measured outputs.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a84", "#e3e2dd"
SURF = "#fcfcfb"; FIBRE = "#b5236b"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.edgecolor": MUTED})

ISLAND_SITES = {          # real sites, shown for reference only
    "Pointe-Claire": (45.4486, -73.8200), "Saint-Laurent": (45.5100, -73.6800),
    "UdeM": (45.5048, -73.6168), "ÉTS": (45.4945, -73.5631),
    "McGill": (45.5048, -73.5772), "Laval": (45.5600, -73.7450),
    "Longueuil": (45.5300, -73.5100), "Brossard": (45.4500, -73.4650),
    "Anjou": (45.6100, -73.5600), "Varennes": (45.6420, -73.4520),
    "Repentigny": (45.7420, -73.4500), "Loyola": (45.4581, -73.6397),
}
CITY = {
    "Montréal":    (45.4945, -73.5631),
    "Granby":      (45.4001, -72.7340),
    "Sherbrooke":  (45.4042, -71.8929),
    "Trois-Rivières": (46.3432, -72.5429),
    "Québec":      (46.8139, -71.2080),
}
R = 6371.0
def geo(a, b):
    la1, lo1 = map(math.radians, a); la2, lo2 = map(math.radians, b)
    h = (math.sin((la2-la1)/2)**2
         + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2)
    return 2*R*math.asin(math.sqrt(h))
RF = 1.30            # intercity route factor
HOP = 25.0           # km - the SIMULATED hop length

# measured QBER at each N, advanced profile, 25 km hops, 8000 pooled rounds
QBER = {1:1.79, 2:2.56, 3:3.69, 4:5.07, 5:5.23, 6:5.90, 7:7.14, 8:7.43,
        9:8.03, 10:9.03, 11:9.94, 12:10.64, 13:11.59, 14:11.71}

def chain(a, b, waypoints=()):
    """Uniform HOP-spaced nodes along a route, as simulated."""
    pts = [CITY[a]] + [CITY[w] for w in waypoints] + [CITY[b]]
    segs, total = [], 0.0
    for i in range(len(pts)-1):
        d = geo(pts[i], pts[i+1]) * RF
        segs.append((pts[i], pts[i+1], d)); total += d
    nhop = max(1, round(total / HOP))
    out = []
    for k in range(nhop + 1):
        t = k / nhop * total
        acc = 0.0
        for p, q, d in segs:
            if acc + d >= t or (p, q, d) is segs[-1]:
                f = (t - acc) / d if d else 0
                f = min(max(f, 0), 1)
                out.append((p[0] + (q[0]-p[0])*f, p[1] + (q[1]-p[1])*f))
                break
            acc += d
    return out, total, nhop

ROUTES = [("Montréal", "Sherbrooke", ("Granby",), FIBRE),
          ("Montréal", "Québec", ("Trois-Rivières",), "#6250d6")]

fig, (axM, ax) = plt.subplots(1, 2, figsize=(11.6, 5.3),
                              gridspec_kw={"width_ratios": [1, 1.18],
                                           "wspace": 0.10})
LAT0 = 46.1; K = math.cos(math.radians(LAT0))
def xy(p): return p[1]*K, p[0]

# ---------------- panel a: metropolitan Montreal, 10 km simulated hops ----
HOP_M = 10.0
RF_M = 1.40
A_ = ISLAND_SITES["Pointe-Claire"]; B_ = ISLAND_SITES["Repentigny"]
span_km = geo(A_, B_) * RF_M
nhop_m = max(1, round(span_km / HOP_M))
N_m = nhop_m - 1
mnodes = [(A_[0] + (B_[0]-A_[0])*k/nhop_m, A_[1] + (B_[1]-A_[1])*k/nhop_m)
          for k in range(nhop_m + 1)]
K2 = math.cos(math.radians(45.59))
def xy2(p): return p[1]*K2, p[0]

SOFF = {"McGill": (0.012, 0.004, "left", "center"),
        "ÉTS": (0.0, -0.013, "center", "top"),
        "Repentigny": (-0.012, 0.0, "right", "center"),
        "Saint-Laurent": (-0.010, -0.004, "right", "center"),
        "UdeM": (0.0, -0.013, "center", "top"),
        "Pointe-Claire": (0.0, -0.014, "center", "top")}
for nm, p in ISLAND_SITES.items():
    x, y = xy2(p)
    dx, dy, ha, va = SOFF.get(nm, (0.0, -0.013, "center", "top"))
    axM.plot(x, y, "s", ms=6, mfc="white", mec=MUTED, mew=1.2, zorder=3)
    axM.text(x+dx, y+dy, nm, fontsize=6.4, color=MUTED, ha=ha,
             va=va, zorder=4)

xs = [xy2(p)[0] for p in mnodes]; ys = [xy2(p)[1] for p in mnodes]
axM.plot(xs, ys, color=C_AQUA, lw=2.4, zorder=5, solid_capstyle="round")
for i, p in enumerate(mnodes):
    x, y = xy2(p)
    if i in (0, len(mnodes)-1):
        axM.plot(x, y, "s", ms=11, mfc=C_BLUE, mec="white", mew=1.3, zorder=7)
    else:
        axM.plot(x, y, "s", ms=7, mfc=C_ORANGE, mec="white", mew=1.0, zorder=6)

QM = {1:1.48, 2:2.15, 3:2.65, 4:4.91, 5:4.25, 6:5.65, 7:5.56, 8:6.35,
      9:7.65, 10:8.91, 11:9.72}
axM.text(0.02, 0.985, "Metropolitan Montréal", transform=axM.transAxes,
         fontsize=8.6, color=C_AQUA, weight="bold", va="top")
axM.text(0.02, 0.935,
         f"{span_km:.0f} km · {nhop_m} hops × {HOP_M:g} km · {N_m} Charlies"
         f" · {N_m+2} nodes", transform=axM.transAxes, fontsize=7.4,
         color=INK2, va="top")
axM.text(0.02, 0.892,
         f"simulated QBER {QM[N_m]:.2f}%  (advanced, 10 km sweep)",
         transform=axM.transAxes, fontsize=7.4, color=INK2, va="top")
axM.set_aspect("equal"); axM.set_xticks([]); axM.set_yticks([])
axM.margins(0.13)
for sp in axM.spines.values():
    sp.set_edgecolor(MUTED)
axM.set_title("a   metropolitan — 10 km hops", loc="left", fontsize=9.5,
              weight="bold", color=INK, pad=6)


info = []
for a, b, wp, col in ROUTES:
    nodes, total, nhop = chain(a, b, wp)
    N = nhop - 1                                  # Charlies
    xs = [xy(p)[0] for p in nodes]; ys = [xy(p)[1] for p in nodes]
    ax.plot(xs, ys, color=col, lw=2.2, zorder=2, solid_capstyle="round")
    for i, p in enumerate(nodes):
        x, y = xy(p)
        if i in (0, len(nodes)-1):
            ax.plot(x, y, "s", ms=11, mfc=C_BLUE, mec="white", mew=1.3,
                    zorder=6)
        else:
            ax.plot(x, y, "s", ms=6.5, mfc=C_ORANGE, mec="white", mew=1.0,
                    zorder=5)
    info.append((a, b, total, N, col))

OFF = {"Montréal": (-0.03, -0.085, "center", "top"),
       "Sherbrooke": (0.0, -0.085, "center", "top"),
       "Québec": (-0.07, -0.025, "right", "center"),
       "Granby": (0.0, -0.075, "center", "top"),
       "Trois-Rivières": (0.035, -0.015, "left", "center")}
for nm, p in CITY.items():
    x, y = xy(p)
    dx, dy, ha, va = OFF[nm]
    big = nm in ("Montréal", "Sherbrooke", "Québec")
    ax.text(x+dx, y+dy, nm, fontsize=8.6 if big else 7.2,
            color=INK if big else MUTED, ha=ha, va=va,
            weight="bold" if big else "normal", zorder=8)
    if not big:
        ax.plot(x, y, "o", ms=4.5, mfc="white", mec=MUTED, mew=1.0, zorder=4)

ty = 0.97
for a, b, total, N, col in info:
    q = QBER.get(N)
    ax.text(0.015, ty, f"{a} → {b}", transform=ax.transAxes, fontsize=8.4,
            color=col, weight="bold", va="top")
    ax.text(0.015, ty-0.045,
            f"{total:.0f} km · {N+1} hops × 25 km · {N} Charlies · "
            f"{N+2} nodes", transform=ax.transAxes, fontsize=7.4,
            color=INK2, va="top")
    ax.text(0.015, ty-0.088,
            f"simulated QBER {q:.2f}%  (advanced, 8 000 rounds)"
            if q else "beyond simulated range",
            transform=ax.transAxes, fontsize=7.4, color=INK2, va="top")
    ty -= 0.155

h = [Line2D([], [], marker="s", ls="", mfc="white", mec=MUTED, ms=6,
            label="real site (reference only, not a simulated node)"),
     Line2D([], [], marker="s", ls="", mfc=C_BLUE, mec="white", ms=9,
            label="end node (Alice / Bob)"),
     Line2D([], [], marker="s", ls="", mfc=C_ORANGE, mec="white", ms=7,
            label="simulated Charlie (10 km panel a / 25 km panel b)"),
     Line2D([], [], marker="o", ls="", mfc="white", mec=MUTED, ms=5,
            label="city passed through")]
fig.legend(handles=h, loc="lower center", ncol=4, fontsize=7.2,
           frameon=False, bbox_to_anchor=(0.5, -0.005))

ax.set_title("b   intercity — 25 km hops", loc="left", fontsize=9.5,
             weight="bold", color=INK, pad=6)
fig.suptitle("Simulated chains on Québec geography — every coloured node "
             "shown corresponds to a simulated node",
             fontsize=10.5, weight="bold", color=INK, x=0.012, ha="left",
             y=0.985)
ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
ax.margins(0.11)
fig.tight_layout(rect=[0, 0.045, 1, 0.955])
fig.savefig("fig4_simulated_map.png", dpi=300, facecolor=SURF)
fig.savefig("fig4_simulated_map.pdf", facecolor=SURF)
for a, b, total, N, col in info:
    print(f"{a} -> {b}: {total:.1f} km, {N+1} hops, {N} Charlies, "
          f"{N+2} nodes, QBER {QBER.get(N)}%")
