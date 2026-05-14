"""Worker tasks for system maintenance and outbox polling."""

from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task


@worker_task()
async def run_outbox_poller_task(ctx: TaskContext) -> None:
    """Cron task to poll the transactional outbox and dispatch to ARQ."""
    # We use a dedicated span name for the poller
    ctx.span.update_name('cron.outbox_poller')
    await ctx.container.outbox_processor.process_pending_events()
