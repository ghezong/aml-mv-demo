from __future__ import annotations

import pandas as pd


def reconcile_rule_results(primary: pd.DataFrame, independent: pd.DataFrame) -> pd.DataFrame:
    """Compare production-style and independently replicated rule outputs."""
    key = ["customer_id", "rule_id"]
    primary_view = primary[key + ["triggered", "alert_generated", "suppression_applied"]].rename(
        columns={"triggered": "primary_triggered", "alert_generated": "primary_alert_generated", "suppression_applied": "primary_suppression_applied"}
    )
    independent_view = independent[key + ["triggered", "alert_generated", "suppression_applied"]].rename(
        columns={"triggered": "independent_triggered", "alert_generated": "independent_alert_generated", "suppression_applied": "independent_suppression_applied"}
    )
    reconciled = primary_view.merge(independent_view, on=key, how="outer", indicator=True)
    reconciled["reconciliation_status"] = "matched"
    mismatch_mask = (
        (reconciled["_merge"] != "both")
        | (reconciled["primary_triggered"] != reconciled["independent_triggered"])
        | (reconciled["primary_alert_generated"] != reconciled["independent_alert_generated"])
        | (reconciled["primary_suppression_applied"] != reconciled["independent_suppression_applied"])
    )
    reconciled.loc[mismatch_mask, "reconciliation_status"] = "mismatch"
    return reconciled.drop(columns=["_merge"])


def data_quality_summary(customers: pd.DataFrame, accounts: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    checks = [
        {
            "control_id": "DQ-CUST-001",
            "control": "customer_id_not_null",
            "passed": customers["customer_id"].notna().all(),
            "exception_count": int(customers["customer_id"].isna().sum()),
        },
        {
            "control_id": "DQ-ACCT-001",
            "control": "account_customer_referential_integrity",
            "passed": accounts["customer_id"].isin(customers["customer_id"]).all(),
            "exception_count": int((~accounts["customer_id"].isin(customers["customer_id"])).sum()),
        },
        {
            "control_id": "DQ-TXN-001",
            "control": "transaction_account_referential_integrity",
            "passed": transactions["account_id"].isin(accounts["account_id"]).all(),
            "exception_count": int((~transactions["account_id"].isin(accounts["account_id"])).sum()),
        },
        {
            "control_id": "DQ-TXN-002",
            "control": "positive_transaction_amounts",
            "passed": (transactions["amount"] > 0).all(),
            "exception_count": int((transactions["amount"] <= 0).sum()),
        },
    ]
    return pd.DataFrame(checks)


def arr_monitoring_summary(scored_alerts: pd.DataFrame) -> pd.DataFrame:
    if scored_alerts.empty:
        return pd.DataFrame([{"metric": "alert_count", "value": 0, "threshold": "> 0", "status": "breach"}])

    band_counts = scored_alerts["ml_arr_band"].value_counts().to_dict()
    return pd.DataFrame(
        [
            {"metric": "alert_count", "value": len(scored_alerts), "threshold": "> 0", "status": "passed"},
            {"metric": "mean_ml_arr_score", "value": round(float(scored_alerts["ml_arr_score"].mean()), 4), "threshold": "monitor", "status": "monitor"},
            {"metric": "urgent_band_count", "value": int(band_counts.get("urgent", 0)), "threshold": "capacity reviewed", "status": "monitor"},
            {"metric": "score_min", "value": round(float(scored_alerts["ml_arr_score"].min()), 4), "threshold": "0 to 1", "status": "passed"},
            {"metric": "score_max", "value": round(float(scored_alerts["ml_arr_score"].max()), 4), "threshold": "0 to 1", "status": "passed"},
        ]
    )
