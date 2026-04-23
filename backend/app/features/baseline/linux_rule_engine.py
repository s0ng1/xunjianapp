from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.features.baseline.linux_rule_collector import LinuxCollectCommand
from app.features.baseline.schemas import BaselineCheckWrite

DEFAULT_LINUX_RULES_PATH = Path(__file__).with_name("rules").joinpath("linux_mlps_level3_v1.json")


class LinuxRuleCollectDefinition(BaseModel):
    type: str
    command: str | None = None
    cache_key: str | None = None


class LinuxRuleParseDefinition(BaseModel):
    type: str
    logic: str | None = None
    pattern: str | None = None
    group: int = 1
    flags: list[str] = Field(default_factory=list)


class LinuxRuleExpectDefinition(BaseModel):
    operator: str
    value: Any = None


class LinuxRuleResultDefinition(BaseModel):
    pass_message: str
    fail_message: str
    unknown_message: str = "当前巡检数据不足，无法自动判断。"
    not_applicable_message: str = "当前规则不适用。"


class LinuxBaselineRuleDefinition(BaseModel):
    id: str
    name: str
    category: str
    target_type: str
    severity: str
    check_type: str
    collect: LinuxRuleCollectDefinition | None = None
    parse: LinuxRuleParseDefinition | None = None
    expect: LinuxRuleExpectDefinition | None = None
    result: LinuxRuleResultDefinition
    remediation: str
    manual_check_hint: str | None = None


@dataclass(slots=True)
class ParsedValue:
    value: Any
    evidence: str
    unknown_reason: str | None = None


ASSIGNMENT_TOKEN_RE = re.compile(r"(?P<key>[a-z_][a-z0-9_]*)\s*=\s*(?P<value>[^\s#]+)", re.IGNORECASE)
PACKAGE_UPDATE_APT_RE = re.compile(
    r"^(?P<name>[a-z0-9][a-z0-9+_.:/@-]*)\s+(?P<version>[^\s]+)(?:\s+(?P<arch>[^\s]+))?\s+\[upgradable from:\s*(?P<from>[^\]]+)\]$",
    re.IGNORECASE,
)
PACKAGE_UPDATE_INST_RE = re.compile(
    r"^inst\s+(?P<name>[^\s]+)\s+\[(?P<from>[^\]]+)\]\s+\((?P<version>[^ )]+)",
    re.IGNORECASE,
)
PACKAGE_UPDATE_YUM_RE = re.compile(
    r"^(?P<name>[a-z0-9][a-z0-9+_.:/@-]*)\s+(?P<version>[0-9][^\s]*)\s+\S+",
    re.IGNORECASE,
)
PACKAGE_UPDATE_ZYPPER_RE = re.compile(
    r"^\S+\s+\|\s+\S+\s+\|\s+(?P<name>[^\s|]+)\s+\|\s+(?P<current>[^\s|]+)\s+\|\s+(?P<available>[^\s|]+)\s+\|\s+[^\s|]+$",
    re.IGNORECASE,
)
PACKAGE_UPDATE_INLINE_RE = re.compile(
    r"\bupdate\s+(?P<name>[a-z0-9][a-z0-9+_.:/@-]*)\s+(?P<version>[0-9][^\s|]*)",
    re.IGNORECASE,
)


class LinuxBaselineRuleEngine:
    def __init__(self, *, rules_path: Path | None = None) -> None:
        self.rules = load_linux_rules(rules_path)

    def build_collection_plan(self) -> list[LinuxCollectCommand]:
        plan: dict[str, LinuxCollectCommand] = {}
        for rule in self.rules:
            if rule.collect is None:
                continue
            if rule.collect.type not in {"command", "config"}:
                continue
            if not rule.collect.command or not rule.collect.cache_key:
                continue
            plan[rule.collect.cache_key] = LinuxCollectCommand(
                key=rule.collect.cache_key,
                collect_type=rule.collect.type,
                command=rule.collect.command,
            )
        return list(plan.values())

    def evaluate_linux_inspection(self, inspection: dict[str, Any]) -> list[BaselineCheckWrite]:
        return [self._evaluate_rule(rule, inspection) for rule in self.rules if rule.target_type == "linux"]

    def _evaluate_rule(self, rule: LinuxBaselineRuleDefinition, inspection: dict[str, Any]) -> BaselineCheckWrite:
        if rule.check_type == "manual":
            detail = rule.result.unknown_message
            evidence = rule.manual_check_hint or "该项无法通过当前巡检命令自动确认。"
            return self._build_result(
                rule=rule,
                status="unknown",
                detail=detail,
                evidence=evidence,
            )

        if rule.check_type == "not_applicable":
            detail = rule.result.not_applicable_message
            evidence = "该要求不属于当前 Linux 服务器自动巡检范围。"
            return self._build_result(
                rule=rule,
                status="not_applicable",
                detail=detail,
                evidence=evidence,
            )

        parsed = self._parse_rule(rule, inspection)
        if parsed.unknown_reason is not None:
            return self._build_result(
                rule=rule,
                status="unknown",
                detail=rule.result.unknown_message,
                evidence=parsed.evidence or parsed.unknown_reason,
            )

        status = self._compare(rule.expect, parsed.value)
        if status == "pass":
            detail = rule.result.pass_message
        elif status == "fail":
            detail = rule.result.fail_message
        else:
            detail = rule.result.unknown_message
        return self._build_result(
            rule=rule,
            status=status,
            detail=detail,
            evidence=parsed.evidence,
        )

    def _build_result(
        self,
        *,
        rule: LinuxBaselineRuleDefinition,
        status: str,
        detail: str,
        evidence: str,
    ) -> BaselineCheckWrite:
        return BaselineCheckWrite(
            rule_id=rule.id,
            rule_name=rule.name,
            device_type=rule.target_type,
            category=rule.category,
            risk_level=rule.severity,
            check_type=rule.check_type,
            check_method=rule.collect.type if rule.collect is not None else rule.check_type,
            judge_logic=self._build_judge_logic(rule),
            remediation=rule.remediation,
            status=status,
            detail=detail,
            evidence=evidence,
            manual_check_hint=rule.manual_check_hint,
            raw_matcher=rule.model_dump(mode="json"),
        )

    def _build_judge_logic(self, rule: LinuxBaselineRuleDefinition) -> str:
        if rule.expect is None:
            return f"{rule.check_type} rule"
        value = rule.expect.value
        return f"{rule.expect.operator} {value!r}" if value is not None else rule.expect.operator

    def _parse_rule(self, rule: LinuxBaselineRuleDefinition, inspection: dict[str, Any]) -> ParsedValue:
        if rule.collect is None or rule.parse is None:
            return ParsedValue(value=None, evidence="", unknown_reason="Rule definition is incomplete")

        collected_data = inspection.get("collected_data") or {}
        item = collected_data.get(rule.collect.cache_key or "")
        if not isinstance(item, dict):
            return ParsedValue(value=None, evidence="", unknown_reason="采集结果缺失")

        if item.get("error"):
            return ParsedValue(value=None, evidence=str(item["error"]), unknown_reason="采集命令执行失败")

        raw_output = self._get_collected_output(item)
        if rule.parse.type == "regex":
            return self._parse_regex(raw_output, rule.parse)
        if rule.parse.type == "json":
            return self._parse_json(raw_output)
        if rule.parse.type == "logic":
            return self._parse_logic(rule.parse.logic or "", raw_output, inspection)
        return ParsedValue(value=None, evidence="", unknown_reason=f"Unsupported parse type: {rule.parse.type}")

    def _get_collected_output(self, item: dict[str, Any]) -> str:
        normalized_output = item.get("normalized_output")
        if normalized_output is not None:
            return str(normalized_output)
        return str(item.get("raw_output") or "")

    def _parse_regex(self, raw_output: str, parse: LinuxRuleParseDefinition) -> ParsedValue:
        if not parse.pattern:
            return ParsedValue(value=None, evidence="", unknown_reason="regex pattern is missing")
        flags = 0
        if "ignorecase" in parse.flags:
            flags |= re.IGNORECASE
        if "multiline" in parse.flags:
            flags |= re.MULTILINE
        match = re.search(parse.pattern, raw_output, flags=flags)
        if match is None:
            return ParsedValue(value="", evidence=raw_output.strip())
        value = match.group(parse.group).strip()
        return ParsedValue(value=value, evidence=f"提取结果：{value}")

    def _parse_json(self, raw_output: str) -> ParsedValue:
        try:
            value = json.loads(raw_output)
        except json.JSONDecodeError:
            return ParsedValue(value=None, evidence=raw_output.strip(), unknown_reason="JSON 解析失败")
        return ParsedValue(value=value, evidence=json.dumps(value, ensure_ascii=False))

    def _parse_logic(self, logic: str, raw_output: str, inspection: dict[str, Any]) -> ParsedValue:
        handlers = {
            "line_list": self._logic_line_list,
            "integer": self._logic_integer,
            "telnet_disabled": self._logic_telnet_disabled,
            "ssh_service_enabled": self._logic_ssh_service_enabled,
            "auditd_enabled": self._logic_auditd_enabled,
            "firewall_enabled": self._logic_firewall_enabled,
            "uid0_non_root_accounts": self._logic_uid0_non_root_accounts,
            "sudo_nopasswd_risk": self._logic_sudo_nopasswd_risk,
            "secure_passwd_shadow_permissions": self._logic_secure_passwd_shadow_permissions,
            "selinux_enforcing": self._logic_selinux_enforcing,
            "risky_ports_present": self._logic_risky_ports_present,
            "pam_pwquality": self._logic_pam_pwquality,
            "faillock_configured": self._logic_faillock_configured,
            "audit_log_protection": self._logic_audit_log_protection,
            "audit_process_protection": self._logic_audit_process_protection,
            "suspicious_enabled_services": self._logic_suspicious_enabled_services,
            "hosts_access_restriction": self._logic_hosts_access_restriction,
            "package_updates": self._logic_package_updates,
            "ids_presence": self._logic_ids_presence,
            "interactive_system_accounts": self._logic_interactive_system_accounts,
            "interactive_user_accounts": self._logic_interactive_user_accounts,
        }
        handler = handlers.get(logic)
        if handler is None:
            return ParsedValue(value=None, evidence="", unknown_reason=f"Unsupported logic parser: {logic}")
        return handler(raw_output, inspection)

    def _compare(self, expect: LinuxRuleExpectDefinition | None, actual: Any) -> str:
        if expect is None:
            return "unknown"
        operator = expect.operator
        if operator == "empty":
            return "pass" if self._is_empty(actual) else "fail"
        if operator == "not_empty":
            return "pass" if not self._is_empty(actual) else "fail"
        if operator == "equals":
            return "pass" if actual == expect.value else "fail"
        if operator == "less_or_equal":
            return "pass" if isinstance(actual, (int, float)) and actual <= expect.value else "fail"
        if operator == "greater_or_equal":
            return "pass" if isinstance(actual, (int, float)) and actual >= expect.value else "fail"
        if operator == "bool_is":
            return "pass" if bool(actual) is bool(expect.value) else "fail"
        if operator == "set_equals":
            actual_set = sorted(str(item) for item in (actual or []))
            expected_set = sorted(str(item) for item in (expect.value or []))
            return "pass" if actual_set == expected_set else "fail"
        return "unknown"

    def _is_empty(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return str(value).strip() == ""

    def _extract_assignment_tokens(self, raw_output: str) -> dict[str, str]:
        assignments: dict[str, str] = {}
        for match in ASSIGNMENT_TOKEN_RE.finditer(raw_output):
            assignments[match.group("key").lower()] = match.group("value").strip("\"'")
        return assignments

    def _active_config_lines(self, raw_output: str) -> list[str]:
        lines: list[str] = []
        for line in raw_output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("__") and stripped.endswith("__"):
                continue
            lines.append(stripped)
        return lines

    def _to_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _logic_line_list(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        evidence = "未发现命中项" if not lines else f"命中项：{', '.join(lines)}"
        return ParsedValue(value=lines, evidence=evidence)

    def _logic_integer(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        text = raw_output.strip()
        if not text:
            return ParsedValue(value=None, evidence="", unknown_reason="未采集到数值")
        match = re.search(r"-?\d+", text)
        if match is None:
            return ParsedValue(value=None, evidence=text, unknown_reason="未能解析整数")
        value = int(match.group(0))
        return ParsedValue(value=value, evidence=f"当前值：{value}")

    def _logic_telnet_disabled(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip().lower() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=None, evidence="", unknown_reason="未获取 Telnet 服务状态")
        enabled = lines[0]
        active = lines[1] if len(lines) > 1 else "unknown"
        is_disabled = enabled not in {"enabled", "static"} and active != "active"
        evidence = f"enabled={enabled}, active={active}"
        return ParsedValue(value=is_disabled, evidence=evidence)

    def _logic_ssh_service_enabled(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip().lower() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=None, evidence="", unknown_reason="未获取 SSH 服务状态")
        enabled = lines[0]
        active = lines[1] if len(lines) > 1 else "unknown"
        is_enabled = enabled in {"enabled", "static", "alias", "indirect"} or active == "active"
        evidence = f"enabled={enabled}, active={active}"
        return ParsedValue(value=is_enabled, evidence=evidence)

    def _logic_auditd_enabled(self, _: str, inspection: dict[str, Any]) -> ParsedValue:
        auditd = inspection.get("auditd_status")
        if not isinstance(auditd, dict):
            return ParsedValue(value=None, evidence="", unknown_reason="未返回 auditd 状态")
        service_status = str(auditd.get("service_status") or "").strip().lower()
        auditctl_status = str(auditd.get("auditctl_status") or "").strip().lower()
        is_enabled = service_status == "active" or "enabled 1" in auditctl_status or "enabled 2" in auditctl_status
        evidence = f"service={service_status or 'unknown'}, auditctl={auditctl_status or 'unknown'}"
        return ParsedValue(value=is_enabled, evidence=evidence)

    def _logic_firewall_enabled(self, _: str, inspection: dict[str, Any]) -> ParsedValue:
        firewall = inspection.get("firewall_status")
        if not isinstance(firewall, dict):
            return ParsedValue(value=None, evidence="", unknown_reason="未返回防火墙状态")
        firewalld = str(firewall.get("firewalld") or "").strip().lower()
        ufw = str(firewall.get("ufw") or "").strip().lower()
        iptables_rules = [str(line).strip() for line in firewall.get("iptables_rules") or [] if str(line).strip()]
        is_enabled = firewalld == "active" or ufw.startswith("status: active") or ufw == "active" or bool(iptables_rules)
        evidence = f"firewalld={firewalld or 'unknown'}, ufw={ufw or 'unknown'}, iptables_rules={len(iptables_rules)}"
        return ParsedValue(value=is_enabled, evidence=evidence)

    def _logic_uid0_non_root_accounts(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        accounts = [line.strip() for line in raw_output.splitlines() if line.strip() and line.strip() != "root"]
        evidence = "仅 root 具备 UID 0" if not accounts else f"额外 UID 0 账户：{', '.join(accounts)}"
        return ParsedValue(value=accounts, evidence=evidence)

    def _logic_sudo_nopasswd_risk(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        evidence = "未发现高风险 sudo 授权" if not lines else f"高风险授权：{' | '.join(lines[:5])}"
        return ParsedValue(value=lines, evidence=evidence)

    def _logic_secure_passwd_shadow_permissions(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        file_states: dict[str, tuple[int, str, str]] = {}
        for line in raw_output.splitlines():
            parts = line.split()
            if len(parts) != 4:
                continue
            path, mode, owner, group = parts
            if path in {"/etc/passwd", "/etc/shadow"} and mode.isdigit():
                file_states[path] = (int(mode), owner, group)
        passwd_state = file_states.get("/etc/passwd")
        shadow_state = file_states.get("/etc/shadow")
        if passwd_state is None or shadow_state is None:
            return ParsedValue(value=None, evidence=raw_output.strip(), unknown_reason="文件权限信息不完整")
        passwd_ok = passwd_state[0] <= 644 and passwd_state[1] == "root"
        shadow_ok = shadow_state[0] <= 640 and shadow_state[1] == "root"
        evidence = (
            f"/etc/passwd={passwd_state[0]} {passwd_state[1]}:{passwd_state[2]}, "
            f"/etc/shadow={shadow_state[0]} {shadow_state[1]}:{shadow_state[2]}"
        )
        return ParsedValue(value=passwd_ok and shadow_ok, evidence=evidence)

    def _logic_selinux_enforcing(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        text = raw_output.strip()
        if not text:
            return ParsedValue(value=False, evidence="SELinux 状态输出为空")
        lowered = text.lower()
        if lowered in {"unavailable", "0", "permissive"}:
            return ParsedValue(value=False, evidence=f"SELinux={text}")
        if lowered in {"1", "enforcing"}:
            return ParsedValue(value=True, evidence=f"SELinux={text}")
        if "disabled" in lowered:
            return ParsedValue(value=False, evidence=f"SELinux={text}")
        if "selinux=enforcing" in lowered or ("current mode:" in lowered and "enforcing" in lowered):
            return ParsedValue(value=True, evidence=f"SELinux={text}")
        if "selinux=permissive" in lowered or ("current mode:" in lowered and "permissive" in lowered):
            return ParsedValue(value=False, evidence=f"SELinux={text}")
        if "enforcing" in lowered:
            return ParsedValue(value=True, evidence=f"SELinux={text}")
        if "permissive" in lowered:
            return ParsedValue(value=False, evidence=f"SELinux={text}")
        return ParsedValue(value=None, evidence=text, unknown_reason="SELinux 状态不明确")

    def _logic_risky_ports_present(self, _: str, inspection: dict[str, Any]) -> ParsedValue:
        open_ports = ((inspection.get("open_ports") or {}).get("ports") or []) if isinstance(inspection.get("open_ports"), dict) else []
        risky_ports = {"21", "23", "69", "111", "135", "139", "445", "2049", "3306", "5432", "6379", "27017"}
        findings: list[str] = []
        for entry in open_ports:
            port = str(entry.get("port") or "").strip()
            address = str(entry.get("local_address") or "").strip()
            if port in risky_ports and address in {"0.0.0.0", "::", "[::]"}:
                findings.append(f"{port}@{address}")
        evidence = "未发现高危对外监听端口" if not findings else f"高危监听端口：{', '.join(findings)}"
        return ParsedValue(value=findings, evidence=evidence)

    def _logic_pam_pwquality(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lowered = raw_output.lower()
        if not lowered.strip():
            return ParsedValue(value=False, evidence="未检测到 PAM 复杂度配置")
        has_module = "pam_pwquality.so" in lowered or "pam_cracklib.so" in lowered
        assignments = self._extract_assignment_tokens(lowered)
        minlen = self._to_int(assignments.get("minlen"))
        minclass = self._to_int(assignments.get("minclass"))
        credit_keys = [key for key in ("dcredit", "ucredit", "lcredit", "ocredit") if key in assignments]
        has_policy = (
            (minlen is not None and minlen >= 8)
            or (minclass is not None and minclass >= 3)
            or len(credit_keys) >= 3
        )
        evidence = ", ".join(
            [
                f"module={'yes' if has_module else 'no'}",
                f"minlen={minlen if minlen is not None else 'missing'}",
                f"minclass={minclass if minclass is not None else 'missing'}",
                f"credits={','.join(sorted(credit_keys)) if credit_keys else 'missing'}",
            ]
        )
        return ParsedValue(value=has_module and has_policy, evidence=evidence)

    def _logic_faillock_configured(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lowered = raw_output.lower()
        if not lowered.strip():
            return ParsedValue(value=False, evidence="未检测到登录失败锁定配置")
        has_module = "pam_faillock.so" in lowered or "pam_tally2.so" in lowered
        assignments = self._extract_assignment_tokens(lowered)
        deny = self._to_int(assignments.get("deny"))
        unlock_time = self._to_int(assignments.get("unlock_time"))
        fail_interval = self._to_int(assignments.get("fail_interval"))
        has_threshold = deny is not None and (unlock_time is not None or fail_interval is not None)
        evidence = (
            f"module={'yes' if has_module else 'no'}, "
            f"deny={deny if deny is not None else 'missing'}, "
            f"unlock_time={unlock_time if unlock_time is not None else 'missing'}, "
            f"fail_interval={fail_interval if fail_interval is not None else 'missing'}"
        )
        return ParsedValue(value=has_module and has_threshold, evidence=evidence)

    def _logic_audit_log_protection(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=False, evidence="未采集到审计日志目录或文件权限")
        if len(lines) == 1 and lines[0].lower() == "unavailable":
            return ParsedValue(value=False, evidence=lines[0])
        permissive = [line for line in lines if re.search(r"\s(7[0-7]{2}|6[5-7][0-7])\s", f" {line} ")]
        evidence = raw_output.strip()
        return ParsedValue(value=not permissive, evidence=evidence)

    def _logic_audit_process_protection(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lowered = raw_output.lower()
        if not lowered.strip():
            return ParsedValue(value=False, evidence="未采集到 auditctl 保护状态")
        if lowered.strip() == "unavailable":
            return ParsedValue(value=False, evidence=raw_output.strip())
        if "enabled 2" in lowered:
            return ParsedValue(value=True, evidence=raw_output.strip())
        if "enabled 0" in lowered:
            return ParsedValue(value=False, evidence=raw_output.strip())
        if "enabled 1" in lowered:
            return ParsedValue(value=False, evidence=raw_output.strip())
        return ParsedValue(value=None, evidence=raw_output.strip(), unknown_reason="未能确认 audit 进程保护状态")

    def _logic_suspicious_enabled_services(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        suspicious = []
        for line in raw_output.splitlines():
            lowered = line.strip().lower()
            if not lowered:
                continue
            if any(name in lowered for name in ["telnet", "tftp", "rsh", "rexec", "vsftpd", "ftp", "nfs", "rpcbind"]):
                suspicious.append(line.strip())
        evidence = "未发现明显多余高风险服务" if not suspicious else f"可疑启用服务：{' | '.join(suspicious[:5])}"
        return ParsedValue(value=suspicious, evidence=evidence)

    def _logic_hosts_access_restriction(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        active_lines = self._active_config_lines(raw_output)
        if not active_lines:
            return ParsedValue(value=False, evidence="未检测到 hosts.allow/deny 或 SSH 管理源限制配置")

        lowered_lines = [line.lower() for line in active_lines]
        has_hosts_allow = any(line.startswith(("sshd:", "in.sshd:", "all:")) for line in lowered_lines)
        has_hosts_deny = any("all: all" in line or "sshd: all" in line for line in lowered_lines)
        has_sshd_restriction = any(
            re.match(r"(allowusers|allowgroups|denyusers|denygroups|listenaddress)\b", line) is not None
            or line.startswith("match address")
            for line in lowered_lines
        )
        evidence = " | ".join(active_lines[:10])
        if has_sshd_restriction or (has_hosts_allow and has_hosts_deny):
            return ParsedValue(value=True, evidence=evidence)
        return ParsedValue(value=False, evidence=evidence)

    def _logic_package_updates(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        text = raw_output.strip()
        if not text:
            return ParsedValue(value=None, evidence="", unknown_reason="未采集到补丁更新状态")
        lowered = text.lower()
        if "0 upgraded" in lowered or "no packages marked for update" in lowered or "security: 0" in lowered:
            return ParsedValue(value=True, evidence="未发现待安装更新")
        update_entries = self._extract_package_update_entries(text)
        if update_entries:
            return ParsedValue(value=False, evidence=" | ".join(update_entries[:10]))
        if "listing... done" in lowered and "[upgradable from:" not in lowered:
            return ParsedValue(value=True, evidence="未发现待安装更新")
        if any(token in lowered for token in ["upgradable", "updates available", "available package updates", "security updates"]):
            return ParsedValue(value=False, evidence=self._compact_package_update_text(text))
        compact_text = self._compact_package_update_text(text)
        return ParsedValue(value=None, evidence=compact_text, unknown_reason="补丁状态输出格式未识别")

    def _extract_package_update_entries(self, raw_output: str) -> list[str]:
        entries: list[str] = []
        seen: set[str] = set()

        for line in raw_output.splitlines():
            entry = self._parse_package_update_entry(line)
            if entry is None or entry in seen:
                continue
            seen.add(entry)
            entries.append(entry)

        for match in PACKAGE_UPDATE_INLINE_RE.finditer(raw_output):
            entry = f"{match.group('name')} -> {match.group('version')}"
            if entry in seen:
                continue
            seen.add(entry)
            entries.append(entry)

        return entries

    def _parse_package_update_entry(self, line: str) -> str | None:
        cleaned = re.sub(r"\s+", " ", line.strip())
        if not cleaned:
            return None

        lowered = cleaned.lower()
        if (
            lowered.startswith("listing")
            or lowered.startswith("[")
            or re.search(r"\beta\b", cleaned, re.IGNORECASE)
            or re.search(r"\bb/s\b", cleaned, re.IGNORECASE)
        ):
            return None

        apt_match = PACKAGE_UPDATE_APT_RE.match(cleaned)
        if apt_match:
            name = apt_match.group("name")
            version = apt_match.group("version")
            arch = apt_match.group("arch")
            current_version = apt_match.group("from")
            label = f"{name} ({arch})" if arch and arch.isalnum() else name
            return f"{label} -> {version}（当前 {current_version}）"

        inst_match = PACKAGE_UPDATE_INST_RE.match(cleaned)
        if inst_match:
            return (
                f"{inst_match.group('name')} -> {inst_match.group('version')}"
                f"（当前 {inst_match.group('from')}）"
            )

        zypper_match = PACKAGE_UPDATE_ZYPPER_RE.match(cleaned)
        if zypper_match:
            return (
                f"{zypper_match.group('name')} -> {zypper_match.group('available')}"
                f"（当前 {zypper_match.group('current')}）"
            )

        yum_match = PACKAGE_UPDATE_YUM_RE.match(cleaned)
        if yum_match:
            return f"{yum_match.group('name')} -> {yum_match.group('version')}"

        return None

    def _compact_package_update_text(self, raw_output: str) -> str:
        parts = [re.sub(r"\s+", " ", line.strip()) for line in raw_output.splitlines() if line.strip()]
        if not parts:
            return raw_output.strip()
        return " | ".join(parts[:10])

    def _logic_ids_presence(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=None, evidence="未检测到明显 IDS/IPS 进程或服务", unknown_reason="未发现部署痕迹")
        return ParsedValue(value=True, evidence="检测到安全代理/IDS： " + " | ".join(lines[:5]))

    def _logic_interactive_system_accounts(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=[], evidence="未发现可直接登录的系统默认账户")
        return ParsedValue(value=lines, evidence="可登录系统账户： " + " | ".join(lines[:5]))

    def _logic_interactive_user_accounts(self, raw_output: str, _: dict[str, Any]) -> ParsedValue:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return ParsedValue(value=None, evidence="未发现普通交互账号", unknown_reason="未采集到可供人工确认的账号清单")
        return ParsedValue(value=None, evidence="当前交互账号： " + " | ".join(lines[:10]), unknown_reason="需要人工确认哪些属于多余账户")


@lru_cache
def _load_linux_rules(path: str) -> tuple[LinuxBaselineRuleDefinition, ...]:
    raw_rules = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(LinuxBaselineRuleDefinition.model_validate(item) for item in raw_rules)


def load_linux_rules(rules_path: Path | None = None) -> list[LinuxBaselineRuleDefinition]:
    selected_path = (rules_path or DEFAULT_LINUX_RULES_PATH).resolve()
    return list(_load_linux_rules(str(selected_path)))
