"""
MTR896 - Phase 2 (scope-correct version): Qiskit node-level implementation.

Phase 2 deliverable, per approved methodology:
    "Implementer la logique quantique de chaque noeud (Alice, Bob et
    noeuds intermediaires/repeteurs) sous forme de circuits Qiskit."
    "Livrable intermediaire: Un module Python fonctionnel simulant une
    liaison point-a-point simple dans Qiskit pur (sans bruit reseau)."

This file does ONLY that:
    - defines the quantum logic for each node role (Alice, intermediate
      nodes, Bob) as Qiskit circuit operations
    - runs ONE point-to-point / multi-hop exchange, pure Qiskit, no noise
    - verifies the result is internally consistent (Doosti's XOR
      invariant), since that is a property of the protocol LOGIC itself,
      not a comparison to published results

Explicitly OUT of scope here (belongs to later phases):
    - noise/loss modeling                -> Phase 3 (SquidASM/NetSquid)
    - QBER / secret key rate statistics  -> Phase 4 (benchmarking)
    - comparison to Sena/Doosti figures  -> Phase 4 (validation)

Protocol logic follows the general phase/rotation-accumulation rule
described in both reference papers (not their specific worked-example
values):
    Sena et al. (2024), IEEE Photonics Journal, Eq. 2-4.
    Doosti et al. (2024), IEEE QCNC, Section 3.2.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib
matplotlib.use("Agg")


# --------------------------------------------------------------------------
# Node logic
# --------------------------------------------------------------------------

@dataclass
class Node:
    """
    A single Qline participant's quantum logic for one round.

    basis : random basis choice (0 or 1)
    bit   : random key bit (0 or 1). Unused for the terminal receiver
            (Bob), who does not encode a bit, only chooses a basis.
    """
    name: str
    is_terminal_receiver: bool = False
    basis: int = field(init=False)
    bit: int = field(init=False)

    def __post_init__(self):
        self.basis = random.randint(0, 1)
        self.bit = 0 if self.is_terminal_receiver else random.randint(0, 1)

    def rotation_angle(self) -> float:
        if self.is_terminal_receiver:
            return self.basis * (math.pi / 2)
        return self.basis * (math.pi / 2) + self.bit * math.pi


def alice_prepare(qc: QuantumCircuit, qubit: int, alice: Node) -> None:
    """Alice's node logic: initialize and apply her rotation."""
    qc.ry(alice.rotation_angle(), qubit)


def charlie_transform(qc: QuantumCircuit, qubit: int, node: Node) -> None:
    """A Charlie (intermediate/repeater) node's logic: apply its rotation only."""
    qc.ry(node.rotation_angle(), qubit)


def bob_measure(qc: QuantumCircuit, qubit: int, clbit: int, bob: Node) -> None:
    """Bob's node logic: apply his rotation, then measure."""
    qc.ry(bob.rotation_angle(), qubit)
    qc.measure(qubit, clbit)


# --------------------------------------------------------------------------
# Build one point-to-point / multi-hop circuit (Phase 2 deliverable)
# --------------------------------------------------------------------------

def build_circuit(alice: Node, charlies: List[Node], bob: Node) -> QuantumCircuit:
    """
    Assemble one full round as a single Qiskit circuit: Alice's node,
    each intermediate node, then Bob's node. Pure Qiskit, no noise.
    """
    qc = QuantumCircuit(1, 1)
    alice_prepare(qc, 0, alice)
    for node in charlies:
        charlie_transform(qc, 0, node)
    bob_measure(qc, 0, 0, bob)
    return qc


# --------------------------------------------------------------------------
# Correctness check: Doosti's XOR invariant (a property of the LOGIC,
# not a comparison against the papers' numerical results)
# --------------------------------------------------------------------------

def basis_match(alice: Node, charlies: List[Node], bob: Node) -> bool:
    x = alice.basis
    for n in charlies:
        x ^= n.basis
    x ^= bob.basis
    return x == 0


def expected_key_bit(alice: Node, charlies: List[Node], bob: Node) -> int:
    bit_sum = alice.bit
    for n in charlies:
        bit_sum ^= n.bit
    basis_sum_mod4 = (alice.basis + sum(n.basis for n in charlies) + bob.basis) % 4
    return bit_sum ^ (basis_sum_mod4 // 2)


# --------------------------------------------------------------------------
# Run one round and report the node-level circuit + outcome
# --------------------------------------------------------------------------

if __name__ == "__main__":
    N_CHARLIES = 2  # Alice - Charlie1 - Charlie2 - Bob (matches Sena/Doosti topology)

    alice = Node(name="Alice")
    charlies = [Node(name=f"Charlie{i+1}") for i in range(N_CHARLIES)]
    bob = Node(name="Bob", is_terminal_receiver=True)

    qc = build_circuit(alice, charlies, bob)

    # Save the circuit diagram (this IS a Phase 2 artifact -- it shows
    # the node-level quantum logic your methodology asks you to build).
    fig = qc.draw("mpl")
    fig.savefig("qline_node_circuit.png", bbox_inches="tight", dpi=150)
    print("Circuit diagram saved to: qline_node_circuit.png\n")

    print(qc.draw())

    # Run the single round.
    backend = AerSimulator()
    job = backend.run(qc, shots=1)
    measured = int(list(job.result().get_counts().keys())[0])

    matched = basis_match(alice, charlies, bob)

    print(f"\nAlice   : basis={alice.basis}, bit={alice.bit}")
    for n in charlies:
        print(f"{n.name:8}: basis={n.basis}, bit={n.bit}")
    print(f"Bob     : basis={bob.basis}")
    print(f"\nBasis match (public announcement accepted): {matched}")

    if matched:
        expected = expected_key_bit(alice, charlies, bob)
        print(f"Expected key bit (from protocol logic): {expected}")
        print(f"Measured bit:                           {measured}")
        print(f"Logic self-consistent: {expected == measured}")
    else:
        print("Round discarded during sifting (basis mismatch).")
