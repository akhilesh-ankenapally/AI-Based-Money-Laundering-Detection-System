"""Command-line driver for the transaction language frontend."""

from pathlib import Path

from compiler.lexer import build_lexer
from compiler.parser import parse_source


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
