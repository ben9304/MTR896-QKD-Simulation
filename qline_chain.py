"""
MTR896 - Phase 3/4: generalised N-Charlie Qline. SELF-CONTAINED.

    python3 qline_chain.py --check                      # schema probe
    python3 qline_chain.py --emit --charlies 3          # print the config
    python3 qline_chain.py --run --charlies 2 --rounds 600
    python3 qline_chain.py --sweep --rounds 600         # node ceiling
    python3 qline_chain.py --sweep --hop 20 --max-n 8

Use the SAME interpreter that has SquidASM, e.g.
    ~/qkd-env/bin/python qline_chain.py --check

==========================================================================
WHY THIS FILE EXISTS, AND WHY IT IS NOT montreal_mesh.py
==========================================================================
montreal_mesh.py implements ONE Charlie using entanglement swapping. That
construction is correct at N=1 and CANNOT be extended. Verified exactly
by statevector enumeration: for N>=2 only the FIRST Charlie may choose a
basis freely; with any later Charlie active, rA^rB is NON-DETERMINISTIC
in 12 of 16 basis combinations at N=2 and 28 of 32 at N=3. The key does
not merely come out wrong - it does not exist.

The reason is physical. In a Qline, Charlie rotates a TRAVELLING photon
and the phase accumulates down the line. Under entanglement swapping,
Charlie rotates one half of an EPR pair and then consumes it in a Bell
measurement. Those are different operations: each swap scrambles the
next rotation's reference frame.

So this file uses PREPARE-AND-MEASURE, which is also what the reference
deployments actually do. Verified exhaustively for N = 1..8: zero
non-deterministic configurations, zero key errors, and the sifting
condition is tight (no deterministic case is wrongly rejected).

SquidASM cannot send a bare photon - the stack moves qubits only through
EPR sockets - so prepare-and-measure is realised as a chain of
TELEPORTATIONS. Verified exhaustively for N = 1..4 that this reproduces
prepare-and-measure EXACTLY, provided each node applies its Pauli
correction BEFORE its rotation. X and RY do not commute: with the
rotation first, 94% of configurations break. That ordering is the
protocol.

==========================================================================
ARCHITECTURAL CAVEAT - STATE THIS IN PHASE 4
==========================================================================
A teleportation chain is a QUANTUM REPEATER, not a passive optical line.
Every hop costs a CNOT and two measurements, so gate noise accumulates
per node in a way it does not in a deployment where Charlie is a
modulator the photon passes through. The node ceiling this file reports
will therefore be LOWER than a pass-through Qline's for reasons of
ARCHITECTURE, not hardware. Saying so is what makes the comparison
honest rather than unflattering.

==========================================================================
VERIFIED RELATIONS (exact statevector enumeration, N = 1..8)
==========================================================================
    sift  :  (bA + SUM_i bCi - bB) mod 2 == 0
    key   :  rB = rA XOR (SUM_i bit_i mod 2) XOR carry
    carry :  ((bA + SUM_i bCi - bB) mod 4) // 2

Note the MINUS on Bob's basis, and that the trailing bA term of the
entanglement-based formula is absent here.

==========================================================================
INPUTS vs OUTPUTS
==========================================================================
INPUTS   hop length, Charlie count, visibility, dark counts, detector
         efficiency, gate depolarisation, node insertion loss, fibre
         attenuation built from cited component specs
OUTPUTS  QBER, sifting fraction, node ceiling

No quantity from a reference paper's RESULTS section is an input.
"""

import argparse
import math
import os
import random
import sys
import tempfile

# ==========================================================================
# INPUTS: hardware profiles (identical to montreal_mesh.py)
# ==========================================================================

class Hardware:
    def __init__(self, name, visibility, p_dark, eta_det, node_loss_db,
                 depolar_1q, depolar_2q):
        self.name = name
        self.visibility = visibility
        self.p_dark = p_dark
        self.eta_det = eta_det
        self.node_loss_db = node_loss_db
        self.depolar_1q = depolar_1q
        self.depolar_2q = depolar_2q


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

# Fibre loss from cited component specs, NOT from any paper's results.
#   fibre @1550 nm  0.22 dB/km   Prysmian G.652.D datasheet
#   fusion splice   0.15 dB      FOA loss-budget reference
#   drum length     4.0 km       typical metro pull
#   connector       0.30 dB      FOA (TIA-568 max 0.75)
FIBRE_DB_KM        = 0.22
SPLICE_DB          = 0.15
DRUM_KM            = 4.0
CONNECTOR_DB       = 0.30
ATTENUATION        = FIBRE_DB_KM + SPLICE_DB / DRUM_KM     # 0.2575
CONNECTORS_PER_HOP = 2

QBER_THRESHOLD = 0.11
DEFAULT_HOP_KM = 10.0      # adjacent-borough spacing on the island

# Entanglement-attempt duration. netsquid-netbuilder DEFAULTS THIS TO 0,
# which makes every attempt free: loss then costs no time and the key rate
# cannot reflect distance at all. It must be set explicitly.
# Stated as a source repetition rate, which is the citable quantity:
SOURCE_REP_RATE_HZ = 100e6              # 100 MHz pulsed source
EMISSION_DURATION_NS = 1e9 / SOURCE_REP_RATE_HZ      # = 10 ns per attempt

_SEEDED_NS = False         # set by _seed_everything()


# ==========================================================================
# MONTREAL GEOGRAPHY  (optional: --route)
# ==========================================================================
# By default this file simulates a chain of UNIFORM hops (--hop). With
# --route it instead uses the real per-hop distances of a named Montreal
# route, so the geography becomes a simulation INPUT rather than an
# interpretation applied to the results afterwards.
#
# Off-island sites are routed through an actual bridge or tunnel: fibre
# does not cross water wherever it likes. Anjou->Varennes is 13.7 km
# straight but 18.7 km routed, because it must detour to the
# Louis-Hippolyte-La Fontaine tunnel.
PLACES = {
    "PointeClaire": (45.4486, -73.8200), "StLaurent": (45.5100, -73.6800),
    "UdeM": (45.5048, -73.6168), "Loyola": (45.4581, -73.6397),
    "McGill": (45.5048, -73.5772), "ETS": (45.4945, -73.5631),
    "Concordia": (45.4972, -73.5789), "UQAM": (45.5088, -73.5617),
    "Longueuil": (45.5300, -73.5100), "Brossard": (45.4500, -73.4650),
    "Anjou": (45.6100, -73.5600), "Laval": (45.5600, -73.7450),
    "Varennes": (45.6420, -73.4520), "Repentigny": (45.7420, -73.4500),
}
CROSSINGS = {
    "MedericMartin": (45.5520, -73.7050), "PontViau": (45.5650, -73.6800),
    "PapineauLeblanc": (45.5750, -73.6450), "Champlain": (45.4650, -73.5200),
    "Victoria": (45.4800, -73.5250), "JacquesCartier": (45.5250, -73.5350),
    "LaFontaine": (45.5800, -73.5100),
}
SERVES = {
    "Laval": ["MedericMartin", "PontViau", "PapineauLeblanc"],
    "Longueuil": ["JacquesCartier", "Victoria"],
    "Brossard": ["Champlain", "Victoria"],
    "Varennes": ["LaFontaine"], "Repentigny": ["LaFontaine"],
}
ROUTE_FACTOR = 1.40          # on-land duct meander
_COORDS = {**PLACES, **CROSSINGS}

ROUTES = {
    # island / north spine, 9 sites
    "ISLAND": ["PointeClaire", "Loyola", "ETS", "McGill", "UdeM",
               "StLaurent", "Laval", "Anjou", "Repentigny"],
    # south shore, 3 sites
    "RIVESUD": ["Brossard", "Longueuil", "Varennes"],
    # west-east island span only
    "WESTEAST": ["PointeClaire", "StLaurent", "UdeM", "ETS", "McGill",
                 "Anjou", "Repentigny"],
}


def geodesic_km(a, b):
    R = 6371.0
    la1, lo1 = map(math.radians, _COORDS[a])
    la2, lo2 = map(math.radians, _COORDS[b])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def route_hop(a, b):
    """(km, crossing_or_None) for one hop, through the shortest crossing."""
    cands = SERVES.get(a, []) + SERVES.get(b, [])
    if not cands:
        return geodesic_km(a, b) * ROUTE_FACTOR, None
    best, via = None, None
    for x in dict.fromkeys(cands):
        d = (geodesic_km(a, x) + geodesic_km(x, b)) * ROUTE_FACTOR
        if best is None or d < best:
            best, via = d, x
    return best, via


def route_hops(route):
    """[(km, crossing), ...] for a named route or an explicit site list."""
    sites = ROUTES[route] if route in ROUTES else route.split(",")
    for s in sites:
        if s not in PLACES:
            raise SystemExit(f"unknown site: {s}\n"
                             f"known: {', '.join(sorted(PLACES))}")
    return sites, [route_hop(sites[i], sites[i+1])
                   for i in range(len(sites)-1)]


# ==========================================================================
# Verified protocol relations
# ==========================================================================

def sifts(bA, bCs, bB):
    return (bA + sum(bCs) - bB) % 2 == 0


def expected_key(bA, rA, bCs, bits, bB):
    carry = ((bA + sum(bCs) - bB) % 4) // 2
    return rA ^ (sum(bits) % 2) ^ carry


# ==========================================================================
# Config generation
# ==========================================================================

def node_names(n_charlies):
    return (["Alice"] + [f"Charlie{i+1}" for i in range(n_charlies)]
            + ["Bob"])


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


def make_config(n_charlies, hw, hops, link_type="heralded"):
    """`hops` is a list of per-link lengths in km (len == n_charlies+1)."""
    if not isinstance(hops, (list, tuple)):
        hops = [hops] * (n_charlies + 1)
    names = node_names(n_charlies)
    n_links = len(names) - 1

    out = [f"# MTR896 Qline chain, {n_charlies} Charlie(s),"
           f" profile {hw.name}",
           f"# path  : {' -> '.join(names)}",
           f"# hops  : {', '.join(f'{h:.1f}' for h in hops)} km"
           f"  ({sum(hops):.1f} km total)",
           f"# fibre : {ATTENUATION:.4f} dB/km",
           f"# nodes : {hw.node_loss_db} dB/Charlie"
           f" -> {n_charlies*hw.node_loss_db:.2f} dB",
           "",
           "qdevice: &qdevice", qdevice_block(hw, 3), "",
           "stacks:"]
    for nm in names:
        out.append(f"  - {{name: {nm}, qdevice_typ: generic,"
                   f" qdevice_cfg: {{<<: *qdevice}}}}")
    out += ["", "links:"]

    for i, hop_km in enumerate(hops):
        # Fixed loss on this hop: connectors at both ends, plus the
        # insertion loss of the Charlie this hop terminates at (not Bob).
        fixed_db = CONNECTORS_PER_HOP * CONNECTOR_DB
        if i < n_charlies:
            fixed_db += hw.node_loss_db
        # p_loss_init is a PER-SIDE parameter: a global value is applied
        # at BOTH ends of the link. Halve the dB so the intended total is
        # applied once per link, not twice.
        p_init = 1 - 10 ** (-(fixed_db / 2) / 10)
        out += [f"  - stack1: {names[i]}", f"    stack2: {names[i+1]}"]
        if link_type == "heralded":
            out += ["    typ: heralded", "    cfg:",
                    f"      length: {hop_km:.4f}",
                    f"      p_loss_init: {p_init:.6f}",
                    f"      p_loss_length: {ATTENUATION:.4f}",
                    "      speed_of_light: 200000",
                    f"      dark_count_probability: {hw.p_dark}",
                    f"      detector_efficiency: {hw.eta_det}",
                    f"      visibility: {hw.visibility}",
                    f"      emission_duration: {EMISSION_DURATION_NS:g}",
                    "      num_resolving: False"]
        else:
            out += ["    typ: depolarise", "    cfg:",
                    f"      fidelity: {hw.visibility:.4f}"]

    out += ["", "clinks:"]
    # Corrections travel one hop forward only; sifting is done offline by
    # the runner from each program's returned basis, so no other classical
    # links are needed.
    for i in range(n_links):
        out.append(f"  - {{stack1: {names[i]}, stack2: {names[i+1]},"
                   f" typ: default, cfg: {{delay: 1000000}}}}")
    return "\n".join(out) + "\n"


# ==========================================================================
# Programs
# ==========================================================================

def _load_squidasm():
    from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
    from squidasm.run.stack.config import StackNetworkConfig
    from squidasm.run.stack.run import run
    return Program, ProgramContext, ProgramMeta, StackNetworkConfig, run


def _qubit_class():
    """netqasm has moved Qubit between modules across versions."""
    try:
        from netqasm.sdk.qubit import Qubit
        return Qubit
    except ImportError:
        from netqasm.sdk import Qubit
        return Qubit


def theta_units(theta):
    """rot_Y(n, d) applies n*pi/2^d. With d=1, n = theta/(pi/2)."""
    return int(round(theta / (math.pi / 2))) % 4


def build_programs(n_charlies):
    Program, ProgramContext, ProgramMeta, _, _ = _load_squidasm()
    names = node_names(n_charlies)

    def teleport_forward(context, q, right):
        """Bell-measure the travelling qubit q against a fresh EPR half
        shared with `right`, then send the two outcomes forward.
        Caller must flush before this returns usable values."""
        e = context.epr_sockets[right].create_keep()[0]
        q.cnot(e)
        q.H()
        m1 = q.measure()
        m2 = e.measure()
        return m1, m2

    class AliceProgram(Program):
        RIGHT = names[1]

        @property
        def meta(self):
            return ProgramMeta(name="Qline_Alice", csockets=[self.RIGHT],
                               epr_sockets=[self.RIGHT], max_qubits=3)

        def run(self, context):
            # Drawn per round: run() is called once per round, __init__
            # only once for the whole campaign.
            basis = random.randint(0, 1)
            bit = random.randint(0, 1)
            conn = context.connection
            q = _qubit_class()(conn)
            if bit:
                q.X()
            n = theta_units(basis * math.pi / 2)
            if n:
                q.rot_Y(n, 1)
            m1, m2 = teleport_forward(context, q, self.RIGHT)
            yield from conn.flush()
            cs = context.csockets[self.RIGHT]
            cs.send_int(int(m1))
            cs.send_int(int(m2))
            return {"basis": basis, "bit": bit}

    def make_charlie(idx):
        left, me, right = names[idx - 1], names[idx], names[idx + 1]

        class CharlieProgram(Program):
            @property
            def meta(self):
                return ProgramMeta(name=f"Qline_{me}",
                                   csockets=[left, right],
                                   epr_sockets=[left, right], max_qubits=3)

            def run(self, context):
                basis = random.randint(0, 1)
                bit = random.randint(0, 1)
                conn = context.connection
                q = context.epr_sockets[left].recv_keep()[0]
                # Flush BEFORE blocking on a classical recv: recv_keep
                # only queues the request, which executes at flush.
                # Blocking first deadlocks against the sender's flush.
                yield from conn.flush()
                cl = context.csockets[left]
                m1 = yield from cl.recv_int()
                m2 = yield from cl.recv_int()
                # CORRECT FIRST, THEN ROTATE. Reversing this breaks the
                # protocol in 94% of configurations - X and RY do not
                # commute.
                if m2:
                    q.X()
                if m1:
                    q.Z()
                n = theta_units(basis * math.pi / 2 + bit * math.pi)
                if n:
                    q.rot_Y(n, 1)
                o1, o2 = teleport_forward(context, q, right)
                yield from conn.flush()
                cr = context.csockets[right]
                cr.send_int(int(o1))
                cr.send_int(int(o2))
                return {"basis": basis, "bit": bit}

        return CharlieProgram

    class BobProgram(Program):
        LEFT = names[-2]

        @property
        def meta(self):
            return ProgramMeta(name="Qline_Bob", csockets=[self.LEFT],
                               epr_sockets=[self.LEFT], max_qubits=3)

        def run(self, context):
            basis = random.randint(0, 1)
            conn = context.connection
            q = context.epr_sockets[self.LEFT].recv_keep()[0]
            yield from conn.flush()
            cl = context.csockets[self.LEFT]
            m1 = yield from cl.recv_int()
            m2 = yield from cl.recv_int()
            if m2:
                q.X()
            if m1:
                q.Z()
            # Bob rotates BACK by his basis, then measures in Z.
            n = theta_units(-basis * math.pi / 2)
            if n:
                q.rot_Y(n, 1)
            out = q.measure()
            yield from conn.flush()
            return {"basis": basis, "measured": int(out)}

    return (AliceProgram, [make_charlie(i + 1) for i in range(n_charlies)],
            BobProgram)


# ==========================================================================
# Runner
# ==========================================================================

def budget_db(n_charlies, hw, hops):
    """PER-LINK optical budget - the physically meaningful quantity.

    In a repeater chain each heralded link is independent and the optical
    budget RESETS at every node. Summing loss along the whole chain, as
    an earlier version of this file did, describes a single unbroken
    fibre that does not exist here: no photon ever traverses it. Reporting
    that sum as a budget was wrong and made loss look inert.

    Returns (fibre_per_link, connectors_per_link, node, total_per_link).
    """
    if not isinstance(hops, (list, tuple)):
        hops = [hops]
    fibre = max(hops) * ATTENUATION          # worst link sets the budget
    conn = CONNECTORS_PER_HOP * CONNECTOR_DB
    nodes = hw.node_loss_db
    return fibre, conn, nodes, fibre + conn + nodes


def _write_cfg(text):
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    return path


def _seed_everything(seed):
    """Seed BOTH RNGs.

    random.seed() controls only the basis/bit choices inside the programs.
    The quantum noise - loss, dark counts, visibility, gate depolarisation
    - is drawn by NetSquid's own RNG. Without seeding that too, repeated
    runs of the same command return DIFFERENT QBER, which was observed:
    9.21% then 12.50% at identical settings and seed.
    """
    global _SEEDED_NS
    random.seed(seed)
    try:
        import netsquid as ns
        ns.set_random_state(seed=seed)
        _SEEDED_NS = True
    except Exception:
        _SEEDED_NS = False
        try:
            import numpy as _np
            _np.random.seed(seed)
        except Exception:
            pass
    return _SEEDED_NS


def simulate(n_charlies, hw, hops, link_type, rounds, seed, quiet=False):
    """Return (sifted, errors, rounds). QBER = errors / sifted."""
    _, _, _, StackNetworkConfig, run = _load_squidasm()
    Alice, Charlies, Bob = build_programs(n_charlies)
    names = node_names(n_charlies)

    _seed_everything(seed)
    path = _write_cfg(make_config(n_charlies, hw, hops, link_type))
    try:
        cfg = StackNetworkConfig.from_file(path)
    finally:
        os.remove(path)

    programs = {names[0]: Alice()}
    for i, C in enumerate(Charlies):
        programs[names[i + 1]] = C()
    programs[names[-1]] = Bob()

    results = run(config=cfg, programs=programs, num_times=rounds)
    # squidasm's run() calls sim_reset() internally, so the clock starts at
    # 0 for THIS run. Read it after, and do NOT subtract a pre-run value -
    # that was a bug which made rate appear to RISE with loss.
    try:
        import netsquid as _ns
        _elapsed_ns = _ns.sim_time()
    except Exception:
        _elapsed_ns = None
    # run() returns per stack in CONFIG stack order.
    res = dict(zip(names, results))

    sifted = errors = 0
    for r in range(rounds):
        a = res[names[0]][r]
        b = res[names[-1]][r]
        cs = [res[names[i + 1]][r] for i in range(n_charlies)]
        bCs = [c["basis"] for c in cs]
        bits = [c["bit"] for c in cs]
        if not sifts(a["basis"], bCs, b["basis"]):
            continue
        sifted += 1
        want = expected_key(a["basis"], a["bit"], bCs, bits, b["basis"])
        if b["measured"] != want:
            errors += 1
    return sifted, errors, rounds, _elapsed_ns


def cmd_check(n_charlies, hw, hops, link_type):
    _, _, _, StackNetworkConfig, _ = _load_squidasm()
    path = _write_cfg(make_config(n_charlies, hw, hops, link_type))
    try:
        StackNetworkConfig.from_file(path)
    except Exception as e:
        print("SCHEMA CHECK FAILED")
        print(f"  link type : {link_type}")
        print(f"  error     : {type(e).__name__}: {e}")
        if link_type == "heralded":
            print("  Retry with --link depolarise.")
        return 1
    finally:
        if os.path.exists(path):
            os.remove(path)
    print(f"SCHEMA CHECK PASSED  ({link_type}, {n_charlies} Charlie(s),"
          f" profile {hw.name})")
    return 0


def repeated(n_charlies, hw, hops, link_type, rounds, seed, repeats):
    """Pool `repeats` independent runs. Returns pooled counts plus the
    per-run QBER list, so the spread ACROSS runs can be reported - that is
    the honest uncertainty, since sim_reset() defeats seeding."""
    tot_s = tot_e = tot_r = 0
    el = 0.0
    qs = []
    for i in range(repeats):
        s_, e_, r_, ela = simulate(n_charlies, hw, hops, link_type,
                                   rounds, seed + i)
        tot_s += s_; tot_e += e_; tot_r += r_
        if ela:
            el += ela
        if s_:
            qs.append(e_ / s_)
    return tot_s, tot_e, tot_r, (el or None), qs


def cmd_run(n_charlies, hw, hops, link_type, rounds, seed, repeats=1,
            sites=None):
    if not isinstance(hops, (list, tuple)):
        hops = [hops] * (n_charlies + 1)
    fibre, conn, nodes, total = budget_db(n_charlies, hw, hops)
    sifted, errors, rounds, elapsed, qs = repeated(
        n_charlies, hw, hops, link_type, rounds, seed, repeats)
    names = node_names(n_charlies)
    print("=" * 72)
    print(f"  Qline chain: {n_charlies} Charlie(s)   profile: {hw.name}"
          f"   link: {link_type}")
    print("=" * 72)
    print(f"  path      : {' -> '.join(sites or names)}")
    if len(set(hops)) == 1:
        print(f"  hops      : {len(hops)} x {hops[0]:g} km"
              f" = {sum(hops):g} km")
    else:
        print(f"  hops      : {', '.join(f'{h:.1f}' for h in hops)} km"
              f"   = {sum(hops):.1f} km  [REAL GEOGRAPHY]")
    print(f"  worst link: fibre {fibre:.2f} + connectors {conn:.2f}"
          f" + node {nodes:.2f} = {total:.2f} dB   [INPUT]")
    print(f"              (budget RESETS at every node - there is no"
          f" cumulative dB)")
    if len(qs) > 1:
        print(f"  rounds    : {rounds // len(qs)} x {len(qs)} repeats"
              f" = {rounds} pooled")
    else:
        print(f"  rounds    : {rounds}")
    print(f"  note      : NetSquid re-randomises inside run(), so runs are")
    print(f"              NOT seed-reproducible. Use --repeats and quote the")
    print(f"              pooled QBER with its interval.")
    print("-" * 72)
    print(f"  sifted    : {sifted} ({sifted/rounds:.1%}, expect ~50%)")
    if sifted:
        q = errors / sifted
        se = math.sqrt(max(q * (1 - q), 1e-12) / sifted)
        print(f"  QBER      : {q:.2%}  +/- {se:.2%} (1 s.e.)"
              f"   [OUTPUT]")
        lo, hi = q - 2 * se, q + 2 * se
        if lo > QBER_THRESHOLD:
            verdict = "ABOVE 11% THRESHOLD"
        elif hi < QBER_THRESHOLD:
            verdict = "SECURE"
        else:
            verdict = (f"INCONCLUSIVE - 95% CI [{max(lo,0):.2%}, {hi:.2%}]"
                       f" straddles 11%; run more rounds")
        print(f"  verdict   : {verdict}")
        if len(qs) > 1:
            print(f"  per-run   : "
                  + ", ".join(f"{x:.2%}" for x in qs)
                  + f"   (spread {max(qs)-min(qs):.2%})")
        if elapsed:
            secs = elapsed * 1e-9
            print(f"  sim time  : {secs:.4g} s for {rounds} rounds")
            print(f"  key rate  : {(sifted-errors)/secs:.4g} bit/s"
                  f"   [OUTPUT - this is where loss bites, not QBER:")
            print(f"              a heralded link discards failed attempts,")
            print(f"              so loss costs RATE, not fidelity]")
    else:
        print("  QBER      : no sifted rounds")
    print("=" * 72)
    return 0


def cmd_sweep(hw_names, hop_km, link_type, rounds, seed, max_n,
              repeats=1, full_curve=False):
    print("=" * 72)
    print(f"  NODE CEILING SWEEP   hop {hop_km:g} km,"
          f" {rounds} rounds, {link_type} link")
    print("=" * 72)
    print("  Walks the Charlie count upward until simulated QBER crosses")
    print(f"  the {QBER_THRESHOLD:.0%} BB84 threshold. The last secure N is")
    print("  the node ceiling for that hardware profile.")
    ceilings = {}
    for hname in hw_names:
        hw = hname if isinstance(hname, Hardware) else PROFILES[hname]
        hname = hw.name
        print()
        print(f"  profile: {hname}  (visibility {hw.visibility},"
              f" 2q depolar {hw.depolar_2q}, {hw.node_loss_db} dB/node)")
        print(f"    {'N':>3}{'nodes':>7}{'km':>8}{'dB/lnk':>8}"
              f"{'sifted':>8}{'QBER':>9}{'+/-':>8}  verdict")
        ceiling = 0
        first_fail = None
        stop_reason = "reached max-n"
        for N in range(1, max_n + 1):
            _, _, _, total = budget_db(N, hw, hop_km)
            try:
                sifted, errors, _, elapsed, _qs = repeated(
                    N, hw, [hop_km]*(N+1), link_type, rounds, seed, repeats)
            except Exception as e:
                print(f"    {N:>3}  simulation failed:"
                      f" {type(e).__name__}: {e}")
                break
            if not sifted:
                print(f"    {N:>3}{N+2:>7}{hop_km*(N+1):>8.1f}"
                      f"{total:>8.2f}{0:>8}{'-':>9}{'-':>8}  no sifted rounds")
                break
            q = errors / sifted
            se = math.sqrt(max(q * (1 - q), 1e-12) / sifted)
            lo, hi = q - 2 * se, q + 2 * se
            if hi < QBER_THRESHOLD:
                tag, ok = "secure", True
            elif lo > QBER_THRESHOLD:
                tag, ok = "ABOVE THRESHOLD", False
            else:
                tag, ok = "inconclusive (CI straddles 11%)", False
            if ok and first_fail is None:
                ceiling = N
            rate = ((sifted-errors)/(elapsed*1e-9)) if elapsed else float('nan')
            print(f"    {N:>3}{N+2:>7}{hop_km*(N+1):>8.1f}{total:>8.2f}"
                  f"{sifted:>8}{q:>8.2%}{se:>8.2%}{rate:>12.3g}  {tag}")
            if not ok and not full_curve:
                stop_reason = ("INCONCLUSIVE at N=%d - more rounds needed"
                               % N) if "inconclusive" in tag else (
                               "QBER above threshold at N=%d" % N)
                break
            if not ok and first_fail is None:
                first_fail = N
                stop_reason = ("first failure at N=%d (%s); curve continued"
                               % (N, "inconclusive"
                                  if "inconclusive" in tag else "above"))
        ceilings[hname] = (ceiling, stop_reason)
    print()
    print("=" * 72)
    print("  NODE CEILING  [OUTPUT]")
    if full_curve:
        print("  Full curve taken. Report the CROSSING AS AN INTERVAL, not")
        print("  a single N: a thresholded ceiling moves with noise, the")
        print("  curve does not.")
    for hname, (c, why) in ceilings.items():
        if c:
            print(f"    {hname}")
            print(f"      -> {c} Charlie(s), {c+2} nodes,"
                  f" {hop_km*(c+1):g} km reach")
            print(f"      stopped: {why}")
        else:
            print(f"    {hname}")
            print(f"      -> no secure N established")
            print(f"      reason: {why}")
    print()
    print("  Compare to published figures ONLY now. Neither entered the")
    print("  simulation, so the comparison carries information:")
    print("    Sena et al.   projected 12 nodes (their own extrapolation)")
    print("    Nicosia       7 end nodes (measured deployment)")
    print()
    print("  Remember the architectural caveat: this is a teleportation")
    print("  chain (a repeater), so gate noise accumulates per node in a")
    print("  way a pass-through modulator Qline avoids. A lower ceiling")
    print("  here is an architecture difference, not a hardware one.")
    print("=" * 72)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--charlies", type=int, default=2)
    ap.add_argument("--hop", type=float, default=DEFAULT_HOP_KM,
                    help="km per hop, uniform (default 10)")
    ap.add_argument("--route", default=None,
                    help="named Montreal route (" + ", ".join(ROUTES)
                         + ") or a comma-separated list of sites. Uses the "
                           "REAL per-hop distances instead of --hop, so the "
                           "geography is a simulation input.")
    ap.add_argument("--profile", default="modest", choices=list(PROFILES))
    ap.add_argument("--all-profiles", action="store_true",
                    help="sweep every profile")
    ap.add_argument("--link", default="heralded",
                    choices=["heralded", "depolarise"])
    ap.add_argument("--rounds", type=int, default=600)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-n", type=int, default=20)
    ap.add_argument("--repeats", type=int, default=1,
                    help="independent runs to pool (default 1)")
    # One-at-a-time component study: hold a profile and change a single
    # parameter. The bundled profiles vary several at once, so they cannot
    # attribute a result to any one component.
    ap.add_argument("--visibility", type=float, default=None)
    ap.add_argument("--depolar2q", type=float, default=None)
    ap.add_argument("--depolar1q", type=float, default=None)
    ap.add_argument("--node-loss", type=float, default=None)
    ap.add_argument("--p-dark", type=float, default=None)
    ap.add_argument("--eta-det", type=float, default=None)
    ap.add_argument("--full-curve", action="store_true",
                    help="do not stop at the threshold - sweep every N up "
                         "to --max-n so the whole QBER curve can be "
                         "plotted. A thresholded ceiling is a noisy "
                         "statistic; the curve is not.")
    a = ap.parse_args()

    base = PROFILES[a.profile]
    ov = [("visibility", a.visibility), ("depolar_2q", a.depolar2q),
          ("depolar_1q", a.depolar1q), ("node_loss_db", a.node_loss),
          ("p_dark", a.p_dark), ("eta_det", a.eta_det)]
    ov = [(k, v) for k, v in ov if v is not None]
    if ov:
        name = a.profile + "+" + ",".join(f"{k}={v:g}" for k, v in ov)
        hw = Hardware(name, base.visibility, base.p_dark, base.eta_det,
                      base.node_loss_db, base.depolar_1q, base.depolar_2q)
        for k, v in ov:
            setattr(hw, k, v)
        print(f"OVERRIDE: {a.profile} with "
              + ", ".join(f"{k}={v:g}" for k, v in ov))
        print("  (one-at-a-time study - results are NOT the stock profile)")
    else:
        hw = base
    sites = None
    hops = a.hop
    ncharlies = a.charlies
    if a.route:
        sites, detail = route_hops(a.route)
        hops = [d[0] for d in detail]
        ncharlies = len(sites) - 2
        vias = [d[1] for d in detail if d[1]]
        print(f"ROUTE: {' -> '.join(sites)}")
        print(f"  {len(sites)} sites, {ncharlies} Charlies, "
              f"{sum(hops):.1f} km"
              + (f", crossings: {', '.join(vias)}" if vias else ""))
    if a.emit:
        print(make_config(ncharlies, hw, hops, a.link))
        return 0
    if a.check:
        return cmd_check(ncharlies, hw, hops, a.link)
    if a.run:
        return cmd_run(ncharlies, hw, hops, a.link, a.rounds,
                       a.seed, a.repeats, sites)
    if a.sweep:
        hws = list(PROFILES) if a.all_profiles else [hw]
        return cmd_sweep(hws, a.hop, a.link, a.rounds, a.seed,
                         a.max_n, a.repeats, a.full_curve)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
