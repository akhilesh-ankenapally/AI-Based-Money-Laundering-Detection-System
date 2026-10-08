"""Explainable NetworkX analytics for transfer relationships."""

import networkx as nx

from compiler.ast_nodes import TransferNode


class TransactionGraph:
    """Build and query a directed account transfer graph."""

    def __init__(self, program):
        self.graph = build_transaction_graph(program)

    def find_shortest_path(self, source_account, destination_account):
        """Return the shortest transfer chain and its number of edges."""
        return find_shortest_path(
            self.graph,
            source_account,
            destination_account,
        )


def build_transaction_graph(program):
    """Build a directed graph whose nodes are accounts and edges are transfers."""
    graph = nx.DiGraph()
    for statement in program.statements:
        if isinstance(statement, TransferNode):
            graph.add_edge(
                statement.source_account,
                statement.destination_account,
                amount=statement.amount,
            )
    return graph


def find_highly_connected_accounts(graph, top_n=5):
    """Return accounts ordered by total in-degree plus out-degree."""
    connected = [
        {
            "account": account,
            "in_degree": graph.in_degree(account),
            "out_degree": graph.out_degree(account),
            "degree": graph.degree(account),
        }
        for account in graph.nodes
    ]
    return sorted(connected, key=lambda item: (-item["degree"], item["account"]))[:top_n]


def detect_suspicious_hubs(graph, minimum_degree=3):
    """Return accounts with at least the configured total degree."""
    return [
        account for account in graph.nodes
        if graph.degree(account) >= minimum_degree
    ]


def calculate_degree_statistics(graph):
    """Return simple degree metrics suitable for a dashboard or viva."""
    degrees = [degree for _, degree in graph.degree()]
    return {
        "average_degree": round(sum(degrees) / len(degrees), 2) if degrees else 0,
        "maximum_degree": max(degrees) if degrees else 0,
        "connected_accounts": find_highly_connected_accounts(graph),
    }


def analyze_graph(graph, top_n=5, minimum_hub_degree=3):
    """Return the requested graph summary in one dictionary."""
    cycles = [cycle + [cycle[0]] for cycle in nx.simple_cycles(graph)]
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "cycle_count": len(cycles),
        "cycles": cycles,
        "top_connected_accounts": find_highly_connected_accounts(graph, top_n),
        "suspicious_hubs": detect_suspicious_hubs(graph, minimum_hub_degree),
        "degree_statistics": calculate_degree_statistics(graph),
    }


def find_shortest_path(graph, source_account, destination_account):
    """Return a shortest transfer path or a clear not-found result."""
    try:
        path = nx.shortest_path(
            graph,
            source_account,
            destination_account,
            method="dijkstra",
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return {"path": [], "path_length": None}
    return {"path": path, "path_length": len(path) - 1}