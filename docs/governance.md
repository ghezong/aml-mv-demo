# Governance And Operating Model

## Three Lines Of Defense

| Function | Role |
|---|---|
| First line operations | Investigate alerts, capture dispositions, manage case SLAs, identify workflow defects |
| Second line AML compliance | Own typologies, rules, thresholds, policies, SAR decisions, and monitoring oversight |
| Second line model risk | Validate CRR and ML ARR methodology, implementation, monitoring, and limitations |
| Technology and data | Implement controlled code, data pipelines, access, lineage, resilience, rollback |
| Internal audit | Independently test governance, controls, evidence, and regulatory readiness |

## Change Classification

| Change Type | Examples | Approval |
|---|---|---|
| Non-material | Documentation clarification, dashboard label | Rule/model owner |
| Parameter | Threshold, cooldown, segment assignment | AML compliance and change authority |
| Logic | Eligibility, feature calculation, suppression criteria | AML, technology, validation |
| Model | Feature set, algorithm, labels, training data | Model owner, model risk, AML |
| Emergency | Urgent legal, regulatory, outage, or severe control gap | Expedited approval with retrospective validation |

## Feedback Governance

Investigator dispositions, QA findings, SAR referrals, and confirmed outcomes are feedback signals. They must be governed because they can shape tuning and ML labels. Controls include a disposition taxonomy, QA calibration, label maturity windows, issue escalation, and prohibition of uncontrolled circular feedback into CRR or suppression decisions.
