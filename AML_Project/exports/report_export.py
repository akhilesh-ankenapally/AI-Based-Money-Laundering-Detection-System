"""Export AML, anomaly, and graph results to TXT and CSV files."""

import csv
from pathlib import Path


def export_txt_report(path, report_text, graph_statistics, anomaly_results):
    """Write the readable report with graph and anomaly sections."""
    path = Path(path)
    lines = [
        report_text,
        "",
        "GRAPH STATISTICS",
        "Nodes: " + str(graph_statistics["node_count"]),
        "Edges: " + str(graph_statistics["edge_count"]),
        "Cycles: " + str(graph_statistics["cycle_count"]),
        "Suspicious hubs: " + ", ".join(graph_statistics["suspicious_hubs"]),
        "",
        "AI ANOMALY RESULTS",
    ]
    lines.extend(
        result["account"] + ": " + str(result["score"])
        + " (" + result["classification"] + ")"
        for result in anomaly_results
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_csv_report(path, risk_scores, anomaly_results, graph_statistics):
    """Write account results and one graph summary row to CSV."""
    path = Path(path)
    anomaly_by_account = {item["account"]: item for item in anomaly_results}
    fieldnames = [
        "record_type", "account", "risk_score", "risk_level", "reasons",
        "anomaly_score", "classification", "nodes", "edges", "cycles",
        "top_connected_accounts",
    ]
    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for account, risk in sorted(risk_scores.items()):
            anomaly = anomaly_by_account.get(account, {})
            writer.writerow({
                "record_type": "account",
                "account": account,
                "risk_score": risk["score"],
                "risk_level": risk["level"],
                "reasons": "; ".join(risk["reasons"]),
                "anomaly_score": anomaly.get("score", ""),
                "classification": anomaly.get("classification", ""),
            })
        writer.writerow({
            "record_type": "graph_summary",
            "nodes": graph_statistics["node_count"],
            "edges": graph_statistics["edge_count"],
            "cycles": graph_statistics["cycle_count"],
            "top_connected_accounts": "; ".join(
                item["account"] for item in graph_statistics["top_connected_accounts"]
            ),
        })
    return path


def export_reports(output_directory, report_text, risk_scores, anomaly_results,
                   graph_statistics):
    """Create the requested aml_report.txt and aml_report.csv files."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    txt_path = export_txt_report(
        output_directory / "aml_report.txt",
        report_text,
        graph_statistics,
        anomaly_results,
    )
    csv_path = export_csv_report(
        output_directory / "aml_report.csv",
        risk_scores,
        anomaly_results,
        graph_statistics,
    )
    return {"txt": txt_path, "csv": csv_path}