from __future__ import annotations

from pathlib import Path
import json

from aml_mv_demo.config import load_risk_indicator_config, load_rule_config, load_suppression_config
from aml_mv_demo.crr import calculate_behavioral_crr
from aml_mv_demo.data_generator import generate_synthetic_data, write_synthetic_data
from aml_mv_demo.features import build_customer_features
from aml_mv_demo.ml_arr import build_training_frame, evaluate_arr_model, score_alerts, split_training_validation, train_arr_model
from aml_mv_demo.replication import replicate_rule_results
from aml_mv_demo.rules import IMPLEMENTED_RULE_IDS, consolidate_alerts, evaluate_rules
from aml_mv_demo.validation import arr_monitoring_summary, config_coverage_summary, data_quality_summary, exclusion_summary, reconcile_rule_results


def main() -> None:
    write_synthetic_data()
    customers, accounts, transactions, outcomes = generate_synthetic_data()
    as_of_timestamp = "2026-03-31T23:59:59Z"
    rule_config = load_rule_config()
    suppression_config = load_suppression_config()
    risk_indicator_config = load_risk_indicator_config()
    features = build_customer_features(transactions, as_of_timestamp=as_of_timestamp, risk_indicator_config=risk_indicator_config)
    behavioral_crr = calculate_behavioral_crr(customers, features.merge(customers[["customer_id", "expected_monthly_volume"]], on="customer_id", how="left"))
    rule_results = evaluate_rules(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp, rule_config=rule_config, suppression_config=suppression_config, risk_indicator_config=risk_indicator_config)
    independent_rule_results = replicate_rule_results(customers, transactions, behavioral_crr, as_of_timestamp=as_of_timestamp, rule_config=rule_config, suppression_config=suppression_config, risk_indicator_config=risk_indicator_config)
    alerts = consolidate_alerts(rule_results)
    model_frame = build_training_frame(alerts, behavioral_crr, features, outcomes)
    development_frame, validation_frame = split_training_validation(model_frame)
    model = train_arr_model(development_frame)
    scored_alerts = score_alerts(model, validation_frame)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    features.to_csv(output_dir / "customer_features.csv", index=False)
    behavioral_crr.to_csv(output_dir / "behavioral_crr.csv", index=False)
    rule_results.to_csv(output_dir / "rule_results.csv", index=False)
    alerts.to_csv(output_dir / "alerts.csv", index=False)
    model_frame.to_csv(output_dir / "ml_arr_model_frame.csv", index=False)
    development_frame.to_csv(output_dir / "ml_arr_development_frame.csv", index=False)
    validation_frame.to_csv(output_dir / "ml_arr_validation_frame.csv", index=False)
    scored_alerts.to_csv(output_dir / "scored_alerts.csv", index=False)
    data_quality_summary(customers, accounts, transactions, risk_indicator_config=risk_indicator_config).to_csv(output_dir / "data_quality_summary.csv", index=False)
    exclusion_summary(transactions, as_of_timestamp, risk_indicator_config).to_csv(output_dir / "exclusion_summary.csv", index=False)
    config_coverage_summary(rule_results, rule_config, IMPLEMENTED_RULE_IDS).to_csv(output_dir / "config_coverage_summary.csv", index=False)
    reconcile_rule_results(rule_results, independent_rule_results).to_csv(output_dir / "rule_reconciliation.csv", index=False)
    arr_monitoring_summary(scored_alerts).to_csv(output_dir / "arr_monitoring_summary.csv", index=False)
    evaluate_arr_model(scored_alerts).to_csv(output_dir / "arr_validation_metrics.csv", index=False)
    (output_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": "DEMO-RUN-2026-03-31",
                "as_of_timestamp": as_of_timestamp,
                "rule_set_id": rule_config["rule_set_id"],
                "rule_set_version": rule_config["version"],
                "suppression_policy_id": suppression_config["suppression_policy_id"],
                "risk_indicator_set_id": risk_indicator_config["risk_indicator_set_id"],
                "risk_indicator_version": risk_indicator_config["version"],
                "feature_version": "AML-FEATURES-2.1",
                "rule_engine_version": "TM-RULES-2.1",
                "ml_model_version": "ML-ARR-LR-1.0",
                "synthetic_seed": 42,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Generated {len(customers)} customers, {len(accounts)} accounts, {len(transactions)} transactions")
    print(f"Created {len(rule_results)} rule results and {len(alerts)} consolidated alerts")
    print(f"Scored {len(scored_alerts)} holdout validation alerts")
    print("Outputs written to outputs/")


if __name__ == "__main__":
    main()
