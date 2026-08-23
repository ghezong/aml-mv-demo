from __future__ import annotations

import hashlib

import pandas as pd

from aml_mv_demo.features import normalize_transactions


RULE_VERSION = "TM-RULES-2.0"
SUPPRESSION_VERSION = "SUP-LOW-RISK-1.0"


def evaluate_rules(customers: pd.DataFrame, transactions: pd.DataFrame, behavioral_crr: pd.DataFrame, as_of_timestamp: str | pd.Timestamp | None = None) -> pd.DataFrame:
    """Evaluate deterministic AML rules and retain triggered and suppressed results."""
    txns = normalize_transactions(transactions)
    if as_of_timestamp is None:
        as_of = txns["timestamp_utc"].max()
    else:
        as_of = pd.Timestamp(as_of_timestamp)
        if as_of.tzinfo is None:
            as_of = as_of.tz_localize("UTC")
        else:
            as_of = as_of.tz_convert("UTC")

    eligible_txns = txns[(txns["status"] == "settled") & (txns["timestamp_utc"] <= as_of)].copy()
    customer_context = customers.merge(behavioral_crr, on="customer_id", how="left")

    results = []
    results.extend(_structuring_rule(eligible_txns, customer_context, as_of))
    results.extend(_high_velocity_rule(eligible_txns, customer_context, as_of))
    results.extend(_high_risk_geo_rule(eligible_txns, customer_context, as_of))
    results.extend(_rapid_movement_rule(eligible_txns, customer_context, as_of))
    results.extend(_flow_through_rule(eligible_txns, customer_context, as_of))
    results.extend(_network_hub_rule(eligible_txns, customer_context, as_of))
    return pd.DataFrame(results)


def consolidate_alerts(rule_results: pd.DataFrame) -> pd.DataFrame:
    triggered = rule_results[rule_results["alert_generated"]].copy()
    if triggered.empty:
        return pd.DataFrame(columns=["alert_id", "customer_id", "typology_family", "observation_end", "rule_ids", "max_rule_severity", "evidence_count", "rule_result_ids"])

    grouped = triggered.groupby(["customer_id", "typology_family", "observation_end"]).agg(
        rule_ids=("rule_id", lambda values: ";".join(sorted(set(values)))),
        max_rule_severity=("rule_severity", "max"),
        evidence_count=("evidence_count", "sum"),
        rule_result_ids=("rule_result_id", lambda values: ";".join(values)),
        evidence_transaction_ids=("evidence_transaction_ids", lambda values: ";".join(sorted(set(";".join(values).split(";"))))),
    ).reset_index()
    grouped.insert(0, "alert_id", grouped.apply(lambda row: _stable_id("ALERT", row["customer_id"], row["typology_family"], row["observation_end"], row["rule_ids"]), axis=1))
    grouped["alert_version"] = "ALERT-CONSOLIDATION-1.0"
    return grouped


def _structuring_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 7)
    near_threshold = window_txns[(window_txns["amount_usd_gross"] >= 9_000) & (window_txns["amount_usd_gross"] < 10_000) & (window_txns["currency"] == "USD")]
    counts = _aggregate_evidence(near_threshold)
    return [_result(row, "TM-STRUCT-001", "threshold_avoidance", "Potential threshold avoidance", 4, row["evidence_count"] >= 2, customers, as_of, 7) for row in counts.to_dict("records")]


def _high_velocity_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 1)
    counts = _aggregate_evidence(window_txns)
    return [_result(row, "TM-VEL-001", "velocity", "Unusual 24-hour transaction velocity", 3, row["evidence_count"] >= 8, customers, as_of, 1) for row in counts.to_dict("records")]


def _high_risk_geo_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 30)
    high_risk_geo = window_txns[window_txns["counterparty_country"].isin(["BR", "MX", "PA"])]
    counts = _aggregate_evidence(high_risk_geo)
    return [_result(row, "TM-GEO-001", "high_risk_geography", "Higher-risk geography exposure", 3, row["evidence_count"] >= 4, customers, as_of, 30) for row in counts.to_dict("records")]


def _rapid_movement_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 3)
    rows = []
    for customer_id, group in window_txns.groupby("customer_id"):
        inbound_amount = group.loc[group["direction"] == "inbound", "amount_usd_gross"].sum()
        outbound_amount = group.loc[group["direction"] == "outbound", "amount_usd_gross"].sum()
        if inbound_amount == 0:
            continue
        evidence_ids = group["transaction_id"].astype(str).tolist()
        rows.append(
            {
                "customer_id": customer_id,
                "evidence_count": len(evidence_ids),
                "total_amount": outbound_amount,
                "evidence_transaction_ids": ";".join(evidence_ids),
                "threshold": "outbound/inbound>=0.80 and inbound>=5000",
                "triggered": outbound_amount / inbound_amount >= 0.80 and inbound_amount >= 5_000,
            }
        )
    return [_result(row, "TM-RAPID-001", "rapid_movement", "Rapid movement of funds", 5, row["triggered"], customers, as_of, 3) for row in rows]


def _flow_through_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 30)
    rows = []
    for customer_id, group in window_txns.groupby("customer_id"):
        inbound_amount = group.loc[group["direction"] == "inbound", "amount_usd_gross"].sum()
        outbound_amount = group.loc[group["direction"] == "outbound", "amount_usd_gross"].sum()
        unique_counterparties = group["counterparty_id"].nunique()
        evidence_ids = group["transaction_id"].astype(str).tolist()
        rows.append(
            {
                "customer_id": customer_id,
                "evidence_count": len(evidence_ids),
                "total_amount": inbound_amount + outbound_amount,
                "evidence_transaction_ids": ";".join(evidence_ids),
                "threshold": "inbound>=10000 and outbound/inbound>=0.75 and counterparties>=8",
                "triggered": inbound_amount >= 10_000 and inbound_amount > 0 and outbound_amount / inbound_amount >= 0.75 and unique_counterparties >= 8,
            }
        )
    return [_result(row, "TM-FLOW-001", "pass_through", "Potential pass-through or account cycling", 4, row["triggered"], customers, as_of, 30) for row in rows]


def _network_hub_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp) -> list[dict]:
    window_txns = _window(txns, as_of, 30)
    counterparty_customer_counts = window_txns.groupby("counterparty_id")["customer_id"].nunique().rename("linked_customer_count")
    hub_counterparties = set(counterparty_customer_counts[counterparty_customer_counts >= 4].index)
    hub_txns = window_txns[window_txns["counterparty_id"].isin(hub_counterparties)]
    counts = _aggregate_evidence(hub_txns)
    return [_result(row, "TM-NET-001", "network", "Shared high-risk counterparty hub", 4, row["evidence_count"] >= 2, customers, as_of, 30) for row in counts.to_dict("records")]


def _window(txns: pd.DataFrame, as_of: pd.Timestamp, days: int) -> pd.DataFrame:
    return txns[(txns["timestamp_utc"] > as_of - pd.Timedelta(days=days)) & (txns["timestamp_utc"] <= as_of)].copy()


def _aggregate_evidence(txns: pd.DataFrame) -> pd.DataFrame:
    if txns.empty:
        return pd.DataFrame(columns=["customer_id", "evidence_count", "total_amount", "evidence_transaction_ids", "threshold"])
    return txns.groupby("customer_id").agg(
        evidence_count=("transaction_id", "count"),
        total_amount=("amount_usd_gross", "sum"),
        evidence_transaction_ids=("transaction_id", lambda values: ";".join(values.astype(str))),
    ).reset_index()


def _result(row: dict, rule_id: str, typology_family: str, reason: str, severity: int, triggered: bool, customers: pd.DataFrame, as_of: pd.Timestamp, window_days: int) -> dict:
    customer_row = customers[customers["customer_id"] == row["customer_id"]].iloc[0]
    suppression_applied = bool(triggered and customer_row["behavioral_crr_tier"] == "low" and severity <= 3 and row["evidence_count"] < 5)
    observation_start = as_of - pd.Timedelta(days=window_days)
    return {
        "rule_result_id": _stable_id("RR", rule_id, row["customer_id"], as_of.date().isoformat()),
        "customer_id": row["customer_id"],
        "rule_id": rule_id,
        "rule_version": RULE_VERSION,
        "feature_version": "AML-FEATURES-2.0",
        "typology_family": typology_family,
        "segment_id": customer_row.get("segment_id", "unassigned"),
        "observation_start": observation_start.isoformat(),
        "observation_end": as_of.isoformat(),
        "rule_reason": reason,
        "rule_severity": severity,
        "customer_eligible": True,
        "transaction_eligible": True,
        "triggered": bool(triggered),
        "raw_trigger_retained": bool(triggered),
        "suppression_applied": suppression_applied,
        "suppression_policy_id": SUPPRESSION_VERSION if suppression_applied else "",
        "alert_generated": bool(triggered and not suppression_applied),
        "suppression_reason": "low_risk_low_evidence" if suppression_applied else "",
        "evidence_count": int(row["evidence_count"]),
        "evidence_amount": round(float(row["total_amount"]), 2),
        "evidence_transaction_ids": row.get("evidence_transaction_ids", ""),
        "threshold": row.get("threshold", "configured_threshold"),
        "data_quality_status": "passed",
    }


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{digest}"
