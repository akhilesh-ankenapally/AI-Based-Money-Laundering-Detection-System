"""Lexical analyzer for the custom banking transaction language."""

import ply.lex as lex


# Reserved words are recognized after an identifier is matched.
reserved = {
    "DEPOSIT": "DEPOSIT",
    "WITHDRAW": "WITHDRAW",
    "TRANSFER": "TRANSFER",
}

# PLY needs this complete list when constructing the lexer.
tokens = (
    "DEPOSIT",
    "WITHDRAW",
    "TRANSFER",
    "ACCOUNT_ID",
    "NUMBER",
    "SEMICOLON",
)


# A semicolon terminates every transaction statement.
t_SEMICOLON = r";"

# An integer amount must contain at least one digit.
t_NUMBER = r"\d+"


def t_ACCOUNT_ID(token):
    r"[A-Za-z][A-Za-z0-9_]*"

    # Keywords use their own token types in the parser.
    token.type = reserved.get(token.value, "ACCOUNT_ID")

    # Keep identifiers manageable for this introductory language.
    if token.type == "ACCOUNT_ID" and len(token.value) > 20:
        print(
            "Lexical error at line "
            + str(token.lineno)
            + ": account identifier is longer than 20 characters: "
            + token.value
        )
        return None

    return token


def t_COMMENT(token):
    r"//[^\n]*"
    return None


def t_newline(token):
    r"\n+"
    token.lexer.lineno += len(token.value)


# Spaces, tabs, and carriage returns have no meaning in the language.
t_ignore = " \t\r"


def find_column(text, lex_position):
    """Return the one-based column for a lexer position."""
    line_start = text.rfind("\n", 0, lex_position) + 1
    return lex_position - line_start + 1


def t_error(token):
    """Report and skip a character that is not part of the language."""
    column = find_column(token.lexer.lexdata, token.lexpos)
    print(
        "Lexical error at line "
        + str(token.lineno)
        + ", column "
        + str(column)
        + ": illegal character "
        + repr(token.value[0])
    )
    token.lexer.skip(1)


def build_lexer():
    """Build and return a fresh lexer instance."""
    return lex.lex()


if __name__ == "__main__":
    # This small smoke test is useful when studying the lexer independently.
    lexer = build_lexer()
    lexer.input("DEPOSIT ACC1001 50000;")
    for token in lexer:
        print(token)
