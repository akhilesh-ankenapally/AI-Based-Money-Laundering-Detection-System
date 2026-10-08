"""Abstract Syntax Tree nodes for the transaction language."""


class ProgramNode:
    """Root node containing all statements in the input program."""

    def __init__(self, statements):
        self.statements = statements

    def to_lines(self):
        """Return the program as lines suitable for readable tree output."""
        lines = ["PROGRAM"]
        for index, statement in enumerate(self.statements):
            is_last = index == len(self.statements) - 1
            branch = "`-- " if is_last else "|-- "
            child_lines = statement.to_lines()
            lines.append(branch + child_lines[0])

            continuation = "    " if is_last else "|   "
            lines.extend(continuation + line for line in child_lines[1:])
        return lines

    def __str__(self):
        return "\n".join(self.to_lines())


class DepositNode:
    """AST node representing a deposit transaction."""

    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

    def to_lines(self):
        return [
            "DEPOSIT",
            "|-- account: " + self.account_id,
            "`-- amount: " + str(self.amount),
        ]


class WithdrawNode:
    """AST node representing a withdrawal transaction."""

    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

    def to_lines(self):
        return [
            "WITHDRAW",
            "|-- account: " + self.account_id,
            "`-- amount: " + str(self.amount),
        ]


class TransferNode:
    """AST node representing a transfer between two accounts."""

    def __init__(self, source_account, destination_account, amount):
        self.source_account = source_account
        self.destination_account = destination_account
        self.amount = amount

    def to_lines(self):
        return [
            "TRANSFER",
            "|-- source: " + self.source_account,
            "|-- destination: " + self.destination_account,
            "`-- amount: " + str(self.amount),
        ]
