from aml_mv_demo.config import load_risk_indicator_config, load_rule_config, load_suppression_config
from aml_mv_demo.crr import calculate_behavioral_crr
from aml_mv_demo.data_generator import generate_synthetic_data
from aml_mv_demo.features import build_customer_features
from aml_mv_demo.replication import replicate_rule_results
from aml_mv_demo.rules import evaluate_rules
from aml_mv_demo.validation import reconcile_rule_results


def test_independent_replication_matches_primary_rule_outputs():
    customers, _, transactions, _ = generate_synthetic_data(seed=42)
    as_of_timestamp = "2026-03-31T23:59:59Z"
    risk_config = load_risk_indicator_config()
    rule_config = load_rule_config()
    suppression_config = load_suppression_config()
    features = build_customer_features(transactions, as_of_timestamp=as_of_timestamp, risk_indicator_config=risk_config)
    behavioral_crr = calculate_behavioral_crr(customers, features.merge(customers[["customer_id", "expected_monthly_volume"]], on="customer_id", how="left"))
    primary = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp, rule_config=rule_config, suppression_config=suppression_config, risk_indicator_config=risk_config)
    independent = replicate_rule_results(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp, rule_config=rule_config, suppression_config=suppression_config, risk_indicator_config=risk_config)

    reconciled = reconcile_rule_results(primary, independent)

    assert set(reconciled["reconciliation_status"]) == {"matched"}