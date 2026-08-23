import pandas as pd

from aml_mv_demo.validation import data_quality_summary, reconcile_rule_results


def test_reconciliation_identifies_matching_rule_results():
    primary = pd.DataFrame([{"customer_id": "C1", "rule_id": "R1", "triggered": True, "alert_generated": True, "suppression_applied": False}])
    independent = primary.copy()

    reconciled = reconcile_rule_results(primary, independent)

    assert reconciled.loc[0, "reconciliation_status"] == "matched"


def test_data_quality_summary_detects_referential_breaks():
    customers = pd.DataFrame([{"customer_id": "C1"}])
    accounts = pd.DataFrame([{"account_id": "A1", "customer_id": "C2"}])
    transactions = pd.DataFrame([{"transaction_id": "T1", "account_id": "A2", "amount": 10}])

    summary = data_quality_summary(customers, accounts, transactions)

    assert summary["passed"].tolist().count(False) == 2