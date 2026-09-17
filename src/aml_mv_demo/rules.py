from __future__ import annotations

import hashlib

import pandas as pd

from aml_mv_demo.config import active_rule_ids, load_risk_indicator_config, load_rule_config, load_suppression_config, rule_by_id
from aml_mv_demo.features import normalize_transactions


RULE_VERSION = "TM-RULES-2.1"
IMPLEMENTED_RULE_IDS = {"TM-STRUCT-001", "TM-VEL-001", "TM-GEO-001", "TM-RAPID-001", "TM-FLOW-001", "TM-NET-001"}


def evaluate_rules(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    behavioral_crr: pd.DataFrame,
    as_of_timestamp: str | pd.Timestamp | None = None,
    rule_config: dict | None = None,
    suppression_config: dict | None = None,
    risk_indicator_config: dict | None = None,
) -> pd.DataFrame:
    """Evaluate deterministic AML rules and retain triggered and suppressed results."""
    rule_config = rule_config or load_rule_config()
    suppression_config = suppression_config or load_suppression_config()
    risk_indicator_config = risk_indicator_config or load_risk_indicator_config()
    txns = normalize_transactions(transactions, risk_indicator_config=risk_indicator_config)
    if as_of_timestamp is None:
        as_of = txns["timestamp_utc"].max()
    else:
        as_of = pd.Timestamp(as_of_timestamp)
        if as_of.tzinfo is None:
            as_of = as_of.tz_localize("UTC")
        else:
            as_of = as_of.tz_convert("UTC")

    eligible_statuses = set(risk_indicator_config["rule_eligible_statuses"])
    eligible_txns = txns[txns["status"].isin(eligible_statuses) & (txns["timestamp_utc"] <= as_of)].copy()
    customer_context = customers.merge(behavioral_crr, on="customer_id", how="left")

    results = []
    configured_rule_ids = active_rule_ids(rule_config)
    if "TM-STRUCT-001" in configured_rule_ids:
        results.extend(_structuring_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-STRUCT-001"), suppression_config))
    if "TM-VEL-001" in configured_rule_ids:
        results.extend(_high_velocity_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-VEL-001"), suppression_config))
    if "TM-GEO-001" in configured_rule_ids:
        results.extend(_high_risk_geo_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-GEO-001"), suppression_config, risk_indicator_config))
    if "TM-RAPID-001" in configured_rule_ids:
        results.extend(_rapid_movement_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-RAPID-001"), suppression_config))
    if "TM-FLOW-001" in configured_rule_ids:
        results.extend(_flow_through_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-FLOW-001"), suppression_config))
    if "TM-NET-001" in configured_rule_ids:
        results.extend(_network_hub_rule(eligible_txns, customer_context, as_of, rule_by_id(rule_config, "TM-NET-001"), suppression_config))
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


def _structuring_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
    near_threshold = window_txns[(window_txns["amount_usd_gross"] >= thresholds["lower_usd"]) & (window_txns["amount_usd_gross"] < thresholds["upper_usd"]) & (window_txns["currency"] == "USD")]
    counts = _aggregate_evidence(near_threshold)
    return [_result(row, rule, row["evidence_count"] >= thresholds["minimum_count"], customers, as_of, suppression) for row in counts.to_dict("records")]


def _high_velocity_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
    counts = _aggregate_evidence(window_txns)
    return [_result(row, rule, row["evidence_count"] >= thresholds["minimum_count"], customers, as_of, suppression) for row in counts.to_dict("records")]


def _high_risk_geo_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict, risk_indicator_config: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
    high_risk_geo = window_txns[window_txns["counterparty_country"].isin(risk_indicator_config["high_risk_countries"])]
    counts = _aggregate_evidence(high_risk_geo)
    return [_result(row, rule, row["evidence_count"] >= thresholds["minimum_count"], customers, as_of, suppression) for row in counts.to_dict("records")]


def _rapid_movement_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
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
                "threshold": f"outbound/inbound>={thresholds['minimum_outbound_to_inbound_ratio']} and inbound>={thresholds['minimum_inbound_usd']}",
                "triggered": outbound_amount / inbound_amount >= thresholds["minimum_outbound_to_inbound_ratio"] and inbound_amount >= thresholds["minimum_inbound_usd"],
            }
        )
    return [_result(row, rule, row["triggered"], customers, as_of, suppression) for row in rows]


def _flow_through_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
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
                "threshold": f"inbound>={thresholds['minimum_inbound_usd']} and outbound/inbound>={thresholds['minimum_outbound_to_inbound_ratio']} and counterparties>={thresholds['minimum_counterparties']}",
                "triggered": inbound_amount >= thresholds["minimum_inbound_usd"] and inbound_amount > 0 and outbound_amount / inbound_amount >= thresholds["minimum_outbound_to_inbound_ratio"] and unique_counterparties >= thresholds["minimum_counterparties"],
            }
        )
    return [_result(row, rule, row["triggered"], customers, as_of, suppression) for row in rows]


def _network_hub_rule(txns: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp, rule: dict, suppression: dict) -> list[dict]:
    thresholds = rule["thresholds"]
    window_txns = _window(txns, as_of, rule["lookback_days"])
    counterparty_customer_counts = window_txns.groupby("counterparty_id")["customer_id"].nunique().rename("linked_customer_count")
    hub_counterparties = set(counterparty_customer_counts[counterparty_customer_counts >= thresholds["minimum_linked_customers"]].index)
    hub_txns = window_txns[window_txns["counterparty_id"].isin(hub_counterparties)]
    counts = _aggregate_evidence(hub_txns)
    return [_result(row, rule, row["evidence_count"] >= thresholds["minimum_customer_evidence_count"], customers, as_of, suppression) for row in counts.to_dict("records")]


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


def _result(row: dict, rule: dict, triggered: bool, customers: pd.DataFrame, as_of: pd.Timestamp, suppression: dict) -> dict:
    customer_row = customers[customers["customer_id"] == row["customer_id"]].iloc[0]
    criteria = suppression["criteria"]
    severity = int(rule["severity"])
    suppression_applied = bool(triggered and customer_row["behavioral_crr_tier"] == criteria["behavioral_crr_tier"] and severity <= criteria["maximum_rule_severity"] and row["evidence_count"] < criteria["maximum_evidence_count_exclusive"])
    window_days = int(rule["lookback_days"])
    observation_start = as_of - pd.Timedelta(days=window_days)
    return {
        "rule_result_id": _stable_id("RR", rule["rule_id"], row["customer_id"], as_of.date().isoformat()),
        "customer_id": row["customer_id"],
        "rule_id": rule["rule_id"],
        "rule_version": RULE_VERSION,
        "rule_set_version": "2.0",
        "feature_version": "AML-FEATURES-2.1",
        "typology_family": rule["typology_family"],
        "segment_id": customer_row.get("segment_id", "unassigned"),
        "observation_start": observation_start.isoformat(),
        "observation_end": as_of.isoformat(),
        "rule_reason": rule["reason"],
        "rule_severity": severity,
        "customer_eligible": True,
        "transaction_eligible": True,
        "triggered": bool(triggered),
        "raw_trigger_retained": bool(triggered),
        "suppression_applied": suppression_applied,
        "suppression_policy_id": suppression["suppression_policy_id"] if suppression_applied else "",
        "suppression_approval_reference": suppression["approval_reference"] if suppression_applied else "",
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
