"""Shared analysis pipeline used by the CLI and Streamlit dashboard."""

from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode
from analysis.anomaly_detection import detect_anomalies
from analysis.circular_transfer import detect_circular_transfers
from analysis.risk_score import calculate_risk_scores
from analysis.structuring import detect_structuring
from analysis.temporal_analysis import detect_high_frequency
from graph.transaction_graph import analyze_graph, build_transaction_graph


def analyze_program(program):
    """Run all AML, graph, and anomaly analyses on one existing ProgramNode."""
    structuring_findings = detect_structuring(program)
    circular_cycles = detect_circular_transfers(program)
    temporal_findings = detect_high_frequency(program)
    risk_scores = calculate_risk_scores(
        program,
        structuring_findings,
        circular_cycles,
        temporal_findings,
    )
    graph = build_transaction_graph(program)
    graph_statistics = analyze_graph(graph)
    anomaly_results = detect_anomalies(program, graph)

    accounts = set()
    for statement in program.statements:
        if isinstance(statement, TransferNode):
            accounts.update((statement.source_account, statement.destination_account))
        elif isinstance(statement, (DepositNode, WithdrawNode)):
            accounts.add(statement.account_id)

    return {
        "structuring_findings": structuring_findings,
        "circular_cycles": circular_cycles,
        "temporal_findings": temporal_findings,
        "risk_scores": risk_scores,
        "graph": graph,
        "graph_statistics": graph_statistics,
        "anomaly_results": anomaly_results,
        "total_accounts": len(accounts),
        "total_transactions": len(program.statements),
    }