from __future__ import annotations

import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.features.baseline.schemas import BaselineCheckWrite, BaselineRuleDefinition

DEFAULT_RULES_PATH = Path(__file__).with_name("rules_v1.json")
MatcherHandler = Callable[[dict[str, Any], dict[str, Any]], tuple[str, str]]


class BaselineRuleEngine:
    def __init__(
        self,
        rules: list[BaselineRuleDefinition] | None = None,
        *,
        rules_path: Path | None = None,
        operator_handlers: dict[str, MatcherHandler] | None = None,
    ) -> None:
        self.rules = rules or load_rules(rules_path)
        self.operator_handlers = self._default_operator_handlers()
        if operator_handlers:
            for operator, handler in operator_handlers.items():
                self.register_operator(operator, handler)

    def evaluate_linux_inspection(self, inspection: dict[str, Any]) -> list[BaselineCheckWrite]:
        return self._evaluate(device_type="linux", inspection=inspection)

    def evaluate_switch_inspection(self, inspection: dict[str, Any]) -> list[BaselineCheckWrite]:
        return self._evaluate(device_type="switch", inspection=inspection)

    def _evaluate(self, *, device_type: str, inspection: dict[str, Any]) -> list[BaselineCheckWrite]:
        results: list[BaselineCheckWrite] = []
        for rule in self.rules:
            if rule.device_type != device_type:
                continue
            status, detail = self._evaluate_rule(rule, inspection)
            results.append(
                BaselineCheckWrite(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    device_type=rule.device_type,
                    risk_level=rule.risk_level,
                    check_method=rule.check_method,
                    judge_logic=rule.judge_logic,
                    remediation=rule.remediation,
                    status=status,
                    detail=detail,
                    raw_matcher=rule.matcher,
                )
            )
        return results

    def _evaluate_rule(self, rule: BaselineRuleDefinition, inspection: dict[str, Any]) -> tuple[str, str]:
        operator = str(rule.matcher.get("operator", "")).strip().lower()
        handler = self.operator_handlers.get(operator)
        if handler is not None:
            return handler(rule.matcher, inspection)
        return "unknown", f"Unsupported matcher operator: {operator}"

    def register_operator(self, operator: str, handler: MatcherHandler) -> None:
        self.operator_handlers[operator.strip().lower()] = handler

    def _default_operator_handlers(self) -> dict[str, MatcherHandler]:
        return {
            "equals": self._evaluate_equals,
            "firewall_enabled": self._evaluate_firewall_enabled,
            "time_sync_enabled": self._evaluate_time_sync_enabled,
            "auditd_enabled": self._evaluate_auditd_enabled,
            "contains_any": self._evaluate_contains_any,
            "explicit_match": self._evaluate_explicit_match,
        }

    def _evaluate_equals(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        actual = self._extract_value(inspection, str(matcher.get("source", "")))
        if actual is None:
            return "unknown", f"Missing source value: {matcher.get('source')}"
        actual_text = str(actual).strip()
        expected = str(matcher.get("expected", "")).strip()
        if matcher.get("case_insensitive", False):
            actual_cmp = actual_text.lower()
            expected_cmp = expected.lower()
        else:
            actual_cmp = actual_text
            expected_cmp = expected
        if actual_cmp == expected_cmp:
            return "pass", f"Observed `{matcher.get('source')}` = {actual_text}"
        return "fail", f"Observed `{matcher.get('source')}` = {actual_text}, expected {expected}"

    def _evaluate_firewall_enabled(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        firewall = inspection.get("firewall_status")
        if not isinstance(firewall, dict):
            return "unknown", "Firewall raw output not available"
        firewalld = str(firewall.get("firewalld") or "").strip().lower()
        ufw = str(firewall.get("ufw") or "").strip().lower()
        iptables_rules = firewall.get("iptables_rules") or []
        effective_iptables_rules = [
            str(line).strip() for line in iptables_rules if str(line).strip() and str(line).strip().lower() != "unavailable"
        ]
        if firewalld == "active":
            return "pass", "firewalld is active"
        if ufw.startswith("status: active") or ufw == "active":
            return "pass", "ufw is active"
        if effective_iptables_rules:
            return "pass", f"iptables returned {len(effective_iptables_rules)} non-empty rule lines"
        if any(value for value in [firewalld, ufw]):
            return "fail", f"firewalld={firewalld or 'unknown'}, ufw={ufw or 'unknown'}, iptables has no effective rules"
        return "unknown", "Firewall raw output is incomplete"

    def _evaluate_time_sync_enabled(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        time_sync = inspection.get("time_sync_status")
        if not isinstance(time_sync, dict):
            return "unknown", "Time sync raw output not available"
        timedatectl = str(time_sync.get("timedatectl") or "")
        service_status = str(time_sync.get("service_status") or "").strip().lower()
        lowered = timedatectl.lower()
        if "system clock synchronized: yes" in lowered or "ntp service: active" in lowered:
            return "pass", "timedatectl reports time sync enabled"
        if service_status == "active":
            return "pass", "Time sync service is active"
        if timedatectl or service_status:
            return "fail", f"timedatectl/service indicates sync is not enabled: service={service_status or 'unknown'}"
        return "unknown", "Time sync raw output is incomplete"

    def _evaluate_auditd_enabled(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        auditd = inspection.get("auditd_status")
        if not isinstance(auditd, dict):
            return "unknown", "auditd raw output not available"
        service_status = str(auditd.get("service_status") or "").strip().lower()
        auditctl_status = str(auditd.get("auditctl_status") or "").lower()
        if service_status == "active" or "enabled 1" in auditctl_status:
            return "pass", "auditd is active"
        if service_status or auditctl_status:
            return "fail", f"auditd is not active: service={service_status or 'unknown'}"
        return "unknown", "auditd raw output is incomplete"

    def _evaluate_contains_any(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        source = str(matcher.get("source", ""))
        raw_value = self._extract_value(inspection, source)
        if raw_value is None:
            return "unknown", f"Missing source value: {source}"
        text = str(raw_value)
        patterns = [str(item) for item in matcher.get("patterns", [])]
        for pattern in patterns:
            if self._match_pattern(text, pattern, bool(matcher.get("regex", False))):
                return "pass", f"Matched pattern `{pattern}`"
        return matcher.get("default_status", "fail"), f"No pattern matched in `{source}`"

    def _evaluate_explicit_match(self, matcher: dict[str, Any], inspection: dict[str, Any]) -> tuple[str, str]:
        source = str(matcher.get("source", ""))
        raw_value = self._extract_value(inspection, source)
        if raw_value is None:
            return "unknown", f"Missing source value: {source}"
        text = str(raw_value)
        regex = bool(matcher.get("regex", False))
        pass_patterns = [str(item) for item in matcher.get("pass_patterns", [])]
        fail_patterns = [str(item) for item in matcher.get("fail_patterns", [])]
        for pattern in pass_patterns:
            if self._match_pattern(text, pattern, regex):
                return "pass", f"Matched pass pattern `{pattern}`"
        for pattern in fail_patterns:
            if self._match_pattern(text, pattern, regex):
                return "fail", f"Matched fail pattern `{pattern}`"
        return matcher.get("default_status", "unknown"), f"No explicit pattern matched in `{source}`"

    def _extract_value(self, data: dict[str, Any], path: str) -> Any:
        if not path:
            return None
        current: Any = data
        for segment in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
            if current is None:
                return None
        return current

    def _match_pattern(self, text: str, pattern: str, regex: bool) -> bool:
        if regex:
            return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None
        return pattern.lower() in text.lower()


@lru_cache
def _load_rules_from_path(path: str) -> tuple[BaselineRuleDefinition, ...]:
    raw_rules = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(BaselineRuleDefinition.model_validate(item) for item in raw_rules)


def load_rules(rules_path: Path | None = None) -> list[BaselineRuleDefinition]:
    selected_path = (rules_path or DEFAULT_RULES_PATH).resolve()
    return list(_load_rules_from_path(str(selected_path)))
