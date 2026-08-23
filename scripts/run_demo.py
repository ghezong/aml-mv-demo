from __future__ import annotations

from pathlib import Path

from aml_mv_demo.crr import calculate_behavioral_crr
from aml_mv_demo.data_generator import generate_synthetic_data, write_synthetic_data
from aml_mv_demo.features import build_customer_features
from aml_mv_demo.ml_arr import build_training_frame, score_alerts, train_arr_model
from aml_mv_demo.rules import consolidate_alerts, evaluate_rules
from aml_mv_demo.validation import arr_monitoring_summary, data_quality_summary, reconcile_rule_results


def main() -> None:
    write_synthetic_data()
    customers, accounts, transactions, outcomes = generate_synthetic_data()
    as_of_timestamp = "2026-03-31T23:59:59Z"
    features = build_customer_features(transactions, as_of_timestamp=as_of_timestamp)
    behavioral_crr = calculate_behavioral_crr(customers, features.merge(customers[["customer_id", "expected_monthly_volume"]], on="customer_id", how="left"))
    rule_results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp)
    independent_rule_results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp)
    alerts = consolidate_alerts(rule_results)
    training_frame = build_training_frame(alerts, behavioral_crr, features, outcomes)
    model = train_arr_model(training_frame)
    scored_alerts = score_alerts(model, training_frame)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    features.to_csv(output_dir / "customer_features.csv", index=False)
    behavioral_crr.to_csv(output_dir / "behavioral_crr.csv", index=False)
    rule_results.to_csv(output_dir / "rule_results.csv", index=False)
    alerts.to_csv(output_dir / "alerts.csv", index=False)
    scored_alerts.to_csv(output_dir / "scored_alerts.csv", index=False)
    data_quality_summary(customers, accounts, transactions).to_csv(output_dir / "data_quality_summary.csv", index=False)
    reconcile_rule_results(rule_results, independent_rule_results).to_csv(output_dir / "rule_reconciliation.csv", index=False)
    arr_monitoring_summary(scored_alerts).to_csv(output_dir / "arr_monitoring_summary.csv", index=False)

    print(f"Generated {len(customers)} customers, {len(accounts)} accounts, {len(transactions)} transactions")
    print(f"Created {len(rule_results)} rule results and {len(alerts)} consolidated alerts")
    print("Outputs written to outputs/")


if __name__ == "__main__":
    main()
