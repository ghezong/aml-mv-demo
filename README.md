# AML Rule Engine and Model Validation Demo

This repository is a synthetic, public-safe portfolio demo for a sophisticated Anti-Money Laundering (AML) rule engine and model validation program. It does not contain confidential information, production logic, client data, proprietary thresholds, or institution-specific controls.

The demo focuses on the problem being solved: designing, validating, and governing a risk-based AML monitoring capability that integrates Customer Risk Rating (CRR), deterministic Transaction Monitoring (TM) rules, Machine Learning Alert Risk Rating (ML ARR), alert consolidation, investigation workflow, and examiner-ready evidence.

## Problem Statement

Fintech and payments environments often operate across multiple products, payment rails, geographies, customer segments, and data platforms. AML monitoring programs must prove that rules and models are reasonably designed, accurately implemented, risk-based, explainable, reproducible, and governed. A frequent validation challenge is that documented rulebooks, approved configurations, source code, data mappings, and production alert outcomes do not always align.

This demo shows how to structure an AML rule engine validation program that independently reproduces key logic, preserves below-the-line outcomes, separates detection from prioritization and suppression, and uses ML only in a controlled, explainable alert prioritization role.

## What This Demo Includes

| Area | Artifact |
|---|---|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| Governance and validation | [docs/model_validation_framework.md](docs/model_validation_framework.md), [docs/governance.md](docs/governance.md) |
| Data model | [docs/data_dictionary.md](docs/data_dictionary.md) |
| Rule inventory | [docs/rulebook.md](docs/rulebook.md) |
| Synthetic datasets | [data/synthetic/customers.csv](data/synthetic/customers.csv), [data/synthetic/accounts.csv](data/synthetic/accounts.csv), [data/synthetic/transactions.csv](data/synthetic/transactions.csv) |
| Source code | [src/aml_mv_demo](src/aml_mv_demo) |
| Notebook | [notebooks/aml_model_validation_demo.ipynb](notebooks/aml_model_validation_demo.ipynb) |
| Tests | [tests](tests) |

## Approach

1. Generate synthetic customers, accounts, transactions, and investigator outcomes.
2. Compute activation and behavioral CRR with reason codes.
3. Build point-in-time customer and transaction features.
4. Execute deterministic AML rules with separate eligibility, trigger, suppression, and alert decision fields.
5. Train a simple ML ARR model on synthetic alert outcomes to prioritize alerts without autonomously closing regulatory alerts.
6. Validate outputs through unit tests, independent replication checks, lineage fields, and governance documentation.

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python scripts\run_demo.py
pytest
```

The demo writes generated outputs to `outputs/`, including CRR results, rule results, alerts, and ML-scored alerts.

## Core Design Choices

| Design Choice | Rationale |
|---|---|
| Synthetic-only data | Safe for public portfolio use |
| Deterministic TM generates alerts | Preserves regulatory traceability |
| ML ARR ranks generated alerts | Improves prioritization while keeping human review |
| Below-the-line retention | Supports false-negative and suppression testing |
| Point-in-time features | Reduces leakage and improves reproducibility |
| Rule/model version fields | Supports audit, rollback, and examiner evidence |

## AI/ML Used

The ML ARR component uses a transparent logistic regression classifier trained on synthetic investigator outcome labels. It is intentionally simple and explainable for model validation demonstration purposes. The model produces alert risk scores, priority bands, and top contributing features. It is not intended to represent a production-ready typology discovery model.

## Results Demonstrated

The runnable demo produces evidence for:

- CRR score and reason-code generation
- TM rule triggering and suppression traceability
- Alert consolidation by customer and rule family
- ML-based alert ranking with calibrated score bands
- Validation tests for rule boundaries, reproducibility, and leakage controls
- Governance-ready documentation structure

Because this is synthetic data, results are illustrative and should not be interpreted as regulatory conclusions or production performance claims.

## What I Would Do Differently In A Production Program

- Use institution-specific risk assessment, typology inventory, and policy decisions.
- Validate actual source-to-target mappings and production code paths independently.
- Perform historical replay over mature production outcomes.
- Conduct deeper false-negative analysis using below-the-line populations and QA-confirmed cases.
- Expand model validation to include stability, fairness, calibration, drift, and challenger models by segment.
- Integrate case-management workflow evidence and investigator QA results directly into governed feedback loops.

## Confidentiality Note

All data, thresholds, names, transaction patterns, and outcomes in this repository are synthetic and illustrative. The project is designed to demonstrate architecture, validation thinking, documentation depth, and implementation discipline without exposing confidential work product.
