"""Deterministic regression tests for transaction intelligence features."""

import csv

from analysis.filtering import filter_accounts, filter_patterns, filter_transactions
from analysis.pipeline import analyze_program
from compiler.ast_nodes import ProgramNode
from analysis.similar_transactions import detect_similar_transactions
from compiler.parser import parse_source
from exports.filtered_export import export_filtered_csv, export_filtered_txt


def program(source):
    parsed = parse_source(source)
    assert parsed is not None
    return parsed


def test_similar_amounts_group_across_accounts():
    result = detect_similar_transactions(program(
        "TRANSFER ACC1001 ACC2001 49000;"
        "TRANSFER ACC1002 ACC2002 49200;"
        "TRANSFER ACC1003 ACC2003 48900;"
    ))
    assert len(result) == 1
    assert result[0]["matching_transactions"] == 3
    assert len(result[0]["accounts"]) == 6


def test_transaction_types_are_not_mixed_and_tolerance_is_configurable():
    parsed = program(
        "TRANSFER ACC1001 ACC2001 49000;"
        "DEPOSIT ACC1002 49000;"
        "TRANSFER ACC1003 ACC2003 50000;"
    )
    assert detect_similar_transactions(parsed, tolerance_percent=1, minimum_accounts=2) == []
    patterns = detect_similar_transactions(parsed, tolerance_percent=3, minimum_accounts=2)
    assert len(patterns) == 1
    assert patterns[0]["transaction_type"] == "TRANSFER"


def test_absolute_tolerance_and_minimum_constraints_are_applied():
    parsed = program(
        "TRANSFER ACC1001 ACC2001 1000;"
        "TRANSFER ACC1002 ACC2002 1050;"
        "TRANSFER ACC1003 ACC2003 1040;"
    )
    assert detect_similar_transactions(
        parsed, tolerance_percent=0, absolute_tolerance=50,
        minimum_matching_transactions=3, minimum_accounts=2,
    )[0]["matching_transactions"] == 3
    assert detect_similar_transactions(
        parsed, tolerance_percent=0, absolute_tolerance=50,
        minimum_matching_transactions=4,
    ) == []
    assert detect_similar_transactions(
        parsed, tolerance_percent=0, absolute_tolerance=50,
        minimum_accounts=7,
    ) == []


def test_similarity_does_not_use_transitive_out_of_range_amounts():
    parsed = program(
        "TRANSFER ACC1001 ACC2001 1000;"
        "TRANSFER ACC1002 ACC2002 1020;"
        "TRANSFER ACC1003 ACC2003 1040;"
    )
    patterns = detect_similar_transactions(parsed, tolerance_percent=2)
    assert len(patterns) == 1
    assert patterns[0]["matching_transactions"] == 2


def test_empty_similarity_input_and_duplicate_amounts_are_deterministic():
    assert detect_similar_transactions(ProgramNode([])) == []
    parsed = program(
        "TRANSFER ACC1001 ACC2001 1000;"
        "TRANSFER ACC1002 ACC2002 1000;"
        "TRANSFER ACC1003 ACC2003 1000;"
    )
    patterns = detect_similar_transactions(parsed)
    assert len(patterns) == 1
    assert patterns[0]["transaction_indices"] == [0, 1, 2]


def test_pattern_filter_requires_complete_group():
    parsed = program(
        "TRANSFER ACC1001 ACC2001 49000;"
        "TRANSFER ACC1002 ACC2002 49200;"
    )
    pattern = detect_similar_transactions(parsed)[0]
    assert filter_patterns([pattern], [0]) == []
    assert filter_patterns([pattern], [0, 1]) == [pattern]


def test_account_intelligence_deduplicates_rule_flags_per_transaction():
    results = analyze_program(program(
        "TRANSFER ACC1001 ACC2001 49000;"
        "TRANSFER ACC1001 ACC2002 49500;"
        "TRANSFER ACC1001 ACC2003 48000;"
        "TRANSFER ACC1001 ACC2004 49900;"
    ))
    account = next(item for item in results["account_intelligence"] if item["account"] == "ACC1001")
    assert account["suspicious_transaction_count"] == 4
    assert account["detection_rule_count"] >= 2


def test_filters_change_transaction_and_account_records():
    results = analyze_program(program(
        "TRANSFER ACC1001 ACC2001 1000;"
        "TRANSFER ACC1002 ACC2002 90000;"
    ))
    assert len(filter_transactions(results["transaction_records"], transaction_types=["TRANSFER"],
                                   minimum_amount=50000)) == 1
    assert len(filter_accounts(results["account_intelligence"], risk_level="HIGH")) == 0
    assert len(filter_accounts(results["account_intelligence"], account_query="ACC1002")) == 1
    assert filter_transactions(results["transaction_records"], transaction_types=[]) == []
    assert filter_transactions(results["transaction_records"]) == results["transaction_records"]
    assert filter_accounts(results["account_intelligence"]) == results["account_intelligence"]


def test_filtered_exports_contain_only_selected_records(tmp_path):
    results = analyze_program(program(
        "TRANSFER ACC1001 ACC2001 1000;"
        "TRANSFER ACC1002 ACC2002 2000;"
    ))
    selected = [results["transaction_records"][1]]
    csv_path = export_filtered_csv(tmp_path / "filtered.csv", selected)
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["transaction_id"] for row in rows] == ["TX-0002"]
    txt_path = export_filtered_txt(tmp_path / "filtered.txt", "test subset", selected)
    text = txt_path.read_text(encoding="utf-8")
    assert "TX-0002" in text
    assert "TX-0001" not in text


def test_chart_input_changes_with_filtered_accounts():
    from dashboard.app import risk_chart

    low = [{"account": "A", "risk_level": "LOW"}]
    high = [{"account": "B", "risk_level": "HIGH"}]
    assert list(risk_chart(low).data[0].y) != list(risk_chart(high).data[0].y)


def test_empty_and_single_account_programs_are_supported():
    empty = program("DEPOSIT ACC1001 1;")
    results = analyze_program(empty)
    assert results["total_accounts"] == 1
    assert results["similar_patterns"] == []
    assert results["graph_statistics"]["node_count"] == 0
    empty_results = analyze_program(ProgramNode([]))
    assert empty_results["total_transactions"] == 0
    assert empty_results["account_intelligence"] == []
