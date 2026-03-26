from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

from app.core.config import settings

payments_exchange = RabbitExchange(
    name=settings.payments_exchange,
    type=ExchangeType.DIRECT,
    durable=True,
)

payments_dlq = RabbitQueue(
    name=settings.payments_dlq,
    durable=True,
)

payments_queue = RabbitQueue(
    name=settings.payments_queue,
    durable=True,
    routing_key=settings.payments_routing_key,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": settings.payments_dlq,
    },
)

broker = RabbitBroker(settings.rabbitmq_url)
