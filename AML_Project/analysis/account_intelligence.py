"""Account-level investigation records derived from transaction findings."""

from collections import defaultdict

from analysis.transaction_records import transaction_records


def build_account_intelligence(
    program,
    risk_scores,
    anomaly_results,
    suspicious_transaction_indices=None,
    transaction_pattern_indices=None,
    records=None,
):
    """Aggregate account activity while deduplicating transaction references."""
    records = transaction_records(program) if records is None else records
    suspicious_indices = set(suspicious_transaction_indices or ())
    patterns_by_index = defaultdict(set)
    for pattern in transaction_pattern_indices or ():
        for index in pattern.get("transaction_indices", ()):
            patterns_by_index[index].add(pattern["pattern_id"])
    anomalies = {item["account"]: item for item in anomaly_results}
    records_by_account = defaultdict(list)
    for record in records:
        for account in record["accounts"]:
            records_by_account[account].append(record)
    accounts = sorted(records_by_account)
    output = []
    for account in accounts:
        account_records = records_by_account[account]
        incoming = [record for record in account_records if record["destination_account"] == account]
        outgoing = [record for record in account_records if record["source_account"] == account]
        suspicious = [record for record in account_records if record["index"] in suspicious_indices]
        pattern_ids = {
            pattern_id for record in account_records
            for pattern_id in patterns_by_index.get(record["index"], set())
        }
        risk = risk_scores.get(account, {
            "account": account, "score": 0, "level": "LOW", "reasons": [],
        })
        anomaly = anomalies.get(account, {"score": 0, "classification": "NORMAL"})
        output.append({
            "account": account,
            "total_transactions": len(account_records),
            "incoming_transfers": len(incoming),
            "outgoing_transfers": len(outgoing),
            "total_incoming_amount": sum(record["amount"] for record in incoming),
            "total_outgoing_amount": sum(record["amount"] for record in outgoing),
            "suspicious_transaction_count": len({record["index"] for record in suspicious}),
            "suspicious_transaction_amount": sum(record["amount"] for record in suspicious),
            "distinct_pattern_count": len(pattern_ids),
            "detection_rule_count": len(risk.get("reasons", [])),
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "anomaly_score": anomaly.get("score", 0),
            "anomaly_classification": anomaly.get("classification", "NORMAL"),
            "reasons": list(risk.get("reasons", [])),
            "transaction_indices": [record["index"] for record in account_records],
            "suspicious_transaction_indices": [record["index"] for record in suspicious],
            "pattern_ids": sorted(pattern_ids),
        })
    return sorted(
        output,
        key=lambda item: (
            -item["suspicious_transaction_count"],
            -item["distinct_pattern_count"],
            -item["risk_score"],
            item["account"],
        ),
    )
