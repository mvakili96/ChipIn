# App Structure

This document reflects the current layout of the ChipIn repo.

```bash
chipin/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── manual-cd.yml
├── docker-compose.yml
├── Dockerfile
├── app/
│   ├── main.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── uwsgi.ini
│   ├── models/
│   │   ├── expense.py
│   │   ├── group.py
│   │   ├── settlement.py
│   │   └── user.py
│   ├── routes/
│   │   ├── expenses.py
│   │   ├── groups.py
│   │   ├── settlements.py
│   │   ├── telegram.py
│   │   └── users.py
│   ├── services/
│   │   ├── redis_service.py
│   │   ├── telegram_auth.py
│   │   └── telegram_bot.py
│   ├── static/
│   │   ├── admin/
│   │   │   ├── app.js
│   │   │   ├── chipin-mark.svg
│   │   │   ├── index.html
│   │   │   └── styles.css
│   │   └── telegram/
│   │       ├── app.js
│   │       ├── index.html
│   │       └── styles.css
│   └── tests/
│       ├── conftest.py
│       ├── test_api_contracts.py
│       ├── test_telegram.py
│       ├── test_admin.py
│       ├── test_expenses.py
│       ├── test_groups.py
│       ├── test_main.py
│       ├── test_models.py
│       ├── test_redis_service.py
│       ├── test_settlement_model.py
│       ├── test_settlements.py
│       └── test_users.py
└── docs/
    ├── APP_STRUCTURE.md
    ├── COMMANDS.md
    └── GET_STARTED_REDIS-STACK.md
```

## What Each Part Does

- `.github/workflows/ci.yml`:
  Runs the GitHub Actions CI workflow on pushes and pull requests targeting `main`. Its `test` job runs pytest with mocked Redis, while its `integration` job builds the Docker Compose stack and exercises the core API flow against real Redis Stack.

- `.github/workflows/manual-cd.yml`:
  Runs the manual deployment workflow on a self-hosted GitHub Actions runner. It updates the server checkout to the latest `main`, rebuilds and restarts only the `app` service, and leaves Redis and ngrok untouched.

- `docker-compose.yml`:
  Runs the Flask app container and the Redis Stack container together.

- `Dockerfile`:
  Builds the application image and installs Python dependencies.

- `app/main.py`:
  Flask entrypoint. Registers the `users`, `groups`, `expenses`, `settlements`, and `telegram` blueprints, serves the admin panel at `/admin/`, serves the Telegram Mini App at `/telegram/`, and exposes a small health-style Redis test route.

- `app/models/`:
  Domain objects and settlement logic.
  - `user.py`: user entity
  - `group.py`: group entity
  - `expense.py`: expense entity
  - `settlement.py`: computes balances/settlements from expenses

- `app/routes/`:
  HTTP API endpoints grouped by resource.
  - `users.py`: create and fetch users
  - `groups.py`: create, fetch, and delete groups
  - `expenses.py`: create, fetch, and delete expenses; fetch expenses by group and by payer
  - `settlements.py`: fetch settlements by group, across all groups, and by user involvement
  - `telegram.py`: Telegram Mini App auth/client API routes and bot webhook handling

- `app/services/redis_service.py`:
  Redis access layer. Handles JSON storage, search indexes, and query helpers for users, groups, expenses, and settlements.

- `app/services/telegram_auth.py`:
  Validates Telegram Mini App `initData` before the client API trusts a Telegram identity.

- `app/services/telegram_bot.py`:
  Minimal Telegram Bot API client used by the webhook route to send Mini App buttons and balance replies.

- `app/static/admin/`:
  Static admin panel for creating and viewing users, creating groups and expenses, and viewing balances.

- `app/static/telegram/`:
  Static Telegram Mini App client for user-facing groups, expenses, balances, and settlements.

- `app/tests/`:
  Pytest-based route, unit, and static smoke tests. Route tests use a mocked in-memory Redis service so they run quickly without depending on Redis state.
  - `conftest.py`: shared Flask app/client fixtures, helpers, and mock Redis service
  - `test_api_contracts.py`: API response shape, type, and error contract tests
  - `test_admin.py`: admin panel and static asset smoke tests
  - `test_users.py`: user route tests
  - `test_groups.py`: group route tests
  - `test_telegram.py`: Telegram auth, Mini App route, group linking, expense creation, and webhook tests
  - `test_expenses.py`: expense route tests
  - `test_main.py`: root API metadata smoke test
  - `test_models.py`: model serialization unit tests
  - `test_redis_service.py`: focused Redis service helper unit tests
  - `test_settlement_model.py`: settlement calculation unit tests
  - `test_settlements.py`: settlement route tests

- `app/requirements.txt`:
  Python dependencies for the app and tests.

- `app/pytest.ini`:
  Pytest configuration.

- `app/uwsgi.ini`:
  uWSGI configuration used by the container image.

- `docs/COMMANDS.md`:
  Example curl commands for using the API.

- `docs/GET_STARTED_REDIS-STACK.md`:
  Notes on Redis Stack, JSON documents, and search indexing.

- `docs/APP_STRUCTURE.md`:
  This file.
