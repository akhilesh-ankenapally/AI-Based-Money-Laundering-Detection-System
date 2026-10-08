"""Detection of transfers clustered just below a reporting threshold."""

from compiler.ast_nodes import TransferNode


def detect_structuring(program, threshold=50000, lower_percentage=0.95,
                       minimum_transaction_count=2):
    """Return accounts with multiple transfers in the configured threshold band."""
    lower_bound = threshold * lower_percentage
    transfers_by_account = {}

    for statement in program.statements:
        if isinstance(statement, TransferNode):
            if lower_bound <= statement.amount < threshold:
                transfers_by_account.setdefault(statement.source_account, []).append(
                    statement.amount
                )

    findings = {}
    for account, amounts in transfers_by_account.items():
        if len(amounts) >= minimum_transaction_count:
            findings[account] = {
                "account": account,
                "transfers": amounts,
                "reason": (
                    "Multiple transfers fall between "
                    + str(lower_bound)
                    + " and "
                    + str(threshold)
                    + ", just below the reporting threshold."
                ),
            }
    return findings