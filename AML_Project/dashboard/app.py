"""AML Intelligence Streamlit investigation workspace."""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis.filtering import filter_accounts, filter_patterns, filter_transactions
from analysis.pipeline import analyze_program
from analysis.report import generate_report
from data.csv_ingestion import load_transactions_csv
from data.generate_dataset import generate_dataset
from dashboard.workflow import (
    DISCLAIMER, ORGANIZATION, PLATFORM, TAGLINE, DEMO_USERS, PERMISSIONS,
    append_audit, authenticate, can, create_case, load_audit, load_cases, update_case,
)


TRANSACTIONS_FILE = PROJECT_ROOT / "data" / "transactions.txt"
GENERATED_DIR = PROJECT_ROOT / "data" / "generated"
CASES_FILE = PROJECT_ROOT / "data" / "workflow_cases.json"
AUDIT_FILE = PROJECT_ROOT / "data" / "audit_log.json"
RISK_COLORS = {"LOW": "#37c7a0", "MEDIUM": "#f0b35b", "HIGH": "#ee6b6e"}
ACCENT = "#5b8def"
TEMPLATE = "plotly_dark"


@st.cache_data(show_spinner=False)
def load_dataset(dataset_path, accounts_path, dataset_version=None):
    """Load and validate the selected dataset, returning the real profile metadata."""
    transactions_path = Path(dataset_path)
    accounts_path = Path(accounts_path)
    account_rows = pd.read_csv(accounts_path, usecols=["account_id"])
    account_ids = set(account_rows["account_id"].astype(str))
    program = load_transactions_csv(transactions_path)
    records = []
    timestamps = []
    for statement in program.statements:
        timestamp = getattr(statement, "timestamp", None)
        if timestamp:
            timestamps.append(pd.Timestamp(timestamp))
        if hasattr(statement, "source_account") and statement.source_account:
            records.append(statement.source_account)
        if hasattr(statement, "destination_account") and statement.destination_account:
            records.append(statement.destination_account)
        if hasattr(statement, "account_id"):
            records.append(statement.account_id)
    referenced_accounts = set(records)
    invalid = referenced_accounts - account_ids
    if invalid:
        raise ValueError("Dataset references unknown accounts: " + ", ".join(sorted(invalid)[:5]))
    if len(account_ids) != len(account_rows):
        raise ValueError("The account file contains duplicate account IDs.")
    if not timestamps:
        raise ValueError("The selected dataset has no timestamps.")
    return {
        "program": program,
        "account_count": len(account_ids),
        "transaction_count": len(program.statements),
        "transaction_volume": sum(statement.amount for statement in program.statements),
        "start_date": min(timestamps).date().isoformat(),
        "end_date": max(timestamps).date().isoformat(),
        "dataset_path": str(transactions_path),
        "account_path": str(accounts_path),
    }


@st.cache_data(show_spinner="Running AML analysis on the selected dataset...")
def load_results(dataset_path, accounts_path, tolerance_percent, absolute_tolerance, minimum_transactions,
                 minimum_accounts, transaction_types, dataset_version=None):
    """Analyze the validated CSV dataset through the existing AML pipeline."""
    dataset = load_dataset(dataset_path, accounts_path, dataset_version)
    started = time.perf_counter()
    results = analyze_program(
        dataset["program"],
        similarity_tolerance_percent=tolerance_percent,
        similarity_absolute_tolerance=absolute_tolerance,
        similarity_minimum_transactions=minimum_transactions,
        similarity_minimum_accounts=minimum_accounts,
        similarity_transaction_types=transaction_types,
        max_graph_cycles=0 if dataset["transaction_count"] > 50000 else 200,
        enable_similarity=dataset["transaction_count"] <= 50000,
    )
    results["analysis_seconds"] = round(time.perf_counter() - started, 2)
    return results


def inject_styles():
    st.markdown(
        """
        <style>
        .stApp { background: #0b1220; color: #e8eef8; }
        [data-testid="stSidebar"] { background: #101a2c; border-right: 1px solid #263856; }
        .block-container { max-width: 1540px; padding: 1.25rem 2.25rem 3rem; }
        [data-testid="stHeader"] { background: rgba(11, 18, 32, .96); }
        [data-testid="stToolbar"] { right: .75rem; }
        @media (max-width: 900px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
        }
        .eyebrow { color: #8ea3c0; font-size: .72rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
        .hero-title { color: #f6f8fc; font-size: 2.2rem; font-weight: 750; letter-spacing: -.03em; margin: .1rem 0 .2rem; }
        .hero-subtitle { color: #9caec6; margin-bottom: 1.4rem; }
        div[data-testid="stMetric"] { background: #121f34; border: 1px solid #2b3d5b; border-radius: 10px; padding: .8rem .9rem; min-height: 96px; }
        div[data-testid="stMetricLabel"] { white-space: normal; line-height: 1.25; }
        div[data-testid="stMetricValue"] { font-size: clamp(1.15rem, 2vw, 1.8rem); line-height: 1.15; }
        div[data-testid="stDataFrame"] { border: 1px solid #263856; border-radius: 8px; overflow: hidden; }
        .section-rule { border-top: 1px solid #263856; margin: 1.2rem 0 .9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def empty_state(message):
    st.info(message)


def chart_layout(figure, height=330):
    figure.update_layout(
        template=TEMPLATE, height=height, margin=dict(l=12, r=12, t=28, b=12),
        paper_bgcolor="#121f34", plot_bgcolor="#121f34",
        legend=dict(orientation="h", y=1.08),
    )
    return figure


def risk_chart(accounts):
    counts = pd.Series([item["risk_level"] for item in accounts]).value_counts()
    frame = pd.DataFrame({
        "Risk Level": ["LOW", "MEDIUM", "HIGH"],
        "Accounts": [int(counts.get(level, 0)) for level in ("LOW", "MEDIUM", "HIGH")],
    })
    return chart_layout(px.bar(frame, x="Risk Level", y="Accounts", color="Risk Level",
        color_discrete_map=RISK_COLORS, text="Accounts"), 310)


def top_accounts_chart(accounts, metric="risk_score", top_n=10):
    if not accounts:
        return None
    labels = {"risk_score": "Risk Score", "suspicious_transaction_count": "Suspicious Transactions",
              "suspicious_transaction_amount": "Suspicious Amount"}
    frame = pd.DataFrame([
        {"Account": item["account"], labels[metric]: item[metric]} for item in accounts
    ]).sort_values(labels[metric]).tail(top_n)
    return chart_layout(px.bar(frame, x=labels[metric], y="Account", orientation="h",
        color=labels[metric], color_continuous_scale=["#37c7a0", "#f0b35b", "#ee6b6e"]),
        360).update_layout(coloraxis_showscale=False, yaxis_title=None)


def graph_figure(graph, accounts, cycles, max_nodes=40):
    if graph.number_of_nodes() == 0:
        return None
    allowed = {item["account"] for item in accounts}
    nodes = sorted(allowed.intersection(graph.nodes), key=lambda node: graph.degree(node), reverse=True)
    nodes = nodes[:max_nodes]
    graph = graph.subgraph(nodes).copy()
    if graph.number_of_nodes() == 0:
        return None
    positions = nx.spring_layout(graph, seed=42, k=1.5, iterations=80)
    cycle_accounts = {account for cycle in cycles for account in cycle}
    risk_by_account = {item["account"]: item for item in accounts}
    edge_x, edge_y = [], []
    for source, target in graph.edges:
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        edge_x.extend([x1, x2, None])
        edge_y.extend([y1, y2, None])
    figure = go.Figure(go.Scatter(x=edge_x, y=edge_y, mode="lines",
        line=dict(color="#536886", width=1.5), hoverinfo="none", showlegend=False))
    figure.add_trace(go.Scatter(
        x=[positions[node][0] for node in graph.nodes],
        y=[positions[node][1] for node in graph.nodes],
        mode="markers+text", text=list(graph.nodes), textposition="top center",
        marker=dict(
            size=[18 + graph.degree(node) * 6 for node in graph.nodes],
            color=[RISK_COLORS.get(risk_by_account.get(node, {}).get("risk_level"), ACCENT)
                   for node in graph.nodes],
            line=dict(color=["#ee6b6e" if node in cycle_accounts else "#dbe7f6"
                             for node in graph.nodes], width=2),
        ),
        hovertemplate="<b>%{text}</b><br>Connections: %{customdata}<extra></extra>",
        customdata=[graph.degree(node) for node in graph.nodes],
        showlegend=False,
    ))
    return chart_layout(figure, 570).update_layout(xaxis_visible=False, yaxis_visible=False)


def records_frame(records, suspicious_indices):
    rows = []
    suspicious = set(suspicious_indices)
    for record in records:
        rows.append({
            "Transaction": record["transaction_id"], "Type": record["type"],
            "Source": record["source_account"] or "-", "Destination": record["destination_account"] or "-",
            "Amount": record["amount"], "Status": "REVIEW" if record["index"] in suspicious else "NORMAL",
        })
    return pd.DataFrame(rows)


def paged_frame(frame, key, page_size=50):
    """Render a bounded table while keeping the complete filtered frame exportable."""
    if frame.empty:
        empty_state("No records match the current filters.")
        return
    page_count = max(1, (len(frame) + page_size - 1) // page_size)
    page = st.number_input(
        "Page", min_value=1, max_value=page_count, value=1, step=1, key=key,
    )
    start = (page - 1) * page_size
    st.caption(f"Showing rows {start + 1:,}-{min(start + page_size, len(frame)):,} of {len(frame):,}.")
    st.dataframe(frame.iloc[start:start + page_size], use_container_width=True, hide_index=True)


def render_overview(accounts, transactions, patterns):
    st.markdown("#### Executive overview")
    if not accounts:
        empty_state("No accounts match the current filters.")
        return
    left, middle, right = st.columns(3)
    with left:
        st.plotly_chart(chart_layout(risk_chart(accounts).update_layout(
            title="Risk distribution — filtered accounts",
        ), 310), use_container_width=True, config={"displayModeBar": False})
    with middle:
        figure = top_accounts_chart(accounts)
        if figure:
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    with right:
        counts = pd.Series([item["anomaly_classification"] for item in accounts]).value_counts()
        figure = chart_layout(px.pie(values=counts.values, names=counts.index,
            color=counts.index, color_discrete_map={"NORMAL": "#37c7a0", "SUSPICIOUS": "#ee6b6e"}), 310)
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    st.caption("Charts reflect the filtered account and transaction view, not the full dataset.")
    render_suspicious_activity(accounts)


def render_transactions(transactions, suspicious_indices):
    st.markdown("#### Transaction intelligence")
    if not transactions:
        empty_state("No transactions match the current filters.")
        return
    frame = records_frame(transactions, suspicious_indices)
    paged_frame(frame, "transaction_table_page")
    amount_frame = frame.assign(Bin=pd.cut(frame["Amount"], bins=min(8, max(1, len(frame))),
                                            duplicates="drop"))
    st.plotly_chart(chart_layout(px.histogram(
        amount_frame, x="Amount", nbins=min(8, len(frame)),
        color="Status", color_discrete_map={"REVIEW": "#ee6b6e", "NORMAL": ACCENT},
        title="Transaction amount distribution — filtered view",
    ), 320),
        use_container_width=True, config={"displayModeBar": False})


def render_pattern_chart(patterns):
    if not patterns:
        empty_state("No complete similar-transaction groups match the current filters.")
        return
    frame = pd.DataFrame([{
        "Pattern": pattern["pattern_id"],
        "Type": pattern["pattern_type"],
        "Matching transactions": pattern["matching_transactions"],
    } for pattern in patterns])
    st.plotly_chart(chart_layout(px.bar(
        frame, x="Pattern", y="Matching transactions", color="Type",
        title="Potential similar transaction patterns — filtered view",
        hover_data=["Type"],
    ), 320), use_container_width=True, config={"displayModeBar": False})


def render_suspicious_activity(accounts):
    if not accounts:
        empty_state("No suspicious transaction activity matches the current filters.")
        return
    frame = pd.DataFrame([{
        "Account": item["account"],
        "Suspicious transactions": item["suspicious_transaction_count"],
    } for item in accounts if item["suspicious_transaction_count"] > 0])
    if frame.empty:
        empty_state("No suspicious transaction activity matches the current filters.")
        return
    st.plotly_chart(chart_layout(px.bar(
        frame.sort_values("Suspicious transactions"),
        x="Suspicious transactions", y="Account", orientation="h",
        title="Suspicious transactions per account — filtered view",
        color="Suspicious transactions",
        color_continuous_scale=["#f0b35b", "#ee6b6e"],
    ), 330).update_layout(coloraxis_showscale=False, yaxis_title=None),
        use_container_width=True, config={"displayModeBar": False})


def render_accounts(accounts, all_records, patterns):
    st.markdown("#### Account investigation")
    if not accounts:
        empty_state("No accounts match the current filters.")
        return
    frame = pd.DataFrame([{
        "Account": item["account"], "Risk": item["risk_level"], "Score": item["risk_score"],
        "Transactions": item["total_transactions"],
        "Suspicious Transactions": item["suspicious_transaction_count"],
        "Distinct Patterns": item["distinct_pattern_count"],
        "Rule Triggers": item["detection_rule_count"],
        "Anomaly": item["anomaly_classification"],
    } for item in accounts])
    paged_frame(frame, "account_table_page")
    displayed_accounts = frame["Account"].tolist()[:500]
    selected = st.selectbox("Account under investigation", displayed_accounts)
    item = next(account for account in accounts if account["account"] == selected)
    cols = st.columns(4)
    cols[0].metric("Risk score", item["risk_score"])
    cols[1].metric("Suspicious transactions", item["suspicious_transaction_count"])
    cols[2].metric("Distinct patterns", item["distinct_pattern_count"])
    cols[3].metric("Anomaly", item["anomaly_classification"])
    if item["reasons"]:
        st.write("Detection explanations: " + "; ".join(item["reasons"]))
    selected_records = [record for record in all_records if record["index"] in item["transaction_indices"]]
    paged_frame(
        records_frame(selected_records, item["suspicious_transaction_indices"]),
        "account_transactions_page",
    )
    related = sorted({account for record in selected_records for account in record["accounts"]
                      if account != selected})
    st.caption("Related accounts: " + (", ".join(related) if related else "None"))
    account_patterns = [pattern for pattern in patterns if selected in pattern["accounts"]]
    if account_patterns:
        st.dataframe(pd.DataFrame(account_patterns)[
            ["pattern_id", "pattern_type", "matching_transactions", "amount_min", "amount_max", "explanation"]
        ], use_container_width=True, hide_index=True)


def render_network(results, accounts):
    st.markdown("#### Network analysis")
    stats = results["graph_statistics"]
    metrics = st.columns(4)
    metrics[0].metric("Nodes in full graph", stats["node_count"])
    metrics[1].metric("Edges in full graph", stats["edge_count"])
    metrics[2].metric("Cycles", stats["cycle_count"])
    metrics[3].metric("Visible nodes", min(len(accounts), 40))
    if not accounts:
        empty_state("No accounts match the current filters.")
        return
    max_nodes = st.slider("Maximum visible nodes", 5, 100, min(40, max(5, len(accounts))))
    figure = graph_figure(results["graph"], accounts, stats["cycles"], max_nodes)
    if figure:
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    else:
        empty_state("No transfer relationships exist in the filtered view.")


def render_anomalies(accounts):
    st.markdown("#### AI anomaly detection")
    if not accounts:
        empty_state("No anomaly records match the current filters.")
        return
    frame = pd.DataFrame([{
        "Account": item["account"], "Anomaly Score": item["anomaly_score"],
        "Classification": item["anomaly_classification"], "Risk Level": item["risk_level"],
    } for item in accounts]).sort_values("Anomaly Score", ascending=False)
    paged_frame(frame, "anomaly_table_page")
    st.plotly_chart(chart_layout(px.bar(frame.head(15).sort_values("Anomaly Score"),
        x="Anomaly Score", y="Account", orientation="h", color="Classification",
        color_discrete_map={"NORMAL": "#37c7a0", "SUSPICIOUS": "#ee6b6e"}), 360),
        use_container_width=True, config={"displayModeBar": False})


def render_reports(results, transactions, accounts, patterns):
    st.markdown("#### Reports and exports")
    report = generate_report({item["account"]: {
        "account": item["account"], "score": item["risk_score"], "level": item["risk_level"],
        "reasons": item["reasons"],
    } for item in accounts}, len(accounts))
    st.caption("This report covers the current filtered subset. The CLI export remains dataset-wide.")
    full_report = generate_report(results["risk_scores"], results["total_accounts"])
    st.download_button("Download full dataset TXT report", full_report,
                       "aml_full_report.txt", "text/plain")
    transaction_lines = [
        "",
        "FILTERED TRANSACTIONS",
        "Transactions: " + str(len(transactions)),
    ]
    transaction_lines.extend(
        record["transaction_id"] + " | " + record["type"]
        + " | " + str(record["amount"])
        for record in transactions
    )
    st.download_button("Download filtered TXT report", report + "\n" + "\n".join(transaction_lines),
                       "aml_filtered_report.txt", "text/plain")
    filtered_csv = records_frame(
        transactions, results["suspicious_transaction_indices"]
    ).to_csv(index=False)
    st.download_button("Download filtered transaction CSV", filtered_csv,
                       "aml_filtered_transactions.csv", "text/csv")
    st.download_button("Download filtered account investigation CSV",
                       pd.DataFrame(accounts).to_csv(index=False),
                       "aml_filtered_accounts.csv", "text/csv")
    if patterns:
        st.download_button("Download similarity groups CSV", pd.DataFrame(patterns).to_csv(index=False),
                           "similar_transaction_patterns.csv", "text/csv")
    st.code(report, language="text")


def available_datasets():
    options = {}
    if (GENERATED_DIR / "transactions.csv").exists() and (GENERATED_DIR / "accounts.csv").exists():
        options["Generated synthetic dataset (validated on load)"] = (
            GENERATED_DIR / "transactions.csv", GENERATED_DIR / "accounts.csv"
        )
    options["Compiler sample dataset (12 transactions)"] = (TRANSACTIONS_FILE, None)
    return options


def dataset_version(dataset_path, accounts_path):
    """Return a cache key that changes when either source file is replaced."""
    transaction_stat = Path(dataset_path).stat()
    account_stat = Path(accounts_path).stat()
    return (
        transaction_stat.st_mtime_ns, transaction_stat.st_size,
        account_stat.st_mtime_ns, account_stat.st_size,
    )


def render_login():
    st.markdown(
        '<div class="login-card"><div class="eyebrow">Academic financial intelligence platform</div>'
        '<div class="hero-title">' + ORGANIZATION + '</div><div class="hero-subtitle">'
        + PLATFORM + " — " + TAGLINE + "</div></div>",
        unsafe_allow_html=True,
    )
    st.warning(DISCLAIMER)
    with st.form("login_form"):
        username = st.text_input("Demonstration username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")
    st.caption("Demo accounts are documented in README.md. This local login is for academic demonstration only.")
    if submitted:
        identity = authenticate(username, password)
        if identity is None:
            st.error("Invalid demonstration credentials.")
        else:
            st.session_state["identity"] = identity
            append_audit(AUDIT_FILE, identity, "LOGIN")
            st.rerun()


def render_command_dashboard(results, dataset, accounts, transactions):
    st.markdown("#### Command dashboard")
    dataset_accounts = results["account_intelligence"]
    kpis = st.columns(4)
    for column, label, value in zip(
        kpis,
        ("Accounts monitored", "Transactions analyzed", "Transaction volume", "Suspicious findings"),
        (dataset["account_count"], dataset["transaction_count"],
         f"{dataset['transaction_volume']:,.0f}",
         len(results["suspicious_transaction_indices"])),
    ):
        column.metric(label, value)
    secondary_kpis = st.columns(3)
    secondary_kpis[0].metric(
        "Simulation dates", dataset["start_date"] + " to " + dataset["end_date"],
    )
    secondary_kpis[1].metric(
        "High-risk accounts", sum(item["risk_level"] == "HIGH" for item in dataset_accounts),
    )
    secondary_kpis[2].metric(
        "Open cases", len([case for case in load_cases(CASES_FILE) if case["status"] != "Closed"]),
    )
    st.caption(
        "Dataset-wide metrics are calculated from the selected validated files. "
        f"Cached AML analysis: {results.get('analysis_seconds', 'n/a')} seconds."
    )
    activity = pd.DataFrame(results["activity_by_date"])
    if not activity.empty:
        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                chart_layout(px.line(
                    activity, x="Date", y=["Transactions", "Suspicious"],
                    title="Transaction activity over time",
                ), 340),
                use_container_width=True, config={"displayModeBar": False},
            )
        type_counts = pd.DataFrame([
            {"Type": transaction_type, "Transactions": count}
            for transaction_type, count in results["transaction_type_counts"].items()
        ])
        with right:
            st.plotly_chart(
                chart_layout(px.bar(
                    type_counts, x="Type", y="Transactions",
                    title="Transaction type distribution",
                    color="Type",
                    color_discrete_sequence=[ACCENT, "#37c7a0", "#f0b35b"],
                ), 340),
                use_container_width=True, config={"displayModeBar": False},
            )
    st.markdown("#### Highest-risk accounts")
    st.dataframe(pd.DataFrame(dataset_accounts[:15])[[
        "account", "risk_level", "risk_score", "suspicious_transaction_count",
        "anomaly_classification",
    ]], use_container_width=True, hide_index=True)


def render_monitoring(results):
    st.markdown("#### Transaction monitoring")
    query = st.text_input("Search transaction ID or account", key="transaction_search")
    minimum, maximum = st.slider("Amount range", 0, 1000000, (0, 1000000), 1000)
    types = st.multiselect("Transaction types", ["TRANSFER", "DEPOSIT", "WITHDRAW"],
                           default=["TRANSFER", "DEPOSIT", "WITHDRAW"], key="monitor_types")
    records = filter_transactions(
        results["transaction_records"], query, types, minimum, maximum,
        results["records_by_account"], results["record_indices_by_transaction_id"],
    )
    page_size = 50
    page = st.number_input("Page", 1, max(1, (len(records) + page_size - 1) // page_size), 1)
    st.caption("Showing " + str(len(records)) + " matching records; pages are limited to 50 rows.")
    render_transactions(records[(page - 1) * page_size:page * page_size],
                        results["suspicious_transaction_indices"])


def render_suspicious_center(results, accounts):
    st.markdown("#### Suspicious activity center")
    suspicious = [item for item in accounts if item["suspicious_transaction_count"] > 0]
    if not suspicious:
        st.info("No suspicious activity findings are present.")
        return
    paged_frame(pd.DataFrame(suspicious)[[
        "account", "risk_level", "risk_score", "suspicious_transaction_count",
        "suspicious_transaction_amount", "reasons",
    ]], "suspicious_accounts_page")
    st.caption("Risk scores are analytical signals requiring investigation, not findings of guilt.")


def render_cases(identity, results):
    st.markdown("#### Investigation case management")
    cases = load_cases(CASES_FILE)
    if can(identity, "manage_cases"):
        with st.form("create_case"):
            account = st.text_input("Related account ID")
            transaction_id = st.text_input("Related transaction ID")
            officer = st.text_input("Assigned officer", value=identity["username"])
            notes = st.text_area("Investigation notes")
            if st.form_submit_button("Create case"):
                try:
                    case = create_case(CASES_FILE, identity, [account], [transaction_id], officer, notes)
                    append_audit(AUDIT_FILE, identity, "CASE_CREATED", case["case_id"])
                    st.success("Created " + case["case_id"])
                    st.rerun()
                except (PermissionError, ValueError, OSError) as error:
                    st.error(str(error))
    if not cases:
        st.info("No investigation cases have been created.")
        return
    st.dataframe(pd.DataFrame(cases), use_container_width=True, hide_index=True)
    selected = st.selectbox("Case to update", [case["case_id"] for case in cases])
    if can(identity, "manage_cases"):
        status = st.selectbox("Status", ["New", "Under Review", "Escalated", "Closed"])
        notes = st.text_area("Additional notes", key="case_update_notes")
        if st.button("Save case update"):
            update_case(CASES_FILE, identity, selected, status=status, notes=notes)
            append_audit(AUDIT_FILE, identity, "CASE_UPDATED", selected)
            st.success("Case updated.")
    if can(identity, "approve_reports"):
        decision = st.selectbox("Supervisor decision", ["Approved", "Rejected"])
        if st.button("Record report decision"):
            update_case(CASES_FILE, identity, selected, approval=decision)
            append_audit(AUDIT_FILE, identity, "REPORT_DECISION", selected + ": " + decision)
            st.success("Decision recorded.")


def render_audit(identity):
    st.markdown("#### Audit trail")
    if not can(identity, "audit"):
        st.error("Your role is not authorized to view audit records.")
        return
    st.caption("This is a local editable academic audit log, not a tamper-proof government record.")
    entries = load_audit(AUDIT_FILE)
    st.dataframe(pd.DataFrame(entries), use_container_width=True, hide_index=True)


def render_admin(identity, dataset_options):
    st.markdown("#### System administration")
    if not can(identity, "administer_system"):
        st.error("Only the System Administrator can access administration controls.")
        return
    with st.form("generate_dataset"):
        st.markdown("##### Generate a synthetic dataset")
        account_count = st.number_input("Accounts", 1000, 50000, 15000, 1000)
        transaction_count = st.number_input("Transactions", 10000, 1000000, 200000, 10000)
        days = st.number_input("Simulation days", 1, 365, 90)
        seed = st.number_input("Random seed", 0, 2147483647, 42)
        if st.form_submit_button("Generate data/generated"):
            try:
                result = generate_dataset(
                    GENERATED_DIR, int(account_count), int(transaction_count),
                    int(days), int(seed),
                )
                st.cache_data.clear()
                append_audit(AUDIT_FILE, identity, "DATASET_GENERATED",
                             str(result["transaction_count"]) + " transactions")
                st.success("Generated " + str(result["account_count"]) + " accounts and "
                           + str(result["transaction_count"]) + " transactions.")
                st.rerun()
            except (OSError, ValueError) as error:
                st.error("Dataset generation failed: " + str(error))
    st.write("Available datasets:")
    for label, paths in dataset_options.items():
        st.code(label + "\n" + str(paths[0]))
    st.write("Demonstration users and permissions")
    st.dataframe(pd.DataFrame([
        {"Username": username, "Role": details[0],
         "Permissions": ", ".join(sorted(PERMISSIONS[details[0]]))}
        for username, details in DEMO_USERS.items()
    ]), use_container_width=True, hide_index=True)
    st.info("Dataset generation is performed with the documented CLI command; this page does not overwrite data automatically.")


def main():
    st.set_page_config(page_title=PLATFORM, page_icon="shield", layout="wide")
    inject_styles()
    identity = st.session_state.get("identity")
    if identity is None:
        render_login()
        return
    dataset_options = available_datasets()
    with st.sidebar:
        st.markdown("## NFI-AMD")
        st.markdown("### " + PLATFORM)
        st.caption(TAGLINE)
        st.success(identity["role"])
        if st.button("Log out"):
            append_audit(AUDIT_FILE, identity, "LOGOUT")
            st.session_state.pop("identity", None)
            st.rerun()
        allowed_views = ["Command Dashboard", "About FITMS"]
        if can(identity, "review_alerts"):
            allowed_views.extend(["Transaction Monitoring", "Suspicious Activity Center"])
        if can(identity, "investigate_accounts"):
            allowed_views.extend(["Account Intelligence", "Network Investigation"])
        if can(identity, "reports"):
            allowed_views.append("Reports and Exports")
        if can(identity, "manage_cases"):
            allowed_views.append("Case Management")
        if can(identity, "audit"):
            allowed_views.append("Audit Trail")
        if can(identity, "administer_system"):
            allowed_views.append("System Administration")
        view = st.radio("Workspace", allowed_views)
        st.divider()
        dataset_label = st.selectbox("Dataset", list(dataset_options))
        dataset_path, accounts_path = dataset_options[dataset_label]
        if accounts_path is None:
            st.warning("The compiler sample is for language testing; it is not the operational city dataset.")
            st.stop()
        st.caption("Loaded file: " + str(dataset_path))
        st.divider()
        st.markdown("#### Analysis parameters")
        tolerance = st.number_input("Similarity tolerance (%)", 0.0, 100.0, 2.0, .5, key="similarity_tolerance")
        absolute_tolerance = st.number_input("Absolute amount tolerance", 0.0, 1000000.0, 0.0, 100.0, key="similarity_absolute_tolerance")
        minimum_matches = st.number_input("Minimum matching transactions", 1, 100, 2, key="similarity_minimum_matches")
        minimum_accounts = st.number_input("Minimum accounts", 1, 100, 2, key="similarity_minimum_accounts")
        types = st.multiselect("Transaction types", ["TRANSFER", "DEPOSIT", "WITHDRAW"],
                               default=["TRANSFER", "DEPOSIT", "WITHDRAW"], key="transaction_types")
        st.divider()
        st.markdown("#### View filters")
        account_query = st.text_input("Account search", key="account_search")
        risk_level = st.selectbox("Risk level", ["ALL", "HIGH", "MEDIUM", "LOW"], key="risk_level")
        minimum_score, maximum_score = st.slider("Risk score range", 0, 100, (0, 100), key="risk_score_range")
        suspicious_only = st.checkbox("Suspicious accounts only", key="suspicious_only")
        anomaly = st.selectbox("Anomaly classification", ["ALL", "SUSPICIOUS", "NORMAL"], key="anomaly_classification")
        minimum_suspicious = st.number_input("Minimum suspicious transactions", 0, 100, 0, key="minimum_suspicious")
        minimum_amount, maximum_amount = st.slider("Transaction amount range", 0, 1000000, (0, 1000000), 1000, key="transaction_amount_range")
        if st.button("Reset filters"):
            for key in (
                "similarity_tolerance", "similarity_absolute_tolerance",
                "similarity_minimum_matches", "similarity_minimum_accounts",
                "transaction_types", "account_search", "risk_level",
                "risk_score_range", "suspicious_only", "anomaly_classification",
                "minimum_suspicious", "transaction_amount_range",
            ):
                st.session_state.pop(key, None)
            st.rerun()
    try:
        version = dataset_version(dataset_path, accounts_path)
        dataset = load_dataset(str(dataset_path), str(accounts_path), version)
        results = load_results(str(dataset_path), str(accounts_path), tolerance, absolute_tolerance,
                               minimum_matches, minimum_accounts, tuple(types), version)
    except (OSError, ValueError, RuntimeError) as error:
        st.error("Dataset loading or AML analysis failed: " + str(error))
        return
    if not results["transaction_records"]:
        st.warning("The selected dataset is empty.")
        return
    filtered_transactions = filter_transactions(
        results["transaction_records"], account_query, types, minimum_amount, maximum_amount,
        results["records_by_account"], results["record_indices_by_transaction_id"],
    )
    transaction_scope_active = (
        set(types) != {"TRANSFER", "DEPOSIT", "WITHDRAW"}
        or minimum_amount > 0
        or maximum_amount < 1000000
    )
    filtered_indices = {
        record["index"] for record in filtered_transactions
    }
    filtered_accounts = filter_accounts(
        results["account_intelligence"], account_query, risk_level,
        minimum_score, maximum_score, suspicious_only, anomaly,
        minimum_suspicious,
        filtered_indices if transaction_scope_active else None,
    )
    account_names = {item["account"] for item in filtered_accounts}
    account_filter_active = bool(
        account_query or risk_level != "ALL" or minimum_score > 0
        or maximum_score < 100 or suspicious_only or anomaly != "ALL"
        or minimum_suspicious > 0
    )
    if account_filter_active:
        filtered_transactions = [
            record for record in filtered_transactions
            if account_names.intersection(record["accounts"])
        ]
    filtered_patterns = filter_patterns(results["similar_patterns"],
                                        [record["index"] for record in filtered_transactions])

    st.markdown('<div class="eyebrow">NFI-AMD / authenticated intelligence workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">' + PLATFORM + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">' + TAGLINE + ' — ' + identity["role"] + '</div>', unsafe_allow_html=True)
    if view == "Command Dashboard":
        render_command_dashboard(results, dataset, filtered_accounts, filtered_transactions)
    elif view == "Transaction Monitoring":
        render_monitoring(results)
    elif view == "Account Intelligence":
        render_accounts(filtered_accounts, results["transaction_records"], filtered_patterns)
    elif view == "Suspicious Activity Center":
        render_suspicious_center(results, filtered_accounts)
    elif view == "Network Investigation":
        render_network(results, filtered_accounts)
    elif view == "Case Management":
        render_cases(identity, results)
    elif view == "Audit Trail":
        render_audit(identity)
    elif view == "System Administration":
        render_admin(identity, dataset_options)
    elif view == "About FITMS":
        st.markdown("#### About FITMS")
        st.write(ORGANIZATION)
        st.write(PLATFORM)
        st.write(TAGLINE)
        st.info(DISCLAIMER)
        st.caption("All records and findings are synthetic. This local workflow is not affiliated with any government agency.")
    else:
        render_reports(results, filtered_transactions, filtered_accounts, filtered_patterns)
    st.divider()
    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
