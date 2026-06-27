# Getting Started with Redis Stack for Expense Tracking

This guide explains how to set up a Redis-Stack container, define expenses as JSON documents, index them, and perform queries using the Redis CLI.

---

## 1. Run the Redis Stack Container

```bash
docker run --rm --name redis-stack -p 6379:6379 redis/redis-stack
```

---

## 2. Access the Redis CLI

```bash
docker exec -it redis-stack redis-cli
```

---

## 3. Define Expenses on CLI

Each expense is stored as a separate JSON document using **RedisJSON**.

```bash
JSON.SET expense:1 $ '{"id": "1", "name": "Walmart", "group": "Calgary", "amount": 500, "payer": "Alex", "sharers": ["Alex", "Dan", "Joe"], "created_at": "2026-06-21T00:00:00"}'
JSON.SET expense:2 $ '{"id": "2", "name": "Airbnb", "group": "Calgary", "amount": 435, "payer": "Dan", "sharers": ["Dan", "Joe"], "created_at": "2026-06-21T00:00:00"}'
JSON.SET expense:3 $ '{"id": "3", "name": "Bar", "group": "Calgary", "amount": 56, "payer": "Joe", "sharers": ["Dan", "Joe"], "created_at": "2026-06-21T00:00:00"}'
JSON.SET expense:4 $ '{"id": "4", "name": "Car rental", "group": "Vancouver", "amount": 189, "payer": "Joe", "sharers": ["Alex", "Joe"], "created_at": "2026-06-21T00:00:00"}'
```

---

## 4. Print Values on CLI

Retrieve the full JSON object or a specific field:

```bash
JSON.GET expense:2
JSON.GET expense:2 $.payer
```

---

## 5. Create an Index for Querying on CLI

Before querying, create an index using **RediSearch**.

```bash
FT.CREATE idx:expense ON JSON PREFIX 1 "expense:" SCHEMA \
  $.name        AS name        TEXT \
  $.group       AS group       TAG \
  $.amount      AS amount      NUMERIC SORTABLE \
  $.payer       AS payer       TAG \
  $.sharers[*]  AS sharers     TAG \
  $.id          AS id          TAG \
  $.created_at  AS created_at  TEXT
```

---

## 6. Query Examples on CLI

### Expenses greater than 300
```bash
FT.SEARCH idx:expense '@amount:[(300 +inf]'
```

### Expenses paid by Joe
```bash
FT.SEARCH idx:expense '@payer:{Joe}'
```

### Expenses for a group
```bash
FT.SEARCH idx:expense '@group:{Calgary}'
```

### Expenses shared with Alex
```bash
FT.SEARCH idx:expense '@sharers:{Alex}'
```

---

## 7. Stop and Clean Up

```bash
docker stop redis-stack
```

---

## 8. Notes and Tips

- **Redis Stack** includes both RedisJSON and RediSearch for JSON storage + querying.
- You can connect this Redis Stack container to a **Flask (Tiangolo) container**.
- The app's route tests use a mocked in-memory Redis service; real Redis Stack integration tests are deferred to a separate focused pass.
- Add a numeric timestamp field, such as `created_at_ts`, if you plan to run range queries on dates.

---

**Date:** June 2026
