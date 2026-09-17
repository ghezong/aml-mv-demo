# Canonical AML Data Dictionary

The demo data is synthetic and intentionally compact. A production data model should be broader, effective-dated, lineage-rich, and reconciled to source systems.

| Entity | Primary ID | Critical Fields | Source Assumption | Quality Checks | Retention And Lineage |
|---|---|---|---|---|---|
| Customer | `customer_id` | Type, jurisdiction, PEP flag, adverse media flag, expected volume, KYC quality, external geo risk, segment | KYC/CDD platform | Completeness, valid enum, active status | Retain effective-dated attributes and source record IDs |
| Account | `account_id` | Customer ID, product, status, open date | Core ledger/product platform | Customer referential integrity, status validity | Link to customer and product source |
| Transaction | `transaction_id` | Account, customer, timestamp, direction, amount, currency, rail, status, counterparty, device | Ledger/payment rail | Uniqueness, account referential integrity, positive amount, timestamp validity | Preserve raw and normalized values |
| Counterparty | `counterparty_id` | Country, concentration, shared exposure | Payment metadata | Valid identifier and geography | Link to transactions and network features |
| Device | `device_id` | Shared customer usage, transaction link | Device intelligence | Missingness and reuse anomalies | Link to customer/account usage events |
| CRR result | `customer_id` + version | Score, tier, reason codes | CRR service | Score range, reason-code coverage | Preserve version and calculation inputs |
| Rule result | `rule_result_id` | Rule, version, window, trigger, suppression, evidence | Rule engine | Expected-vs-actual reconciliation | Preserve raw trigger, suppression, and evidence transactions |
| ML score | `alert_id` + model version | Score, band, reason codes | ML ARR service | Score range, feature availability | Preserve model and feature version |
| Alert | `alert_id` | Customer, typology family, rule IDs, evidence IDs, priority | Alert service | Deterministic ID, lineage completeness | Retain child rule and transaction evidence |
| Disposition | Case/alert ID | Outcome, date, QA, SAR referral | Case management | Valid taxonomy, maturity windows | Governed feedback store |

## Transaction State Semantics

| Status | Treatment |
|---|---|
| `settled` | Eligible monetary event for value-based rules |
| `pending` | Excluded from settled-value detection; can be monitored separately for real-time controls |
| `failed` | Excluded from monetary value but useful as behavioral signal |
| `reversed` | Retained as gross activity and net negative offset |
| `refund` | Retained as gross activity and net negative offset |
| `chargeback` | Retained as gross activity and net negative offset plus potential risk signal |

## Currency And Time

Amounts are normalized to USD using static demo FX rates in [config/risk_indicators.json](../config/risk_indicators.json). Production implementation requires an approved FX source, effective timestamp, and controls for conversion failures. Timestamps are converted to UTC, and production implementations should preserve source timezone and local business date when required.
