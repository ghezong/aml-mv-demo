from __future__ import annotations

import pandas as pd

from aml_mv_demo.config import load_risk_indicator_config, load_rule_config, load_suppression_config, rule_by_id
from aml_mv_demo.features import normalize_transactions


def replicate_rule_results(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    behavioral_crr: pd.DataFrame,
    as_of_timestamp: str | pd.Timestamp,
    rule_config: dict | None = None,
    suppression_config: dict | None = None,
    risk_indicator_config: dict | None = None,
) -> pd.DataFrame:
    """Independently reproduce core rule outcomes without calling the production rule engine."""
    rule_config = rule_config or load_rule_config()
    suppression_config = suppression_config or load_suppression_config()
    risk_indicator_config = risk_indicator_config or load_risk_indicator_config()
    as_of = pd.Timestamp(as_of_timestamp)
    if as_of.tzinfo is None:
        as_of = as_of.tz_localize("UTC")
    else:
        as_of = as_of.tz_convert("UTC")

    normalized = normalize_transactions(transactions, risk_indicator_config=risk_indicator_config)
    eligible = normalized[normalized["status"].isin(risk_indicator_config["rule_eligible_statuses"]) & (normalized["timestamp_utc"] <= as_of)]
    customer_context = customers[["customer_id", "segment_id"]].merge(behavioral_crr[["customer_id", "behavioral_crr_tier"]], on="customer_id", how="left")

    rows = []
    for customer_id in sorted(customer_context["customer_id"].unique()):
        customer_txns = eligible[eligible["customer_id"] == customer_id]
        customer_tier = customer_context.loc[customer_context["customer_id"] == customer_id, "behavioral_crr_tier"].iloc[0]
        rows.extend(_replicate_customer(customer_id, customer_tier, customer_txns, eligible, as_of, rule_config, suppression_config, risk_indicator_config))
    return pd.DataFrame(rows)


def _replicate_customer(customer_id: str, customer_tier: str, customer_txns: pd.DataFrame, all_txns: pd.DataFrame, as_of: pd.Timestamp, rule_config: dict, suppression_config: dict, risk_indicator_config: dict) -> list[dict]:
    rows = []
    for rule_id in ["TM-STRUCT-001", "TM-VEL-001", "TM-GEO-001", "TM-RAPID-001", "TM-FLOW-001", "TM-NET-001"]:
        rule = rule_by_id(rule_config, rule_id)
        window_start = as_of - pd.Timedelta(days=rule["lookback_days"])
        window = customer_txns[(customer_txns["timestamp_utc"] > window_start) & (customer_txns["timestamp_utc"] <= as_of)]
        triggered, evidence_ids = _replicate_rule(rule, window, all_txns, as_of, risk_indicator_config)
        if evidence_ids:
            suppression_applied = _replicate_suppression(triggered, customer_tier, int(rule["severity"]), len(evidence_ids), suppression_config)
            rows.append(
                {
                    "customer_id": customer_id,
                    "rule_id": rule_id,
                    "triggered": bool(triggered),
                    "alert_generated": bool(triggered and not suppression_applied),
                    "suppression_applied": suppression_applied,
                    "evidence_count": len(evidence_ids),
                    "evidence_transaction_ids": ";".join(evidence_ids),
                }
            )
    return rows


def _replicate_rule(rule: dict, window: pd.DataFrame, all_txns: pd.DataFrame, as_of: pd.Timestamp, risk_indicator_config: dict) -> tuple[bool, list[str]]:
    thresholds = rule["thresholds"]
    rule_id = rule["rule_id"]
    if rule_id == "TM-STRUCT-001":
        evidence = window[(window["currency"] == "USD") & (window["amount_usd_gross"] >= thresholds["lower_usd"]) & (window["amount_usd_gross"] < thresholds["upper_usd"])]
        return len(evidence) >= thresholds["minimum_count"], evidence["transaction_id"].astype(str).tolist()
    if rule_id == "TM-VEL-001":
        return len(window) >= thresholds["minimum_count"], window["transaction_id"].astype(str).tolist()
    if rule_id == "TM-GEO-001":
        evidence = window[window["counterparty_country"].isin(risk_indicator_config["high_risk_countries"])]
        return len(evidence) >= thresholds["minimum_count"], evidence["transaction_id"].astype(str).tolist()
    if rule_id == "TM-RAPID-001":
        inbound = window.loc[window["direction"] == "inbound", "amount_usd_gross"].sum()
        outbound = window.loc[window["direction"] == "outbound", "amount_usd_gross"].sum()
        if inbound == 0:
            return False, []
        return outbound / inbound >= thresholds["minimum_outbound_to_inbound_ratio"] and inbound >= thresholds["minimum_inbound_usd"], window["transaction_id"].astype(str).tolist()
    if rule_id == "TM-FLOW-001":
        inbound = window.loc[window["direction"] == "inbound", "amount_usd_gross"].sum()
        outbound = window.loc[window["direction"] == "outbound", "amount_usd_gross"].sum()
        unique_counterparties = window["counterparty_id"].nunique()
        return inbound >= thresholds["minimum_inbound_usd"] and inbound > 0 and outbound / inbound >= thresholds["minimum_outbound_to_inbound_ratio"] and unique_counterparties >= thresholds["minimum_counterparties"], window["transaction_id"].astype(str).tolist()
    if rule_id == "TM-NET-001":
        window_start = as_of - pd.Timedelta(days=rule["lookback_days"])
        all_window = all_txns[(all_txns["timestamp_utc"] > window_start) & (all_txns["timestamp_utc"] <= as_of)]
        hub_counts = all_window.groupby("counterparty_id")["customer_id"].nunique()
        hubs = set(hub_counts[hub_counts >= thresholds["minimum_linked_customers"]].index)
        evidence = window[window["counterparty_id"].isin(hubs)]
        return len(evidence) >= thresholds["minimum_customer_evidence_count"], evidence["transaction_id"].astype(str).tolist()
    raise KeyError(f"No independent replication implemented for {rule_id}")


def _replicate_suppression(triggered: bool, customer_tier: str, severity: int, evidence_count: int, suppression_config: dict) -> bool:
    criteria = suppression_config["criteria"]
    return bool(triggered and customer_tier == criteria["behavioral_crr_tier"] and severity <= criteria["maximum_rule_severity"] and evidence_count < criteria["maximum_evidence_count_exclusive"])