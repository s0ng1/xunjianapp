from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha1
from zoneinfo import ZoneInfo

from app.core.exceptions import NotFoundError
from app.features.assets.service import AssetService
from app.features.baseline.schemas import BaselineCheckRead
from app.features.daily_focus.repository import DailyFocusItemStateRepository
from app.features.daily_focus.schemas import (
    DailyFocusAssetGroupRead,
    DailyFocusItemRead,
    DailyFocusItemStateRead,
    DailyFocusItemStateUpdate,
    DailyFocusPriorityDeviceRead,
    DailyFocusRead,
    DailyFocusSummaryRead,
)
from app.features.linux_inspections.schemas import LinuxInspectionRead
from app.features.linux_inspections.service import LinuxInspectionService

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
ACTIVE_ITEM_STATUSES = {"pending", "in_progress", "needs_manual_confirmation"}
DEFAULT_UPDATED_BY = "local-operator"
CONFIG_CHANGE_KEYS: dict[str, str] = {
    "legacy_ssh_config": "SSH 配置发生变化",
    "legacy_firewall_status": "防火墙状态发生变化",
    "legacy_auditd_status": "审计配置发生变化",
    "selinux_status": "SELinux 状态发生变化",
    "ssh_service_state": "SSH 服务状态发生变化",
    "telnet_service_state": "Telnet 管理状态发生变化",
}


@dataclass(slots=True)
class AssetMeta:
    asset_id: int | None
    asset_name: str
    asset_ip: str


class DailyFocusService:
    def __init__(
        self,
        state_repository: DailyFocusItemStateRepository,
        asset_service: AssetService,
        linux_inspection_service: LinuxInspectionService,
    ) -> None:
        self.session = state_repository.session
        self.state_repository = state_repository
        self.asset_service = asset_service
        self.linux_inspection_service = linux_inspection_service

    async def get_daily_focus(self, *, reference_date: date | None = None) -> DailyFocusRead:
        today = reference_date or datetime.now(SHANGHAI_TZ).date()
        state_map = await self.state_repository.list_by_reference_date(reference_date=today)
        return await self._build_daily_focus(reference_date=today, state_map=state_map)

    async def update_item_state(
        self,
        *,
        item_id: str,
        payload: DailyFocusItemStateUpdate,
    ) -> DailyFocusItemStateRead:
        focus = await self.get_daily_focus(reference_date=payload.reference_date)
        items_by_id = self._index_items(focus)
        if item_id not in items_by_id:
            raise NotFoundError("Daily focus item", item_id)

        saved_state = await self.state_repository.upsert(
            item_id=item_id,
            reference_date=payload.reference_date,
            status=payload.status,
            remark=self._normalize_remark(payload.remark),
            updated_by=self._normalize_updated_by(payload.updated_by),
            updated_at=datetime.now(SHANGHAI_TZ),
        )
        await self.session.commit()
        return saved_state

    async def _build_daily_focus(
        self,
        *,
        reference_date: date,
        state_map: dict[str, DailyFocusItemStateRead],
    ) -> DailyFocusRead:
        assets = await self.asset_service.list_assets(skip=0, limit=1000)
        inspections = await self.linux_inspection_service.list_inspections(skip=0, limit=1000)

        assets_by_ip = {
            asset.ip: AssetMeta(asset_id=asset.id, asset_name=asset.name, asset_ip=asset.ip)
            for asset in assets
            if asset.type == "linux"
        }
        inspections_by_ip = self._group_inspections_by_ip(inspections)

        today_must_handle_groups: list[DailyFocusAssetGroupRead] = []
        today_changes: list[DailyFocusItemRead] = []
        weekly_plan: list[DailyFocusItemRead] = []

        for ip, history in inspections_by_ip.items():
            latest = history[0]
            previous = history[1] if len(history) > 1 else None
            asset = assets_by_ip.get(ip, AssetMeta(asset_id=None, asset_name=ip, asset_ip=ip))
            latest_results = {item.rule_id: item for item in latest.baseline_results}
            previous_results = {item.rule_id: item for item in previous.baseline_results} if previous else {}
            fail_days = self._build_fail_days(history, reference_date)

            must_handle_items = self._sort_items(
                self._apply_states(
                    self._build_today_must_handle(
                        asset=asset,
                        latest=latest,
                        reference_date=reference_date,
                    ),
                    state_map=state_map,
                )
            )
            if must_handle_items:
                today_must_handle_groups.append(
                    DailyFocusAssetGroupRead(
                        asset_id=asset.asset_id,
                        asset_name=asset.asset_name,
                        asset_ip=asset.asset_ip,
                        items=must_handle_items[:3],
                    )
                )

            today_changes.extend(
                self._apply_states(
                    self._build_today_changes(
                        asset=asset,
                        latest=latest,
                        previous=previous,
                        latest_results=latest_results,
                        previous_results=previous_results,
                        reference_date=reference_date,
                    ),
                    state_map=state_map,
                )
            )

            weekly_plan.extend(
                self._apply_states(
                    self._build_weekly_plan(
                        asset=asset,
                        latest=latest,
                        latest_results=latest_results,
                        fail_days=fail_days,
                        reference_date=reference_date,
                    ),
                    state_map=state_map,
                )
            )

        today_must_handle_groups.sort(key=lambda group: min(self._item_sort_key(item) for item in group.items))
        today_changes = self._sort_items(today_changes)
        weekly_plan = self._sort_items(weekly_plan)
        all_items = self._collect_items(today_must_handle_groups, today_changes, weekly_plan)
        priority_devices = self._build_priority_devices(all_items)

        return DailyFocusRead(
            reference_date=reference_date,
            generated_at=datetime.now(SHANGHAI_TZ),
            today_summary=self._build_today_summary(all_items),
            summary=DailyFocusSummaryRead(
                must_handle_count=sum(len(group.items) for group in today_must_handle_groups),
                today_changes_count=len(today_changes),
                weekly_plan_count=len(weekly_plan),
            ),
            priority_devices=priority_devices,
            today_must_handle=today_must_handle_groups,
            today_changes=today_changes,
            weekly_plan=weekly_plan,
        )

    def _group_inspections_by_ip(self, inspections: list[LinuxInspectionRead]) -> dict[str, list[LinuxInspectionRead]]:
        grouped: dict[str, list[LinuxInspectionRead]] = defaultdict(list)
        for inspection in inspections:
            grouped[inspection.ip].append(inspection)
        for ip in grouped:
            grouped[ip].sort(key=lambda item: item.created_at, reverse=True)
        return dict(grouped)

    def _build_today_must_handle(
        self,
        *,
        asset: AssetMeta,
        latest: LinuxInspectionRead,
        reference_date: date,
    ) -> list[DailyFocusItemRead]:
        items: list[DailyFocusItemRead] = []
        if not latest.success:
            items.append(
                self._build_item(
                    asset=asset,
                    section="today_must_handle",
                    item_key="inspection_failure",
                    reference_date=reference_date,
                    priority_rank=1,
                    severity="high",
                    headline=f"{asset.asset_name}：最新巡检执行失败（高危）",
                    summary="当前没有新鲜巡检结论，建议先恢复巡检链路并重新执行。",
                    detected_at=latest.created_at,
                    source_type="inspection_failure",
                )
            )

        for check in latest.baseline_results:
            if check.status != "fail" or check.risk_level.lower() != "high":
                continue
            items.append(
                self._build_item(
                    asset=asset,
                    section="today_must_handle",
                    item_key=f"rule:{check.rule_id}",
                    reference_date=reference_date,
                    priority_rank=1,
                    severity="high",
                    headline=f"{asset.asset_name}：{check.rule_name}（高危）",
                    summary=check.detail,
                    detected_at=latest.created_at,
                    source_type="baseline_fail",
                    rule_id=check.rule_id,
                )
            )
        return items

    def _build_today_changes(
        self,
        *,
        asset: AssetMeta,
        latest: LinuxInspectionRead,
        previous: LinuxInspectionRead | None,
        latest_results: dict[str, BaselineCheckRead],
        previous_results: dict[str, BaselineCheckRead],
        reference_date: date,
    ) -> list[DailyFocusItemRead]:
        items: list[DailyFocusItemRead] = []
        if self._local_date(latest.created_at) != reference_date:
            return items

        for rule_id, check in latest_results.items():
            if check.status != "fail":
                continue
            previous_status = previous_results.get(rule_id).status if rule_id in previous_results else None
            if previous_status == "fail":
                continue
            summary = "该项在今天新进入 fail 状态，建议优先确认变更原因。"
            if previous_status == "pass":
                summary = "该项今天从 pass 变为 fail，建议优先排查最近变更。"
            items.append(
                self._build_item(
                    asset=asset,
                    section="today_changes",
                    item_key=f"rule:{rule_id}",
                    reference_date=reference_date,
                    priority_rank=2,
                    severity=check.risk_level,
                    headline=f"{asset.asset_name}：{check.rule_name}（{self._format_severity(check.risk_level)}）",
                    summary=summary,
                    detected_at=latest.created_at,
                    source_type="new_fail",
                    rule_id=rule_id,
                )
            )

        if previous is None:
            return items

        for port in self._new_open_ports(latest, previous):
            items.append(
                self._build_item(
                    asset=asset,
                    section="today_changes",
                    item_key=f"port:{port}",
                    reference_date=reference_date,
                    priority_rank=3,
                    severity="medium",
                    headline=f"{asset.asset_name}：检测到新增 {port} 端口（需确认用途）",
                    summary="与上一版巡检相比出现了新的监听端口，建议确认业务归属与访问范围。",
                    detected_at=latest.created_at,
                    source_type="port_change",
                )
            )

        for config_key, config_change in self._config_changes(latest, previous):
            items.append(
                self._build_item(
                    asset=asset,
                    section="today_changes",
                    item_key=f"config:{config_key}",
                    reference_date=reference_date,
                    priority_rank=3,
                    severity="medium",
                    headline=f"{asset.asset_name}：{config_change}（需复核）",
                    summary="与上一版巡检相比，关键安全配置采集结果发生变化，建议确认是否为已授权调整。",
                    detected_at=latest.created_at,
                    source_type="config_change",
                )
            )

        return items

    def _build_weekly_plan(
        self,
        *,
        asset: AssetMeta,
        latest: LinuxInspectionRead,
        latest_results: dict[str, BaselineCheckRead],
        fail_days: dict[str, int],
        reference_date: date,
    ) -> list[DailyFocusItemRead]:
        items: list[DailyFocusItemRead] = []
        for rule_id, check in latest_results.items():
            severity = check.risk_level.lower()
            persistent_days = fail_days.get(rule_id, 0)

            if check.status == "fail" and severity == "medium":
                summary = check.detail
                if persistent_days >= 2:
                    summary = f"{check.detail} 该问题已连续 {persistent_days} 天存在，建议纳入本周计划。"
                items.append(
                    self._build_item(
                        asset=asset,
                        section="weekly_plan",
                        item_key=f"rule:{rule_id}:medium_fail",
                        reference_date=reference_date,
                        priority_rank=4,
                        severity=check.risk_level,
                        headline=f"{asset.asset_name}：{check.rule_name}（中危）",
                        summary=summary,
                        detected_at=latest.created_at,
                        source_type="medium_fail",
                        rule_id=rule_id,
                        persistent_days=persistent_days,
                    )
                )
                continue

            if check.status == "fail" and severity != "high" and persistent_days >= 2:
                items.append(
                    self._build_item(
                        asset=asset,
                        section="weekly_plan",
                        item_key=f"rule:{rule_id}:persistent_fail",
                        reference_date=reference_date,
                        priority_rank=4,
                        severity=check.risk_level,
                        headline=f"{asset.asset_name}：{check.rule_name}（已连续 {persistent_days} 天存在）",
                        summary="该问题连续多天未消除，建议本周安排专门时间彻底处理。",
                        detected_at=latest.created_at,
                        source_type="persistent_fail",
                        rule_id=rule_id,
                        persistent_days=persistent_days,
                    )
                )
                continue

            if check.status == "unknown" or check.check_type == "manual":
                items.append(
                    self._build_item(
                        asset=asset,
                        section="weekly_plan",
                        item_key=f"rule:{rule_id}:manual_review",
                        reference_date=reference_date,
                        priority_rank=5,
                        severity=check.risk_level,
                        headline=f"{asset.asset_name}：{check.rule_name}（需人工确认）",
                        summary=check.manual_check_hint or check.detail,
                        detected_at=latest.created_at,
                        source_type="manual_review",
                        rule_id=rule_id,
                        persistent_days=persistent_days,
                    )
                )
        return items

    def _build_fail_days(self, history: list[LinuxInspectionRead], today: date) -> dict[str, int]:
        window_start = today - timedelta(days=6)
        fail_dates: dict[str, set[date]] = defaultdict(set)
        for inspection in history:
            inspection_date = self._local_date(inspection.created_at)
            if inspection_date < window_start:
                continue
            for check in inspection.baseline_results:
                if check.status == "fail":
                    fail_dates[check.rule_id].add(inspection_date)
        return {rule_id: len(days) for rule_id, days in fail_dates.items()}

    def _new_open_ports(self, latest: LinuxInspectionRead, previous: LinuxInspectionRead) -> list[str]:
        latest_ports = {
            f"{item.protocol}/{item.port}"
            for item in (latest.open_ports.ports if latest.open_ports is not None else [])
        }
        previous_ports = {
            f"{item.protocol}/{item.port}"
            for item in (previous.open_ports.ports if previous.open_ports is not None else [])
        }
        return sorted(latest_ports - previous_ports)

    def _config_changes(self, latest: LinuxInspectionRead, previous: LinuxInspectionRead) -> list[tuple[str, str]]:
        latest_data = latest.collected_data or {}
        previous_data = previous.collected_data or {}
        changes: list[tuple[str, str]] = []
        for key, label in CONFIG_CHANGE_KEYS.items():
            latest_entry = latest_data.get(key)
            previous_entry = previous_data.get(key)
            latest_raw = self._raw_snapshot_value(latest_entry)
            previous_raw = self._raw_snapshot_value(previous_entry)
            if latest_raw and previous_raw and latest_raw != previous_raw:
                changes.append((key, label))
        return changes

    def _raw_snapshot_value(self, entry) -> str:
        if entry is None:
            return ""
        if hasattr(entry, "normalized_output") and entry.normalized_output is not None:
            return str(entry.normalized_output or "").strip()
        if hasattr(entry, "raw_output"):
            return str(entry.raw_output or "").strip()
        if isinstance(entry, dict):
            if entry.get("normalized_output") is not None:
                return str(entry.get("normalized_output") or "").strip()
            return str(entry.get("raw_output") or "").strip()
        return ""

    def _build_item(
        self,
        *,
        asset: AssetMeta,
        section: str,
        item_key: str,
        reference_date: date,
        priority_rank: int,
        severity: str,
        headline: str,
        summary: str,
        detected_at: datetime,
        source_type: str,
        rule_id: str | None = None,
        persistent_days: int = 0,
    ) -> DailyFocusItemRead:
        item_id = self._build_item_id(
            section=section,
            asset_ip=asset.asset_ip,
            item_key=item_key,
            reference_date=reference_date,
        )
        return DailyFocusItemRead(
            id=item_id,
            asset_id=asset.asset_id,
            asset_name=asset.asset_name,
            asset_ip=asset.asset_ip,
            section=section,
            priority_rank=priority_rank,
            severity=severity,
            headline=headline,
            summary=summary,
            detected_at=detected_at,
            source_type=source_type,
            rule_id=rule_id,
            persistent_days=persistent_days,
            status=self._default_status_for_source_type(source_type),
        )

    def _build_item_id(
        self,
        *,
        section: str,
        asset_ip: str,
        item_key: str,
        reference_date: date,
    ) -> str:
        base = "|".join([reference_date.isoformat(), section, asset_ip, item_key])
        return sha1(base.encode("utf-8")).hexdigest()[:16]

    def _default_status_for_source_type(self, source_type: str) -> str:
        if source_type == "manual_review":
            return "needs_manual_confirmation"
        return "pending"

    def _apply_states(
        self,
        items: list[DailyFocusItemRead],
        *,
        state_map: dict[str, DailyFocusItemStateRead],
    ) -> list[DailyFocusItemRead]:
        merged: list[DailyFocusItemRead] = []
        for item in items:
            state = state_map.get(item.id)
            if state is None:
                merged.append(item)
                continue
            merged.append(
                item.model_copy(
                    update={
                        "status": state.status,
                        "remark": state.remark,
                        "updated_at": state.updated_at,
                        "updated_by": state.updated_by,
                    }
                )
            )
        return merged

    def _sort_items(self, items: list[DailyFocusItemRead]) -> list[DailyFocusItemRead]:
        return sorted(items, key=self._item_sort_key)

    def _collect_items(
        self,
        today_must_handle_groups: list[DailyFocusAssetGroupRead],
        today_changes: list[DailyFocusItemRead],
        weekly_plan: list[DailyFocusItemRead],
    ) -> list[DailyFocusItemRead]:
        items = [item for group in today_must_handle_groups for item in group.items]
        items.extend(today_changes)
        items.extend(weekly_plan)
        return items

    def _index_items(self, focus: DailyFocusRead) -> dict[str, DailyFocusItemRead]:
        return {item.id: item for item in self._collect_items(focus.today_must_handle, focus.today_changes, focus.weekly_plan)}

    def _build_priority_devices(self, items: list[DailyFocusItemRead]) -> list[DailyFocusPriorityDeviceRead]:
        by_asset: dict[str, dict] = {}
        for item in items:
            if item.status not in ACTIVE_ITEM_STATUSES:
                continue
            stats = by_asset.setdefault(
                item.asset_ip,
                {
                    "asset_id": item.asset_id,
                    "asset_name": item.asset_name,
                    "asset_ip": item.asset_ip,
                    "high_count": 0,
                    "medium_count": 0,
                    "today_changes_count": 0,
                    "needs_manual_confirmation_count": 0,
                },
            )
            severity = item.severity.strip().lower()
            if severity == "high":
                stats["high_count"] += 1
            elif severity == "medium":
                stats["medium_count"] += 1
            if item.section == "today_changes":
                stats["today_changes_count"] += 1
            if item.status == "needs_manual_confirmation":
                stats["needs_manual_confirmation_count"] += 1

        devices = [DailyFocusPriorityDeviceRead(**payload) for payload in by_asset.values()]
        devices.sort(
            key=lambda item: (
                -item.high_count,
                -item.today_changes_count,
                -item.medium_count,
                item.asset_name,
                item.asset_ip,
            )
        )
        return devices

    def _build_today_summary(self, items: list[DailyFocusItemRead]) -> str:
        active_items = self._sort_items([item for item in items if item.status in ACTIVE_ITEM_STATUSES])
        if not active_items:
            return "今天没有未处理、处理中或待人工确认的工作项。可优先复查已处理结果。"

        device_count = len({item.asset_ip for item in active_items})
        high_count = sum(1 for item in active_items if item.severity.strip().lower() == "high")
        first_sentence = f"今天共有 {device_count} 台 Linux 需要优先处理，活跃工作项 {len(active_items)} 项，其中高危 {high_count} 项。"

        highlights: list[str] = []
        for item in active_items:
            short_text = self._short_headline(item.headline)
            if short_text in highlights:
                continue
            highlights.append(short_text)
            if len(highlights) == 3:
                break

        if not highlights:
            return first_sentence
        if len(highlights) == 1:
            second_sentence = f"先处理{highlights[0]}。"
        elif len(highlights) == 2:
            second_sentence = f"先处理{highlights[0]}和{highlights[1]}。"
        else:
            second_sentence = f"先处理{highlights[0]}、{highlights[1]}和{highlights[2]}。"
        return f"{first_sentence} {second_sentence}"

    def _short_headline(self, headline: str) -> str:
        short_text = headline.split("：", maxsplit=1)[1] if "：" in headline else headline
        return short_text.strip()

    def _normalize_remark(self, remark: str | None) -> str | None:
        if remark is None:
            return None
        cleaned = remark.strip()
        return cleaned or None

    def _normalize_updated_by(self, updated_by: str | None) -> str:
        if updated_by is None:
            return DEFAULT_UPDATED_BY
        cleaned = updated_by.strip()
        return cleaned or DEFAULT_UPDATED_BY

    def _item_sort_key(self, item: DailyFocusItemRead) -> tuple:
        return (
            self._status_order(item.status),
            item.priority_rank,
            self._severity_order(item.severity),
            -item.persistent_days,
            -item.detected_at.timestamp(),
            item.asset_name,
            item.headline,
        )

    def _status_order(self, status: str) -> int:
        normalized = status.strip().lower()
        if normalized == "pending":
            return 0
        if normalized == "in_progress":
            return 1
        if normalized == "needs_manual_confirmation":
            return 2
        if normalized == "resolved":
            return 3
        if normalized == "ignored":
            return 4
        return 5

    def _severity_order(self, severity: str) -> int:
        normalized = severity.strip().lower()
        if normalized == "high":
            return 0
        if normalized == "medium":
            return 1
        if normalized == "low":
            return 2
        return 3

    def _format_severity(self, severity: str) -> str:
        normalized = severity.strip().lower()
        if normalized == "high":
            return "高危"
        if normalized == "medium":
            return "中危"
        if normalized == "low":
            return "低危"
        return severity

    def _local_date(self, value: datetime) -> date:
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(SHANGHAI_TZ).date()
