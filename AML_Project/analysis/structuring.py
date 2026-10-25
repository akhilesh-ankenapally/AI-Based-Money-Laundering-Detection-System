"""Detection of transfers clustered just below a reporting threshold."""

from compiler.ast_nodes import TransferNode


def detect_structuring(program, threshold=50000, lower_percentage=0.95,
                       minimum_transaction_count=2):
    """Return accounts with multiple transfers in the configured threshold band."""
    lower_bound = threshold * lower_percentage
    transfers_by_account = {}

    for index, statement in enumerate(program.statements):
        if isinstance(statement, TransferNode):
            if lower_bound <= statement.amount < threshold:
                transfers_by_account.setdefault(statement.source_account, []).append(
                    (index, statement.amount)
                )

    findings = {}
    for account, entries in transfers_by_account.items():
        if len(entries) >= minimum_transaction_count:
            amounts = [amount for _, amount in entries]
            findings[account] = {
                "account": account,
                "transfers": amounts,
                "transaction_indices": [index for index, _ in entries],
                "reason": (
                    "Multiple transfers fall between "
                    + str(lower_bound)
                    + " and "
                    + str(threshold)
                    + ", just below the reporting threshold."
                ),
            }
    return findings