"""Explainable similarity grouping for transactions in the existing AST."""

from collections import defaultdict

from analysis.transaction_records import transaction_records


def _amounts_match(left, right, tolerance_percent, absolute_tolerance):
    difference = abs(left["amount"] - right["amount"])
    allowed = max(
        absolute_tolerance,
        max(left["amount"], right["amount"]) * tolerance_percent / 100.0,
    )
    return difference <= allowed


def detect_similar_transactions(
    program,
    tolerance_percent=2.0,
    absolute_tolerance=0.0,
    minimum_matching_transactions=2,
    minimum_accounts=2,
    transaction_types=None,
):
    """Group same-type, similarly sized transactions across accounts.

    Statement order is retained as a reference only. No real time-window claim
    is made because the transaction language has no timestamp field.
    """
    if minimum_matching_transactions < 1 or minimum_accounts < 1:
        raise ValueError("Minimum matching transactions and accounts must be positive.")

    selected_types = (
        {"TRANSFER", "DEPOSIT", "WITHDRAW"}
        if transaction_types is None
        else set(transaction_types)
    )
    records = [
        record for record in transaction_records(program)
        if record["type"] in selected_types
    ]
    by_type = defaultdict(list)
    for record in records:
        by_type[record["type"]].append(record)

    patterns = []
    pattern_number = 1
    for transaction_type, candidates in sorted(by_type.items()):
        candidates = sorted(candidates, key=lambda item: (item["amount"], item["index"]))
        groups = []
        for candidate in candidates:
            matching_group = next((
                group for group in groups
                if _amounts_match(
                    candidate,
                    {"amount": min(item["amount"] for item in group)},
                    tolerance_percent,
                    absolute_tolerance,
                )
            ), None)
            if matching_group is None:
                groups.append([candidate])
            else:
                matching_group.append(candidate)

        for group in groups:
            accounts = sorted({account for record in group for account in record["accounts"]})
            if (
                len(group) < minimum_matching_transactions
                or len(accounts) < minimum_accounts
            ):
                continue
            amounts = [record["amount"] for record in group]
            patterns.append({
                "pattern_id": "SIM-" + str(pattern_number).zfill(3),
                "pattern_type": "Similar " + transaction_type.title() + " amounts",
                "transaction_type": transaction_type,
                "accounts": accounts,
                "transaction_indices": [record["index"] for record in group],
                "transaction_ids": [record["transaction_id"] for record in group],
                "matching_transactions": len(group),
                "amount_min": min(amounts),
                "amount_max": max(amounts),
                "similarity_score": round(
                    max(0.0, 100.0 - (max(amounts) - min(amounts))
                        / max(max(amounts), 1) * 100.0),
                    2,
                ),
                "explanation": (
                    str(len(group)) + " " + transaction_type.lower()
                    + " transactions across " + str(len(accounts))
                    + " accounts have amounts within the configured tolerance. "
                    "This is a potential suspicious pattern requiring investigation."
                ),
            })
            pattern_number += 1
    return patterns
