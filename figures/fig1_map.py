"""Figure 1: Montreal QKD network geography and topology."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8a84"
SURF = "#fcfcfb"
FIBRE = "#b5236b"
FIBRE2 = "#6250d6"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8,
    "axes.edgecolor": MUTED, "xtick.color": INK2, "ytick.color": INK2,
    "figure.facecolor": SURF, "axes.facecolor": SURF,
})

# site: lat, lon, role, label-dx, label-dy, h-align
SITES = {
    "PointeClaire": (45.4486, -73.8200, "end",   0,  .010, "center"),
    "Laval":        (45.5600, -73.7450, "end",   0,  .010, "center"),
    "StLaurent":    (45.5100, -73.6800, "relay",-.004,-.004,"right"),
    "UdeM":         (45.5048, -73.6168, "end",   0,  .010, "center"),
    "Loyola":       (45.4581, -73.6397, "end",   0, -.013, "center"),
    "McGill":       (45.5048, -73.5772, "end",  .004, .007,"left"),
    "ETS":          (45.4945, -73.5631, "end", -.005,-.009,"right"),
    "Longueuil":    (45.5300, -73.5100, "end",  .005, .004,"left"),
    "Brossard":     (45.4500, -73.4650, "end",  0, -.013, "center"),
    "Anjou":        (45.6100, -73.5600, "relay",-.005, .004,"right"),
    "Varennes":     (45.6420, -73.4520, "end",  .004, .006,"left"),
    "Repentigny":   (45.7420, -73.4500, "end",  0,  .010, "center"),
}
CROSSINGS = {
    "Médéric-Martin":   (45.5520, -73.7050, -.004, -.006, "right"),
    "Papineau-Leblanc": (45.5750, -73.6450,  .004, -.004, "left"),
    "Victoria":         (45.4800, -73.5250,  .005, -.004, "left"),
    "Jacques-Cartier":  (45.5250, -73.5350,  .005, -.005, "left"),
    "La Fontaine":      (45.5800, -73.5100,  .005,  .002, "left"),
}
LABEL = {"PointeClaire": "Pointe-Claire", "StLaurent": "Saint-Laurent",
         "ETS": "ÉTS", "Loyola": "Loyola"}

ALL = {**{k: (v[0], v[1]) for k, v in SITES.items()},
       **{k: (v[0], v[1]) for k, v in CROSSINGS.items()}}
R = 6371.0
def geo(a, b):
    la1, lo1 = map(math.radians, ALL[a]); la2, lo2 = map(math.radians, ALL[b])
    h = (math.sin((la2-la1)/2)**2
         + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2)
    return 2*R*math.asin(math.sqrt(h))
RF = 1.40

# TWO independent Qlines, each an unbranched path (max degree 2).
# They are NOT interconnected: joining them needs a hub, and a 12x12 AWG
# costs 10*log10(12) = 10.8 dB, which Montreal distances cannot afford.
# The rivers are what force two lines rather than one.
ROUTE1 = ["PointeClaire", "Loyola", "ETS", "McGill", "UdeM",
          "StLaurent", "Laval", "Anjou", "Repentigny"]
ROUTE2 = ["Brossard", "Longueuil", "Varennes"]
SERVES = {"Laval": ["Médéric-Martin", "Papineau-Leblanc"],
          "Longueuil": ["Jacques-Cartier", "Victoria"],
          "Brossard": ["Victoria", "Jacques-Cartier"],
          "Varennes": ["La Fontaine"], "Repentigny": ["La Fontaine"]}
ROUTE = ROUTE1 + ROUTE2

fig = plt.figure(figsize=(7.5, 9.1))
gs = fig.add_gridspec(2, 3, height_ratios=[2.42, 1],
                      wspace=0.26, hspace=0.13,
                      left=0.045, right=0.975, top=0.930, bottom=0.035)
axm = fig.add_subplot(gs[0, :])
axb = fig.add_subplot(gs[1, 0])
axc = fig.add_subplot(gs[1, 1])
axd = fig.add_subplot(gs[1, 2])

LAT0 = 45.59
K = math.cos(math.radians(LAT0))
def xy(n):
    la, lo = ALL[n]; return lo*K, la

def best_via(a, b):
    c = SERVES.get(a, []) + SERVES.get(b, [])
    if not c:
        return None
    return min(dict.fromkeys(c), key=lambda x: geo(a, x) + geo(x, b))

used = set()
SEGS = []
for route, col in ((ROUTE1, FIBRE), (ROUTE2, FIBRE2)):
    for i in range(len(route) - 1):
        SEGS.append((route[i], route[i+1], best_via(route[i], route[i+1]), col))

_lens = {}
for a, b, via, col in SEGS:
    p = [a] + ([via] if via else []) + [b]
    _lens[(a, b)] = sum(geo(p[i], p[i+1]) for i in range(len(p)-1)) * RF
_worst = max(_lens, key=_lens.get)

for a, b, via, col in SEGS:
    if via:
        used.add(via)
    pts = [a] + ([via] if via else []) + [b]
    km = sum(geo(pts[i], pts[i+1]) for i in range(len(pts)-1)) * RF
    xs = [xy(p)[0] for p in pts]; ys = [xy(p)[1] for p in pts]
    if (a, b) == _worst:
        axm.plot(xs, ys, color=col, lw=6.5, solid_capstyle="round",
                 alpha=0.26, zorder=1)
    axm.plot(xs, ys, color=col, lw=2.4, solid_capstyle="round", zorder=2)
    i = len(pts)//2
    axm.text((xs[i-1]+xs[i])/2, (ys[i-1]+ys[i])/2, f"{km:.0f}",
             fontsize=6.0, color="white", ha="center", va="center", zorder=5,
             weight="bold",
             bbox=dict(boxstyle="round,pad=0.16", fc=col, ec="none"))

for nm, (la, lo, dx, dy, ha) in CROSSINGS.items():
    if nm not in used:
        continue
    x, y = xy(nm)
    axm.plot(x, y, "o", ms=6.5, mfc="white", mec=INK, mew=1.0, zorder=4)
    axm.text(x+dx*K, y+dy, nm, fontsize=5.8, color=INK2, ha=ha,
             va="center", style="italic", zorder=7)

for nm, (la, lo, role, dx, dy, ha) in SITES.items():
    x, y = xy(nm)
    if nm in ROUTE:
        end = nm in (ROUTE1[0], ROUTE1[-1], ROUTE2[0], ROUTE2[-1])
        axm.plot(x, y, "s", ms=9, mfc=C_BLUE if end else C_ORANGE,
                 mec="white", mew=1.2, zorder=6)
        tcol, wt = INK, "bold"
    else:
        axm.plot(x, y, "s", ms=7, mfc="white", mec=MUTED, mew=1.3, zorder=5)
        tcol, wt = MUTED, "normal"
        axm.text(x+dx*K, y+dy, LABEL.get(nm, nm), fontsize=7.2, color=tcol,
                 ha=ha, va="center", weight=wt, zorder=7)
        continue
    axm.text(x+dx*K, y+dy, LABEL.get(nm, nm), fontsize=7.2, color=tcol,
             ha=ha, va="center", weight=wt, zorder=7)

h = [Line2D([], [], color=FIBRE, lw=2.4, label="Qline 1 — island / north"),
     Line2D([], [], color=FIBRE2, lw=2.4, label="Qline 2 — south shore"),
     Line2D([], [], marker="s", ls="", mfc=C_BLUE, mec="white", ms=8.5,
            label="end node (Alice / Bob)"),
     Line2D([], [], marker="s", ls="", mfc=C_ORANGE, mec="white", ms=8.5,
            label="intermediate node (Charlie)"),
     Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=6.5,
            label="bridge / tunnel crossing"),
     Line2D([], [], color=FIBRE, lw=6.5, alpha=0.26,
            label="longest hop — sets the loss budget")]
axm.legend(handles=h, loc="upper left", fontsize=6.8, frameon=True,
           facecolor="white", edgecolor=MUTED, framealpha=0.96,
           borderpad=0.65, labelspacing=0.55)
axm.text(0.085, 0.60, "Montréal", transform=axm.transAxes, ha="left",
         va="center", fontsize=12, color=INK, weight="bold",
         bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=MUTED, lw=0.7))
xs = [xy(n)[0] for n in ALL]; ys = [xy(n)[1] for n in ALL]
mx, my = (max(xs)-min(xs))*0.10, (max(ys)-min(ys))*0.055
axm.set_xlim(min(xs)-mx*1.5, max(xs)+mx)
axm.set_ylim(min(ys)-my*1.5, max(ys)+my*0.75)
axm.set_aspect("equal"); axm.set_xticks([]); axm.set_yticks([])
for s in axm.spines.values(): s.set_linewidth(0.8)
axm.set_title("a", loc="left", fontsize=12, weight="bold", color=INK, pad=18)
def _len(r):
    t = 0.0
    for i in range(len(r)-1):
        v = best_via(r[i], r[i+1])
        p = [r[i]] + ([v] if v else []) + [r[i+1]]
        t += sum(geo(p[j], p[j+1]) for j in range(len(p)-1)) * RF
    return t
# SIMULATED results for these exact routes (advanced profile)
axm.text(0.5, 1.048,
         f"Qline 1  {len(ROUTE1)} nodes · {len(ROUTE1)-2} Charlies · "
         f"{_len(ROUTE1):.0f} km   —   simulated QBER 6.81% ± 0.56%, "
         f"51.3 bit/s",
         transform=axm.transAxes, ha="center", va="bottom", fontsize=7.2,
         color=FIBRE, weight="bold")
axm.text(0.5, 1.005,
         f"Qline 2  {len(ROUTE2)} nodes · {len(ROUTE2)-2} Charlie · "
         f"{_len(ROUTE2):.0f} km   —   simulated QBER 1.21% ± 0.70%, "
         f"81.4 bit/s",
         transform=axm.transAxes, ha="center", va="bottom", fontsize=7.2,
         color=FIBRE2, weight="bold")

def sub(ax, t):
    ax.text(0.5, 1.10, t, transform=ax.transAxes, ha="center", va="top",
            fontsize=6.5, color=INK2)

# b: physical chain
n_mid = 3; xs = list(range(n_mid+2))
for i in range(len(xs)-1):
    axb.plot([xs[i], xs[i+1]], [0, 0], color=FIBRE, lw=2.2, zorder=1)
for i, x in enumerate(xs):
    end = i in (0, len(xs)-1)
    axb.plot(x, 0, "s", ms=9, mfc=C_BLUE if end else C_ORANGE,
             mec="white", mew=1.1, zorder=3)
for i, lbl in enumerate(["Alice", "C$_1$", "C$_2$", "C$_3$", "Bob"]):
    axb.text(xs[i], -0.40, lbl, ha="center", fontsize=6.8, color=INK)
axb.set_xlim(-0.65, xs[-1]+0.65); axb.set_ylim(-0.95, 0.55); axb.axis("off")
axb.set_title("b", loc="left", fontsize=12, weight="bold", color=INK, y=1.10, pad=0)
sub(axb, "Physical layer — linear chain,\nbudget resets at each node")

# c: logical mesh
n = 5; ang = [math.pi/2 + 2*math.pi*i/n for i in range(n)]
px = [math.cos(a) for a in ang]; py = [math.sin(a) for a in ang]
for i in range(n):
    for j in range(i+1, n):
        adj = (j-i) % n in (1, n-1)
        axc.plot([px[i], px[j]], [py[i], py[j]],
                 color=FIBRE if adj else MUTED, lw=1.9 if adj else 0.8,
                 ls="-" if adj else (0, (2.5, 2.0)), zorder=1)
names = ["Alice", "C$_1$", "C$_2$", "C$_3$", "Bob"]
for i, nmm in enumerate(names):
    end = nmm in ("Alice", "Bob")
    axc.plot(px[i], py[i], "s", ms=9, mfc=C_BLUE if end else C_ORANGE,
             mec="white", mew=1.1, zorder=3)
    axc.text(px[i]*1.34, py[i]*1.34, nmm, ha="center", va="center",
             fontsize=6.8, color=INK)
axc.set_xlim(-1.85, 1.85); axc.set_ylim(-1.75, 1.6)
axc.set_aspect("equal"); axc.axis("off")
axc.set_title("c", loc="left", fontsize=12, weight="bold", color=INK, y=1.10, pad=0)
sub(axc, "Logical layer — any pair keys\n(virtual mesh on a line)")

# d: corridor
for km in range(25, 301, 25):
    axd.plot(km, 0, "s", ms=4.5, mfc=C_ORANGE, mec="white", mew=0.6, zorder=2)
axd.plot([0, 303], [0, 0], color=MUTED, lw=1.0, zorder=1)
for nm, km, dy in [("Montréal", 0, .30), ("Sherbrooke", 170, .30),
                   ("Québec", 303, .30)]:
    axd.plot(km, 0, "s", ms=9, mfc=C_BLUE, mec="white", mew=1.1, zorder=4)
    axd.text(km, dy, nm, ha="center", fontsize=6.8, color=INK, weight="bold")
    axd.text(km, -0.28, f"{km}", ha="center", va="top", fontsize=6.2,
             color=INK2)
axd.annotate("", xy=(300, -0.70), xytext=(0, -0.70),
             arrowprops=dict(arrowstyle="<->", color=C_AQUA, lw=1.6))
axd.text(150, -0.84, "300 km reach, 11 Charlies\n(advanced, 25 km spacing)",
         ha="center", va="top", fontsize=6.3, color=INK2)
axd.set_xlim(-30, 335); axd.set_ylim(-1.45, 0.72); axd.axis("off")
axd.set_title("d", loc="left", fontsize=12, weight="bold", color=INK, y=1.10, pad=0)
sub(axd, "Kirq corridor — intermediate\nnodes every 25 km")

fig.savefig("fig1_montreal_network.png", dpi=300, facecolor=SURF)
fig.savefig("fig1_montreal_network.pdf", facecolor=SURF)
print("ok")
