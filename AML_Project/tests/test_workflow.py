from dashboard.workflow import authenticate, can, create_case, load_cases, update_case


def test_demo_roles_and_permissions(tmp_path):
    admin = authenticate("admin.demo", "nfi-admin-demo")
    auditor = authenticate("auditor.demo", "nfi-auditor-demo")
    assert admin["role"] == "System Administrator"
    assert auditor["role"] == "Auditor"
    assert can(admin, "administer_system")
    assert not can(auditor, "manage_cases")
    assert authenticate("admin.demo", "incorrect") is None


def test_case_permissions_and_supervisor_approval(tmp_path):
    cases_path = tmp_path / "cases.json"
    investigator = authenticate("investigator.demo", "nfi-investigator-demo")
    supervisor = authenticate("supervisor.demo", "nfi-supervisor-demo")
    case = create_case(
        cases_path, investigator, ["NFI-0000001"], ["TX-000000001"],
        investigator["username"], "Review planted scenario",
    )
    assert load_cases(cases_path)[0]["status"] == "New"
    update_case(cases_path, investigator, case["case_id"], status="Under Review")
    update_case(cases_path, supervisor, case["case_id"], approval="Approved")
    updated = load_cases(cases_path)[0]
    assert updated["status"] == "Under Review"
    assert updated["approval"] == "Approved"
