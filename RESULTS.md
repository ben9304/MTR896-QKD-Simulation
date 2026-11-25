# MTR896 — Phase 3 results

QKD over a Montréal fibre network, simulated in SquidASM/NetSquid.

## What was simulated

A **linear chain** of N intermediate nodes (Charlies) between Alice and Bob:

```
Alice ── C1 ── C2 ── … ── CN ── Bob      max degree 2
```

Prepare-and-measure BB84, realised as a chain of teleportations over
heralded entanglement links. Each node applies its Pauli correction
**before** its rotation.

**Measured quantity: the end-to-end Alice↔Bob key pair.** This is the
longest path in the chain and therefore the binding case for a node
ceiling. Per-pairing (mesh) accounting is not included in this phase —
see *Open items*.

## Verified relations

Exhaustive statevector enumeration, N = 1…6, 21 840 sifted
configurations, zero key errors:

```
sift  :  (bA + Σ bCi − bB) mod 2 == 0
key   :  rB = rA ⊕ (Σ biti mod 2) ⊕ carry
carry :  ((bA + Σ bCi − bB) mod 4) // 2
```

The entanglement-swapping construction used in Phase 2 does **not**
generalise: for N ≥ 2 only the first Charlie may choose a basis freely,
and rA⊕rB is non-deterministic in most basis combinations. Teleportation
reproduces prepare-and-measure exactly, provided corrections precede
rotations — with the order reversed, 94 % of configurations fail.

## Inputs — all from component specifications

No quantity from any reference paper's results section is used as an input.

| Quantity | Value | Source |
|---|---|---|
| Fibre attenuation @1550 nm | 0.22 dB/km | Prysmian G.652.D datasheet |
| Fusion splice | 0.15 dB per 4 km drum | FOA loss-budget reference |
| → distributed loss | **0.2575 dB/km** | derived |
| Connector (FC/APC) | 0.25–0.30 dB | Exail/iXblue, FOA |
| Phase modulator | 2.0–3.5 dB | Exail/iXblue MPZ-LN |
| Optical switch | 0.6 dB typ | Agiltron NanoSpeed 1×1 |
| Source repetition rate | 100 MHz → 10 ns/attempt | stated design input |

Hardware profiles (visibility / 2q depolarising / node loss):
`modest` 0.92 / 0.050 / 4.0 dB · `good` 0.98 / 0.020 / 3.0 dB ·
`advanced` 0.99 / 0.005 / 2.5 dB.

## Results

Node ceiling — last N whose 95 % CI lies entirely below the 11 % BB84
threshold.

| Spacing | modest | good | advanced |
|---|---|---|---|
| 10 km | 0 | 3 — 5 nodes, 40 km | 10 — 12 nodes, 110 km |
| 25 km | 0 | 2 — 4 nodes, 75 km | **11 — 13 nodes, 300 km** |

At 25 km spacing, advanced hardware: QBER rises 1.79 % (N=1) to 9.94 %
(N=11), crossing 11 % between N=12 and N=13 — i.e. between 325 and
350 km. Key rate falls 61.5 → 33.9 bit/s over the same range.

**The node ceiling is nearly independent of spacing; the reach is not.**
Going from 10 km to 25 km hops leaves the advanced ceiling at 10–11
Charlies while reach grows 110 → 300 km. Distance costs rate, not
security, because a heralded link discards failed attempts rather than
counting them as errors.

### Component sensitivity (advanced, 25 km)

| Perturbation | Ceiling | Δ |
|---|---|---|
| baseline | 11 | — |
| visibility error ×2 | 8 | −3 |
| 2q gate error ×2 | 7 | −4 |
| 2q gate error ×4 | 5 | −6 |
| node insertion loss +20 % | 10 | −1 |

Doubling either the visibility error or the gate error costs 3–4 nodes;
a 20 % rise in insertion loss costs 1. **Error accumulation in the
quantum operations, not optical loss, sets the chain length.**

### Real Montréal geography (simulated, not interpolated)

Run with `--route`, using measured per-hop distances through actual
bridge and tunnel crossings rather than uniform spacing.

| Route | Nodes | Charlies | Span | Worst link | QBER advanced | QBER good |
|---|---|---|---|---|---|---|
| ISLAND | 9 | 7 | 110.1 km | 11.66 dB | **6.81 % ± 0.56 %** | 16.67 % ± 0.84 % |
| RIVESUD | 3 | 1 | 35.3 km | 8.07 dB | **1.21 % ± 0.70 %** | — |

ISLAND: Pointe-Claire → Loyola → ÉTS → McGill → UdeM → Saint-Laurent →
Laval → Anjou → Repentigny, crossing at Médéric-Martin,
Papineau-Leblanc and La Fontaine. Hops 19.7, 10.1, 2.2, 4.3, 6.9,
11.6, 21.9, 33.2 km — a factor of fifteen between shortest and longest,
with the 33.2 km Anjou–Repentigny link setting the budget alone.

RIVESUD: Brossard → Longueuil → Varennes, crossing at Victoria and
La Fontaine. Hops 16.0 and 19.3 km.

**Uniform spacing flatters the result.** At the same node count (N = 7)
uniform 10 km hops give 5.56 %; real geography gives 6.81 %. The
1.25-point difference comes from the single long hop.

**The island route requires advanced hardware.** Identical geography,
6.81 % on advanced against 16.67 % on good.

### Montréal implications

| Route | Distance | Hops @25 km | Result |
|---|---|---|---|
| Island span (Pointe-Claire → Repentigny) | 74 km | 3 | comfortable |
| Montréal → Sherbrooke | 170 km | 7 | 5.90 % — secure |
| Montréal → Québec City | 303 km | 12 | 9.94 % — at the limit |

The full Kirq corridor is reachable with **untrusted** intermediate
nodes. Unlike a Qline, where the optical budget accumulates along one
path, a repeater chain resets the budget at every node.

## Comparison (post-hoc only)

| | Nodes | Span |
|---|---|---|
| Sena et al., Berlin | 12 (projected) | 39.8 km deployed |
| Minder et al., Nicosia | 7 end nodes | metropolitan |
| **This work** | **13 (simulated)** | **300 km** |

Comparable node count, roughly seven times the reach. The mechanism is
architectural: a teleportation chain resets the budget per link, and
pays for it in gate fidelity at every node — the dominant limit found
above. Sena's Charlie is a pass-through modulator with no two-qubit
operation, so their binding constraint is loss, not gates.

## Reproducibility

NetSquid re-randomises inside `run()`, so results are **not**
seed-reproducible. Use `--repeats` and quote pooled QBER with its
interval. A thresholded ceiling is a noisy statistic — the same sweep
returned 10 and then 9 Charlies on consecutive runs. **Report the QBER
curve and state the crossing as an interval**, not a single integer.

## Open items

- **Per-pairing (mesh) accounting is not in `qline_chain.py`.** Only the
  end-to-end pair is measured. `montreal_mesh.py` does report all three
  pairings for a single Charlie, but has not been re-run since the link
  configuration was corrected.
- `montreal_mesh.py` still prints a cumulative dB budget, which is not
  physical for a chain; `qline_chain.py` reports per-link.
- UBQC second scope not started.
