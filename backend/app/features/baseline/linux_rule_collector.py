from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LinuxCollectCommand:
    key: str
    collect_type: str
    command: str


LEGACY_LINUX_COLLECTION_PLAN: tuple[LinuxCollectCommand, ...] = (
    LinuxCollectCommand(
        key="legacy_open_ports",
        collect_type="command",
        command='sh -lc "ss -tulnH 2>&1 || netstat -tuln 2>&1"',
    ),
    LinuxCollectCommand(
        key="legacy_ssh_config",
        collect_type="config",
        command=(
            'sh -lc "if command -v sshd >/dev/null 2>&1; then '
            "sshd -T 2>&1 || grep -Ev '^[[:space:]]*(#|$)' /etc/ssh/sshd_config 2>&1; "
            "else grep -Ev '^[[:space:]]*(#|$)' /etc/ssh/sshd_config 2>&1; fi\""
        ),
    ),
    LinuxCollectCommand(
        key="legacy_firewall_status",
        collect_type="command",
        command=(
            'sh -lc "printf \'__FIREWALLD__\\n\'; '
            '(systemctl is-active firewalld 2>&1 || echo unavailable); '
            "printf '\\n__UFW__\\n'; "
            '(ufw status 2>&1 || echo unavailable); '
            "printf '\\n__IPTABLES__\\n'; "
            '(iptables -L -n 2>&1 || echo unavailable)"'
        ),
    ),
    LinuxCollectCommand(
        key="legacy_time_sync_status",
        collect_type="command",
        command=(
            'sh -lc "printf \'__TIMEDATECTL__\\n\'; '
            '(timedatectl status 2>&1 || echo unavailable); '
            "printf '\\n__SERVICE__\\n'; "
            '((systemctl is-active chronyd 2>&1 || '
            'systemctl is-active chrony 2>&1 || '
            'systemctl is-active ntpd 2>&1) || echo unavailable)"'
        ),
    ),
    LinuxCollectCommand(
        key="legacy_auditd_status",
        collect_type="command",
        command=(
            'sh -lc "printf \'__AUDITD__\\n\'; '
            '(systemctl is-active auditd 2>&1 || service auditd status 2>&1 || echo unavailable); '
            "printf '\\n__AUDITCTL__\\n'; "
            '(auditctl -s 2>&1 || echo unavailable)"'
        ),
    ),
)


def merge_collection_plans(*plans: tuple[LinuxCollectCommand, ...] | list[LinuxCollectCommand]) -> list[LinuxCollectCommand]:
    merged: dict[str, LinuxCollectCommand] = {}
    for plan in plans:
        for item in plan:
            merged[item.key] = item
    return list(merged.values())
