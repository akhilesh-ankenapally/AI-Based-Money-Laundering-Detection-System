"""Parser for the custom banking transaction language."""

import ply.yacc as yacc

from compiler.ast_nodes import DepositNode, ProgramNode, TransferNode, WithdrawNode
from compiler.lexer import build_lexer, tokens


# Keep parser diagnostics understandable for a first compiler project.
start = "program"


def p_program(p):
    """program : statement_list"""
    p[0] = ProgramNode(p[1])


def p_statement_list_multiple(p):
    """statement_list : statement_list statement"""
    p[1].append(p[2])
    p[0] = p[1]


def p_statement_list_single(p):
    """statement_list : statement"""
    p[0] = [p[1]]


def p_statement_deposit(p):
    """statement : DEPOSIT ACCOUNT_ID NUMBER SEMICOLON"""
    p[0] = DepositNode(p[2], int(p[3]))


def p_statement_withdraw(p):
    """statement : WITHDRAW ACCOUNT_ID NUMBER SEMICOLON"""
    p[0] = WithdrawNode(p[2], int(p[3]))


def p_statement_transfer(p):
    """statement : TRANSFER ACCOUNT_ID ACCOUNT_ID NUMBER SEMICOLON"""
    p[0] = TransferNode(p[2], p[3], int(p[4]))


def p_error(p):
    """Report a syntax error at the first unexpected token."""
    if p is None:
        print("Syntax error: unexpected end of input; expected a complete statement.")
    else:
        print(
            "Syntax error at line "
            + str(p.lineno)
            + ": unexpected token "
            + p.type
            + " ("
            + repr(p.value)
            + ")"
        )


def build_parser():
    """Build a parser without generating extra parser table files."""
    return yacc.yacc(write_tables=False, debug=False)


def parse_source(source_text):
    """Parse source text and return a ProgramNode or None on syntax failure."""
    lexer = build_lexer()
    parser = build_parser()
    lexer.lineno = 1
    return parser.parse(source_text, lexer=lexer)
