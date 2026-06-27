# ChipIn

ChipIn is a containerized Flask + Redis Stack backend for shared expense tracking and settlement calculation.

The project is structured as a small Splitwise-style API: users can be created, grouped together, linked to expenses, and used to derive settlements based on who paid and who shared each expense.

## What This Repository Is For

This repository is an API-focused backend prototype for modeling shared expenses inside groups.

At a high level, the current workflow is:

1. create users
2. create a group with those users
3. create expenses for that group
4. calculate and retrieve resulting settlements

The codebase currently focuses on:

- storing users, groups, expenses, and settlements in Redis JSON documents
- querying expense data through Redis Stack indexes
- exposing resource-oriented HTTP routes with Flask
- serving a small admin panel for the core shared-expense workflow
- running locally through Docker Compose

## Current Functionality

The API currently supports:

- `users`
  - create a user
  - list users
  - fetch a user or one of its attributes

- `groups`
  - create a group from existing users
  - list groups
  - fetch a group or one of its attributes
  - delete a group

- `expenses`
  - create an expense
  - list all expenses
  - fetch a single expense or one of its attributes
  - delete an expense
  - fetch all expenses for a group
  - fetch all expenses paid by a user across groups

- `settlements`
  - fetch settlements for a group
  - fetch settlements for all groups
  - fetch settlements involving a user

- `admin panel`
  - create users, groups, and expenses from the browser
  - view users, groups, expenses, and settlements

- `telegram client`
  - serve a Telegram Mini App at `/telegram/`
  - validate Telegram Mini App init data server-side
  - map Telegram users to ChipIn users
  - link Telegram group chats to ChipIn groups
  - let authenticated Telegram users view their groups and add expenses
  - receive bot updates at `/telegram/webhook/`

## Tech Stack

- Python
- Flask
- Redis Stack
- Docker Compose
- pytest

## Getting Started

The fastest way to run the project locally is through Docker Compose:

```bash
docker compose up --build
```

From there, the main places to look are:

- `http://localhost/admin/` for the admin panel
- `http://localhost/telegram/` for the Telegram Mini App web client
- [docs/COMMANDS.md](docs/COMMANDS.md) for example API usage with `curl`
- [docs/GET_STARTED_REDIS-STACK.md](docs/GET_STARTED_REDIS-STACK.md) for Redis Stack notes and CLI-oriented indexing examples
- [docs/APP_STRUCTURE.md](docs/APP_STRUCTURE.md) for the current repository layout

## Telegram Client Setup

The Telegram client uses ChipIn as the centralized data store. Telegram provides user/chat identity and the Mini App surface, but expenses, groups, users, and settlements stay in Redis through the existing backend.

Configure these environment variables before using the bot integration:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:your-bot-token
TELEGRAM_WEBHOOK_SECRET=your-random-webhook-secret
TELEGRAM_BOT_USERNAME=your_bot_username
PUBLIC_BASE_URL=https://your-public-chipin-host
```

`TELEGRAM_BOT_TOKEN` comes from BotFather. `TELEGRAM_BOT_USERNAME` is the bot username you chose in BotFather, without the leading `@`. `TELEGRAM_WEBHOOK_SECRET` is a random string you create yourself, for example with `openssl rand -hex 32`. `PUBLIC_BASE_URL` is the public HTTPS URL where Telegram can reach this app, such as an ngrok/cloudflared URL or the deployed production URL.

Then configure the bot with BotFather and set the webhook to:

```text
https://your-public-chipin-host/telegram/webhook/
```

Use the same `TELEGRAM_WEBHOOK_SECRET` as Telegram's webhook secret token:

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d "url=$PUBLIC_BASE_URL/telegram/webhook/" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

The Mini App URL is:

```text
https://your-public-chipin-host/telegram/
```

In a Telegram group, send `/chipin` or `/chipin@your_bot_username`. Telegram only allows Mini App `web_app` buttons in private chats, so the group response links users to the bot's private chat first. From there, the bot opens the Mini App for the linked ChipIn group.

## Repository Overview

This is the main shape of the repo:

```text
.
├── app/
│   ├── main.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── tests/
├── docs/
├── Dockerfile
└── docker-compose.yml
```

Key areas:

- [app/main.py](app/main.py): Flask entrypoint and blueprint registration
- [app/routes/](app/routes): API routes for users, groups, expenses, and settlements
- [app/models/](app/models): domain objects and settlement calculation logic
- [app/services/redis_service.py](app/services/redis_service.py): Redis access layer and search/query helpers
- [app/static/admin/](app/static/admin): admin panel served at `/admin/`
- [app/static/telegram/](app/static/telegram): Telegram Mini App client served at `/telegram/`
- [app/tests/](app/tests): route-level tests with a mocked Redis service

## Where To Look First

If you are visiting the repository for the first time:

- start with [app/main.py](app/main.py) to see the registered API surface
- open [docs/COMMANDS.md](docs/COMMANDS.md) to try the routes quickly
- review [app/routes/expenses.py](app/routes/expenses.py) and [app/routes/settlements.py](app/routes/settlements.py) for the core shared-expense flow
- use [docs/APP_STRUCTURE.md](docs/APP_STRUCTURE.md) if you want a fuller map of the codebase

## Notes

- The app is designed to run with Redis Stack and relies on RedisJSON and RediSearch features.
- The Docker setup defines separate `app` and `redis` services in [docker-compose.yml](docker-compose.yml).
- The admin panel is served by Flask at `/admin/` and calls the existing JSON routes directly.
- The Telegram Mini App is served by Flask at `/telegram/` and uses Telegram `initData` for user authentication.
- Tests are written with pytest and use a mocked in-memory Redis service instead of requiring a real Redis instance for test execution.
- Some detailed Redis CLI examples in [docs/GET_STARTED_REDIS-STACK.md](docs/GET_STARTED_REDIS-STACK.md) describe the underlying data ideas, but the application code is the source of truth for the current API field names and route behavior.

## Documentation

- [docs/COMMANDS.md](docs/COMMANDS.md): request examples and test commands
- [docs/GET_STARTED_REDIS-STACK.md](docs/GET_STARTED_REDIS-STACK.md): Redis Stack setup and query background
- [docs/APP_STRUCTURE.md](docs/APP_STRUCTURE.md): current repository structure
