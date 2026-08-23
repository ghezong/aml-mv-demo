import pandas as pd

from aml_mv_demo.rules import consolidate_alerts, evaluate_rules


def test_structuring_rule_triggers_and_preserves_lineage():
    customers = pd.DataFrame(
        [
            {
                "customer_id": "C0001",
                "customer_type": "consumer",
                "jurisdiction": "US",
                "pep_flag": False,
                "adverse_media_flag": False,
                "expected_monthly_volume": 10_000,
                "account_age_days": 100,
                "kyc_quality_score": 0.95,
                "external_geo_risk": 0.1,
            }
        ]
    )
    customers["segment_id"] = "consumer_wallet"
    behavioral_crr = pd.DataFrame([{"customer_id": "C0001", "behavioral_crr_tier": "medium", "behavioral_crr_score": 50}])
    transactions = pd.DataFrame(
        [
            {"transaction_id": "T1", "customer_id": "C0001", "account_id": "A1", "timestamp_utc": "2026-01-01T00:00:00Z", "amount": 9500, "status": "settled", "counterparty_country": "US"},
            {"transaction_id": "T2", "customer_id": "C0001", "account_id": "A1", "timestamp_utc": "2026-01-02T00:00:00Z", "amount": 9700, "status": "settled", "counterparty_country": "US"},
        ]
    )
    transactions["currency"] = "USD"
    transactions["direction"] = "inbound"
    transactions["counterparty_id"] = ["CP1", "CP2"]
    transactions["rail"] = "ach"
    transactions["device_id"] = "D1"

    results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp="2026-01-07T00:00:00Z")
    structuring = results[results["rule_id"] == "TM-STRUCT-001"].iloc[0]
    alerts = consolidate_alerts(results)

    assert bool(structuring["triggered"]) is True
    assert bool(structuring["alert_generated"]) is True
    assert "TM-STRUCT-001" in alerts.iloc[0]["rule_ids"]
    assert alerts.iloc[0]["rule_result_ids"].startswith("RR-")


def test_suppression_only_applies_to_triggered_results():
    customers = pd.DataFrame([{"customer_id": "C0001", "segment_id": "consumer_wallet"}])
    behavioral_crr = pd.DataFrame([{"customer_id": "C0001", "behavioral_crr_tier": "low", "behavioral_crr_score": 20}])
    transactions = pd.DataFrame(
        [
            {"transaction_id": "T1", "customer_id": "C0001", "account_id": "A1", "timestamp_utc": "2026-01-01T00:00:00Z", "amount": 100, "currency": "USD", "direction": "inbound", "status": "settled", "counterparty_country": "US", "counterparty_id": "CP1", "rail": "ach", "device_id": "D1"},
        ]
    )

    results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp="2026-01-02T00:00:00Z")

    assert not results[~results["triggered"]]["suppression_applied"].any()
