"""Normalized views of the existing transaction AST nodes.

The AST remains the source of truth. These dictionaries provide stable
statement indexes for analysis, filtering, and exports without introducing a
second transaction model.
"""

from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode


def transaction_records(program):
    """Return one serializable record for every AST statement."""
    records = []
    for index, statement in enumerate(program.statements):
        if isinstance(statement, TransferNode):
            records.append({
                "transaction_id": getattr(statement, "transaction_id", None)
                or "TX-" + str(index + 1).zfill(4),
                "index": index,
                "type": "TRANSFER",
                "amount": statement.amount,
                "timestamp": getattr(statement, "timestamp", None),
                "source_account": statement.source_account,
                "destination_account": statement.destination_account,
                "account": statement.source_account,
                "accounts": (statement.source_account, statement.destination_account),
            })
        elif isinstance(statement, DepositNode):
            records.append({
                "transaction_id": getattr(statement, "transaction_id", None)
                or "TX-" + str(index + 1).zfill(4),
                "index": index,
                "type": "DEPOSIT",
                "amount": statement.amount,
                "timestamp": getattr(statement, "timestamp", None),
                "source_account": "",
                "destination_account": statement.account_id,
                "account": statement.account_id,
                "accounts": (statement.account_id,),
            })
        elif isinstance(statement, WithdrawNode):
            records.append({
                "transaction_id": getattr(statement, "transaction_id", None)
                or "TX-" + str(index + 1).zfill(4),
                "index": index,
                "type": "WITHDRAW",
                "amount": statement.amount,
                "timestamp": getattr(statement, "timestamp", None),
                "source_account": statement.account_id,
                "destination_account": "",
                "account": statement.account_id,
                "accounts": (statement.account_id,),
            })
    return records


def accounts_from_records(records):
    """Return all accounts represented by normalized transaction records."""
    return sorted({account for record in records for account in record["accounts"]})
