"""Readable AML report generation."""


def generate_report(risk_scores, total_accounts=None):
    """Generate the final report from risk score dictionaries."""
    if total_accounts is None:
        total_accounts = len(risk_scores)

    lines = [
        "# =================================",
        "AML ANALYSIS REPORT",
        "Total Accounts: " + str(total_accounts),
        "",
        "Suspicious Accounts: " + str(len(risk_scores)),
    ]
    for entry in sorted(risk_scores.values(), key=lambda item: (-item["score"], item["account"])):
        lines.extend([
            "",
            "---",
            "Account: " + entry["account"],
            "",
            "Risk Score: " + str(entry["score"]),
            "",
            "Risk Level: " + entry["level"],
            "",
            "Reasons:",
        ])
        lines.extend("- " + reason for reason in entry["reasons"])
    lines.append("=================================")
    return "\n".join(lines)