"""Local academic-demo authentication, permissions, cases, and audit records."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


DISCLAIMER = (
    "SIMULATED GOVERNMENT SYSTEM — ACADEMIC PROJECT. "
    "Not affiliated with or endorsed by any government agency."
)
ORGANIZATION = "National Financial Intelligence & Anti-Money Laundering Directorate (NFI-AMD)"
PLATFORM = "Financial Intelligence & Transaction Monitoring System (FITMS)"
TAGLINE = "Detect. Investigate. Protect."

ROLES = (
    "System Administrator",
    "Financial Intelligence Officer",
    "Investigation Officer",
    "Supervisory Officer",
    "Auditor",
)
PERMISSIONS = {
    "System Administrator": {
        "view_dashboard", "review_alerts", "investigate_accounts", "network",
        "reports", "manage_cases", "review_cases", "approve_reports",
        "administer_system", "audit",
    },
    "Financial Intelligence Officer": {
        "view_dashboard", "review_alerts", "investigate_accounts", "network", "reports",
    },
    "Investigation Officer": {
        "view_dashboard", "review_alerts", "investigate_accounts", "network",
        "reports", "manage_cases",
    },
    "Supervisory Officer": {
        "view_dashboard", "review_alerts", "review_cases", "approve_reports", "reports",
    },
    "Auditor": {"view_dashboard", "reports", "audit"},
}

# These are deliberately documented demonstration accounts, not production credentials.
DEMO_USERS = {
    "admin.demo": ("System Administrator", "nfi-admin-demo"),
    "intelligence.demo": ("Financial Intelligence Officer", "nfi-intel-demo"),
    "investigator.demo": ("Investigation Officer", "nfi-investigator-demo"),
    "supervisor.demo": ("Supervisory Officer", "nfi-supervisor-demo"),
    "auditor.demo": ("Auditor", "nfi-auditor-demo"),
}


def _password_digest(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 240000
    )


_PASSWORD_RECORDS = {
    username: (role, salt, _password_digest(password, salt))
    for username, (role, password), salt in (
        (username, details, ("FITMS-" + username).encode("utf-8"))
        for username, details in DEMO_USERS.items()
    )
}


def authenticate(username, password):
    """Return a session-safe identity after constant-time password verification."""
    record = _PASSWORD_RECORDS.get(username.strip().lower())
    if record is None:
        return None
    role, salt, expected = record
    if not hmac.compare_digest(_password_digest(password, salt), expected):
        return None
    return {"username": username.strip().lower(), "role": role}


def can(identity, permission):
    return bool(identity and permission in PERMISSIONS.get(identity["role"], set()))


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Unable to read local workflow store: " + str(error)) from error


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def append_audit(path, identity, action, details=""):
    entries = _read_json(path, [])
    entries.append({
        "timestamp": now_utc(),
        "username": identity.get("username", "system") if identity else "system",
        "role": identity.get("role", "system") if identity else "system",
        "action": action,
        "details": details,
    })
    _write_json(path, entries[-2000:])


def create_case(path, identity, account_ids, transaction_ids, assigned_officer, notes):
    if not can(identity, "manage_cases"):
        raise PermissionError("This role cannot create or update investigation cases.")
    cases = _read_json(path, [])
    case_id = "CASE-" + str(len(cases) + 1).zfill(5)
    timestamp = now_utc()
    case = {
        "case_id": case_id,
        "related_accounts": sorted(set(account_ids)),
        "transaction_ids": sorted(set(transaction_ids)),
        "assigned_officer": assigned_officer,
        "notes": notes,
        "status": "New",
        "created_at": timestamp,
        "updated_at": timestamp,
        "approval": "",
    }
    cases.append(case)
    _write_json(path, cases)
    return case


def update_case(path, identity, case_id, status=None, notes=None, approval=None):
    if status is not None and not can(identity, "manage_cases"):
        raise PermissionError("This role cannot update case status.")
    if approval is not None and not can(identity, "approve_reports"):
        raise PermissionError("This role cannot approve or reject reports.")
    cases = _read_json(path, [])
    for case in cases:
        if case["case_id"] == case_id:
            if status is not None:
                case["status"] = status
            if notes is not None:
                case["notes"] = notes
            if approval is not None:
                case["approval"] = approval
            case["updated_at"] = now_utc()
            _write_json(path, cases)
            return case
    raise ValueError("Case not found: " + case_id)


def load_cases(path):
    return _read_json(path, [])


def load_audit(path):
    return _read_json(path, [])
