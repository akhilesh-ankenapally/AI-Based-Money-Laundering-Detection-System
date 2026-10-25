"""Explicit exports for filtered dashboard investigation results."""

import csv
from pathlib import Path


def export_filtered_csv(path, records, suspicious_indices=()):
    """Write exactly the supplied transaction records to a CSV file."""
    path = Path(path)
    fields = [
        "transaction_id", "type", "source_account", "destination_account",
        "amount", "status",
    ]
    suspicious = set(suspicious_indices)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "transaction_id": record["transaction_id"],
                "type": record["type"],
                "source_account": record["source_account"],
                "destination_account": record["destination_account"],
                "amount": record["amount"],
                "status": "REVIEW" if record["index"] in suspicious else "NORMAL",
            })
    return path


def export_filtered_txt(path, scope, records, suspicious_indices=()):
    """Write a readable report containing exactly the supplied records."""
    path = Path(path)
    suspicious = set(suspicious_indices)
    lines = [
        "AML INVESTIGATION REPORT",
        "Scope: " + scope,
        "Transactions: " + str(len(records)),
        "",
        "TRANSACTIONS",
    ]
    for record in records:
        status = "REVIEW" if record["index"] in suspicious else "NORMAL"
        lines.append(
            record["transaction_id"] + " | " + record["type"]
            + " | " + str(record["amount"]) + " | " + status
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
