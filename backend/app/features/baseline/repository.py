from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.baseline.models import BaselineCheckResult
from app.features.baseline.schemas import BaselineCheckRead, BaselineCheckWrite


class BaselineCheckResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_for_linux_inspection(
        self,
        *,
        linux_inspection_id: int,
        results: list[BaselineCheckWrite],
    ) -> list[BaselineCheckRead]:
        return await self._add_many(linux_inspection_id=linux_inspection_id, switch_inspection_id=None, results=results)

    async def add_for_switch_inspection(
        self,
        *,
        switch_inspection_id: int,
        results: list[BaselineCheckWrite],
    ) -> list[BaselineCheckRead]:
        return await self._add_many(linux_inspection_id=None, switch_inspection_id=switch_inspection_id, results=results)

    async def list_by_linux_inspection_ids(self, inspection_ids: list[int]) -> dict[int, list[BaselineCheckRead]]:
        if not inspection_ids:
            return {}
        result = await self.session.execute(
            select(BaselineCheckResult)
            .where(BaselineCheckResult.linux_inspection_id.in_(inspection_ids))
            .order_by(BaselineCheckResult.id.asc())
        )
        grouped: dict[int, list[BaselineCheckRead]] = defaultdict(list)
        for row in result.scalars().all():
            if row.linux_inspection_id is None:
                continue
            grouped[row.linux_inspection_id].append(self._to_read_model(row))
        return dict(grouped)

    async def list_by_switch_inspection_ids(self, inspection_ids: list[int]) -> dict[int, list[BaselineCheckRead]]:
        if not inspection_ids:
            return {}
        result = await self.session.execute(
            select(BaselineCheckResult)
            .where(BaselineCheckResult.switch_inspection_id.in_(inspection_ids))
            .order_by(BaselineCheckResult.id.asc())
        )
        grouped: dict[int, list[BaselineCheckRead]] = defaultdict(list)
        for row in result.scalars().all():
            if row.switch_inspection_id is None:
                continue
            grouped[row.switch_inspection_id].append(self._to_read_model(row))
        return dict(grouped)

    async def replace_for_linux_inspection(
        self,
        *,
        linux_inspection_id: int,
        results: list[BaselineCheckWrite],
    ) -> list[BaselineCheckRead]:
        await self.session.execute(
            delete(BaselineCheckResult).where(BaselineCheckResult.linux_inspection_id == linux_inspection_id)
        )
        return await self.add_for_linux_inspection(linux_inspection_id=linux_inspection_id, results=results)

    async def replace_for_switch_inspection(
        self,
        *,
        switch_inspection_id: int,
        results: list[BaselineCheckWrite],
    ) -> list[BaselineCheckRead]:
        await self.session.execute(
            delete(BaselineCheckResult).where(BaselineCheckResult.switch_inspection_id == switch_inspection_id)
        )
        return await self.add_for_switch_inspection(switch_inspection_id=switch_inspection_id, results=results)

    async def _add_many(
        self,
        *,
        linux_inspection_id: int | None,
        switch_inspection_id: int | None,
        results: list[BaselineCheckWrite],
    ) -> list[BaselineCheckRead]:
        saved_rows: list[BaselineCheckResult] = []
        for item in results:
            row = BaselineCheckResult(
                linux_inspection_id=linux_inspection_id,
                switch_inspection_id=switch_inspection_id,
                rule_id=item.rule_id,
                rule_name=item.rule_name,
                device_type=item.device_type,
                category=item.category,
                risk_level=item.risk_level,
                check_type=item.check_type,
                check_method=item.check_method,
                judge_logic=item.judge_logic,
                remediation=item.remediation,
                status=item.status,
                detail=item.detail,
                evidence=item.evidence,
                manual_check_hint=item.manual_check_hint,
                raw_matcher=item.raw_matcher,
            )
            self.session.add(row)
            saved_rows.append(row)
        await self.session.flush()
        return [self._to_read_model(row) for row in saved_rows]

    def _to_read_model(self, row: BaselineCheckResult) -> BaselineCheckRead:
        return BaselineCheckRead(
            rule_id=row.rule_id,
            rule_name=row.rule_name,
            device_type=row.device_type,
            category=row.category,
            risk_level=row.risk_level,
            check_type=row.check_type,
            check_method=row.check_method,
            judge_logic=row.judge_logic,
            remediation=row.remediation,
            status=row.status,
            detail=row.detail,
            evidence=row.evidence,
            manual_check_hint=row.manual_check_hint,
        )
