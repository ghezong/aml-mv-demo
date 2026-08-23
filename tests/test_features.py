import pandas as pd

from aml_mv_demo.features import build_customer_features, normalize_transactions


def test_customer_features_are_point_in_time_windows():
    transactions = pd.DataFrame(
        [
            {"transaction_id": "T1", "customer_id": "C1", "timestamp_utc": "2026-01-01T00:00:00Z", "amount": 100, "currency": "USD", "direction": "inbound", "status": "settled", "counterparty_country": "US", "counterparty_id": "CP1"},
            {"transaction_id": "T2", "customer_id": "C1", "timestamp_utc": "2026-03-01T00:00:00Z", "amount": 200, "currency": "USD", "direction": "outbound", "status": "settled", "counterparty_country": "PA", "counterparty_id": "CP2"},
        ]
    )

    features = build_customer_features(transactions, as_of_timestamp="2026-03-02T00:00:00Z", windows_days=(30, 90))

    assert features.loc[0, "gross_amount_30d"] == 200
    assert features.loc[0, "gross_amount_90d"] == 300
    assert features.loc[0, "high_risk_geo_txn_count_30d"] == 1


def test_reversals_are_net_negative_but_gross_positive():
    transactions = pd.DataFrame(
        [
            {"transaction_id": "T1", "customer_id": "C1", "timestamp_utc": "2026-03-01T00:00:00Z", "amount": 100, "currency": "USD", "direction": "inbound", "status": "reversed", "counterparty_country": "US", "counterparty_id": "CP1"},
        ]
    )

    normalized = normalize_transactions(transactions)

    assert normalized.loc[0, "amount_usd_gross"] == 100
    assert normalized.loc[0, "amount_usd_net"] == -100