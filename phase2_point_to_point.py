"""
MTR896 - Phase 2, point-to-point deliverable (literal scope).

Methodology wording: "Un module Python fonctionnel simulant une liaison
point-a-point simple dans Qiskit pur (sans bruit reseau)."

This is a SIMPLE POINT-TO-POINT link: Alice -> Bob directly, with NO
Charlie/intermediate nodes. This is the minimal building block before
extending to the multi-hop Qline chain (Alice-Charlie-...-Bob), which
belongs in a separate module (phase2_qiskit_nodes.py) once this simpler
case is validated on its own.

Encoding follows the same rotation rule used throughout this project
(Doosti et al. 2024, Section 3.2 / Sena et al. 2024, Eq. 2-4), reduced
to the two-party case:
    theta_Alice = b_Alice * (pi/2) + r_Alice * pi
    theta_Bob   = b_Bob   * (pi/2)
"""

import math
import random
from dataclasses import dataclass, field

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib
matplotlib.use("Agg")


@dataclass
class Node:
    name: str
    is_bob: bool = False
    basis: int = field(init=False)
    bit: int = field(init=False)

    def __post_init__(self):
        self.basis = random.randint(0, 1)
        self.bit = 0 if self.is_bob else random.randint(0, 1)

    def rotation_angle(self) -> float:
        if self.is_bob:
            return self.basis * (math.pi / 2)
        return self.basis * (math.pi / 2) + self.bit * math.pi


def alice_prepare(qc: QuantumCircuit, qubit: int, alice: Node) -> None:
    """Alice's node logic: initialize and apply her rotation."""
    qc.ry(alice.rotation_angle(), qubit)


def bob_measure(qc: QuantumCircuit, qubit: int, clbit: int, bob: Node) -> None:
    """Bob's node logic: apply his rotation, then measure."""
    qc.ry(bob.rotation_angle(), qubit)
    qc.measure(qubit, clbit)


def build_point_to_point_circuit(alice: Node, bob: Node) -> QuantumCircuit:
    """Alice -> Bob directly. No Charlie / intermediate node."""
    qc = QuantumCircuit(1, 1)
    alice_prepare(qc, 0, alice)
    bob_measure(qc, 0, 0, bob)
    return qc


def basis_match(alice: Node, bob: Node) -> bool:
    return alice.basis == bob.basis


def expected_key_bit(alice: Node) -> int:
    """With no Charlie, no mod-4 correction term is needed: the key
    bit is simply Alice's raw bit, recovered directly by Bob when
    bases match."""
    return alice.bit


if __name__ == "__main__":
    alice = Node(name="Alice")
    bob = Node(name="Bob", is_bob=True)

    qc = build_point_to_point_circuit(alice, bob)

    fig = qc.draw("mpl")
    fig.savefig("point_to_point_circuit.png", bbox_inches="tight", dpi=150)
    print("Circuit diagram saved to: point_to_point_circuit.png\n")

    print(qc.draw())

    backend = AerSimulator()
    job = backend.run(qc, shots=1)
    measured = int(list(job.result().get_counts().keys())[0])

    matched = basis_match(alice, bob)

    print(f"\nAlice: basis={alice.basis}, bit={alice.bit}")
    print(f"Bob  : basis={bob.basis}")
    print(f"\nBasis match (public announcement accepted): {matched}")

    if matched:
        expected = expected_key_bit(alice)
        print(f"Expected key bit: {expected}")
        print(f"Measured bit:     {measured}")
        print(f"Logic self-consistent: {expected == measured}")
    else:
        print("Round discarded during sifting (basis mismatch).")
