from aml_mv_demo.crr import calculate_behavioral_crr
from aml_mv_demo.data_generator import generate_synthetic_data
from aml_mv_demo.features import build_customer_features
from aml_mv_demo.ml_arr import build_training_frame, score_alerts, train_arr_model
from aml_mv_demo.rules import consolidate_alerts, evaluate_rules


def test_ml_arr_scores_alerts_without_using_future_outcome_features():
    customers, _, transactions, outcomes = generate_synthetic_data(seed=42)
    features = build_customer_features(transactions, as_of_timestamp="2026-03-31T23:59:59Z")
    behavioral_crr = calculate_behavioral_crr(customers, features.merge(customers[["customer_id", "expected_monthly_volume"]], on="customer_id", how="left"))
    rule_results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp="2026-03-31T23:59:59Z")
    alerts = consolidate_alerts(rule_results)
    training_frame = build_training_frame(alerts, behavioral_crr, features, outcomes)
    model = train_arr_model(training_frame)
    scored = score_alerts(model, training_frame)

    assert not {"confirmed_suspicious", "sar_referral", "qa_confirmed", "label"}.intersection(set(model.feature_names_in_))
    assert scored["ml_arr_score"].between(0, 1).all()
    assert set(scored["ml_arr_band"]).issubset({"standard", "elevated", "urgent"})
