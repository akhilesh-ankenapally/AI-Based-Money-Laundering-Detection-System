"""Shared analysis pipeline used by the CLI and Streamlit dashboard."""

from collections import defaultdict

from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode
from analysis.anomaly_detection import detect_anomalies
from analysis.circular_transfer import detect_circular_transfers
from analysis.risk_score import calculate_risk_scores
from analysis.structuring import detect_structuring
from analysis.temporal_analysis import detect_high_frequency
from analysis.account_intelligence import build_account_intelligence
from analysis.similar_transactions import detect_similar_transactions
from analysis.transaction_records import accounts_from_records, transaction_records
from graph.transaction_graph import analyze_graph, build_transaction_graph


def analyze_program(
    program,
    similarity_tolerance_percent=2.0,
    similarity_absolute_tolerance=0.0,
    similarity_minimum_transactions=2,
    similarity_minimum_accounts=2,
    similarity_transaction_types=None,
    max_graph_cycles=None,
    enable_similarity=True,
):
    """Run all AML, graph, and anomaly analyses on one existing ProgramNode."""
    structuring_findings = detect_structuring(program)
    circular_cycles = detect_circular_transfers(program, max_cycles=max_graph_cycles)
    temporal_findings = detect_high_frequency(program)
    risk_scores = calculate_risk_scores(
        program,
        structuring_findings,
        circular_cycles,
        temporal_findings,
    )
    graph = build_transaction_graph(program)
    graph_statistics = analyze_graph(graph, max_cycles=max_graph_cycles)
    anomaly_results = detect_anomalies(program, graph)
    records = transaction_records(program)
    records_by_account = defaultdict(list)
    record_indices_by_transaction_id = {}
    activity_by_date = defaultdict(lambda: {"Transactions": 0, "Suspicious": 0})
    transaction_type_counts = defaultdict(int)
    for record in records:
        for account in record["accounts"]:
            records_by_account[account].append(record["index"])
        record_indices_by_transaction_id[record["transaction_id"].lower()] = record["index"]
        transaction_type_counts[record["type"]] += 1
    similar_patterns = detect_similar_transactions(
        program,
        tolerance_percent=similarity_tolerance_percent,
        absolute_tolerance=similarity_absolute_tolerance,
        minimum_matching_transactions=similarity_minimum_transactions,
        minimum_accounts=similarity_minimum_accounts,
        transaction_types=similarity_transaction_types,
    ) if enable_similarity else []

    suspicious_transaction_indices = set()
    for finding in structuring_findings.values():
        suspicious_transaction_indices.update(finding.get("transaction_indices", ()))
    for finding in temporal_findings:
        suspicious_transaction_indices.update(finding.get("transaction_indices", ()))
    for index, statement in enumerate(program.statements):
        if isinstance(statement, TransferNode) and statement.amount >= 50000:
            suspicious_transaction_indices.add(index)
    cycle_edges = {
        (source, target)
        for cycle in circular_cycles
        for source, target in zip(cycle, cycle[1:])
    }
    for index, statement in enumerate(program.statements):
        if isinstance(statement, TransferNode) and (
            statement.source_account, statement.destination_account
        ) in cycle_edges:
            suspicious_transaction_indices.add(index)
    suspicious_index_set = suspicious_transaction_indices
    for record in records:
        date = (record.get("timestamp") or "")[:10]
        if date:
            activity_by_date[date]["Transactions"] += 1
            activity_by_date[date]["Suspicious"] += int(record["index"] in suspicious_index_set)

    account_intelligence = build_account_intelligence(
        program,
        risk_scores,
        anomaly_results,
        suspicious_transaction_indices,
        similar_patterns,
        records,
    )
    return {
        "structuring_findings": structuring_findings,
        "circular_cycles": circular_cycles,
        "temporal_findings": temporal_findings,
        "risk_scores": risk_scores,
        "graph": graph,
        "graph_statistics": graph_statistics,
        "anomaly_results": anomaly_results,
        "similar_patterns": similar_patterns,
        "account_intelligence": account_intelligence,
        "transaction_records": records,
        "records_by_account": dict(records_by_account),
        "record_indices_by_transaction_id": record_indices_by_transaction_id,
        "activity_by_date": [
            {"Date": date, **values}
            for date, values in sorted(activity_by_date.items())
        ],
        "transaction_type_counts": dict(transaction_type_counts),
        "suspicious_transaction_indices": sorted(suspicious_transaction_indices),
        "total_accounts": len(accounts_from_records(records)),
        "total_transactions": len(program.statements),
    }