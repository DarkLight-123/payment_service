from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.broker import broker
from app.core.config import settings
from app.workers.outbox_publisher import OutboxPublisher

publisher = OutboxPublisher()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await broker.connect()
    await publisher.start()
    try:
        yield
    finally:
        await publisher.stop()
        await broker.close()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
