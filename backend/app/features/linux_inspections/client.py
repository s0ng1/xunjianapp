from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import shlex

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

from app.features.baseline.linux_rule_collector import LEGACY_LINUX_COLLECTION_PLAN, LinuxCollectCommand
from app.features.linux_inspections.schemas import (
    AuditdStatusResult,
    CollectedDataEntry,
    FirewallStatusResult,
    OpenPortEntry,
    OpenPortsResult,
    SSHConfigResult,
    TimeSyncStatusResult,
)

logger = logging.getLogger(__name__)

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
BACKSPACE_RE = re.compile(r"[^\n]\x08")
EXIT_STATUS_MARKER_RE = re.compile(r"(?:\n|^)__XUNJIAN_EXIT_STATUS__:(?P<status>\d+)\s*$")


@dataclass(slots=True)
class LinuxInspectionExecution:
    success: bool
    message: str
    open_ports: OpenPortsResult | None = None
    ssh_config: SSHConfigResult | None = None
    firewall_status: FirewallStatusResult | None = None
    time_sync_status: TimeSyncStatusResult | None = None
    auditd_status: AuditdStatusResult | None = None
    collected_data: dict[str, dict] | None = None


class LinuxInspectorClient:
    def __init__(self, connection_timeout_seconds: int = 10, command_read_timeout_seconds: int = 120) -> None:
        self.connection_timeout_seconds = connection_timeout_seconds
        self.command_read_timeout_seconds = command_read_timeout_seconds

    def inspect(
        self,
        *,
        ip: str,
        username: str,
        password: str,
        port: int = 22,
        collection_plan: list[LinuxCollectCommand] | None = None,
    ) -> LinuxInspectionExecution:
        connection = None
        try:
            connection = ConnectHandler(
                device_type="terminal_server",
                host=ip,
                port=port,
                username=username,
                password=password,
                conn_timeout=self.connection_timeout_seconds,
                auth_timeout=self.connection_timeout_seconds,
                banner_timeout=self.connection_timeout_seconds,
                timeout=self.connection_timeout_seconds,
                session_timeout=self.connection_timeout_seconds,
                fast_cli=False,
            )
            collected_data = self._collect(
                connection=connection,
                collection_plan=collection_plan or list(LEGACY_LINUX_COLLECTION_PLAN),
            )
            return LinuxInspectionExecution(
                success=True,
                message="Linux inspection completed",
                open_ports=self._parse_open_ports(self._get_output(collected_data, "legacy_open_ports")),
                ssh_config=self._parse_ssh_config(self._get_output(collected_data, "legacy_ssh_config")),
                firewall_status=self._parse_firewall_status(self._get_output(collected_data, "legacy_firewall_status")),
                time_sync_status=self._parse_time_sync_status(self._get_output(collected_data, "legacy_time_sync_status")),
                auditd_status=self._parse_auditd_status(self._get_output(collected_data, "legacy_auditd_status")),
                collected_data=collected_data,
            )
        except NetmikoAuthenticationException:
            return LinuxInspectionExecution(success=False, message="SSH authentication failed")
        except NetmikoTimeoutException:
            return LinuxInspectionExecution(success=False, message="SSH connection timed out")
        except Exception as exc:
            logger.exception(
                "Unexpected Linux inspection error ip=%s username=%s error_type=%s",
                ip,
                username,
                type(exc).__name__,
            )
            return LinuxInspectionExecution(success=False, message="Linux inspection failed")
        finally:
            if connection is not None:
                connection.disconnect()

    def _collect(
        self,
        *,
        connection,
        collection_plan: list[LinuxCollectCommand],
    ) -> dict[str, dict]:
        results: dict[str, dict] = {}
        for item in collection_plan:
            try:
                output = connection.send_command(
                    self._wrap_command_with_exit_status(item.command),
                    strip_prompt=True,
                    strip_command=True,
                    read_timeout=self.command_read_timeout_seconds,
                )
                raw_output = self._remove_exit_status_marker(output)
                normalized_output = self._normalize_terminal_output(raw_output)
                exit_status = self._extract_exit_status(output)
                error = self._build_collection_error(
                    item=item,
                    normalized_output=normalized_output,
                    exit_status=exit_status,
                )
                entry = CollectedDataEntry(
                    type=item.collect_type,
                    command=item.command,
                    raw_output=raw_output,
                    normalized_output=normalized_output,
                    error=error,
                )
            except Exception as exc:
                logger.warning("Linux collection command failed key=%s error=%s", item.key, type(exc).__name__)
                entry = CollectedDataEntry(
                    type=item.collect_type,
                    command=item.command,
                    raw_output=None,
                    normalized_output=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            results[item.key] = entry.model_dump()
        return results

    def _wrap_command_with_exit_status(self, command: str) -> str:
        script = (
            f"({command}) 2>&1\n"
            "__xunjian_status=$?\n"
            "printf '\\n__XUNJIAN_EXIT_STATUS__:%s\\n' \"$__xunjian_status\""
        )
        return f"sh -lc {shlex.quote(script)}"

    def _remove_exit_status_marker(self, output: str | None) -> str:
        return EXIT_STATUS_MARKER_RE.sub("", str(output or ""))

    def _extract_exit_status(self, output: str | None) -> int | None:
        match = EXIT_STATUS_MARKER_RE.search(str(output or ""))
        if match is None:
            return None
        return int(match.group("status"))

    def _build_collection_error(
        self,
        *,
        item: LinuxCollectCommand,
        normalized_output: str,
        exit_status: int | None,
    ) -> str | None:
        if exit_status is None:
            return None
        if exit_status == 0:
            return None
        if item.key.startswith("legacy_") or self._output_indicates_command_error(normalized_output):
            return f"Command exited with status {exit_status}"
        return None

    def _output_indicates_command_error(self, output: str) -> bool:
        lowered = output.strip().lower()
        if not lowered:
            return False
        error_patterns = (
            "permission denied",
            "cannot open",
            "no such file",
            "not found",
            "operation not permitted",
            "access denied",
            "command not found",
            "unable to",
        )
        return any(pattern in lowered for pattern in error_patterns)

    def _get_output(self, collected_data: dict[str, dict], key: str) -> str:
        entry = collected_data.get(key) or {}
        normalized_output = entry.get("normalized_output")
        if normalized_output is not None:
            return str(normalized_output)
        return str(entry.get("raw_output") or "")

    def _normalize_terminal_output(self, output: str | None) -> str:
        text = str(output or "")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = ANSI_ESCAPE_RE.sub("", text)
        while "\x08" in text:
            updated = BACKSPACE_RE.sub("", text)
            if updated == text:
                break
            text = updated
        text = text.replace("\x08", "")
        return CONTROL_CHAR_RE.sub("", text)

    def _parse_open_ports(self, output: str) -> OpenPortsResult:
        ports: list[OpenPortEntry] = []
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.lower().startswith("proto"):
                continue
            parsed = self._parse_open_port_line(cleaned)
            if parsed is not None:
                ports.append(parsed)
        return OpenPortsResult(ports=ports, raw_output=output)

    def _parse_open_port_line(self, line: str) -> OpenPortEntry | None:
        parts = line.split()
        if len(parts) < 4:
            return None

        protocol = parts[0].lower()
        state: str | None
        local_address: str

        if len(parts) >= 5 and not parts[1].isdigit():
            state = parts[1]
            local_address = parts[4]
        else:
            state = parts[5] if len(parts) >= 6 else None
            local_address = parts[3]

        address, port = self._split_address_and_port(local_address)
        return OpenPortEntry(protocol=protocol, local_address=address, port=port, state=state)

    def _split_address_and_port(self, value: str) -> tuple[str, str]:
        candidate = value.strip()
        if candidate.startswith("[") and "]:" in candidate:
            address, port = candidate.split("]:", 1)
            return address.lstrip("["), port
        if ":" in candidate:
            address, port = candidate.rsplit(":", 1)
            return address, port
        return candidate, ""

    def _parse_ssh_config(self, output: str) -> SSHConfigResult:
        settings: dict[str, str] = {}
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            parts = cleaned.split(None, 1)
            if len(parts) == 2:
                settings[parts[0].lower()] = parts[1].strip()
        return SSHConfigResult(settings=settings, raw_output=output)

    def _parse_firewall_status(self, output: str) -> FirewallStatusResult:
        sections = self._split_sections(output)
        firewalld_lines = self._non_empty_lines(sections.get("__FIREWALLD__", ""))
        ufw_lines = self._non_empty_lines(sections.get("__UFW__", ""))
        iptables_lines = self._non_empty_lines(sections.get("__IPTABLES__", ""))
        return FirewallStatusResult(
            firewalld=firewalld_lines[0] if firewalld_lines else None,
            ufw=ufw_lines[0] if ufw_lines else None,
            iptables_rules=iptables_lines,
            raw_output=output,
        )

    def _parse_time_sync_status(self, output: str) -> TimeSyncStatusResult:
        sections = self._split_sections(output)
        timedatectl_lines = self._non_empty_lines(sections.get("__TIMEDATECTL__", ""))
        service_lines = self._non_empty_lines(sections.get("__SERVICE__", ""))
        return TimeSyncStatusResult(
            timedatectl="\n".join(timedatectl_lines) if timedatectl_lines else None,
            service_status=service_lines[0] if service_lines else None,
            raw_output=output,
        )

    def _parse_auditd_status(self, output: str) -> AuditdStatusResult:
        sections = self._split_sections(output)
        service_lines = self._non_empty_lines(sections.get("__AUDITD__", ""))
        auditctl_lines = self._non_empty_lines(sections.get("__AUDITCTL__", ""))
        return AuditdStatusResult(
            service_status=service_lines[0] if service_lines else None,
            auditctl_status="\n".join(auditctl_lines) if auditctl_lines else None,
            raw_output=output,
        )

    def _split_sections(self, output: str) -> dict[str, str]:
        sections: dict[str, list[str]] = {}
        current_section = "__ROOT__"
        sections[current_section] = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped in {
                "__FIREWALLD__",
                "__UFW__",
                "__IPTABLES__",
                "__TIMEDATECTL__",
                "__SERVICE__",
                "__AUDITD__",
                "__AUDITCTL__",
            }:
                current_section = stripped
                sections.setdefault(current_section, [])
                continue
            sections.setdefault(current_section, []).append(line)
        return {key: "\n".join(value).strip() for key, value in sections.items()}

    def _non_empty_lines(self, output: str) -> list[str]:
        return [line.strip() for line in output.splitlines() if line.strip()]
