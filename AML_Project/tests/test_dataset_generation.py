import csv

from data.csv_ingestion import load_transactions_csv
from data.generate_dataset import generate_dataset


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_generator_has_exact_counts_and_separate_ground_truth(tmp_path):
    result = generate_dataset(tmp_path, accounts=20, transactions=100, days=30, seed=42)
    accounts = read_rows(result["accounts"])
    transactions = read_rows(result["transactions"])
    ground_truth = read_rows(result["ground_truth"])
    assert len(accounts) == 20
    assert len(transactions) == 100
    assert len({row["transaction_id"] for row in transactions}) == 100
    account_ids = {row["account_id"] for row in accounts}
    assert all(
        account in account_ids
        for row in transactions
        for account in (row["source_account"], row["destination_account"])
        if account
    )
    assert ground_truth
    assert "pattern_category" in ground_truth[0]


def test_generator_is_reproducible_and_loader_preserves_metadata(tmp_path):
    first = generate_dataset(tmp_path / "one", accounts=20, transactions=100, days=30, seed=7)
    second = generate_dataset(tmp_path / "two", accounts=20, transactions=100, days=30, seed=7)
    assert first["transactions"].read_bytes() == second["transactions"].read_bytes()
    program = load_transactions_csv(first["transactions"])
    assert len(program.statements) == 100
    assert program.statements[0].transaction_id == "TX-000000001"
    assert program.statements[0].timestamp is not None
