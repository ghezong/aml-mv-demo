# AML Rulebook

This rulebook defines the synthetic scenarios implemented in the demo. Thresholds are illustrative and must not be used as production recommendations.

| Rule ID | Typology | Risk Statement | Window | Trigger | Suppression | Evidence |
|---|---|---|---|---|---|---|
| `TM-STRUCT-001` | Threshold avoidance | Multiple near-threshold transactions may indicate structuring behavior | 7 days | At least 2 settled USD transactions between USD 9,000 and USD 10,000 | Low CRR, severity <= 3, evidence count < 5 | Transaction IDs, amount, count, window |
| `TM-VEL-001` | Velocity | High transaction frequency may indicate unusual movement of funds | 1 day | At least 8 settled transactions | Same governed policy | Transaction IDs, count, window |
| `TM-GEO-001` | Higher-risk geography | Activity involving higher-risk geographies may require review | 30 days | At least 4 settled transactions involving configured higher-risk countries | Same governed policy | Counterparty countries, transaction IDs |
| `TM-RAPID-001` | Rapid movement | Material inbound value followed by outbound movement may indicate layering or pass-through activity | 3 days | Outbound-to-inbound ratio >= 0.80 and inbound >= USD 5,000 | No low-severity suppression because severity is 5 | Inbound/outbound transaction IDs and values |
| `TM-FLOW-001` | Pass-through/account cycling | High inbound and outbound turnover with many counterparties may indicate account cycling | 30 days | Inbound >= USD 10,000, outbound/inbound >= 0.75, and at least 8 counterparties | No low-severity suppression because severity is 4 | Flow-through ratio, counterparties, transactions |
| `TM-NET-001` | Network hub | Multiple customers transacting with the same counterparty may indicate a shared risk node | 30 days | Customer has at least 2 transactions with counterparties used by at least 4 customers | No low-severity suppression because severity is 4 | Counterparty hub, linked transactions |

## Standard Rule Metadata

Each production rule should maintain: rule identifier, version, typology, risk statement, products, segments, customer eligibility, transaction eligibility, lookback, features, thresholds, exclusions, suppressions, grouping, cooldown, evidence, reason codes, limitations, validation tests, monitoring metrics, owner, approver, effective start, effective end, and change ticket.

## Independent Replication Requirement

The validation function `reconcile_rule_results` compares primary rule results with independently replicated results across trigger, alert, and suppression fields. A production validation should implement a separately coded replication, reconcile population counts, and sample evidence at the transaction level.
