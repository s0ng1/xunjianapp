import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.db.session import get_session_factory
from app.features.assets.models import Asset
from app.features.baseline.models import BaselineCheckResult
from app.features.linux_inspections.models import LinuxInspection

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def test_daily_focus_aggregates_status_devices_and_patch_flow(client) -> None:
    asyncio.run(_seed_daily_focus_data())

    response = client.get("/api/v1/daily-focus?reference_date=2026-04-11")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_date"] == "2026-04-11"
    assert payload["today_summary"].count("。") <= 2
    assert payload["priority_devices"][0]["asset_name"] == "prod-web-01"
    assert payload["priority_devices"][0]["high_count"] == 1
    assert payload["priority_devices"][0]["today_changes_count"] == 3
    assert payload["priority_devices"][0]["needs_manual_confirmation_count"] == 1

    manual_items = [item for item in payload["weekly_plan"] if item["status"] == "needs_manual_confirmation"]
    assert manual_items

    first_ids = _collect_item_ids(payload)
    repeated_response = client.get("/api/v1/daily-focus?reference_date=2026-04-11")
    assert repeated_response.status_code == 200
    assert _collect_item_ids(repeated_response.json()) == first_ids

    target_item = payload["today_must_handle"][0]["items"][0]
    patch_response = client.patch(
        f"/api/v1/daily-focus/items/{target_item['id']}",
        json={
            "reference_date": "2026-04-11",
            "status": "resolved",
            "remark": "已完成修复",
            "updated_by": "tester",
        },
    )

    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["item_id"] == target_item["id"]
    assert patched["reference_date"] == "2026-04-11"
    assert patched["status"] == "resolved"
    assert patched["remark"] == "已完成修复"
    assert patched["updated_by"] == "tester"

    refreshed_response = client.get("/api/v1/daily-focus?reference_date=2026-04-11")
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()
    refreshed_item = _find_item_by_id(refreshed, target_item["id"])
    assert refreshed_item["status"] == "resolved"
    assert refreshed_item["remark"] == "已完成修复"
    assert refreshed_item["updated_by"] == "tester"
    assert refreshed["priority_devices"][0]["high_count"] == 0
    assert refreshed["today_summary"].count("。") <= 2


def test_daily_focus_patch_requires_reference_date(client) -> None:
    asyncio.run(_seed_daily_focus_data())

    response = client.get("/api/v1/daily-focus?reference_date=2026-04-11")
    assert response.status_code == 200
    target_item = response.json()["today_must_handle"][0]["items"][0]

    patch_response = client.patch(
        f"/api/v1/daily-focus/items/{target_item['id']}",
        json={"status": "resolved"},
    )

    assert patch_response.status_code == 422


def _collect_item_ids(payload: dict) -> set[str]:
    ids = {
        item["id"]
        for group in payload["today_must_handle"]
        for item in group["items"]
    }
    ids.update(item["id"] for item in payload["today_changes"])
    ids.update(item["id"] for item in payload["weekly_plan"])
    return ids


def _find_item_by_id(payload: dict, item_id: str) -> dict:
    for group in payload["today_must_handle"]:
        for item in group["items"]:
            if item["id"] == item_id:
                return item
    for item in payload["today_changes"]:
        if item["id"] == item_id:
            return item
    for item in payload["weekly_plan"]:
        if item["id"] == item_id:
            return item
    raise AssertionError(f"item not found: {item_id}")


async def _seed_daily_focus_data() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            asset_web = Asset(
                name="prod-web-01",
                asset_type="linux",
                ip="10.0.0.1",
                created_at=_dt(2026, 4, 9, 9, 0),
            )
            asset_db = Asset(
                name="prod-db-01",
                asset_type="linux",
                ip="10.0.0.2",
                created_at=_dt(2026, 4, 9, 9, 30),
            )
            session.add_all([asset_web, asset_db])
            await session.flush()

            previous_inspection = LinuxInspection(
                ip="10.0.0.1",
                username="root",
                success=True,
                message="inspection ok",
                open_ports={
                    "ports": [
                        {"protocol": "tcp", "local_address": "0.0.0.0", "port": "22", "state": "LISTEN"},
                    ],
                    "raw_output": "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*",
                },
                ssh_config=None,
                firewall_status=None,
                time_sync_status=None,
                auditd_status=None,
                collected_data={
                    "legacy_firewall_status": {
                        "type": "command",
                        "command": "systemctl status firewalld",
                        "raw_output": "__FIREWALLD__\ninactive",
                        "error": None,
                    },
                },
                created_at=_dt(2026, 4, 10, 9, 0),
            )
            latest_inspection = LinuxInspection(
                ip="10.0.0.1",
                username="root",
                success=True,
                message="inspection ok",
                open_ports={
                    "ports": [
                        {"protocol": "tcp", "local_address": "0.0.0.0", "port": "22", "state": "LISTEN"},
                        {"protocol": "tcp", "local_address": "0.0.0.0", "port": "6379", "state": "LISTEN"},
                    ],
                    "raw_output": "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\ntcp LISTEN 0 128 0.0.0.0:6379 0.0.0.0:*",
                },
                ssh_config=None,
                firewall_status=None,
                time_sync_status=None,
                auditd_status=None,
                collected_data={
                    "legacy_firewall_status": {
                        "type": "command",
                        "command": "systemctl status firewalld",
                        "raw_output": "__FIREWALLD__\nactive",
                        "error": None,
                    },
                },
                created_at=_dt(2026, 4, 11, 9, 0),
            )
            manual_only_inspection = LinuxInspection(
                ip="10.0.0.2",
                username="root",
                success=True,
                message="inspection ok",
                open_ports={"ports": [], "raw_output": ""},
                ssh_config=None,
                firewall_status=None,
                time_sync_status=None,
                auditd_status=None,
                collected_data={},
                created_at=_dt(2026, 4, 11, 10, 0),
            )
            session.add_all([previous_inspection, latest_inspection, manual_only_inspection])
            await session.flush()

            session.add_all(
                [
                    _baseline_result(
                        linux_inspection_id=previous_inspection.id,
                        rule_id="linux_root_remote_login_disabled",
                        rule_name="允许 root 远程登录",
                        risk_level="high",
                        status="fail",
                        detail="检测到 PermitRootLogin yes。",
                    ),
                    _baseline_result(
                        linux_inspection_id=previous_inspection.id,
                        rule_id="linux_firewall_enabled",
                        rule_name="防火墙已启用",
                        risk_level="medium",
                        status="pass",
                        detail="防火墙处于启用状态。",
                    ),
                    _baseline_result(
                        linux_inspection_id=latest_inspection.id,
                        rule_id="linux_root_remote_login_disabled",
                        rule_name="允许 root 远程登录",
                        risk_level="high",
                        status="fail",
                        detail="检测到 PermitRootLogin yes。",
                    ),
                    _baseline_result(
                        linux_inspection_id=latest_inspection.id,
                        rule_id="linux_firewall_enabled",
                        rule_name="防火墙已启用",
                        risk_level="medium",
                        status="fail",
                        detail="检测到 firewalld 未启用。",
                    ),
                    _baseline_result(
                        linux_inspection_id=latest_inspection.id,
                        rule_id="linux_mfa_manual_review",
                        rule_name="MFA 启用情况",
                        risk_level="medium",
                        status="unknown",
                        detail="需要人工确认 MFA 配置。",
                        check_type="manual",
                        manual_check_hint="请联系系统负责人确认 MFA 是否启用。",
                    ),
                    _baseline_result(
                        linux_inspection_id=manual_only_inspection.id,
                        rule_id="linux_db_backup_manual_review",
                        rule_name="数据库备份链路",
                        risk_level="medium",
                        status="unknown",
                        detail="需要人工确认备份链路有效性。",
                        check_type="manual",
                        manual_check_hint="请检查昨天备份任务与恢复演练记录。",
                    ),
                ]
            )


def _baseline_result(
    *,
    linux_inspection_id: int,
    rule_id: str,
    rule_name: str,
    risk_level: str,
    status: str,
    detail: str,
    check_type: str = "auto",
    manual_check_hint: str | None = None,
) -> BaselineCheckResult:
    return BaselineCheckResult(
        linux_inspection_id=linux_inspection_id,
        switch_inspection_id=None,
        rule_id=rule_id,
        rule_name=rule_name,
        device_type="linux",
        category="security",
        risk_level=risk_level,
        check_type=check_type,
        check_method="snapshot",
        judge_logic="test",
        remediation="test",
        status=status,
        detail=detail,
        evidence="test",
        manual_check_hint=manual_check_hint,
        raw_matcher={},
        created_at=_dt(2026, 4, 11, 8, 0),
    )


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=SHANGHAI_TZ)
