"""Command-line driver for the transaction language frontend."""

from pathlib import Path

from compiler.lexer import build_lexer
from compiler.parser import parse_source
from analysis.pipeline import analyze_program
from analysis.report import generate_report
from exports.report_export import export_reports


# Resolve the sample file from the project location, not the current shell folder.
PROJECT_ROOT = Path(__file__).resolve().parent
TRANSACTIONS_FILE = PROJECT_ROOT / "data" / "transactions.txt"


def display_tokens(source_text):
    """Run the lexer and print every token in a viva-friendly format."""
    lexer = build_lexer()
    lexer.input(source_text)

    print("LEXER OUTPUT")
    while True:
        token = lexer.token()
        if token is None:
            break
        print("TOKEN(" + token.type + ", " + str(token.value) + ")")


def main():
    """Read, tokenize, parse, and display the sample transaction program."""
    if not TRANSACTIONS_FILE.exists():
        print("Input file not found: " + str(TRANSACTIONS_FILE))
        return 1

    source_text = TRANSACTIONS_FILE.read_text(encoding="utf-8")

    print("Reading: " + str(TRANSACTIONS_FILE))
    print()
    display_tokens(source_text)

    print()
    print("AST OUTPUT")
    program = parse_source(source_text)
    if program is None:
        print("AST was not generated because parsing failed.")
        return 1

    print(program)

    results = analyze_program(program)
    report_text = generate_report(results["risk_scores"], results["total_accounts"])
    export_paths = export_reports(
        PROJECT_ROOT / "exports",
        report_text,
        results["risk_scores"],
        results["anomaly_results"],
        results["graph_statistics"],
    )

    print()
    print(report_text)
    print()
    print("GRAPH STATISTICS")
    print("Nodes: " + str(results["graph_statistics"]["node_count"]))
    print("Edges: " + str(results["graph_statistics"]["edge_count"]))
    print("Cycles: " + str(results["graph_statistics"]["cycle_count"]))
    print()
    print("AI ANOMALY OUTPUT")
    for anomaly in results["anomaly_results"]:
        print(
            anomaly["account"] + ": " + str(anomaly["score"])
            + " (" + anomaly["classification"] + ")"
        )
    print()
    print("Reports exported to: " + str(export_paths["txt"]))
    print("Reports exported to: " + str(export_paths["csv"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
