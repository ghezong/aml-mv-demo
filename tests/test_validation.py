import pandas as pd

from aml_mv_demo.validation import config_coverage_summary, data_quality_summary, reconcile_rule_results


def test_reconciliation_identifies_matching_rule_results():
    primary = pd.DataFrame([{"customer_id": "C1", "rule_id": "R1", "triggered": True, "alert_generated": True, "suppression_applied": False, "evidence_count": 2, "evidence_transaction_ids": "T1;T2"}])
    independent = primary.copy()

    reconciled = reconcile_rule_results(primary, independent)

    assert reconciled.loc[0, "reconciliation_status"] == "matched"


def test_reconciliation_detects_evidence_mismatch():
    primary = pd.DataFrame([{"customer_id": "C1", "rule_id": "R1", "triggered": True, "alert_generated": True, "suppression_applied": False, "evidence_count": 2, "evidence_transaction_ids": "T1;T2"}])
    independent = primary.copy()
    independent.loc[0, "evidence_transaction_ids"] = "T1"

    reconciled = reconcile_rule_results(primary, independent)

    assert reconciled.loc[0, "reconciliation_status"] == "mismatch"


def test_data_quality_summary_detects_referential_breaks():
    customers = pd.DataFrame([{"customer_id": "C1"}])
    accounts = pd.DataFrame([{"account_id": "A1", "customer_id": "C2"}])
    transactions = pd.DataFrame([{"transaction_id": "T1", "account_id": "A2", "amount": 10}])

    summary = data_quality_summary(customers, accounts, transactions)

    failed_controls = set(summary.loc[~summary["passed"], "control"])

    assert "required_transaction_columns_present" in failed_controls
    assert "account_customer_referential_integrity" in failed_controls
    assert "transaction_account_referential_integrity" in failed_controls


def test_config_coverage_detects_unexecuted_configured_rules():
    rule_results = pd.DataFrame([{"rule_id": "R1"}])
    rule_config = {"rules": [{"rule_id": "R1", "status": "demo_active"}, {"rule_id": "R2", "status": "demo_active"}]}

    summary = config_coverage_summary(rule_results, rule_config)

    assert summary.loc[summary["rule_id"] == "R2", "status"].iloc[0] == "mismatch"
    assert "result_record_count" in summary.columns