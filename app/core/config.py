from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "payment-processing-service"
    app_env: str = "dev"
    api_v1_prefix: str = "/api/v1"
    api_key: str = "dev-api-key"

    postgres_db: str = "payments_db"
    postgres_user: str = "payments_user"
    postgres_password: str = "payments_pass"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"

    database_url: str | None = None
    sync_database_url: str | None = None

    outbox_poll_interval_seconds: float = 1.0
    outbox_batch_size: int = 100
    payments_exchange: str = "payments"
    payments_routing_key: str = "payments.new"
    payments_queue: str = "payments.new"
    payments_dlq: str = "payments.dlq"

    webhook_timeout_seconds: float = 10.0
    payment_processing_min_delay_seconds: int = 2
    payment_processing_max_delay_seconds: int = 5
    payment_success_rate: float = 0.9
    max_processing_attempts: int = 3

    @computed_field
    @property
    def rabbitmq_url(self) -> str:
        vhost = self.rabbitmq_vhost
        if vhost.startswith("/"):
            vhost = vhost[1:]
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@"
            f"{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"
        )

    @computed_field
    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def effective_sync_database_url(self) -> str:
        if self.sync_database_url:
            return self.sync_database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
