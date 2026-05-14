"""ARQ Worker entry point with refactored task structure."""

from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from src.core.config import config
from src.core.otel import setup_otel
from src.infrastructure.workers.tasks.advisor_tasks import (
    run_advisor_created_task,
    run_evaluate_badges_task,
)
from src.infrastructure.workers.tasks.ai_tasks import (
    run_ai_health_check_task,
    run_batch_case_overviews_task,
    run_generate_case_overview_task,
)
from src.infrastructure.workers.tasks.case_tasks import (
    run_auto_resolve_case_task,
    run_case_accepted_task,
    run_case_failed_task,
    run_case_resolved_task,
    run_case_review_requested_task,
)
from src.infrastructure.workers.tasks.email_tasks import (
    run_dispatch_email_task,
    run_dispatch_review_email_task,
    run_email_draft_task,
)
from src.infrastructure.workers.tasks.maintenance_tasks import run_outbox_poller_task
from src.infrastructure.workers.tasks.student_tasks import (
    run_student_booked_task,
)

logger = structlog.get_logger(__name__)


async def on_startup(_ctx: dict[Any, Any]) -> None:
    """Initializes observability on worker startup."""
    setup_otel()
    logger.info('worker_started', version='2.0.0')


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        # AI Tasks
        run_ai_health_check_task,
        run_batch_case_overviews_task,
        run_generate_case_overview_task,

        # Email Tasks
        run_email_draft_task,
        run_dispatch_email_task,
        run_dispatch_review_email_task,

        # Event Handlers
        run_case_accepted_task,
        run_student_booked_task,
        run_case_resolved_task,
        run_case_failed_task,
        run_case_review_requested_task,
        run_auto_resolve_case_task,
        run_advisor_created_task,

        # Gamification
        run_evaluate_badges_task,

        # Maintenance
        run_outbox_poller_task,
    ]

    on_startup = on_startup

    cron_jobs = [
        # Poll outbox every 5 seconds
        cron(run_outbox_poller_task, second=set(range(0, 60, 5))),

        # AI health check every 30 minutes
        cron(run_ai_health_check_task, minute=30),

        # Batch AI overviews generation every 10 minutes
        cron(run_batch_case_overviews_task, minute=set(range(0, 60, 10))),
    ]

    redis_settings = RedisSettings(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
    )

    max_jobs = config.worker_max_jobs
    job_timeout = config.worker_job_timeout_sec
