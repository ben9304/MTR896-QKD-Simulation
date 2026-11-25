"""
QLINE PHASE 3 — First NetSquid/SquidASM Test
"""

import os
import tempfile
from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
from squidasm.run.stack.run import run
from squidasm.run.stack.config import StackNetworkConfig


NETWORK_YAML = """
stacks:
  - name: Alice
    qdevice_typ: generic
    qdevice_cfg:
      num_qubits: 5

  - name: Charlie
    qdevice_typ: generic
    qdevice_cfg:
      num_qubits: 5

  - name: Bob
    qdevice_typ: generic
    qdevice_cfg:
      num_qubits: 5

links:
  - name: alice_charlie
    stack1: Alice
    stack2: Charlie
    typ: perfect

  - name: charlie_bob
    stack1: Charlie
    stack2: Bob
    typ: perfect
"""


def get_config():
    fd, path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(NETWORK_YAML)
        return StackNetworkConfig.from_file(path)
    finally:
        os.remove(path)


class AliceProgram(Program):
    PEER = "Charlie"

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="alice",
            csockets=[],
            epr_sockets=[],
            max_qubits=1,
        )

    def run(self, context: ProgramContext):
        connection = context.connection
        q = connection.create_qubit()
        q.H()
        q.send(self.PEER)
        yield from connection.flush()
        return {"status": "sent"}


class CharlieProgram(Program):
    PEER_IN = "Alice"
    PEER_OUT = "Bob"

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="charlie",
            csockets=[],
            epr_sockets=[],
            max_qubits=1,
        )

    def run(self, context: ProgramContext):
        connection = context.connection
        q = connection.recv_qubit(self.PEER_IN)
        q.rot_Z(angle=0.5)
        q.send(self.PEER_OUT)
        yield from connection.flush()
        return {"status": "forwarded"}


class BobProgram(Program):
    PEER = "Charlie"

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="bob",
            csockets=[],
            epr_sockets=[],
            max_qubits=1,
        )

    def run(self, context: ProgramContext):
        connection = context.connection
        q = connection.recv_qubit(self.PEER)
        q.H()
        outcome = q.measure()
        yield from connection.flush()
        return {"measurement": int(outcome)}


if __name__ == "__main__":
    print("=" * 60)
    print("Running first NetSquid/SquidASM test...")
    print("=" * 60)

    cfg = get_config()

    results = run(
        config=cfg,
        programs={
            "Alice": AliceProgram(),
            "Charlie": CharlieProgram(),
            "Bob": BobProgram(),
        },
        num_times=1,
    )

    print("\nResults:")
    print(f"  Alice:   {results['Alice'][0]}")
    print(f"  Charlie: {results['Charlie'][0]}")
    print(f"  Bob:     {results['Bob'][0]}")
    print("\nNetSquid is working!")
