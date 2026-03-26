from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class PaymentCreatedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    payment_id: UUID
    amount: str
    currency: str
    description: str
    metadata: dict[str, Any]
    webhook_url: HttpUrl
    status: str
    idempotency_key: str
