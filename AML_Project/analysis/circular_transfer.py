"""Circular transfer detection using NetworkX directed cycles."""

import networkx as nx

from compiler.ast_nodes import TransferNode


def detect_circular_transfers(program):
    """Return directed account cycles, with the starting account repeated at the end."""
    graph = nx.DiGraph()
    for statement in program.statements:
        if isinstance(statement, TransferNode):
            graph.add_edge(statement.source_account, statement.destination_account)

    cycles = []
    seen = set()
    for cycle in nx.simple_cycles(graph):
        smallest_rotation = min(
            tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle))
        )
        if smallest_rotation not in seen:
            seen.add(smallest_rotation)
            cycles.append(list(smallest_rotation) + [smallest_rotation[0]])
    return cycles


def format_cycle(cycle):
    """Return a cycle in the readable arrow format used by the report."""
    return " -> ".join(cycle)