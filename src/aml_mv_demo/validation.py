from __future__ import annotations

import pandas as pd

from aml_mv_demo.config import active_rule_ids
from aml_mv_demo.features import normalize_transactions


def reconcile_rule_results(primary: pd.DataFrame, independent: pd.DataFrame) -> pd.DataFrame:
    """Compare production-style and independently replicated rule outputs."""
    key = ["customer_id", "rule_id"]
    fields = ["triggered", "alert_generated", "suppression_applied", "evidence_count", "evidence_transaction_ids"]
    primary = _ensure_columns(primary, key + fields)
    independent = _ensure_columns(independent, key + fields)
    primary_view = primary[key + fields].rename(
        columns={
            "triggered": "primary_triggered",
            "alert_generated": "primary_alert_generated",
            "suppression_applied": "primary_suppression_applied",
            "evidence_count": "primary_evidence_count",
            "evidence_transaction_ids": "primary_evidence_transaction_ids",
        }
    )
    independent_view = independent[key + fields].rename(
        columns={
            "triggered": "independent_triggered",
            "alert_generated": "independent_alert_generated",
            "suppression_applied": "independent_suppression_applied",
            "evidence_count": "independent_evidence_count",
            "evidence_transaction_ids": "independent_evidence_transaction_ids",
        }
    )
    reconciled = primary_view.merge(independent_view, on=key, how="outer", indicator=True)
    reconciled["reconciliation_status"] = "matched"
    mismatch_mask = (
        (reconciled["_merge"] != "both")
        | (reconciled["primary_triggered"] != reconciled["independent_triggered"])
        | (reconciled["primary_alert_generated"] != reconciled["independent_alert_generated"])
        | (reconciled["primary_suppression_applied"] != reconciled["independent_suppression_applied"])
        | (reconciled["primary_evidence_count"] != reconciled["independent_evidence_count"])
        | (reconciled["primary_evidence_transaction_ids"].fillna("") != reconciled["independent_evidence_transaction_ids"].fillna(""))
    )
    reconciled.loc[mismatch_mask, "reconciliation_status"] = "mismatch"
    return reconciled.drop(columns=["_merge"])


def data_quality_summary(customers: pd.DataFrame, accounts: pd.DataFrame, transactions: pd.DataFrame, risk_indicator_config: dict | None = None) -> pd.DataFrame:
    required_transaction_columns = {"transaction_id", "account_id", "timestamp_utc", "amount", "currency", "status", "counterparty_country", "counterparty_id"}
    missing_transaction_columns = required_transaction_columns - set(transactions.columns)
    if missing_transaction_columns:
        transactions_for_normalization = transactions.copy()
        for column in missing_transaction_columns:
            transactions_for_normalization[column] = pd.NA
        normalized = transactions_for_normalization.copy()
        normalized["timestamp_utc"] = pd.to_datetime(normalized["timestamp_utc"], utc=True, errors="coerce")
        normalized["unknown_currency"] = True
    else:
        transactions_for_normalization = transactions.copy()
        normalized = normalize_transactions(transactions, risk_indicator_config=risk_indicator_config)
    valid_statuses = set(risk_indicator_config["monetary_statuses"] + ["pending", "failed"]) if risk_indicator_config else set(transactions_for_normalization["status"].dropna().unique())
    checks = [
        {
            "control_id": "DQ-SCHEMA-001",
            "control": "required_transaction_columns_present",
            "passed": not missing_transaction_columns,
            "exception_count": len(missing_transaction_columns),
        },
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
        {
            "control_id": "DQ-TXN-003",
            "control": "transaction_id_unique",
            "passed": transactions["transaction_id"].is_unique,
            "exception_count": int(transactions["transaction_id"].duplicated().sum()),
        },
        {
            "control_id": "DQ-TXN-004",
            "control": "timestamp_parseable",
            "passed": normalized["timestamp_utc"].notna().all(),
            "exception_count": int(normalized["timestamp_utc"].isna().sum()),
        },
        {
            "control_id": "DQ-TXN-005",
            "control": "status_valid",
            "passed": transactions_for_normalization["status"].notna().all() and transactions_for_normalization["status"].isin(valid_statuses).all(),
            "exception_count": int(transactions_for_normalization["status"].isna().sum() + (~transactions_for_normalization["status"].dropna().isin(valid_statuses)).sum()),
        },
        {
            "control_id": "DQ-TXN-006",
            "control": "known_currency",
            "passed": (~normalized["unknown_currency"]).all(),
            "exception_count": int(normalized["unknown_currency"].sum()),
        },
        {
            "control_id": "DQ-TXN-007",
            "control": "counterparty_present",
            "passed": transactions_for_normalization["counterparty_id"].notna().all(),
            "exception_count": int(transactions_for_normalization["counterparty_id"].isna().sum()),
        },
    ]
    return pd.DataFrame(checks)


def _ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = "" if column == "evidence_transaction_ids" else 0
    return output


def exclusion_summary(transactions: pd.DataFrame, as_of_timestamp: str | pd.Timestamp, risk_indicator_config: dict) -> pd.DataFrame:
    normalized = normalize_transactions(transactions, risk_indicator_config=risk_indicator_config)
    as_of = pd.Timestamp(as_of_timestamp)
    if as_of.tzinfo is None:
        as_of = as_of.tz_localize("UTC")
    else:
        as_of = as_of.tz_convert("UTC")
    eligible_statuses = set(risk_indicator_config["rule_eligible_statuses"])
    normalized["exclusion_reason"] = "included_rule_population"
    normalized.loc[normalized["timestamp_utc"] > as_of, "exclusion_reason"] = "after_as_of_timestamp"
    normalized.loc[(normalized["timestamp_utc"] <= as_of) & (~normalized["status"].isin(eligible_statuses)), "exclusion_reason"] = "non_rule_eligible_status"
    normalized.loc[normalized["unknown_currency"], "exclusion_reason"] = "unknown_currency"
    return normalized.groupby(["exclusion_reason", "status"], dropna=False).size().reset_index(name="transaction_count")


def config_coverage_summary(rule_results: pd.DataFrame, rule_config: dict, implemented_rule_ids: set[str] | None = None) -> pd.DataFrame:
    configured = active_rule_ids(rule_config)
    implemented = implemented_rule_ids or set(rule_results["rule_id"].unique())
    result_rule_counts = rule_results["rule_id"].value_counts().to_dict() if "rule_id" in rule_results else {}
    rows = []
    for rule_id in sorted(configured | implemented | set(result_rule_counts)):
        rows.append(
            {
                "rule_id": rule_id,
                "configured": rule_id in configured,
                "implemented": rule_id in implemented,
                "result_record_count": int(result_rule_counts.get(rule_id, 0)),
                "status": "matched" if rule_id in configured and rule_id in implemented else "mismatch",
            }
        )
    return pd.DataFrame(rows)


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
