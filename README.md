# Payment Processing Service

Асинхронный микросервис процессинга платежей, реализованный в рамках тестового задания для Python Backend / Fintech позиции.

## Описание проекта

Сервис принимает запрос на создание платежа, сохраняет платеж и outbox-событие в одной транзакции, публикует событие в RabbitMQ и обрабатывает его отдельным consumer-процессом. После обработки обновляется статус платежа и отправляется webhook-уведомление.

## Стек технологий

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 Async
- PostgreSQL
- Alembic
- RabbitMQ
- FastStream
- Docker
- Docker Compose

## Реализованный функционал

- REST API для создания и получения платежей
- авторизация по API key через заголовок `X-API-Key`
- защита от дублей через `Idempotency-Key`
- асинхронная работа с PostgreSQL
- миграции базы данных через Alembic
- публикация событий через RabbitMQ
- реализация Outbox pattern
- отдельный consumer для обработки платежей
- эмуляция внешнего платежного шлюза
- webhook-уведомления после завершения обработки
- retry-механизм с экспоненциальной задержкой
- Dead Letter Queue для неуспешных сообщений
- контейнеризированный запуск через Docker Compose

## Сценарий обработки

1. Клиент отправляет запрос на создание платежа.
2. API сохраняет запись о платеже и outbox-событие в одной транзакции.
3. Outbox publisher публикует событие в RabbitMQ.
4. Consumer получает сообщение и запускает обработку платежа.
5. После обработки consumer обновляет статус платежа.
6. Consumer отправляет webhook по адресу, переданному при создании платежа.
7. При временных ошибках выполняются повторные попытки обработки.
8. После исчерпания попыток сообщение отправляется в `payments.dlq`.

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
Dockerfile
docker-compose.yml
alembic.ini
pyproject.toml
README.md
.env.example
```

## Переменные окружения

Конфигурация хранится в файле `.env`.

Пример переменных окружения приведён в `.env.example`.

Основные параметры:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `RABBITMQ_USER`
- `RABBITMQ_PASSWORD`
- `RABBITMQ_HOST`
- `RABBITMQ_PORT`
- `RABBITMQ_VHOST`
- `API_KEY`

## Запуск проекта

### Windows CMD

```cmd
copy .env.example .env
docker compose up --build
```

### Остановка и удаление контейнеров и томов

```cmd
docker compose down -v
```

## Доступные сервисы

После запуска доступны следующие адреса:

- API: `http://localhost:8000`
- OpenAPI / Swagger UI: `http://localhost:8000/docs`
- RabbitMQ Management UI: `http://localhost:15672`

Стандартные учетные данные RabbitMQ из `.env.example`:

- username: `guest`
- password: `guest`

## API endpoints

### Создание платежа

`POST /api/v1/payments`

Обязательные заголовки:

- `X-API-Key`
- `Idempotency-Key`

Пример тела запроса:

```json
{
  "amount": 1500.50,
  "currency": "RUB",
  "description": "Test payment",
  "metadata": {
    "order_id": "ORD-1"
  },
  "webhook_url": "https://webhook.site/replace-me"
}
```

Ожидаемый ответ:

- `202 Accepted`
- `payment_id`
- `status = pending`

### Получение информации о платеже

`GET /api/v1/payments/{payment_id}`

Обязательный заголовок:

- `X-API-Key`

Ожидаемый ответ:

- `200 OK`
- данные платежа
- текущий статус: `pending`, `succeeded` или `failed`

## Ручная проверка

### 1. Создание платежа

```cmd
curl -X POST "http://localhost:8000/api/v1/payments" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: <your-api-key>" ^
  -H "Idempotency-Key: payment-001" ^
  -d "{\"amount\":1500.50,\"currency\":\"RUB\",\"description\":\"Test payment\",\"metadata\":{\"order_id\":\"ORD-1\"},\"webhook_url\":\"https://webhook.site/replace-me\"}"
```

Ожидаемый результат:

- HTTP `202 Accepted`
- в ответе присутствует `payment_id`
- начальный статус платежа — `pending`

### 2. Получение информации о платеже

```cmd
curl -X GET "http://localhost:8000/api/v1/payments/<payment_id>" ^
  -H "X-API-Key: <your-api-key>"
```

Ожидаемый результат:

- HTTP `200 OK`
- через несколько секунд статус становится `succeeded` или `failed`

### 3. Проверка идемпотентности

Нужно повторить тот же `POST` запрос с тем же `Idempotency-Key`.

Ожидаемый результат:

- возвращается тот же `payment_id`
- дубликат платежа не создаётся

### 4. Проверка webhook

Нужно указать `webhook_url` на временный endpoint, например webhook.site, и создать платеж.

Ожидаемый результат:

- после обработки на указанный endpoint приходит POST-запрос с результатом обработки платежа

### 5. Проверка брокера и очередей

В интерфейсе RabbitMQ нужно проверить очереди:

- `payments.new`
- `payments.dlq`

## Гарантии и надёжность

### Идемпотентность

`Idempotency-Key` используется для защиты от повторного создания одного и того же платежа при повторной отправке запроса клиентом.

### Outbox Pattern

Запись о платеже и событие для публикации сохраняются в рамках одной транзакции, что исключает потерю события после успешной записи платежа в базу данных.

### Retry и DLQ

Если обработка платежа или отправка webhook завершается ошибкой, consumer выполняет до трёх повторных попыток с экспоненциальной задержкой. Если все попытки исчерпаны, сообщение отправляется в dead-letter очередь `payments.dlq`.

## Что покрывает решение

Реализация покрывает основные требования тестового задания:

- асинхронный API
- асинхронная работа с базой данных
- идемпотентное создание платежей
- событийная обработка через RabbitMQ
- транзакционный outbox
- отдельный consumer-процесс
- webhook-уведомления
- retry-механизм
- dead-letter queue
- контейнеризированное локальное окружение

## Примечание

Проект выполнен как тестовое задание и сфокусирован на корректности бизнес-потока, декомпозиции сервиса и паттернах надёжности. Вне рамок задания остались вопросы production-уровня, такие как полноценная observability-интеграция, централизованное логирование, tracing, метрики, секрет-менеджмент и политика горизонтального масштабирования.
