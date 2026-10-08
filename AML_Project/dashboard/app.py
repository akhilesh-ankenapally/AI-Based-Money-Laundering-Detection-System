"""Professional Streamlit presentation layer for the AML analysis platform."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis.pipeline import analyze_program
from analysis.report import generate_report
from compiler.parser import parse_source


TRANSACTIONS_FILE = PROJECT_ROOT / "data" / "transactions.txt"
RISK_COLORS = {"LOW": "#27c499", "MEDIUM": "#f5b942", "HIGH": "#f05d5e"}
PLOTLY_TEMPLATE = "plotly_dark"


@st.cache_data(show_spinner=False)
def load_results():
    """Parse and analyze the source once per input file state."""
    source_text = TRANSACTIONS_FILE.read_text(encoding="utf-8")
    program = parse_source(source_text)
    if program is None:
        raise ValueError("The transaction file could not be parsed.")
    return analyze_program(program)


def inject_styles():
    """Apply restrained enterprise dashboard styling."""
    st.markdown(
        """
        <style>
        .stApp { background: #0b111b; color: #e7edf5; }
        [data-testid="stHeader"] { background: rgba(11, 17, 27, 0.94); }
        [data-testid="stSidebar"] { background: #101927; border-right: 1px solid #223149; }
        .block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 3rem; }
        .eyebrow { color: #7f94ae; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }
        .hero-title { color: #f4f7fb; font-size: 2.15rem; font-weight: 700; letter-spacing: -0.02em; margin: 0.15rem 0 0.25rem; }
        .hero-subtitle { color: #91a3b8; font-size: 0.98rem; margin-bottom: 1.4rem; }
        .section-kicker { color: #6f849f; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
        .section-title { color: #f4f7fb; font-size: 1.25rem; font-weight: 650; margin: 0.15rem 0 0.8rem; }
        div[data-testid="stMetric"] { background: #121d2c; border: 1px solid #24344c; border-radius: 8px; padding: 1rem 1.1rem; }
        div[data-testid="stMetricLabel"] { color: #91a3b8; }
        div[data-testid="stMetricValue"] { color: #f4f7fb; }
        .source-note { color: #6f849f; font-size: 0.78rem; margin-top: 0.55rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_heading(kicker, title, description=None):
    st.markdown('<div class="section-kicker">' + kicker + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">' + title + "</div>", unsafe_allow_html=True)
    if description:
        st.caption(description)


def risk_rows(results, minimum_score, selected_level, suspicious_only):
    rows = []
    for item in results["risk_scores"].values():
        if item["score"] < minimum_score:
            continue
        if selected_level != "ALL" and item["level"] != selected_level:
            continue
        if suspicious_only and item["score"] == 0:
            continue
        rows.append({
            "Account": item["account"],
            "Risk Score": item["score"],
            "Risk Level": item["level"],
            "Flags": "; ".join(item["reasons"]) or "No flags",
        })
    return sorted(rows, key=lambda row: (-row["Risk Score"], row["Account"]))


def style_risk_table(dataframe):
    def row_style(row):
        color = RISK_COLORS.get(row["Risk Level"], "#91a3b8")
        return ["color: " + color + "; font-weight: 700" if column == "Risk Level" else "" for column in row.index]

    return dataframe.style.apply(row_style, axis=1)


def show_table(rows, columns, styled=False):
    if not rows:
        st.info("No data available")
        return
    dataframe = pd.DataFrame(rows, columns=columns)
    if styled:
        st.dataframe(style_risk_table(dataframe), use_container_width=True, hide_index=True)
    else:
        st.dataframe(dataframe, use_container_width=True, hide_index=True)


def make_risk_distribution(results):
    counts = {level: 0 for level in ("LOW", "MEDIUM", "HIGH")}
    for item in results["risk_scores"].values():
        counts[item["level"]] += 1
    dataframe = pd.DataFrame({"Risk Level": list(counts), "Accounts": list(counts.values())})
    return px.bar(
        dataframe,
        x="Risk Level",
        y="Accounts",
        color="Risk Level",
        color_discrete_map=RISK_COLORS,
        template=PLOTLY_TEMPLATE,
        height=300,
    ).update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10), xaxis_title=None)


def make_top_risk_chart(results):
    rows = sorted(results["risk_scores"].values(), key=lambda item: item["score"], reverse=True)[:10]
    if not rows:
        return None
    dataframe = pd.DataFrame({"Account": [row["account"] for row in rows], "Risk Score": [row["score"] for row in rows]})
    return px.bar(
        dataframe.sort_values("Risk Score"),
        x="Risk Score",
        y="Account",
        orientation="h",
        color="Risk Score",
        color_continuous_scale=[[0, "#27c499"], [0.6, "#f5b942"], [1, "#f05d5e"]],
        template=PLOTLY_TEMPLATE,
        height=300,
    ).update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10), yaxis_title=None)


def make_detection_chart(results):
    counts = {"Structuring": 0, "Circular Transfer": 0, "High Frequency": 0, "Large Transfer": 0}
    labels = {
        "Structuring detected": "Structuring",
        "Circular transfer detected": "Circular Transfer",
        "High frequency activity": "High Frequency",
        "Large transfer detected": "Large Transfer",
    }
    for item in results["risk_scores"].values():
        for reason in item["reasons"]:
            if reason in labels:
                counts[labels[reason]] += 1
    dataframe = pd.DataFrame({"Detection Type": list(counts), "Accounts": list(counts.values())})
    return px.bar(
        dataframe,
        x="Detection Type",
        y="Accounts",
        color="Detection Type",
        color_discrete_sequence=["#4c8dff", "#b18cff", "#f5b942", "#f05d5e"],
        template=PLOTLY_TEMPLATE,
        height=300,
    ).update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10), xaxis_title=None)


def graph_figure(graph, risk_scores, cycles):
    """Create a presentation-ready curved-edge Plotly account graph."""
    if graph.number_of_nodes() == 0:
        return None

    positions = nx.spring_layout(graph, seed=42, k=1.6, iterations=100, scale=2.2)
    suspicious = set(risk_scores)
    cycle_accounts = {account for cycle in cycles for account in cycle}
    edge_x, edge_y = [], []
    for source, target in graph.edges:
        start_x, start_y = positions[source]
        end_x, end_y = positions[target]
        mid_x, mid_y = (start_x + end_x) / 2, (start_y + end_y) / 2
        offset_x, offset_y = -(end_y - start_y) * 0.12, (end_x - start_x) * 0.12
        edge_x.extend([start_x, mid_x + offset_x, end_x, None])
        edge_y.extend([start_y, mid_y + offset_y, end_y, None])

    node_x = [positions[node][0] for node in graph.nodes]
    node_y = [positions[node][1] for node in graph.nodes]
    node_colors = [
        RISK_COLORS.get(risk_scores[node]["level"], "#4c8dff") if node in suspicious
        else "#4c8dff"
        for node in graph.nodes
    ]
    node_sizes = [18 + graph.degree(node) * 9 for node in graph.nodes]
    node_lines = ["#f05d5e" if node in cycle_accounts else "#d9e6f5" for node in graph.nodes]

    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(color="#52657f", width=1.6, shape="spline"),
        hoverinfo="none",
        showlegend=False,
    ))
    figure.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(graph.nodes),
        textposition="top center",
        textfont=dict(color="#dce7f4", size=11),
        marker=dict(size=node_sizes, color=node_colors, line=dict(color=node_lines, width=2)),
        customdata=[[graph.degree(node)] for node in graph.nodes],
        hovertemplate="<b>%{text}</b><br>Transfer activity: %{customdata[0]}<extra></extra>",
        showlegend=False,
    ))
    return figure.update_layout(
        template=PLOTLY_TEMPLATE,
        height=570,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="#121d2c",
        plot_bgcolor="#121d2c",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        hovermode="closest",
    )


def render_overview(results):
    section_heading("Executive overview", "Risk posture at a glance", "Rule-based detections and model signals from the current transaction file.")
    chart_columns = st.columns(3)
    with chart_columns[0].container():
        st.plotly_chart(make_risk_distribution(results), use_container_width=True, config={"displayModeBar": False})
    with chart_columns[1].container():
        top_chart = make_top_risk_chart(results)
        if top_chart is None:
            st.info("No data available")
        else:
            st.plotly_chart(top_chart, use_container_width=True, config={"displayModeBar": False})
    with chart_columns[2].container():
        st.plotly_chart(make_detection_chart(results), use_container_width=True, config={"displayModeBar": False})


def render_risk_analysis(results, minimum_score, selected_level, suspicious_only):
    section_heading("Risk analysis", "Account risk register", "Filter the register from the sidebar and sort any column directly in the table.")
    rows = risk_rows(results, minimum_score, selected_level, suspicious_only)
    show_table(rows, ["Account", "Risk Score", "Risk Level", "Flags"], styled=True)


def render_graph_analytics(results):
    section_heading("Graph analytics", "Transaction relationship intelligence", "Node size represents transfer activity. Colored nodes are rule-flagged accounts; red outlines identify cycle participants.")
    statistics = results["graph_statistics"]
    metrics = st.columns(4)
    metrics[0].metric("Graph Nodes", statistics["node_count"])
    metrics[1].metric("Transfer Edges", statistics["edge_count"])
    metrics[2].metric("Circular Cycles", statistics["cycle_count"])
    metrics[3].metric("Suspicious Hubs", len(statistics["suspicious_hubs"]))
    figure = graph_figure(results["graph"], results["risk_scores"], statistics["cycles"])
    if figure is None:
        st.info("No transfer graph available")
    else:
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    top_accounts = statistics["top_connected_accounts"]
    if top_accounts:
        st.dataframe(pd.DataFrame(top_accounts), use_container_width=True, hide_index=True)
    else:
        st.info("No data available")


def render_anomaly_detection(results):
    section_heading("Anomaly detection", "AI-assisted account review", "IsolationForest scores are model signals and complement the explainable rule-based risk score.")
    anomaly_rows = [
        {
            "Account": result["account"],
            "Anomaly Score": result["score"],
            "Classification": result["classification"],
        }
        for result in results["anomaly_results"]
    ]
    show_table(anomaly_rows, ["Account", "Anomaly Score", "Classification"])
    top_anomalies = results["anomaly_results"][:10]
    if top_anomalies:
        dataframe = pd.DataFrame({"Account": [item["account"] for item in top_anomalies], "Anomaly Score": [item["score"] for item in top_anomalies]})
        figure = px.bar(
            dataframe.sort_values("Anomaly Score"),
            x="Anomaly Score",
            y="Account",
            orientation="h",
            color="Anomaly Score",
            color_continuous_scale=[[0, "#27c499"], [0.65, "#f5b942"], [1, "#f05d5e"]],
            template=PLOTLY_TEMPLATE,
            height=360,
        ).update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=10), yaxis_title=None)
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No data available")


def render_reports(results):
    section_heading("Reports", "Compliance review workspace", "Use the tabs to move between executive context and detailed findings.")
    report_text = generate_report(results["risk_scores"], results["total_accounts"])
    overview_tab, findings_tab, graph_tab, ai_tab = st.tabs(["Overview", "AML Findings", "Graph Insights", "AI Findings"])
    with overview_tab:
        st.metric("Accounts Under Review", results["total_accounts"])
        st.metric("Transactions Analyzed", results["total_transactions"])
        st.caption("Generated from the parsed transaction AST and current analysis configuration.")
        st.code(report_text, language="text")
    with findings_tab:
        findings = results["risk_scores"]
        if findings:
            for account, item in sorted(findings.items()):
                with st.expander(account + "  |  " + item["level"] + "  |  " + str(item["score"]) + " points"):
                    for reason in item["reasons"]:
                        st.write("- " + reason)
        else:
            st.info("No data available")
    with graph_tab:
        statistics = results["graph_statistics"]
        st.write("Nodes: " + str(statistics["node_count"]))
        st.write("Edges: " + str(statistics["edge_count"]))
        st.write("Cycles: " + str(statistics["cycle_count"]))
        if statistics["cycles"]:
            for cycle in statistics["cycles"]:
                st.write(" -> ".join(cycle))
        else:
            st.info("No data available")
    with ai_tab:
        if results["anomaly_results"]:
            st.dataframe(pd.DataFrame([
                {"Account": item["account"], "Anomaly Score": item["score"], "Classification": item["classification"]}
                for item in results["anomaly_results"]
            ]), use_container_width=True, hide_index=True)
        else:
            st.info("No data available")


def main():
    st.set_page_config(page_title="AML Intelligence Dashboard", page_icon="shield", layout="wide", initial_sidebar_state="expanded")
    inject_styles()
    try:
        results = load_results()
    except (OSError, ValueError) as error:
        st.error(str(error))
        return

    risk_values = [item["score"] for item in results["risk_scores"].values()]
    average_risk = round(sum(risk_values) / len(risk_values), 1) if risk_values else 0
    st.markdown('<div class="eyebrow">Compliance intelligence / live analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">AI-Based Money Laundering Detection System</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Real-Time Risk Analysis and Transaction Intelligence</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## AML Intelligence")
        st.caption("Enterprise monitoring workspace")
        view = st.radio("Workspace", ["Dashboard", "Risk Analysis", "Graph Analytics", "Anomaly Detection", "Reports"], label_visibility="collapsed")
        st.divider()
        st.markdown("#### Review filters")
        minimum_score = st.slider("Minimum Risk Score", 0, 100, 0, 5)
        selected_level = st.selectbox("Risk Level", ["ALL", "HIGH", "MEDIUM", "LOW"])
        suspicious_only = st.toggle("Suspicious Accounts Only", value=False)
        st.divider()
        st.caption("Source: " + TRANSACTIONS_FILE.name)
        st.caption("Pipeline status: analysis complete")

    kpis = st.columns(5)
    kpis[0].metric("Total Accounts", results["total_accounts"])
    kpis[1].metric("Total Transactions", results["total_transactions"])
    kpis[2].metric("Suspicious Accounts", len(results["risk_scores"]))
    kpis[3].metric("Average Risk Score", average_risk)
    kpis[4].metric("Circular Transfer Cycles", results["graph_statistics"]["cycle_count"])
    st.markdown('<div class="source-note">Rule engine and IsolationForest results are calculated from the existing parsed AST.</div>', unsafe_allow_html=True)
    st.divider()

    if view == "Dashboard":
        render_overview(results)
        st.divider()
        render_risk_analysis(results, minimum_score, selected_level, suspicious_only)
    elif view == "Risk Analysis":
        render_risk_analysis(results, minimum_score, selected_level, suspicious_only)
    elif view == "Graph Analytics":
        render_graph_analytics(results)
    elif view == "Anomaly Detection":
        render_anomaly_detection(results)
    else:
        render_reports(results)


if __name__ == "__main__":
    main()
