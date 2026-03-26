from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.payment import Payment


async def send_payment_webhook(payment: Payment) -> None:
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "description": payment.description,
        "metadata": payment.metadata_json,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }

    timeout = httpx.Timeout(settings.webhook_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(payment.webhook_url, json=payload)
        response.raise_for_status()
