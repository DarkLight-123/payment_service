from __future__ import annotations

import asyncio
import logging
import random

from faststream import FastStream
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker import broker, payments_exchange, payments_queue
from app.core.config import settings
from app.db.session import async_session_maker
from app.models.payment import PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.schemas.events import PaymentCreatedEvent
from app.utils.webhook import send_payment_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastStream(broker)


async def _process_payment(session: AsyncSession, event: PaymentCreatedEvent) -> None:
    payment_repository = PaymentRepository(session)
    payment = await payment_repository.get_by_id(event.payment_id)
    if payment is None:
        logger.warning("Payment %s not found, skipping", event.payment_id)
        return

    if payment.status != PaymentStatus.pending:
        logger.info("Payment %s already processed with status %s", payment.id, payment.status.value)
        return

    delay = random.randint(
        settings.payment_processing_min_delay_seconds,
        settings.payment_processing_max_delay_seconds,
    )
    await asyncio.sleep(delay)

    is_success = random.random() <= settings.payment_success_rate
    new_status = PaymentStatus.succeeded if is_success else PaymentStatus.failed
    await payment_repository.update_status(payment, new_status)
    await session.commit()
    await session.refresh(payment)

    await send_payment_webhook(payment)


@broker.subscriber(payments_queue, exchange=payments_exchange)
async def consume_payment(event: PaymentCreatedEvent, message) -> None:
    for attempt in range(1, settings.max_processing_attempts + 1):
        try:
            async with async_session_maker() as session:
                await _process_payment(session, event)
            logger.info("Payment %s processed successfully", event.payment_id)
            return
        except Exception:
            logger.exception(
                "Payment %s processing failed on attempt %s/%s",
                event.payment_id,
                attempt,
                settings.max_processing_attempts,
            )
            if attempt >= settings.max_processing_attempts:
                await message.reject(requeue=False)
                return
            await asyncio.sleep(2 ** (attempt - 1))


if __name__ == "__main__":
    asyncio.run(app.run())
