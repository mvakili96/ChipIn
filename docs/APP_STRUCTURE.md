# App Structure

This document reflects the current layout of the ChipIn repo.

```bash
chipin/
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
│   │   └── users.py
│   ├── services/
│   │   └── redis_service.py
│   ├── static/
│   │   └── client/
│   │       ├── app.js
│   │       ├── chipin-mark.svg
│   │       ├── index.html
│   │       └── styles.css
│   └── tests/
│       ├── test_client.py
│       ├── conftest.py
│       ├── test_expenses.py
│       ├── test_groups.py
│       └── test_users.py
└── docs/
    ├── APP_STRUCTURE.md
    ├── COMMANDS.md
    └── GET_STARTED_REDIS-STACK.md
```

## What Each Part Does

- `docker-compose.yml`:
  Runs the Flask app container and the Redis Stack container together.

- `Dockerfile`:
  Builds the application image and installs Python dependencies.

- `app/main.py`:
  Flask entrypoint. Registers the `users`, `groups`, `expenses`, and `settlements` blueprints, serves the web client at `/client`, and exposes a small health-style Redis test route.

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

- `app/services/redis_service.py`:
  Redis access layer. Handles JSON storage, search indexes, and query helpers for users, groups, expenses, and settlements.

- `app/static/client/`:
  Static browser client for creating people, groups, and expenses and viewing balances.

- `app/tests/`:
  Pytest-based API tests using a mocked in-memory Redis service.
  - `test_client.py`: web client serving tests
  - `conftest.py`: shared fixtures and mock service
  - `test_users.py`: user route tests
  - `test_groups.py`: group route tests
  - `test_expenses.py`: expense route tests

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
