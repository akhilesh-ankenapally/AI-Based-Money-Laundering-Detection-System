"""Lightweight account anomaly detection using IsolationForest."""

from collections import defaultdict

from sklearn.ensemble import IsolationForest

from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode


def _account_features(program, graph):
    """Create one numeric feature row for every account in the AST."""
    amounts = defaultdict(list)
    frequencies = defaultdict(int)
    accounts = set(graph.nodes)

    for statement in program.statements:
        if isinstance(statement, TransferNode):
            involved = {statement.source_account, statement.destination_account}
        elif isinstance(statement, (DepositNode, WithdrawNode)):
            involved = {statement.account_id}
        else:
            involved = set()
        accounts.update(involved)
        for account in involved:
            amounts[account].append(statement.amount)
            frequencies[account] += 1

    features = []
    for account in sorted(accounts):
        features.append({
            "account": account,
            "amount": sum(amounts[account]) / len(amounts[account]) if amounts[account] else 0,
            "transaction_frequency": frequencies[account],
            "in_degree": int(graph.in_degree(account)) if account in graph else 0,
            "out_degree": int(graph.out_degree(account)) if account in graph else 0,
        })
    return features


def detect_anomalies(program, graph, contamination="auto"):
    """Return IsolationForest scores and NORMAL/SUSPICIOUS classifications."""
    features = _account_features(program, graph)
    if not features:
        return []

    values = [
        [
            row["amount"],
            row["transaction_frequency"],
            row["in_degree"],
            row["out_degree"],
        ]
        for row in features
    ]
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    labels = model.fit_predict(values)
    raw_scores = model.decision_function(values)

    results = []
    for row, label, raw_score in zip(features, labels, raw_scores):
        anomaly_score = round(max(0.0, min(100.0, 50.0 - (raw_score * 100.0))), 2)
        results.append({
            "account": row["account"],
            "score": anomaly_score,
            "classification": "SUSPICIOUS" if label == -1 else "NORMAL",
            "features": row,
        })
    return sorted(results, key=lambda item: (-item["score"], item["account"]))