

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


def intermediate_transform(qc: QuantumCircuit, qubit: int, node: Node) -> None:
    """An intermediate/repeater node's logic: apply its rotation only."""
    qc.ry(node.rotation_angle(), qubit)


def bob_measure(qc: QuantumCircuit, qubit: int, clbit: int, bob: Node) -> None:
    """Bob's node logic: apply his rotation, then measure."""
    qc.ry(bob.rotation_angle(), qubit)
    qc.measure(qubit, clbit)




def build_circuit(alice: Node, intermediates: List[Node], bob: Node) -> QuantumCircuit:
    """
    Assemble one full round as a single Qiskit circuit: Alice's node,
    each intermediate node, then Bob's node. Pure Qiskit, no noise.
    """
    qc = QuantumCircuit(1, 1)
    alice_prepare(qc, 0, alice)
    for node in intermediates:
        intermediate_transform(qc, 0, node)
    bob_measure(qc, 0, 0, bob)
    return qc


def basis_match(alice: Node, intermediates: List[Node], bob: Node) -> bool:
    x = alice.basis
    for n in intermediates:
        x ^= n.basis
    x ^= bob.basis
    return x == 0


def expected_key_bit(alice: Node, intermediates: List[Node], bob: Node) -> int:
    bit_sum = alice.bit
    for n in intermediates:
        bit_sum ^= n.bit
    basis_sum_mod4 = (alice.basis + sum(n.basis for n in intermediates) + bob.basis) % 4
    return bit_sum ^ (basis_sum_mod4 // 2)




if __name__ == "__main__":
    N_INTERMEDIATE = 2  # Alice - Node1 - Node2 - Bob

    alice = Node(name="Alice")
    intermediates = [Node(name=f"Node{i+1}") for i in range(N_INTERMEDIATE)]
    bob = Node(name="Bob", is_terminal_receiver=True)

    qc = build_circuit(alice, intermediates, bob)

    # Save the circuit diagram (this IS a Phase 2 artifact 
    
    fig = qc.draw("mpl")
    fig.savefig("qline_node_circuit.png", bbox_inches="tight", dpi=150)
    print("Circuit diagram saved to: qline_node_circuit.png\n")

    print(qc.draw())

    # Run the single round.
    backend = AerSimulator()
    job = backend.run(qc, shots=1)
    measured = int(list(job.result().get_counts().keys())[0])

    matched = basis_match(alice, intermediates, bob)

    print(f"\nAlice   : basis={alice.basis}, bit={alice.bit}")
    for n in intermediates:
        print(f"{n.name:8}: basis={n.basis}, bit={n.bit}")
    print(f"Bob     : basis={bob.basis}")
    print(f"\nBasis match (public announcement accepted): {matched}")

    if matched:
        expected = expected_key_bit(alice, intermediates, bob)
        print(f"Expected key bit (from protocol logic): {expected}")
        print(f"Measured bit:                           {measured}")
        print(f"Logic self-consistent: {expected == measured}")
    else:
        print("Round discarded during sifting (basis mismatch).")
