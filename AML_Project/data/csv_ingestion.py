"""Validated CSV ingestion into the existing transaction AST."""

import csv
from datetime import datetime
from pathlib import Path

from compiler.ast_nodes import DepositNode, ProgramNode, TransferNode, WithdrawNode


REQUIRED_COLUMNS = {
    "transaction_id", "timestamp", "transaction_type", "source_account",
    "destination_account", "amount",
}


def load_transactions_csv(path):
    """Load a generated transaction CSV without using ground-truth labels."""
    path = Path(path)
    statements = []
    seen_ids = set()
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or ())
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError("Transaction CSV is missing columns: " + ", ".join(sorted(missing)))
        for line_number, row in enumerate(reader, start=2):
            transaction_id = row["transaction_id"]
            if not transaction_id or transaction_id in seen_ids:
                raise ValueError("Invalid or duplicate transaction_id at line " + str(line_number))
            seen_ids.add(transaction_id)
            try:
                timestamp = datetime.fromisoformat(row["timestamp"])
                amount = int(row["amount"])
            except (TypeError, ValueError) as error:
                raise ValueError("Invalid timestamp or amount at line " + str(line_number)) from error
            if amount <= 0:
                raise ValueError("Amount must be positive at line " + str(line_number))
            transaction_type = row["transaction_type"].upper()
            source = row["source_account"]
            destination = row["destination_account"]
            if transaction_type == "TRANSFER":
                if not source or not destination or source == destination:
                    raise ValueError("Transfer accounts are invalid at line " + str(line_number))
                statement = TransferNode(source, destination, amount,
                                         timestamp.isoformat(), transaction_id)
            elif transaction_type == "DEPOSIT":
                if not destination or source:
                    raise ValueError("Deposit accounts are invalid at line " + str(line_number))
                statement = DepositNode(destination, amount, timestamp.isoformat(), transaction_id)
            elif transaction_type == "WITHDRAW":
                if not source or destination:
                    raise ValueError("Withdrawal accounts are invalid at line " + str(line_number))
                statement = WithdrawNode(source, amount, timestamp.isoformat(), transaction_id)
            else:
                raise ValueError("Unsupported transaction type at line " + str(line_number))
            statements.append(statement)
    return ProgramNode(statements)
