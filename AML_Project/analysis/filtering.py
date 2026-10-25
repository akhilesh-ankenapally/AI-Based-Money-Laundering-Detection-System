"""Shared filtering functions used by dashboard tables, charts, and exports."""


def filter_transactions(
    records,
    account_query="",
    transaction_types=None,
    minimum_amount=0,
    maximum_amount=None,
    records_by_account=None,
    record_indices_by_transaction_id=None,
):
    """Filter normalized transaction records without mutating the source list."""
    selected_types = None if transaction_types is None else set(transaction_types)
    query = account_query.strip().lower()
    candidate_indices = None
    if query and records_by_account is not None:
        matching_accounts = [
            account for account in records_by_account
            if query in account.lower()
        ]
        candidate_indices = {
            index for account in matching_accounts
            for index in records_by_account[account]
        }
        if record_indices_by_transaction_id:
            candidate_indices.update(
                index for transaction_id, index in record_indices_by_transaction_id.items()
                if query in transaction_id
            )
    return [
        record for record in records
        if (not query or (
            (candidate_indices is not None and record["index"] in candidate_indices)
            or (
                candidate_indices is None
                and any(query in account.lower() for account in record["accounts"])
            )
        ))
        and (selected_types is None or record["type"] in selected_types)
        and record["amount"] >= minimum_amount
        and (maximum_amount is None or record["amount"] <= maximum_amount)
    ]


def filter_accounts(
    accounts,
    account_query="",
    risk_level="ALL",
    minimum_risk_score=0,
    maximum_risk_score=100,
    suspicious_only=False,
    anomaly_classification="ALL",
    minimum_suspicious_transactions=0,
    transaction_indices=None,
):
    """Filter account intelligence records using the same account semantics."""
    query = account_query.strip().lower()
    return [
        item for item in accounts
        if (not query or query in item["account"].lower())
        and (risk_level == "ALL" or item["risk_level"] == risk_level)
        and minimum_risk_score <= item["risk_score"] <= maximum_risk_score
        and (not suspicious_only or item["suspicious_transaction_count"] > 0)
        and (
            anomaly_classification == "ALL"
            or item["anomaly_classification"] == anomaly_classification
        )
        and item["suspicious_transaction_count"] >= minimum_suspicious_transactions
        and (
            transaction_indices is None
            or set(item["transaction_indices"]).intersection(transaction_indices)
        )
    ]


def filter_patterns(patterns, transaction_indices):
    """Keep complete pattern groups represented by the filtered view."""
    allowed = set(transaction_indices)
    return [
        pattern for pattern in patterns
        if set(pattern.get("transaction_indices", ())).issubset(allowed)
    ]
