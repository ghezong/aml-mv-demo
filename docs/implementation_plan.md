# Implementation-Ready Project Plan

## 1. Executive Summary

Build a synthetic but production-shaped AML monitoring platform that demonstrates CRR, deterministic TM rules, ML ARR, alert consolidation, case workflow, validation, governance, and monitoring. The demo is designed for a GitHub portfolio and excludes confidential information.

## 2. Assumptions And Scope

No source systems, transaction volumes, staffing levels, delivery dates, production thresholds, or regulatory conclusions are assumed. The demo uses representative synthetic entities and generic risk typologies only.

## 3. Target-State Capability Model

| Capability | Required Design Element | Demo Implementation |
|---|---|---|
| Activation CRR | KYC/inherent risk score and reason codes | `calculate_activation_crr` |
| Continuous CRR | Behavioral reassessment using point-in-time features | `calculate_behavioral_crr` |
| TM rules | Modular deterministic scenarios | `evaluate_rules` |
| ML ARR | Explainable alert ranking | `train_arr_model` and `score_alerts` |
| Workflow | Consolidation and lineage | `consolidate_alerts` |
| Validation | Independent replication and DQ checks | `validation.py` |

## 4. Architecture And Component Design

See [architecture.md](architecture.md).

## 5. Integrated CRR, TM, And ML ARR Methodology

The recommended pattern is deterministic rule-generated alerts with ML ARR prioritization. This preserves rule-level regulatory traceability while demonstrating ML-driven queue management. ML does not autonomously close alerts.

## 6. Data And Feature Requirements

See [data_dictionary.md](data_dictionary.md). The implemented feature layer computes 1-, 7-, 30-, and 90-day point-in-time measures, separates gross and net transaction treatment, and preserves transaction-state semantics.

## 7. Rule And Model Lifecycle

| Stage | Deliverable |
|---|---|
| Risk identification | Typology inventory |
| Coverage assessment | Risk-control-data matrix |
| Requirements | Rule specification |
| Data feasibility | Source and CDE assessment |
| Development | Versioned code/config |
| Testing | Unit, integration, replay, boundary tests |
| Independent validation | Replication and challenge report |
| Approval | Signed change record |
| Deployment | Release manifest and rollback plan |
| Monitoring | KPI/KRI dashboard and issue log |

## 8. Testing And Validation Strategy

The test suite covers CRR range/tier behavior, point-in-time windows, transaction-state normalization, rule trigger lineage, suppression controls, ML leakage controls, and rule reconciliation. A production implementation would extend this with historical replay, false-negative sampling, model calibration, fairness/proxy review, and UAT evidence.

## 9. Tuning And Optimization Strategy

Tuning must evaluate detection effectiveness, false negatives, coverage, alert quality, investigator capacity, customer impact, threshold sensitivity, and stability. Alert-volume reduction is never sufficient as a standalone objective.

## 10. Alert And Investigation Workflow

Raw rule results become alerts only after suppression evaluation. Alerts are consolidated by customer, typology family, and observation window. Child rule results and transaction IDs remain available for investigation evidence.

## 11. Governance And Operating Model

See [governance.md](governance.md).

## 12. Phased Development Plan

| Phase | Purpose | Gate |
|---|---|---|
| 0 Mobilization | Scope, governance, inventories | Charter approved |
| 1 Current state | Assess code, data, docs, workflows | Gap log accepted |
| 2 Coverage design | Map risks to typologies and controls | Coverage approved |
| 3 Data foundation | Build canonical model, DQ, lineage, features | Data readiness |
| 4 Rule engine MVP | Implement representative CRR and TM rules | Rule validation |
| 5 ML ARR | Train and validate prioritization model | Model risk approval |
| 6 Workflow | Integrate alerts, cases, feedback | UAT signoff |
| 7 Expansion | Add products, segments, jurisdictions | Coverage acceptance |
| 8 Production readiness | Complete validation, approvals, rollback | Go-live approval |
| 9 Continuous monitoring | PIR, tuning, challenger analysis | Governance cadence |

## 13. Workstream-Level Plan

| Workstream | Objective | Acceptance Criteria |
|---|---|---|
| PMO | Manage scope, risks, decisions | Active RAID and decision log |
| Regulatory/typology | Define obligations and behaviors | Approved typology inventory |
| Data | Build traceable canonical inputs | Reconciled CDEs |
| Features | Create governed feature catalog | Point-in-time reproducibility |
| CRR | Build activation and behavioral ratings | Explainable score outputs |
| TM rules | Implement deterministic scenarios | Rule outputs independently replicated |
| ML ARR | Rank alerts for human review | Validated performance and fallback |
| Workflow | Route and investigate alerts | UAT-approved case journey |
| Monitoring | Produce MI and escalation | Dashboard thresholds assigned |
| Validation | Challenge implementation | Findings closed or accepted |

## 14. Deliverables Register

Project charter, scope document, current-state assessment, inventories, typology inventory, coverage matrix, target operating model, architecture, canonical data model, data dictionary, lineage documentation, CDE inventory, feature catalog, CRR methodology, TM rulebook, ML ARR development document, configuration specification, testing results, replication results, tuning package, validation package, governance framework, change procedure, monitoring plan, operational procedures, investigator training, production-readiness assessment, PIR, and evidence repository.

## 15. RACI

| Activity | Sponsor | AML Officer | Product | Data | Engineering | Data Science | QA | Validation | Operations |
|---|---|---|---|---|---|---|---|---|---|
| Scope | A | C | R | C | C | C | I | C | C |
| Typology inventory | C | A/R | C | C | I | C | I | C | C |
| Data model | I | C | C | A/R | R | C | C | C | I |
| Rule development | I | A | C | C | R | C | R | C | C |
| ML ARR | I | C | C | C | C | R | C | A | C |
| Testing | I | C | C | C | R | R | A/R | C | C |
| Go-live | A | A | C | C | R | R | C | C | R |

## 16. Dependency Map

Product scope, source inventory, customer identity keys, transaction-state policy, disposition taxonomy, case-management capabilities, model risk classification, suppression policy, and operational capacity must be known before production rollout.

## 17. Risk And Control Register

See the README and validation framework for key risk/control themes. Production registers should include likelihood, impact, preventive control, detective control, contingency, owner, and escalation trigger for each risk.

## 18. Acceptance Criteria

Data is reconciled and traceable; every rule links to a typology; documented logic matches production behavior; outputs are reproducible; suppressions are retained and tested; ML is explainable and monitored; alerts contain investigator-ready evidence; approvals are complete.

## 19. Production-Readiness Checklist

All source feeds reconciled, rulebook approved, production configuration verified, independent replication complete, ML validation complete where applicable, UAT passed, runbooks tested, monitoring active, investigator training complete, and go-live approvals recorded.

## 20. Open Decisions And Required Client Inputs

Actual source systems, products, legal entities, jurisdictions, transaction volumes, operational capacity, case platform, risk appetite, thresholds, suppression policy, ML use policy, data retention, and regulatory interpretation require client confirmation.
