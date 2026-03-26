from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from faststream.exceptions import SetupError

from app.broker import broker, payments_exchange
from app.core.config import settings
from app.db.session import async_session_maker
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="outbox-publisher")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                async with async_session_maker() as session:
                    repository = OutboxRepository(session)
                    events = await repository.get_pending_batch(settings.outbox_batch_size)
                    if not events:
                        await asyncio.sleep(settings.outbox_poll_interval_seconds)
                        continue

                    for event in events:
                        try:
                            await broker.publish(
                                event.payload,
                                exchange=payments_exchange,
                                routing_key=settings.payments_routing_key,
                            )
                            await repository.mark_published(event)
                            await session.commit()
                        except Exception as exc:
                            await repository.mark_failed(event, str(exc))
                            await session.commit()
                            logger.exception("Failed to publish outbox event %s", event.id)
            except SetupError:
                logger.warning("RabbitMQ broker is not ready yet, retrying...")
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error in outbox publisher loop")
                await asyncio.sleep(settings.outbox_poll_interval_seconds)
