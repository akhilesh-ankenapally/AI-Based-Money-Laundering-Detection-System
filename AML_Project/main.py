"""Command-line driver for the transaction language frontend."""

from pathlib import Path

from compiler.lexer import build_lexer
from compiler.parser import parse_source
from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode
from analysis.circular_transfer import detect_circular_transfers
from analysis.report import generate_report
from analysis.risk_score import calculate_risk_scores
from analysis.structuring import detect_structuring
from analysis.temporal_analysis import detect_high_frequency


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

    structuring_findings = detect_structuring(program)
    circular_cycles = detect_circular_transfers(program)
    temporal_findings = detect_high_frequency(program)
    risk_scores = calculate_risk_scores(
        program,
        structuring_findings,
        circular_cycles,
        temporal_findings,
    )

    accounts = set()
    for statement in program.statements:
        if isinstance(statement, TransferNode):
            accounts.update((statement.source_account, statement.destination_account))
        elif isinstance(statement, (DepositNode, WithdrawNode)):
            accounts.add(statement.account_id)

    print()
    print(generate_report(risk_scores, total_accounts=len(accounts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
