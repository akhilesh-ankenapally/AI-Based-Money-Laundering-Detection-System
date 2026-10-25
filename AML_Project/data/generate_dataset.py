"""Generate reproducible, city-scale synthetic FITMS datasets."""

import argparse
import csv
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class DatasetConfig:
    accounts: int
    transactions: int
    days: int
    seed: int


ACCOUNT_TYPES = (
    "INDIVIDUAL", "SALARIED", "SMALL_BUSINESS", "LARGE_BUSINESS",
    "RETAIL_MERCHANT", "SERVICE_PROVIDER", "INTERMEDIARY",
)
AREAS = (
    "COMMERCIAL_CENTRE", "RESIDENTIAL_NORTH", "INDUSTRIAL_ESTATE",
    "RETAIL_MARKET", "SMALL_BUSINESS_DISTRICT", "FINANCIAL_SERVICES",
)
TRANSACTION_TYPES = ("DEPOSIT", "WITHDRAW", "TRANSFER")
GROUND_TRUTH_FIELDS = (
    "scenario_id", "label", "pattern_category", "account_ids",
    "transaction_ids", "scenario_timestamp",
)


def _validate(config):
    if config.accounts < 3 or config.transactions < config.accounts:
        raise ValueError("accounts must be at least 3 and transactions must cover every account")
    if config.days < 1:
        raise ValueError("days must be positive")


def _timestamp(start, days, rng):
    return (start + timedelta(seconds=rng.randrange(days * 86400))).isoformat()


def _accounts(count, rng):
    rows = []
    for index in range(1, count + 1):
        rows.append({
            "account_id": "NFI-" + str(index).zfill(7),
            "account_type": rng.choice(ACCOUNT_TYPES),
            "area": rng.choice(AREAS),
        })
    return rows


def generate_dataset(output_dir, accounts=15000, transactions=200000, days=90, seed=42):
    """Write accounts, transactions, and separate ground-truth CSV files."""
    config = DatasetConfig(accounts, transactions, days, seed)
    _validate(config)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    account_rows = _accounts(accounts, rng)
    account_ids = [row["account_id"] for row in account_rows]
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    transaction_path = output_dir / "transactions.csv"
    account_path = output_dir / "accounts.csv"
    ground_truth_path = output_dir / "ground_truth.csv"
    transaction_fields = (
        "transaction_id", "timestamp", "transaction_type",
        "source_account", "destination_account", "amount",
    )
    scenarios = []
    replacements = {}

    def add_scenario(category, scenario_accounts, transaction_ids, timestamp):
        scenario_id = "SCN-" + str(len(scenarios) + 1).zfill(4)
        scenarios.append({
            "scenario_id": scenario_id, "label": "SUSPICIOUS",
            "pattern_category": category, "account_ids": "|".join(scenario_accounts),
            "transaction_ids": "|".join(transaction_ids),
            "scenario_timestamp": timestamp,
        })

    with account_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("account_id", "account_type", "area"))
        writer.writeheader()
        writer.writerows(account_rows)

    temporary_path = output_dir / "transactions.csv.tmp"
    with temporary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=transaction_fields)
        writer.writeheader()
        for index in range(transactions):
            transaction_id = "TX-" + str(index + 1).zfill(9)
            source = account_ids[index % accounts]
            destination = account_ids[(index * 17 + 11) % accounts]
            if source == destination:
                destination = account_ids[(index + 1) % accounts]
            transaction_type = rng.choices(TRANSACTION_TYPES, weights=(12, 8, 80))[0]
            amount = rng.randint(50, 25000)
            if transaction_type == "DEPOSIT":
                source, destination = "", source
            elif transaction_type == "WITHDRAW":
                source, destination = source, ""
            else:
                amount = rng.randint(100, 100000)
            row = {
                "transaction_id": transaction_id,
                "timestamp": _timestamp(start, days, rng),
                "transaction_type": transaction_type,
                "source_account": source,
                "destination_account": destination,
                "amount": amount,
            }
            writer.writerow(row)
            if index % max(1, transactions // 5) == 0:
                print("Generated " + str(index) + "/" + str(transactions) + " transactions")

    # Append deterministic planted scenarios by replacing selected normal rows.
    scenario_count = min(24, max(3, accounts // 1000))
    for scenario_index in range(scenario_count):
        base = (scenario_index * 7919) % (transactions - 4)
        scenario_accounts = [
            account_ids[(scenario_index * 13 + offset) % accounts] for offset in range(4)
        ]
        selected = []
        with temporary_path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            for row_index, row in enumerate(reader):
                if base <= row_index < base + 4:
                    selected.append(row)
                if row_index >= base + 3:
                    break
        if scenario_index % 3 == 0:
            category = "STRUCTURING"
            for offset, row in enumerate(selected):
                row.update({
                    "timestamp": (start + timedelta(days=scenario_index, minutes=offset)).isoformat(),
                    "transaction_type": "TRANSFER",
                    "source_account": scenario_accounts[0],
                    "destination_account": scenario_accounts[(offset % 3) + 1],
                    "amount": 49000 + offset * 200,
                })
        elif scenario_index % 3 == 1:
            category = "CIRCULAR_TRANSFER"
            for offset, row in enumerate(selected):
                row.update({
                    "timestamp": (start + timedelta(days=scenario_index, minutes=offset)).isoformat(),
                    "transaction_type": "TRANSFER",
                    "source_account": scenario_accounts[offset],
                    "destination_account": scenario_accounts[(offset + 1) % 4],
                    "amount": 12000 + offset * 500,
                })
        else:
            category = "RAPID_MOVEMENT"
            for offset, row in enumerate(selected):
                row.update({
                    "timestamp": (start + timedelta(days=scenario_index, seconds=offset * 30)).isoformat(),
                    "transaction_type": "TRANSFER",
                    "source_account": scenario_accounts[offset],
                    "destination_account": scenario_accounts[(offset + 1) % 4],
                    "amount": 75000 + offset * 1000,
                })
        transaction_ids = [row["transaction_id"] for row in selected]
        timestamp = selected[0]["timestamp"]
        add_scenario(category, scenario_accounts, transaction_ids, timestamp)
        for offset, transaction_id in enumerate(transaction_ids):
            replacements[base + offset] = selected[offset]
    with temporary_path.open(newline="", encoding="utf-8") as source, \
            transaction_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=transaction_fields)
        writer.writeheader()
        for row_index, row in enumerate(csv.DictReader(source)):
            writer.writerow(replacements.get(row_index, row))
    os.remove(temporary_path)
    with ground_truth_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=GROUND_TRUTH_FIELDS)
        writer.writeheader()
        writer.writerows(scenarios)
    print("Generated " + str(accounts) + " accounts and " + str(transactions) + " transactions")
    return {
        "accounts": account_path,
        "transactions": transaction_path,
        "ground_truth": ground_truth_path,
        "account_count": len(account_rows),
        "transaction_count": transactions,
        "scenario_count": len(scenarios),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic FITMS data")
    parser.add_argument("--accounts", type=int, default=15000)
    parser.add_argument("--transactions", type=int, default=200000)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data/generated")
    args = parser.parse_args()
    try:
        generate_dataset(args.output_dir, args.accounts, args.transactions, args.days, args.seed)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
