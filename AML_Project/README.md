# AI-Based Money Laundering Detection System

This project is the compiler frontend foundation for a college CBP project. It reads a small banking transaction language, performs lexical analysis with PLY Lex, parses the statements with PLY Yacc, and builds a readable Abstract Syntax Tree (AST).

The current version intentionally does **not** implement money laundering detection, graph analysis, three-address code, machine code, networking, CRC, Dijkstra's algorithm, or AI features. Those can be added after the frontend foundation is stable.

## Supported Language

Each statement must end with a semicolon:

```text
DEPOSIT ACCOUNT_ID AMOUNT;
WITHDRAW ACCOUNT_ID AMOUNT;
TRANSFER SOURCE_ACCOUNT_ID DESTINATION_ACCOUNT_ID AMOUNT;
```

Example:

```text
DEPOSIT ACC1001 50000;
WITHDRAW ACC1001 10000;
TRANSFER ACC1001 ACC2001 49000;
```

The lexer ignores spaces, tabs, newlines, and comments beginning with `//`. Account identifiers begin with a letter and can contain letters, digits, and underscores. They are limited to 20 characters.

## Folder Structure

```text
AML_Project/
|
|-- data/
|   `-- transactions.txt    Sample input with 15 transactions
|
|-- compiler/
|   |-- lexer.py            PLY lexical analyzer
|   |-- parser.py           PLY Yacc grammar and AST creation
|   `-- ast_nodes.py        Program and transaction AST classes
|
|-- main.py                 Program entry point
|-- requirements.txt        Python dependency list
`-- README.md               Project documentation
```

### File Responsibilities

- `data/transactions.txt` contains sample banking transactions, comments, and blank lines.
- `compiler/ast_nodes.py` defines `ProgramNode`, `DepositNode`, `WithdrawNode`, and `TransferNode`.
- `compiler/lexer.py` recognizes keywords, account IDs, amounts, and semicolons while reporting lexical errors.
- `compiler/parser.py` defines the transaction grammar and creates AST nodes.
- `main.py` reads the sample file, displays tokens, parses the source, and prints the AST.
- `requirements.txt` pins PLY version 3.11.

## Installation

Open a terminal in the `AML_Project` folder and optionally create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependency:

```powershell
python -m pip install -r requirements.txt
```

## Execution

Run the frontend from the project folder:

```powershell
python main.py
```

The program automatically loads `data/transactions.txt` using a path relative to `main.py`, so it can also be launched from another current directory:

```powershell
python C:\path\to\AML_Project\main.py
```

## Expected Output

The first part displays tokens similar to:

```text
LEXER OUTPUT
TOKEN(DEPOSIT, DEPOSIT)
TOKEN(ACCOUNT_ID, ACC1001)
TOKEN(NUMBER, 50000)
TOKEN(SEMICOLON, ;)
```

After token output, the parser prints an AST similar to:

```text
AST OUTPUT
PROGRAM
|-- DEPOSIT
|   |-- account: ACC1001
|   `-- amount: 50000
|-- WITHDRAW
|   |-- account: ACC1001
|   `-- amount: 10000
`-- TRANSFER
    |-- source: ACC1001
    |-- destination: ACC2001
    `-- amount: 49000
```

The sample file contains 15 valid statements, so the complete AST contains 15 transaction branches.

## Testing Checklist

The current sample execution tests:

1. Keyword recognition for `DEPOSIT`, `WITHDRAW`, and `TRANSFER`.
2. Account identifier recognition.
3. Integer amount recognition.
4. Semicolon recognition.
5. Comment and whitespace ignoring.
6. Parsing all three statement forms.
7. AST creation and readable tree output.

For a quick lexer-only check, run:

```powershell
python compiler\lexer.py
```

## Common Errors and Fixes

### `ModuleNotFoundError: No module named 'ply'`

Install the project dependency:

```powershell
python -m pip install -r requirements.txt
```

Make sure VS Code and the terminal use the same Python interpreter.

### Syntax error for a transaction

Check that the statement uses the correct order and ends with `;`:

```text
TRANSFER ACC1001 ACC2001 49000;
```

### Illegal character error

The language currently accepts letters, digits, underscores in account IDs, integer amounts, semicolons, whitespace, and `//` comments. Remove unsupported characters.

### Account identifier is too long

Keep each account identifier at 20 characters or fewer.

### Input file not found

Run `main.py` from the project, or use the full path to `main.py`. The program expects `data/transactions.txt` inside the same project folder.

## Syllabus Mapping

### Week 1: Lexical Analyzer Design

The token set and lexical rules are designed for the transaction language. The project identifies keywords, account identifiers, numbers, semicolons, comments, whitespace, and illegal characters.

### Week 2: Lexical Analyzer Implementation

`compiler/lexer.py` implements those rules using PLY Lex. It tracks line numbers, reports illegal characters, and restricts account identifiers to a reasonable length.

### Week 5: LALR Parsing Using Yacc

`compiler/parser.py` implements the statement-list grammar using PLY Yacc. PLY generates the LALR parser behavior from the grammar productions.

### Week 6: Abstract Syntax Tree Generation

The parser creates `ProgramNode`, `DepositNode`, `WithdrawNode`, and `TransferNode` objects from the recognized statements. Each node stores transaction data and supports readable tree output.

## Current Scope

This milestone ends after frontend AST generation. The next project milestones may build on this AST, but they are intentionally not included yet:

- money laundering detection
- graph analysis
- three-address code generation
- machine code generation
- networking
- CRC
- Dijkstra algorithm
- AI or machine-learning features
