"""Simple high-frequency analysis over the ordered AST statements."""

from compiler.ast_nodes import DepositNode, TransferNode, WithdrawNode


def _accounts_for(statement):
    if isinstance(statement, TransferNode):
        return {statement.source_account, statement.destination_account}
    if isinstance(statement, (DepositNode, WithdrawNode)):
        return {statement.account_id}
    return set()


def detect_high_frequency(program, window_minutes=5, minimum_transaction_count=4,
                          transaction_interval_minutes=1):
    """Find accounts involved in many ordered statements within a short window.

    The existing parser does not produce timestamps. Therefore statement order is
    used as time, with each statement representing the configured interval.
    """
    events_by_account = {}
    for index, statement in enumerate(program.statements):
        event_time = index * transaction_interval_minutes
        for account in _accounts_for(statement):
            events_by_account.setdefault(account, []).append((event_time, statement))

    findings = []
    for account, events in events_by_account.items():
        for start_index, (start_time, _) in enumerate(events):
            matching = [
                event for event in events[start_index:]
                if event[0] - start_time <= window_minutes
            ]
            if len(matching) >= minimum_transaction_count:
                findings.append({
                    "account": account,
                    "count": len(matching),
                    "window_minutes": window_minutes,
                    "start_minute": start_time,
                    "end_minute": matching[-1][0],
                    "reason": (
                        str(len(matching)) + " transactions in "
                        + str(window_minutes) + " minutes."
                    ),
                })
                break
    return findings