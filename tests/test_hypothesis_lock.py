import json, sys

CONTRACT = "contracts/hypothesis_lock.py"
PREREG_URL = "https://registry.example/studies/reminder-trial"
REPORT_URL = "https://journal.example/reports/reminder-trial"
PREREG = "PREREGISTERED STUDY. HYPOTHESIS: A single reminder increases completed applications. PRIMARY_OUTCOME: proportion of complete applications submitted within 7 days. POPULATION: first-time adult applicants enrolled from 1 January through 31 March 2026. EXCLUSIONS: duplicate accounts and unreachable email addresses. ANALYSIS_WINDOW: outcomes measured for 7 days after enrollment. This is the complete frozen protocol."
REPORT_CHANGED = "FINAL STUDY REPORT. HYPOTHESIS: A single reminder increases completed applications. PRIMARY_OUTCOME: proportion of applications started within 14 days. POPULATION: first-time adult applicants enrolled from 1 January through 31 March 2026. EXCLUSIONS: duplicate accounts and unreachable email addresses. ANALYSIS_WINDOW: outcomes measured for 7 days after enrollment. No protocol deviations are described in this report."
REPORT_ALIGNED = "FINAL STUDY REPORT. HYPOTHESIS: A single reminder increases completed applications. PRIMARY_OUTCOME: proportion of complete applications submitted within 7 days. POPULATION: first-time adult applicants enrolled from 1 January through 31 March 2026. EXCLUSIONS: duplicate accounts and unreachable email addresses. ANALYSIS_WINDOW: outcomes measured for 7 days after enrollment. The report follows the frozen protocol."
DIMENSIONS = ["HYPOTHESIS", "PRIMARY_OUTCOME", "POPULATION", "EXCLUSIONS", "ANALYSIS_WINDOW"]


def enable_consensus(contract, monkeypatch):
    module = sys.modules[contract.__class__.__module__]
    monkeypatch.setattr(module.gl.eq_principle, "strict_eq", lambda fn: fn())
    monkeypatch.setattr(module.gl.eq_principle, "prompt_comparative", lambda fn, *_args, **_kwargs: fn())


def matrix(states=None):
    values = states or ["MATCH"] * 5
    return {"dimensions": [{"dimension": dimension, "state": values[index]} for index, dimension in enumerate(DIMENSIONS)]}


def mock_llm(vm, value):
    vm.mock_llm("HYPOTHESISLOCK_PRODUCER", json.dumps(json.dumps(value)))


def create(contract):
    return contract.create_study("reminder-trial", "Application reminder trial", "Does one reminder increase the proportion of first-time applicants who submit a complete application?", PREREG_URL)


def prepare(contract, vm, monkeypatch, report=REPORT_CHANGED, notice="NONE"):
    enable_consensus(contract, monkeypatch)
    study_id = create(contract)
    vm.mock_web(PREREG_URL, {"method": "GET", "status": 200, "body": PREREG})
    contract.freeze_preregistration(study_id)
    vm.clear_mocks()
    contract.submit_report(study_id, REPORT_URL, notice)
    vm.mock_web(REPORT_URL, {"method": "GET", "status": 200, "body": report})
    contract.freeze_report(study_id)
    vm.clear_mocks()
    return study_id


def test_contract_loads(direct_deploy):
    assert direct_deploy(CONTRACT) is not None


def test_preregistration_must_be_complete_and_immutable(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    enable_consensus(contract, monkeypatch)
    study_id = create(contract)
    direct_vm.mock_web(PREREG_URL, {"method": "GET", "status": 200, "body": "too short"})
    with direct_vm.expect_revert("unavailable or incomplete"):
        contract.freeze_preregistration(study_id)
    direct_vm.clear_mocks()
    direct_vm.mock_web(PREREG_URL, {"method": "GET", "status": 200, "body": PREREG})
    frozen = contract.freeze_preregistration(study_id)
    state = contract.get_study(study_id)
    assert frozen["status"] == "PREREG_FROZEN" and len(frozen["prereg_digest"]) == 64
    assert state["prereg_snapshot"]["content"] == PREREG
    with direct_vm.expect_revert("unavailable"):
        contract.freeze_preregistration(study_id)


def test_report_requires_owner_frozen_prereg_and_distinct_url(direct_vm, direct_deploy, direct_alice, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = create(contract)
    with direct_vm.expect_revert("frozen preregistration"):
        contract.submit_report(study_id, REPORT_URL, "NONE")
    enable_consensus(contract, monkeypatch)
    direct_vm.mock_web(PREREG_URL, {"method": "GET", "status": 200, "body": PREREG})
    contract.freeze_preregistration(study_id)
    direct_vm.clear_mocks()
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the study owner"):
        contract.submit_report(study_id, REPORT_URL, "NONE")
    owner = contract.get_study(study_id)["owner"]
    direct_vm.sender = bytes.fromhex(owner[2:])
    with direct_vm.expect_revert("distinct document URL"):
        contract.submit_report(study_id, PREREG_URL, "NONE")


def test_matrix_is_complete_ordered_and_bounded(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = prepare(contract, direct_vm, monkeypatch)
    missing = matrix(); missing["dimensions"].pop(); mock_llm(direct_vm, missing)
    with direct_vm.expect_revert("Every preregistration dimension"):
        contract.evaluate_report(study_id)
    direct_vm.clear_mocks()
    wrong = matrix(); wrong["dimensions"][0]["dimension"] = "PRIMARY_OUTCOME"; mock_llm(direct_vm, wrong)
    with direct_vm.expect_revert("out of order"):
        contract.evaluate_report(study_id)
    direct_vm.clear_mocks()
    invalid = matrix(); invalid["dimensions"][0]["state"] = "MAYBE"; mock_llm(direct_vm, invalid)
    with direct_vm.expect_revert("Invalid deviation state"):
        contract.evaluate_report(study_id)


def test_undisclosed_outcome_switch_blocks_trust(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = prepare(contract, direct_vm, monkeypatch)
    mock_llm(direct_vm, matrix(["MATCH", "UNDISCLOSED_CHANGE", "MATCH", "MATCH", "MATCH"]))
    result = contract.evaluate_report(study_id)
    gate = contract.get_trust_gate(study_id)
    assert result["outcome"] == "SELECTIVE_REPORTING"
    assert gate["status"] == "SELECTIVE_REPORTING" and gate["trust_gate"] == "BLOCKED"
    assert len(result["receipts"]) == 2


def test_aligned_report_becomes_trusted_and_terminal(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = prepare(contract, direct_vm, monkeypatch, REPORT_ALIGNED)
    mock_llm(direct_vm, matrix())
    result = contract.evaluate_report(study_id)
    assert result["outcome"] == "ALIGNED"
    assert contract.get_trust_gate(study_id)["trust_gate"] == "TRUSTED"
    with direct_vm.expect_revert("complete frozen report"):
        contract.evaluate_report(study_id)


def test_disclosed_change_is_qualified_not_blocked(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = prepare(contract, direct_vm, monkeypatch, notice="PRIMARY_OUTCOME changed from completed within 7 days to started within 14 days because the form service was unavailable.")
    mock_llm(direct_vm, matrix(["MATCH", "DISCLOSED_CHANGE", "MATCH", "MATCH", "MATCH"]))
    assert contract.evaluate_report(study_id)["outcome"] == "DISCLOSED_DEVIATION"
    assert contract.get_trust_gate(study_id)["trust_gate"] == "QUALIFIED"


def test_unverifiable_dimension_stays_blocked(direct_vm, direct_deploy, monkeypatch):
    contract = direct_deploy(CONTRACT)
    study_id = prepare(contract, direct_vm, monkeypatch)
    mock_llm(direct_vm, matrix(["MATCH", "MATCH", "MATCH", "UNVERIFIABLE", "MATCH"]))
    assert contract.evaluate_report(study_id)["outcome"] == "INCONCLUSIVE"
    assert contract.get_trust_gate(study_id)["trust_gate"] == "BLOCKED"

