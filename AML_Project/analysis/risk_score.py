"""Explainable rule-based risk scoring."""

from compiler.ast_nodes import TransferNode


def calculate_risk_scores(program, structuring_findings, circular_cycles,
                          temporal_findings, large_transfer_threshold=50000):
    """Return one capped score and reason list for each account involved in AML findings."""
    scores = {}

    def add_reason(account, points, reason):
        entry = scores.setdefault(account, {"account": account, "score": 0, "reasons": []})
        entry["score"] = min(100, entry["score"] + points)
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)

    for account in structuring_findings:
        add_reason(account, 40, "Structuring detected")

    for cycle in circular_cycles:
        for account in set(cycle[:-1]):
            add_reason(account, 30, "Circular transfer detected")

    for finding in temporal_findings:
        add_reason(finding["account"], 20, "High frequency activity")

    for statement in program.statements:
        if (isinstance(statement, TransferNode)
                and statement.amount >= large_transfer_threshold):
            add_reason(statement.source_account, 10, "Large transfer detected")

    for entry in scores.values():
        entry["level"] = (
            "LOW" if entry["score"] <= 30
            else "MEDIUM" if entry["score"] <= 60
            else "HIGH"
        )
    return scores