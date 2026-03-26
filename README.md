# Payment Processing Service

Асинхронный микросервис процессинга платежей для тестового задания.

## Что реализовано
- FastAPI + Pydantic v2
- SQLAlchemy 2.0 async + PostgreSQL
- Alembic миграции
- RabbitMQ + FastStream
- API key авторизация через `X-API-Key`
- `POST /api/v1/payments`
- `GET /api/v1/payments/{payment_id}`
- Idempotency-Key для защиты от дублей
- Outbox pattern: запись в `payments` и `outbox_events` в одной транзакции
- Фоновый outbox publisher в API-сервисе
- Consumer-сервис, который читает `payments.new`
- Эмуляция платежного шлюза: 2-5 сек, 90% успех, 10% ошибка
- Webhook уведомление клиента
- Retry 3 попытки с экспоненциальной задержкой
- Dead Letter Queue: `payments.dlq`
- Docker + docker-compose

## Архитектура
1. Клиент создает платеж через API.
2. Платеж и outbox-событие сохраняются в одной транзакции.
3. Outbox publisher публикует событие в RabbitMQ exchange `payments` с routing key `payments.new`.
4. Consumer получает событие, эмулирует обработку, обновляет статус платежа и отправляет webhook.
5. Если обработка или webhook падают, consumer делает до 3 попыток.
6. После 3 неудач сообщение уходит в DLQ `payments.dlq`.

## Структура проекта
```text
app/
  api/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
  utils/
  workers/
  broker.py
  main.py
alembic/
docker-compose.yml
Dockerfile
README.md
```

## Запуск
### Windows CMD
```cmd
copy .env.example .env
docker compose up --build
```

### После запуска
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- RabbitMQ UI: `http://localhost:15672`
  - login: `guest`
  - password: `guest`

## Ручная проверка
### 1. Создать платеж
```cmd
curl -X POST "http://localhost:8000/api/v1/payments" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: super-secret-api-key" ^
  -H "Idempotency-Key: payment-001" ^
  -d "{\"amount\":1500.50,\"currency\":\"RUB\",\"description\":\"Test payment\",\"metadata\":{\"order_id\":\"ORD-1\"},\"webhook_url\":\"https://webhook.site/replace-me\"}"
```

Ожидаемо: `202 Accepted`, в ответе `payment_id`, `status=pending`, `created_at`.

### 2. Проверить платеж
```cmd
curl -X GET "http://localhost:8000/api/v1/payments/<payment_id>" ^
  -H "X-API-Key: super-secret-api-key"
```

Через несколько секунд статус станет `succeeded` или `failed`.

### 3. Проверить идемпотентность
Повтори тот же `POST` с тем же `Idempotency-Key`. Должен вернуться тот же `payment_id`.

### 4. Проверить RabbitMQ
Открой `http://localhost:15672`:
- Queues -> `payments.new`
- Queues -> `payments.dlq`

### 5. Проверить webhook
Укажи `webhook_url` через webhook.site и убедись, что после обработки пришел POST с результатом платежа.

## Полезные команды
### Остановить и удалить контейнеры с томами
```cmd
docker compose down -v
```

### Перезапуск после изменений
```cmd
docker compose up --build
```

## Переменные окружения
Смотри `.env.example`.

## Что важно для оценки
- API принимает платеж и не создает дубликаты по `Idempotency-Key`
- Outbox событие создается вместе с платежом
- Сообщение попадает в RabbitMQ
- Consumer обрабатывает сообщение и обновляет статус
- Webhook отправляется после обработки
- При ошибках есть retry и DLQ
