"""
MTR896 - Phase 3: Montreal Qline mesh simulation. SELF-CONTAINED.

    python3.12 montreal_mesh.py --check                 # schema probe, ~2 s
    python3.12 montreal_mesh.py --emit                  # print the config
    python3.12 montreal_mesh.py --run                   # full simulation
    python3.12 montreal_mesh.py --run --profile good --rounds 600

==========================================================================
WHAT CHANGED FROM qline_mesh.py
==========================================================================
Same verified protocol programs - they passed a mutation-tested offline
harness and are reproduced here unchanged. What changed is where the
NUMBERS come from.

Before: link parameters were Sena et al.'s, and the comparison was
circular - a model fed a paper's results reproduces that paper's results.

Now: link parameters come from a HARDWARE PROFILE (component datasheet
quantities) and MONTREAL GEOGRAPHY. QBER and key rate are OUTPUTS of the
simulation, compared to published values only afterwards.

This is why the simulation matters rather than being a formality. An
analytic model can be quietly contaminated by borrowed constants. A
simulator fed only component specs and distances cannot be: SquidASM's
heralded link takes visibility, dark-count probability, detector
efficiency, fibre length and attenuation, and PRODUCES the error rate.
The direction of inference is correct by construction.

==========================================================================
INPUTS vs OUTPUTS
==========================================================================
INPUTS   visibility, dark counts, detector efficiency, gate depolarisation,
         per-node insertion loss, fibre attenuation, distances, node count
OUTPUTS  QBER, secret key rate, sifting fraction, per-pairing agreement

No quantity from a reference paper's RESULTS section appears as an input.

==========================================================================
KNOWN UNVERIFIED POINT
==========================================================================
The heralded link field names below come from SquidASM documentation.
HeraldedLinkConfig inherits from netsquid-netbuilder, which requires
NetSquid credentials, so the names could not be checked against source.

RUN --check FIRST. It loads the config and nothing else, so a schema
mismatch surfaces in seconds. If it fails, the error names the offending
field and --link depolarise gives a fallback that uses only `fidelity`,
whose nesting under `cfg:` IS verified from squidasm/run/stack/config.py.

==========================================================================
VERIFIED KEY RELATION
==========================================================================
Numerically verified, exhaustively, for 1, 2 and 3 Charlies:

    r_A XOR r_B = (XOR_i r_Ci) XOR carry XOR b_A
    carry = ((b_A + SUM_i b_Ci + b_B) mod 4) // 2

valid when b_A XOR (XOR_i b_Ci) XOR b_B == 0.

The trailing b_A term is absent from the papers' prepare-and-send
formula. It arises because for |Phi+> the two parties' rotations
SUBTRACT rather than add. Using the papers' formula gives ~50% QBER.
"""

import argparse
import itertools
import math
import os
import random
import sys
import tempfile

# ==========================================================================
# INPUTS: hardware profiles. Datasheet and design quantities only.
# ==========================================================================

class Hardware:
    def __init__(self, name, visibility, p_dark, eta_det, node_loss_db,
                 depolar_1q, depolar_2q):
        self.name = name
        self.visibility = visibility        # interferometer visibility
        self.p_dark = p_dark                # per detection window
        self.eta_det = eta_det              # detector efficiency
        self.node_loss_db = node_loss_db    # per-Charlie insertion loss
        self.depolar_1q = depolar_1q        # single-qubit gate depolarisation
        self.depolar_2q = depolar_2q        # two-qubit gate depolarisation


# ==========================================================================
# NODE INSERTION LOSS - built from component datasheets, NOT from any
# reference paper. (The previous 5.0 / 3.5 / 3.0 dB were lifted from
# Sena et al.'s results section and have been replaced.)
#
#   Phase modulator, Exail/iXblue MPX-MPZ series, 1550 nm, no connectors:
#       MPZ-LN-10               2.5 dB typ   3.5 dB max
#       MPZ-LN-10 "LIL" option  2.0 dB typ   2.5 dB max
#   FC/APC connector            0.25 dB each, 2 per node
#   Optical switch, Agiltron NanoSpeed 1x1, 1260-1650 nm:
#       0.6 dB typ, 1.0 dB max  (only if a bypass path is modelled -
#                                not included in the figures below)
#
# -> modest   3.5 (max) + 0.50 = 4.0 dB
#    good     2.5 (typ) + 0.50 = 3.0 dB
#    advanced 2.0 (LIL) + 0.50 = 2.5 dB
#
# DEPLOYMENT NOTE, Montreal-specific: the Agiltron switch is specified
# -5 to +45 C (degraded to -10..+70 C), and its insertion loss drifts up
# to 0.5 dB with temperature. Montreal reaches -25 C in winter, so
# intermediate nodes cannot live in unheated roadside enclosures - they
# need ODFs, central offices or campus buildings. That constrains WHERE
# a Charlie can be sited, independently of where the geometry wants one.
#
# An EDFA cannot substitute for any of this: no-cloning forbids
# amplifying the quantum channel, and a single photon at 1 MHz sits
# ~-99 dBm, about 69 dB below a preamp's minimum specified input.
# Amplifiers belong on the classical channels only.
# ==========================================================================
MODULATOR_DB   = {"modest": 3.5, "good": 2.5, "advanced": 2.0}
CONNECTOR_DB_N = 0.25     # per FC/APC connector
CONNECTORS_PER_NODE = 2
SWITCH_DB      = 0.6      # Agiltron NanoSpeed 1x1 typ, bypass only

PROFILES = {
    "modest":   Hardware("modest",   0.92, 1e-4, 0.90, 4.0, 0.010, 0.050),
    "good":     Hardware("good",     0.98, 1e-4, 0.90, 3.0, 0.005, 0.020),
    "advanced": Hardware("advanced", 0.99, 1e-5, 0.95, 2.5, 0.001, 0.005),
}

# Fibre loss, built up from independently cited component specifications.
# NOT taken from any reference paper's measured results.
#   fibre @1550 nm   0.22 dB/km   Prysmian G.652.D datasheet (<= 0.22)
#   fusion splice    0.15 dB      FOA loss-budget reference
#   drum length      4.0 km       typical metro pull length
#   connector        0.30 dB      FOA (TIA-568 max 0.75)
# -> distributed loss = 0.22 + 0.15/4.0 = 0.2575 dB/km
#
# For the record, and only AFTER the fact: Sena et al. measured 5.04 dB over
# 19.9 km = 0.253 dB/km. The agreement with the figure built above is a
# RESULT (independent corroboration of fibre quality), not an input. Their
# number was not used to derive ours.
FIBRE_DB_KM     = 0.22
SPLICE_DB       = 0.15
DRUM_KM         = 4.0
CONNECTOR_DB    = 0.30
ATTENUATION     = FIBRE_DB_KM + SPLICE_DB / DRUM_KM      # 0.2575 dB/km
CONNECTORS_PER_HOP = 2   # one patch panel at each end of a hop

QBER_THRESHOLD = 0.11    # BB84 security threshold, theoretical

# ==========================================================================
# INPUTS: Montreal geography
# ==========================================================================

PLACES = {
    # Downtown cluster. All within ~2 km of each other - these are four
    # buildings in one neighbourhood, NOT a metropolitan network. Kept
    # only as a reference case showing the loss-irrelevant regime.
    "ETS":           (45.4945, -73.5631),
    "Concordia":     (45.4972, -73.5789),
    "McGill":        (45.5048, -73.5772),
    "UQAM":          (45.5088, -73.5617),
    "Polytechnique": (45.5045, -73.6131),
    "UdeM":          (45.5048, -73.6168),
    # Island-spanning and greater-Montreal sites. These give the 10-20 dB
    # budgets where the security threshold actually lives.
    "Loyola":        (45.4581, -73.6397),   # Concordia Loyola, NDG
    "StLaurent":     (45.5100, -73.6800),
    "Longueuil":     (45.5300, -73.5100),
    "Brossard":      (45.4500, -73.4650),
    "Anjou":         (45.6100, -73.5600),
    "Laval":         (45.5600, -73.7450),
    "PointeClaire":  (45.4486, -73.8200),   # West Island
    "Repentigny":    (45.7420, -73.4500),   # NE edge
    "Varennes":      (45.6420, -73.4520),   # IREQ, Hydro-Quebec research
}

ROUTE_FACTOR = 1.40      # on-land duct meander, geodesic -> fibre route

# Fibre cannot cross water wherever it likes: it crosses at specific bridges
# and tunnels. Five of the sites above are off-island, so a straight-line
# estimate understates those hops. Each off-island site is routed through an
# actual crossing (approximate mid-span coordinates), and the shortest
# serving crossing is chosen per hop.
#
# This matters most where two sites face each other with no crossing between
# them: Anjou -> Varennes is 13.7 km straight but 18.7 km routed (+37%),
# because the fibre must detour to the Louis-Hippolyte-La Fontaine tunnel.
CROSSINGS = {
    "MedericMartin":   (45.5520, -73.7050),   # A-15,  Riviere des Prairies
    "PontViau":        (45.5650, -73.6800),   #        Riviere des Prairies
    "PapineauLeblanc": (45.5750, -73.6450),   # A-19,  Riviere des Prairies
    "Champlain":       (45.4650, -73.5200),   #        St-Lawrence
    "Victoria":        (45.4800, -73.5250),   #        St-Lawrence
    "JacquesCartier":  (45.5250, -73.5350),   #        St-Lawrence
    "LaFontaine":      (45.5800, -73.5100),   # tunnel, St-Lawrence
}

# Which crossings can serve each off-island site. Sites absent from this
# map are on the island of Montreal and need no crossing.
SERVES = {
    "Laval":      ["MedericMartin", "PontViau", "PapineauLeblanc"],
    "Longueuil":  ["JacquesCartier", "Victoria"],
    "Brossard":   ["Champlain", "Victoria"],
    "Varennes":   ["LaFontaine"],
    "Repentigny": ["LaFontaine"],
}

# A Qline has exactly one Charlie in this mesh, so every scenario is a
# three-node path. Multi-Charlie chains need the generalised programs.
#
# Sherbrooke (34.0 dB) and Quebec City (60.7 dB) are deliberately ABSENT.
# They are not Qline spans: a Qline accumulates its error budget along the
# whole chain, so it tops out at metropolitan scale. Those two need a
# TRUSTED-NODE RELAY chain, where each link terminates, the key is
# measured, and the budget resets - a different architecture, sized from
# the per-link budget this simulation establishes. Granby splits
# Montreal-Sherbrooke 85.2/85.4 km for a 0.4% detour penalty; for Quebec
# City the A-20/A-40 relays are Saint-Hyacinthe, Drummondville, Nicolet
# or Trois-Rivieres, Victoriaville or Plessisville, into Levis.
SCENARIOS = {
    # Island-spanning. Budgets in brackets at 5 dB node loss.
    "MTL_CAMPUS":   ["Loyola", "UdeM", "Anjou"],                 # 10.4 dB
    "MTL_CROSS":    ["Laval", "ETS", "Brossard"],                # 12.5 dB
    "MTL_RIVESUD":  ["Laval", "Anjou", "Varennes"],              # 12.4 dB
    "MTL_IREQ":     ["PointeClaire", "ETS", "Varennes"],         # 16.8 dB
    "MTL_WESTEAST": ["PointeClaire", "ETS", "Repentigny"],       # 19.9 dB
    # Reference case only: downtown cluster, 0.6 dB of fibre. Reports
    # gate noise with loss effectively absent.
    "MTL_DOWNTOWN": ["ETS", "Concordia", "McGill"],              #  5.6 dB
}


_COORDS = {**PLACES, **CROSSINGS}


def geodesic_km(a, b):
    R = 6371.0
    la1, lo1 = map(math.radians, _COORDS[a])
    la2, lo2 = map(math.radians, _COORDS[b])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def route_hop(a, b):
    """Fibre route length a->b in km, and the crossing used (or None).

    If either endpoint is off-island the route goes through the shortest
    serving bridge or tunnel rather than straight across the water.
    """
    cands = SERVES.get(a, []) + SERVES.get(b, [])
    if not cands:
        return geodesic_km(a, b) * ROUTE_FACTOR, None
    best, via = None, None
    for x in dict.fromkeys(cands):
        d = (geodesic_km(a, x) + geodesic_km(x, b)) * ROUTE_FACTOR
        if best is None or d < best:
            best, via = d, x
    return best, via


def hops_km(path):
    return [route_hop(path[i], path[i + 1])[0]
            for i in range(len(path) - 1)]


def hops_detail(path):
    """[(km, crossing_or_None), ...] per hop."""
    return [route_hop(path[i], path[i + 1]) for i in range(len(path) - 1)]


# ==========================================================================
# Config generation: profile + geography -> SquidASM YAML
# ==========================================================================

def qdevice_block(hw, n_qubits):
    return f"""  num_qubits: {n_qubits}
  T1: 10000000000
  T2: 1000000000
  init_time: 10000
  single_qubit_gate_time: 1000
  two_qubit_gate_time: 100000
  measure_time: 10000
  single_qubit_gate_depolar_prob: {hw.depolar_1q}
  two_qubit_gate_depolar_prob: {hw.depolar_2q}"""


def make_config(scenario, hw, link_type="heralded"):
    path = SCENARIOS[scenario]
    hops = hops_km(path)
    names = ["Alice", "Charlie", "Bob"]

    out = [f"# MTR896 scenario {scenario}, profile {hw.name}",
           f"# path: {' -> '.join(path)}",
           f"# hops: {', '.join(f'{h:.2f} km' for h in hops)}"
           f"  total {sum(hops):.2f} km",
           f"# visibility {hw.visibility}, p_dark {hw.p_dark},"
           f" eta {hw.eta_det}, {hw.node_loss_db} dB/Charlie",
           "",
           "qdevice_end: &qdevice_end", qdevice_block(hw, 2), "",
           "qdevice_mid: &qdevice_mid", qdevice_block(hw, 4), "",
           "stacks:",
           "  - {name: Alice,   qdevice_typ: generic,"
           " qdevice_cfg: {<<: *qdevice_end}}",
           "  - {name: Charlie, qdevice_typ: generic,"
           " qdevice_cfg: {<<: *qdevice_mid}}",
           "  - {name: Bob,     qdevice_typ: generic,"
           " qdevice_cfg: {<<: *qdevice_end}}",
           "", "links:"]

    for i, L in enumerate(hops):
        # Fixed (length-independent) loss on this hop: patch-panel
        # connectors at both ends, plus Charlie's insertion loss on the
        # hop ENTERING Charlie (not the one entering Bob).
        fixed_db = CONNECTORS_PER_HOP * CONNECTOR_DB
        if i == 0:
            fixed_db += hw.node_loss_db
        p_init = 1 - 10 ** (-fixed_db / 10)
        out += [f"  - stack1: {names[i]}", f"    stack2: {names[i+1]}"]
        if link_type == "heralded":
            out += ["    typ: heralded", "    cfg:",
                    f"      length: {L:.4f}",
                    f"      p_loss_init: {p_init:.6f}",
                    f"      p_loss_length: {ATTENUATION}",
                    "      speed_of_light: 200000",
                    f"      dark_count_probability: {hw.p_dark}",
                    f"      detector_efficiency: {hw.eta_det}",
                    f"      visibility: {hw.visibility}",
                    "      num_resolving: False"]
        else:
            # Fallback. Only `fidelity` is used, and its nesting under
            # cfg: is verified from squidasm/run/stack/config.py.
            # Fidelity is DERIVED from visibility, not assumed.
            out += ["    typ: depolarise", "    cfg:",
                    f"      fidelity: {hw.visibility:.4f}"]

    out += ["", "clinks:"]
    for a, b in itertools.combinations(names, 2):
        out.append(f"  - {{stack1: {a}, stack2: {b},"
                   f" typ: default, cfg: {{delay: 1000000}}}}")
    return "\n".join(out) + "\n"


# ==========================================================================
# Protocol programs - UNCHANGED from the harness-verified qline_mesh.py
# ==========================================================================

def _load_squidasm():
    from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
    from squidasm.run.stack.config import StackNetworkConfig
    from squidasm.run.stack.run import run
    return Program, ProgramContext, ProgramMeta, StackNetworkConfig, run


def theta_units(theta):
    """rot_Y(n, d) applies n*pi/2^d. We use d=1, so n = theta/(pi/2)."""
    return int(round(theta / (math.pi / 2))) % 4


def build_programs():
    Program, ProgramContext, ProgramMeta, _, _ = _load_squidasm()

    class AliceProgram(Program):
        CHARLIE, BOB = "Charlie", "Bob"

        @property
        def meta(self):
            return ProgramMeta(name="MTL_Alice", csockets=[self.BOB],
                               epr_sockets=[self.CHARLIE], max_qubits=2)

        def run(self, context):
            # Drawn here, not __init__: run() is called once per round,
            # __init__ only once for the whole campaign.
            basis = random.randint(0, 1)
            conn = context.connection
            q = context.epr_sockets[self.CHARLIE].create_keep()[0]
            n = theta_units(basis * math.pi / 2)
            if n:
                q.rot_Y(n, 1)
            outcome = q.measure()
            yield from conn.flush()
            context.csockets[self.BOB].send_int(basis)
            return {"basis": basis, "measured": int(outcome)}

    class CharlieProgram(Program):
        ALICE, BOB = "Alice", "Bob"

        @property
        def meta(self):
            return ProgramMeta(name="MTL_Charlie", csockets=[self.BOB],
                               epr_sockets=[self.ALICE, self.BOB],
                               max_qubits=4)

        def run(self, context):
            basis = random.randint(0, 1)
            bit = random.randint(0, 1)
            conn = context.connection
            qL = context.epr_sockets[self.ALICE].recv_keep()[0]
            qR = context.epr_sockets[self.BOB].create_keep()[0]
            n = theta_units(basis * math.pi / 2 + bit * math.pi)
            if n:
                qL.rot_Y(n, 1)
            qL.cnot(qR)
            qL.H()
            m1 = qL.measure()
            m2 = qR.measure()
            yield from conn.flush()
            m1, m2 = int(m1), int(m2)
            cs = context.csockets[self.BOB]
            cs.send_int(m1)
            cs.send_int(m2)
            cs.send_int(basis)
            return {"basis": basis, "bit": bit, "m1": m1, "m2": m2}

    class BobProgram(Program):
        ALICE, CHARLIE = "Alice", "Charlie"

        @property
        def meta(self):
            return ProgramMeta(name="MTL_Bob",
                               csockets=[self.ALICE, self.CHARLIE],
                               epr_sockets=[self.CHARLIE], max_qubits=2)

        def run(self, context):
            basis = random.randint(0, 1)
            conn = context.connection
            q = context.epr_sockets[self.CHARLIE].recv_keep()[0]
            # MUST flush before blocking on a classical recv: recv_keep()
            # only queues the EPR instruction, which executes at flush.
            # Blocking first deadlocks against Charlie's own flush.
            yield from conn.flush()
            cs = context.csockets[self.CHARLIE]
            m1 = yield from cs.recv_int()
            m2 = yield from cs.recv_int()
            if m2:
                q.X()
            if m1:
                q.Z()
            n = theta_units(basis * math.pi / 2)
            if n:
                q.rot_Y(n, 1)
            outcome = q.measure()
            yield from conn.flush()
            cb = yield from cs.recv_int()
            ab = yield from context.csockets[self.ALICE].recv_int()
            return {"basis": basis, "measured": int(outcome),
                    "charlie_basis": cb, "alice_basis": ab}

    return AliceProgram, CharlieProgram, BobProgram


# ==========================================================================
# Sifting and mesh accounting
# ==========================================================================

PAIRINGS = ["Alice-Charlie", "Charlie-Bob", "Alice-Bob"]
ADJACENT = {"Alice-Charlie": "yes", "Charlie-Bob": "yes", "Alice-Bob": "NO"}


def derive_keys(a, c, b):
    """Return (K_A, K_C, K_B), or None if the basis-match test fails."""
    bA, bC, bB = a["basis"], c["basis"], b["basis"]
    if (bA ^ bC ^ bB) != 0:
        return None
    carry = ((bA + bC + bB) % 4) // 2
    return a["measured"], c["bit"] ^ carry ^ bA, b["measured"]


# ==========================================================================
# Entry points
# ==========================================================================

def cmd_check(scenario, hw, link_type):
    _, _, _, StackNetworkConfig, _ = _load_squidasm()
    text = make_config(scenario, hw, link_type)
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        StackNetworkConfig.from_file(path)
    except Exception as e:
        print("SCHEMA CHECK FAILED")
        print(f"  link type : {link_type}")
        print(f"  error     : {type(e).__name__}: {e}")
        print()
        if link_type == "heralded":
            print("  The heralded field names are the unverified part.")
            print("  Retry with:  --link depolarise")
            print("  That path uses only `fidelity`, whose nesting under")
            print("  cfg: is verified from squidasm source.")
        return 1
    finally:
        if os.path.exists(path):
            os.remove(path)
    print(f"SCHEMA CHECK PASSED  ({link_type} link, profile {hw.name})")
    print("  The config loads. Run with --run.")
    return 0


def cmd_run(scenario, hw, link_type, rounds, seed):
    _, _, _, StackNetworkConfig, run = _load_squidasm()
    Alice, Charlie, Bob = build_programs()

    random.seed(seed)
    text = make_config(scenario, hw, link_type)
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        cfg = StackNetworkConfig.from_file(path)
    finally:
        if os.path.exists(path):
            os.remove(path)

    results = run(config=cfg,
                  programs={"Alice": Alice(), "Charlie": Charlie(),
                            "Bob": Bob()},
                  num_times=rounds)
    # run() returns per stack in CONFIG stack order, not dict order.
    res = dict(zip(["Alice", "Charlie", "Bob"], results))

    counts = {p: 0 for p in PAIRINGS}
    errors = {p: 0 for p in PAIRINGS}
    sifted = 0
    for i in range(rounds):
        keys = derive_keys(res["Alice"][i], res["Charlie"][i], res["Bob"][i])
        if keys is None:
            continue
        K_A, K_C, K_B = keys
        # Round-robin over which party reveals (Doosti Sec. 3.2) so each
        # pairing gets disjoint rounds and an independent noise sample.
        pair = PAIRINGS[sifted % len(PAIRINGS)]
        sifted += 1
        counts[pair] += 1
        if (K_A ^ K_C ^ K_B) != 0:
            errors[pair] += 1

    detail = hops_detail(SCENARIOS[scenario])
    hops = [d[0] for d in detail]
    vias = [d[1] for d in detail if d[1]]
    fibre_db = sum(hops) * ATTENUATION
    conn_db = len(hops) * CONNECTORS_PER_HOP * CONNECTOR_DB
    total_db = fibre_db + conn_db + hw.node_loss_db

    print("=" * 70)
    print(f"  {scenario}   profile: {hw.name}   link: {link_type}")
    print("=" * 70)
    print(f"  path      : {' -> '.join(SCENARIOS[scenario])}")
    print(f"  hops      : {', '.join(f'{h:.2f} km' for h in hops)}"
          f"   total {sum(hops):.2f} km")
    if vias:
        print(f"  crossings : {', '.join(vias)}")
    print(f"  budget    : fibre {fibre_db:.2f} ({ATTENUATION:.4f} dB/km)"
          f" + connectors {conn_db:.2f}"
          f" + Charlie {hw.node_loss_db:.1f}"
          f" = {total_db:.2f} dB   [INPUT]")
    print(f"  rounds    : {rounds}, seed {seed}")
    print("-" * 70)
    print(f"  sifted    : {sifted} ({sifted/rounds:.1%}, expect ~50%)")
    print()
    print("  SIMULATION OUTPUTS")
    print(f"  {'pairing':<17}{'adjacent':<11}{'correct':<13}{'QBER'}")
    for p in PAIRINGS:
        n = counts[p]
        if n == 0:
            print(f"  {p:<17}{ADJACENT[p]:<11}{'no rounds':<13}-")
            continue
        q = errors[p] / n
        print(f"  {p:<17}{ADJACENT[p]:<11}{f'{n-errors[p]}/{n}':<13}{q:.2%}")
    tot = sum(counts.values())
    if tot:
        overall = sum(errors.values()) / tot
        print(f"\n  overall QBER : {overall:.2%}"
              f"   {'SECURE' if overall < QBER_THRESHOLD else 'ABOVE 11% THRESHOLD'}")
    print("=" * 70)
    print("  QBER above is an OUTPUT. Nothing from Sena et al. or Minder")
    print("  et al. entered the configuration. Compare to their published")
    print("  values now - that comparison carries information because the")
    print("  simulation did not have access to them.")
    print()
    print("    Sena et al.   (Berlin)  measured 3.6% - 5.5%")
    print("    Minder et al. (Nicosia) measured 0.88% - 1.50%")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="schema probe only")
    ap.add_argument("--emit", action="store_true", help="print the config")
    ap.add_argument("--run", action="store_true", help="run the simulation")
    ap.add_argument("--scenario", default="MTL_CORE", choices=list(SCENARIOS))
    ap.add_argument("--profile", default="modest", choices=list(PROFILES))
    ap.add_argument("--link", default="heralded",
                    choices=["heralded", "depolarise"])
    ap.add_argument("--rounds", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    hw = PROFILES[a.profile]
    if a.emit:
        print(make_config(a.scenario, hw, a.link))
        return 0
    if a.check:
        return cmd_check(a.scenario, hw, a.link)
    if a.run:
        return cmd_run(a.scenario, hw, a.link, a.rounds, a.seed)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
