# AI-Based Money Laundering Detection System

This project reads a small banking transaction language, performs lexical analysis with PLY Lex, parses the statements with PLY Yacc, builds a readable Abstract Syntax Tree (AST), and runs an explainable money laundering detection layer on that AST.

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
|   `-- transactions.txt    Sample input with 12 transactions
|
|-- compiler/
|   |-- lexer.py            PLY lexical analyzer
|   |-- parser.py           PLY Yacc grammar and AST creation
|   `-- ast_nodes.py        Program and transaction AST classes
|
|-- analysis/
|   |-- structuring.py      Below-threshold transfer detection
|   |-- circular_transfer.py NetworkX cycle detection
|   |-- temporal_analysis.py High-frequency activity detection
|   |-- anomaly_detection.py IsolationForest anomaly detection
|   |-- pipeline.py          Shared AML and analytics pipeline
|   |-- risk_score.py       Rule-based risk scoring
|   `-- report.py           Readable AML report generation
|
|-- graph/
|   `-- transaction_graph.py NetworkX graph and shortest-path analytics
|
|-- exports/
|   `-- report_export.py    TXT and CSV report export
|
|-- dashboard/
|   `-- app.py              Streamlit dashboard
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
- `main.py` reads the sample file, displays tokens, parses the source, prints the AST, and prints the AML report.
- `analysis/` consumes the existing AST transaction nodes and does not define a second transaction model.
- `requirements.txt` lists PLY, NetworkX, scikit-learn, Streamlit, Plotly, Pandas, and NumPy.

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

## AML Detection Architecture

```text
transactions.txt -> Lexer -> Parser -> AST
    -> Structuring -> Circular Transfer -> Temporal Analysis
    -> Risk Scoring -> Graph Analytics -> AI Anomaly Detection
    -> TXT/CSV Export -> AML Report and Dashboard
```

The lexer and parser remain unchanged. The analysis modules inspect `ProgramNode.statements` and reuse `TransferNode`, `DepositNode`, and `WithdrawNode` directly.

### Structuring Detection

`detect_structuring()` groups transfer amounts by source account. By default, it flags an account when at least two transfers are between 95% and 100% of the configurable threshold of 50000. Each finding includes the account, suspicious amounts, and an explanation.

### Circular Transfer Detection

`detect_circular_transfers()` builds a directed NetworkX graph. Accounts are nodes and transfers are edges. NetworkX `simple_cycles()` returns loops such as `ACC3001 -> ACC4001 -> ACC5001 -> ACC3001`.

### Temporal Analysis

`detect_high_frequency()` counts transactions involving each account inside a configurable `window_minutes` and requires a configurable `minimum_transaction_count`. The existing grammar has no timestamp token, so statement order is used as time: each parsed statement represents one minute by default. This keeps the transaction language unchanged and deterministic. The function accepts `transaction_interval_minutes` for experiments or future timestamp support.

### Risk Scoring

The rule-based score is capped at 100:

- Structuring: +40
- Circular transfer: +30
- High-frequency activity: +20
- Large transfer: +10

Risk levels are LOW for 0-30, MEDIUM for 31-60, and HIGH for 61 or more. Reasons are retained alongside each score so the report remains explainable.

## Graph Analytics

`graph/transaction_graph.py` builds a directed NetworkX graph from `TransferNode` objects. Each account is a node and each transfer is a directed edge. It reports node count, edge count, degree statistics, top connected accounts, suspicious hubs, and cycles. A suspicious hub is an account whose total in-degree plus out-degree reaches the configured minimum.

The `TransactionGraph.find_shortest_path(source_account, destination_account)` helper uses NetworkX Dijkstra-compatible shortest-path analysis and returns both the account chain and its edge count. For example, a direct transfer returns `{"path": ["ACC1001", "ACC2004"], "path_length": 1}`.

## AI Anomaly Detection

`analysis/anomaly_detection.py` creates one feature row per account using average transaction amount, transaction frequency, in-degree, and out-degree. A deterministic scikit-learn `IsolationForest` assigns an anomaly score from 0 to 100 and classifies each account as `NORMAL` or `SUSPICIOUS`. This is intentionally lightweight and explainable for a college project: the score is a model signal and can be compared with the rule-based risk score.

## Dashboard

Start the interactive dashboard from the `AML_Project` folder:

```powershell
streamlit run dashboard/app.py
```

The dashboard contains project overview metrics, a filtered risk register, Plotly risk charts, graph statistics, a curved Plotly/NetworkX account diagram, AI anomaly results, and the generated AML report. The dashboard reads the same `data/transactions.txt` file and calls the same shared pipeline as `main.py`.

### Dashboard Screenshots

Run the dashboard locally and capture screenshots of the Overview, Risk Analysis, Graph Analytics, AI Detection, and AML Report sections for a project presentation. The graph visualization is generated at runtime from the parsed transfer AST, so screenshots remain tied to the sample input.

## Report Export

Running `python main.py` writes these files under `exports/`:

- `aml_report.txt` contains the readable AML report, graph statistics, and anomaly results.
- `aml_report.csv` contains account risk and anomaly rows plus a graph summary row.

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

The sample file contains 12 valid statements, so the complete AST contains 12 transaction branches. It includes structuring, a circular transfer, high-frequency activity, and one normal deposit.

The AML section includes output similar to:

```text
AML ANALYSIS REPORT
Total Accounts: 14
Suspicious Accounts: 5

Account: ACC1001
Risk Score: 60
Risk Level: MEDIUM
Reasons:
- Structuring detected
- High frequency activity

Account: ACC6001
Risk Score: 20
Risk Level: LOW
Reasons:
- High frequency activity
```

## Testing Checklist

The current sample execution tests:

1. Keyword recognition for `DEPOSIT`, `WITHDRAW`, and `TRANSFER`.
2. Account identifier recognition.
3. Integer amount recognition.
4. Semicolon recognition.
5. Comment and whitespace ignoring.
6. Parsing all three statement forms.
7. AST creation and readable tree output.
8. Structuring, circular transfer, and high-frequency AML findings.
9. Risk scores and readable report generation.
10. Graph node, edge, cycle, hub, and shortest-path analysis.
11. IsolationForest anomaly scores and classifications.
12. TXT and CSV report export.
13. Streamlit dashboard startup.

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

This milestone includes the compiler frontend and explainable AML detection layer. Three-address code generation, machine code generation, networking, CRC, Dijkstra's algorithm, and machine-learning features remain outside the current scope.
