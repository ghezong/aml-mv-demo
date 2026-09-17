from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_json_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def load_rule_config(path: str | Path | None = None) -> dict[str, Any]:
    return load_json_config(path or CONFIG_DIR / "rules.json")


def load_suppression_config(path: str | Path | None = None) -> dict[str, Any]:
    return load_json_config(path or CONFIG_DIR / "suppressions.json")


def load_risk_indicator_config(path: str | Path | None = None) -> dict[str, Any]:
    return load_json_config(path or CONFIG_DIR / "risk_indicators.json")


def rule_by_id(rule_config: dict[str, Any], rule_id: str) -> dict[str, Any]:
    for rule in rule_config["rules"]:
        if rule["rule_id"] == rule_id:
            return rule
    raise KeyError(f"Rule {rule_id} is not present in configured rule set")


def active_rule_ids(rule_config: dict[str, Any]) -> set[str]:
    return {rule["rule_id"] for rule in rule_config["rules"] if rule.get("status") == "demo_active"}
