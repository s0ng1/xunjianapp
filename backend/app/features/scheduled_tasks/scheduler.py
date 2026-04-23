import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.features.scheduled_tasks.repository import ScheduledTaskRepository

logger = logging.getLogger(__name__)


class SchedulerManager:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self.scheduler = AsyncIOScheduler()
        self._executor = None

    @property
    def executor(self):
        if self._executor is None:
            from app.features.scheduled_tasks.executor import ScheduledTaskExecutor

            self._executor = ScheduledTaskExecutor(self.session_factory)
        return self._executor

    async def start(self) -> None:
        await self.reload_from_db()
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown")

    async def reload_from_db(self) -> None:
        for job in list(self.scheduler.get_jobs()):
            if job.id.startswith("scheduled_task:"):
                self.scheduler.remove_job(job.id)
        async with self.session_factory() as session:
            repo = ScheduledTaskRepository(session)
            tasks = await repo.list_all(is_enabled=True)
            for task in tasks:
                self._register_task(task)
            logger.info("Reloaded %d enabled tasks", len(tasks))

    def _register_task(self, task) -> None:
        job_id = f"scheduled_task:{task.id}"
        existing = self.scheduler.get_job(job_id)
        if existing:
            self.scheduler.remove_job(job_id)
        trigger = self._build_trigger(task)
        if trigger is None:
            logger.warning("Cannot build trigger for task %s", task.id)
            return
        self.scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        logger.info("Registered job %s (%s)", job_id, task.name)

    def _build_trigger(self, task):
        if task.schedule_type == "interval" and task.interval_seconds:
            return IntervalTrigger(seconds=task.interval_seconds, timezone=task.timezone or "UTC")
        if task.schedule_type == "cron" and task.cron_expression:
            return CronTrigger.from_crontab(task.cron_expression, timezone=task.timezone or "UTC")
        return None

    async def _run_job(self, task_id: int) -> None:
        logger.info("Running scheduled task %s", task_id)
        async with self.session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)
            if task is None:
                logger.warning("Task %s not found", task_id)
                return
            result = await self.executor.execute(task)
            next_run_job = self.scheduler.get_job(f"scheduled_task:{task_id}")
            next_run = next_run_job.next_run_time if next_run_job else None
            await repo.update_run_result(
                task_id,
                last_run_at=datetime.now(timezone.utc),
                last_status="success" if result.success else "failed",
                last_message=result.message,
                next_run_at=next_run,
            )
            await session.commit()
            logger.info("Task %s finished: %s", task_id, result.message)

    async def add_or_update_task(self, task) -> None:
        if task.is_enabled:
            self._register_task(task)
        else:
            await self.remove_task(task.id)

    async def remove_task(self, task_id: int) -> None:
        job_id = f"scheduled_task:{task_id}"
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.remove_job(job_id)
            logger.info("Removed job %s", job_id)

    async def trigger_now(self, task_id: int) -> None:
        await self._run_job(task_id)
        async with self.session_factory() as session:
            repo = ScheduledTaskRepository(session)
            task = await repo.get_by_id(task_id)
        if task and task.is_enabled:
            self._register_task(task)
