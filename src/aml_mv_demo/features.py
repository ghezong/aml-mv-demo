from __future__ import annotations

import pandas as pd
import numpy as np

from aml_mv_demo.config import load_risk_indicator_config


def normalize_transactions(transactions: pd.DataFrame, risk_indicator_config: dict | None = None) -> pd.DataFrame:
    risk_config = risk_indicator_config or load_risk_indicator_config()
    fx_to_usd = risk_config["fx_to_usd"]
    monetary_statuses = set(risk_config["monetary_statuses"])
    net_negative_statuses = set(risk_config["net_negative_statuses"])
    high_risk_countries = set(risk_config["high_risk_countries"])

    txns = transactions.copy()
    txns["timestamp_utc"] = pd.to_datetime(txns["timestamp_utc"], utc=True)
    txns["unknown_currency"] = ~txns["currency"].isin(fx_to_usd.keys())
    txns["fx_rate_to_usd"] = txns["currency"].map(fx_to_usd).fillna(1.0)
    txns["amount_usd_gross"] = txns["amount"] * txns["fx_rate_to_usd"]
    txns["amount_usd_net"] = txns["amount_usd_gross"]
    txns.loc[txns["status"].isin(net_negative_statuses), "amount_usd_net"] *= -1
    txns["is_monetary"] = txns["status"].isin(monetary_statuses)
    txns["is_settled"] = txns["status"] == "settled"
    txns["is_round_amount"] = (txns["amount"] % 100 == 0).astype(int)
    txns["is_high_risk_geo"] = txns["counterparty_country"].isin(high_risk_countries).astype(int)
    return txns


def build_customer_features(transactions: pd.DataFrame, as_of_timestamp: str | pd.Timestamp | None = None, windows_days: tuple[int, ...] = (1, 7, 30, 90), risk_indicator_config: dict | None = None) -> pd.DataFrame:
    txns = normalize_transactions(transactions, risk_indicator_config=risk_indicator_config)
    if as_of_timestamp is None:
        as_of = txns["timestamp_utc"].max()
    else:
        as_of = pd.Timestamp(as_of_timestamp)
        if as_of.tzinfo is None:
            as_of = as_of.tz_localize("UTC")
        else:
            as_of = as_of.tz_convert("UTC")

    customers = pd.DataFrame({"customer_id": sorted(txns["customer_id"].unique())})
    feature_frames = [customers]

    for days in windows_days:
        window_start = as_of - pd.Timedelta(days=days)
        window_txns = txns[(txns["timestamp_utc"] > window_start) & (txns["timestamp_utc"] <= as_of) & txns["is_monetary"]].copy()
        feature_frames.append(_window_features(window_txns, days))

    features = feature_frames[0]
    for frame in feature_frames[1:]:
        features = features.merge(frame, on="customer_id", how="left")

    numeric_columns = [column for column in features.columns if column != "customer_id"]
    features[numeric_columns] = features[numeric_columns].fillna(0)
    features["as_of_timestamp"] = as_of.isoformat()
    risk_config = risk_indicator_config or load_risk_indicator_config()
    features["feature_version"] = "AML-FEATURES-2.1"
    features["risk_indicator_version"] = risk_config["version"]
    return features


def _window_features(txns: pd.DataFrame, days: int) -> pd.DataFrame:
    if txns.empty:
        return pd.DataFrame(columns=["customer_id"])

    grouped = txns.groupby("customer_id")
    features = grouped.agg(
        **{
            f"gross_amount_{days}d": ("amount_usd_gross", "sum"),
            f"net_amount_{days}d": ("amount_usd_net", "sum"),
            f"txn_count_{days}d": ("transaction_id", "count"),
            f"unique_counterparties_{days}d": ("counterparty_id", "nunique"),
            f"high_risk_geo_txn_count_{days}d": ("is_high_risk_geo", "sum"),
            f"round_amount_count_{days}d": ("is_round_amount", "sum"),
            f"reversal_count_{days}d": ("status", lambda values: values.isin(["reversed", "refund", "chargeback"]).sum()),
        }
    ).reset_index()

    inbound = txns[txns["direction"] == "inbound"].groupby("customer_id")["amount_usd_gross"].sum().rename(f"inbound_amount_{days}d")
    outbound = txns[txns["direction"] == "outbound"].groupby("customer_id")["amount_usd_gross"].sum().rename(f"outbound_amount_{days}d")
    features = features.merge(inbound, on="customer_id", how="left").merge(outbound, on="customer_id", how="left")
    features[[f"inbound_amount_{days}d", f"outbound_amount_{days}d"]] = features[[f"inbound_amount_{days}d", f"outbound_amount_{days}d"]].fillna(0)
    features[f"flow_through_ratio_{days}d"] = features[f"outbound_amount_{days}d"] / features[f"inbound_amount_{days}d"].replace(0, np.nan)
    features[f"flow_through_ratio_{days}d"] = features[f"flow_through_ratio_{days}d"].fillna(0).clip(upper=5)
    return features
