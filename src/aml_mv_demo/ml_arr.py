from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


FEATURE_COLUMNS = ["max_rule_severity", "evidence_count", "behavioral_crr_score", "gross_amount_30d", "high_risk_geo_txn_count_30d", "flow_through_ratio_7d"]


@dataclass
class SimpleARRModel:
    feature_names_in_: list[str]
    means: np.ndarray
    stds: np.ndarray
    coefficients: np.ndarray
    intercept: float
    constant_probability: float | None = None

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        if self.constant_probability is not None:
            positive = np.full(len(frame), self.constant_probability)
        else:
            values = frame[self.feature_names_in_].to_numpy(dtype=float)
            scaled = (values - self.means) / self.stds
            logits = scaled @ self.coefficients + self.intercept
            positive = 1 / (1 + np.exp(-logits))
        return np.column_stack([1 - positive, positive])


def build_training_frame(alerts: pd.DataFrame, behavioral_crr: pd.DataFrame, features: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    frame = alerts.merge(behavioral_crr, on="customer_id", how="left").merge(features, on="customer_id", how="left").merge(outcomes, on="customer_id", how="left")
    frame["label"] = ((frame["confirmed_suspicious"] == 1) | (frame["sar_referral"] == 1) | (frame["qa_confirmed"] == 1)).astype(int)
    frame[FEATURE_COLUMNS] = frame[FEATURE_COLUMNS].fillna(0)
    return frame


def split_training_validation(frame: pd.DataFrame, validation_fraction: float = 0.35, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame.empty:
        raise ValueError("ML ARR split requires at least one alert record")
    customers = pd.Series(frame["customer_id"].unique()).sample(frac=1, random_state=seed).tolist()
    validation_count = max(1, int(len(customers) * validation_fraction)) if len(customers) > 1 else 0
    validation_customers = set(customers[:validation_count])
    validation = frame[frame["customer_id"].isin(validation_customers)].copy()
    development = frame[~frame["customer_id"].isin(validation_customers)].copy()
    if development.empty or validation.empty or development["label"].nunique() < 2:
        sorted_frame = frame.sort_values(["observation_end", "customer_id", "alert_id"]).reset_index(drop=True)
        split_index = max(1, int(len(sorted_frame) * (1 - validation_fraction)))
        development = sorted_frame.iloc[:split_index].copy()
        validation = sorted_frame.iloc[split_index:].copy()
    return development, validation


def train_arr_model(training_frame: pd.DataFrame) -> SimpleARRModel:
    if training_frame.empty:
        raise ValueError("ML ARR training requires at least one alert record")

    numeric_features = FEATURE_COLUMNS
    values = training_frame[numeric_features].fillna(0).to_numpy(dtype=float)
    labels = training_frame["label"].to_numpy(dtype=float)
    means = values.mean(axis=0)
    stds = values.std(axis=0)
    stds[stds == 0] = 1

    if training_frame["label"].nunique() < 2:
        return SimpleARRModel(numeric_features, means, stds, np.zeros(len(numeric_features)), 0.0, float(labels[0]))

    scaled = (values - means) / stds
    coefficients = np.zeros(scaled.shape[1])
    intercept = 0.0
    learning_rate = 0.08
    positive_weight = len(labels) / (2 * max(labels.sum(), 1))
    negative_weight = len(labels) / (2 * max((1 - labels).sum(), 1))
    weights = np.where(labels == 1, positive_weight, negative_weight)

    for _ in range(700):
        logits = scaled @ coefficients + intercept
        probabilities = 1 / (1 + np.exp(-logits))
        errors = (probabilities - labels) * weights
        coefficients -= learning_rate * (scaled.T @ errors) / len(labels)
        intercept -= learning_rate * errors.mean()

    return SimpleARRModel(numeric_features, means, stds, coefficients, intercept)


def score_alerts(model: SimpleARRModel, scoring_frame: pd.DataFrame) -> pd.DataFrame:
    scored = scoring_frame.copy()
    scored[FEATURE_COLUMNS] = scored[FEATURE_COLUMNS].fillna(0)
    scored["ml_arr_score"] = model.predict_proba(scored[FEATURE_COLUMNS])[:, 1]
    scored["ml_arr_band"] = pd.cut(
        scored["ml_arr_score"],
        bins=[-0.001, 0.35, 0.70, 1.0],
        labels=["standard", "elevated", "urgent"],
    ).astype(str)
    scored["ml_model_version"] = "ML-ARR-LR-1.0"
    scored["ml_reason_codes"] = scored.apply(_reason_codes, axis=1)
    return scored


def evaluate_arr_model(scored_validation: pd.DataFrame) -> pd.DataFrame:
    if scored_validation.empty:
        return pd.DataFrame([{"metric": "validation_alert_count", "value": 0, "status": "breach"}])
    scored = scored_validation.sort_values("ml_arr_score", ascending=False).copy()
    label_rate = float(scored["label"].mean()) if "label" in scored else 0.0
    top_decile_count = max(1, int(len(scored) * 0.1))
    top_decile_rate = float(scored.head(top_decile_count)["label"].mean()) if "label" in scored else 0.0
    lift = top_decile_rate / label_rate if label_rate else 0.0
    return pd.DataFrame(
        [
            {"metric": "validation_alert_count", "value": len(scored), "status": "passed"},
            {"metric": "validation_label_rate", "value": round(label_rate, 4), "status": "monitor"},
            {"metric": "top_decile_label_rate", "value": round(top_decile_rate, 4), "status": "monitor"},
            {"metric": "top_decile_lift", "value": round(lift, 4), "status": "monitor"},
            {"metric": "score_min", "value": round(float(scored["ml_arr_score"].min()), 4), "status": "passed"},
            {"metric": "score_max", "value": round(float(scored["ml_arr_score"].max()), 4), "status": "passed"},
        ]
    )


def _reason_codes(row: pd.Series) -> str:
    reasons = []
    if row["behavioral_crr_score"] >= 75:
        reasons.append("high_crr")
    if row["max_rule_severity"] >= 4:
        reasons.append("severe_rule")
    if row["evidence_count"] >= 3:
        reasons.append("multiple_evidence_items")
    if row["high_risk_geo_txn_count_30d"] >= 3:
        reasons.append("high_risk_geo_activity")
    if row.get("flow_through_ratio_7d", 0) >= 0.8:
        reasons.append("rapid_flow_through")
    return ";".join(reasons) or "baseline_alert_features"
