from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_synthetic_data(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create deterministic synthetic AML data for demos and tests."""
    rng = np.random.default_rng(seed)

    customer_count = 120
    customers = pd.DataFrame(
        [
            {
                "customer_id": f"C{i:04d}",
                "customer_type": rng.choice(["consumer", "merchant", "corporate"], p=[0.55, 0.3, 0.15]),
                "jurisdiction": rng.choice(["US", "CA", "GB", "MX", "BR"], p=[0.55, 0.12, 0.12, 0.11, 0.10]),
                "pep_flag": bool(rng.choice([0, 1], p=[0.94, 0.06])),
                "adverse_media_flag": bool(rng.choice([0, 1], p=[0.9, 0.1])),
                "expected_monthly_volume": int(rng.choice([5_000, 10_000, 25_000, 75_000, 150_000])),
                "account_age_days": int(rng.integers(5, 1_200)),
                "kyc_quality_score": round(float(rng.uniform(0.62, 0.99)), 3),
                "external_geo_risk": round(float(rng.uniform(0.05, 0.85)), 3),
                "segment_id": rng.choice(["consumer_wallet", "smb_card", "merchant_payout", "cross_border"], p=[0.4, 0.25, 0.2, 0.15]),
            }
            for i in range(1, customer_count + 1)
        ]
    )

    accounts = pd.DataFrame(
        [
            {
                "account_id": f"A{i:04d}",
                "customer_id": customer_id,
                "product": rng.choice(["wallet", "ach", "card", "merchant_processing", "payout"], p=[0.25, 0.2, 0.25, 0.2, 0.1]),
                "status": "active",
                "open_date": "2025-01-01",
            }
            for i, customer_id in enumerate(customers["customer_id"], start=1)
        ]
    )

    transactions = []
    start = pd.Timestamp("2025-10-01", tz="UTC")
    risky_customers = list(customers.sample(18, random_state=seed)["customer_id"])
    rapid_movement = set(risky_customers[:6])
    structuring = set(risky_customers[6:11])
    network_cluster = set(risky_customers[11:15])
    behavior_change = set(risky_customers[15:])

    for _, account in accounts.iterrows():
        customer_id = account["customer_id"]
        base_count = 45 if customer_id in risky_customers else 18
        txn_count = int(rng.integers(base_count, base_count + 22))
        for idx in range(txn_count):
            amount = float(rng.gamma(shape=2.2, scale=550.0))
            if customer_id in structuring and idx % 9 == 0:
                amount = float(rng.uniform(9_000, 9_950))
            if customer_id in rapid_movement and idx % 8 in {0, 1}:
                amount = float(rng.uniform(4_500, 12_000))
            if customer_id in behavior_change and idx > txn_count * 0.72:
                amount = float(rng.uniform(2_500, 8_500))
            timestamp = start + pd.Timedelta(days=int(rng.integers(0, 180)), hours=int(rng.integers(0, 24)))
            direction = rng.choice(["inbound", "outbound"], p=[0.52, 0.48])
            if customer_id in rapid_movement:
                direction = "inbound" if idx % 8 == 0 else "outbound" if idx % 8 == 1 else direction
            counterparty_id = f"CP{int(rng.integers(1, 150)):04d}"
            if customer_id in network_cluster and idx % 5 == 0:
                counterparty_id = "CP-HIGH-RISK-HUB"
            transactions.append(
                {
                    "transaction_id": f"T{len(transactions)+1:06d}",
                    "account_id": account["account_id"],
                    "customer_id": customer_id,
                    "timestamp_utc": timestamp.isoformat(),
                    "direction": direction,
                    "amount": round(amount, 2),
                    "currency": rng.choice(["USD", "CAD", "GBP"], p=[0.82, 0.1, 0.08]),
                    "counterparty_id": counterparty_id,
                    "counterparty_country": rng.choice(["US", "CA", "GB", "MX", "BR", "PA"], p=[0.5, 0.11, 0.11, 0.1, 0.1, 0.08]),
                    "rail": rng.choice(["card", "ach", "wire", "p2p", "payout"], p=[0.35, 0.25, 0.1, 0.2, 0.1]),
                    "status": rng.choice(["settled", "pending", "failed", "reversed", "refund", "chargeback"], p=[0.82, 0.05, 0.05, 0.03, 0.03, 0.02]),
                    "device_id": f"D{int(rng.integers(1, 55)):04d}",
                }
            )

    transactions_df = pd.DataFrame(transactions).sort_values("timestamp_utc").reset_index(drop=True)
    outcomes = pd.DataFrame(
        {
            "customer_id": customers["customer_id"],
            "confirmed_suspicious": customers["customer_id"].isin(risky_customers).astype(int),
            "sar_referral": customers["customer_id"].isin(set(risky_customers[:8])).astype(int),
            "qa_confirmed": customers["customer_id"].isin(set(risky_customers[:12])).astype(int),
            "outcome_date": "2026-04-30",
            "label_maturity_days": 45,
        }
    )
    return customers, accounts, transactions_df, outcomes


def write_synthetic_data(output_dir: str | Path = "data/synthetic", seed: int = 42) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    customers, accounts, transactions, outcomes = generate_synthetic_data(seed=seed)
    customers.to_csv(output_path / "customers.csv", index=False)
    accounts.to_csv(output_path / "accounts.csv", index=False)
    transactions.to_csv(output_path / "transactions.csv", index=False)
    outcomes.to_csv(output_path / "investigation_outcomes.csv", index=False)
