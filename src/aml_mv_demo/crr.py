from __future__ import annotations

import pandas as pd


def _tier(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def calculate_activation_crr(customers: pd.DataFrame) -> pd.DataFrame:
    """Calculate onboarding-style CRR using KYC and inherent risk factors."""
    rows = []
    for row in customers.to_dict("records"):
        score = 15.0
        reasons = []

        if row["customer_type"] in {"merchant", "corporate"}:
            score += 12
            reasons.append("business_customer")
        if row["pep_flag"]:
            score += 30
            reasons.append("pep")
        if row["adverse_media_flag"]:
            score += 22
            reasons.append("adverse_media")
        if row["external_geo_risk"] >= 0.65:
            score += 18
            reasons.append("higher_geo_risk")
        if row["kyc_quality_score"] < 0.75:
            score += 14
            reasons.append("kyc_quality_gap")
        if row["expected_monthly_volume"] >= 75_000:
            score += 10
            reasons.append("high_expected_volume")

        score = min(score, 100.0)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "activation_crr_score": round(score, 2),
                "activation_crr_tier": _tier(score),
                "activation_reason_codes": ";".join(reasons) or "baseline",
                "crr_version": "CRR-ACT-1.0",
            }
        )
    return pd.DataFrame(rows)


def calculate_behavioral_crr(customers: pd.DataFrame, customer_features: pd.DataFrame) -> pd.DataFrame:
    """Calculate continuous CRR from activation risk plus point-in-time behavior."""
    activation = calculate_activation_crr(customers)
    merged = activation.merge(customer_features, on="customer_id", how="left").fillna(0)
    rows = []
    for row in merged.to_dict("records"):
        score = float(row["activation_crr_score"])
        reasons = []

        if row["gross_amount_30d"] > row.get("expected_monthly_volume", 0) * 1.5:
            score += 16
            reasons.append("activity_above_expected")
        if row["unique_counterparties_30d"] >= 15:
            score += 10
            reasons.append("many_counterparties")
        if row["high_risk_geo_txn_count_30d"] >= 3:
            score += 12
            reasons.append("high_risk_geo_activity")
        if row["round_amount_count_30d"] >= 5:
            score += 8
            reasons.append("round_amount_pattern")
        if row.get("flow_through_ratio_7d", 0) >= 0.85 and row.get("inbound_amount_7d", 0) >= 5_000:
            score += 10
            reasons.append("rapid_flow_through")

        score = min(score, 100.0)
        rows.append(
            {
                "customer_id": row["customer_id"],
                "behavioral_crr_score": round(score, 2),
                "behavioral_crr_tier": _tier(score),
                "behavioral_reason_codes": ";".join(reasons) or "no_behavioral_elevation",
                "crr_version": "CRR-BEH-1.0",
            }
        )
    return pd.DataFrame(rows)
