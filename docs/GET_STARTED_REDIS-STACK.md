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
JSON.SET expense:1 $ '{"id": "1", "title": "Walmart", "expense": 500, "paid_by": "Alex", "sharers": ["Alex", "Dan", "Joe"], "date": "2024-12-22"}'
JSON.SET expense:2 $ '{"id": "2", "title": "Airbnb", "expense": 435, "paid_by": "Dan", "sharers": ["Dan", "Joe"], "date": "2024-12-10"}'
JSON.SET expense:3 $ '{"id": "3", "title": "bar", "expense": 56, "paid_by": "Joe", "sharers": ["Dan", "Joe"], "date": "2024-12-11"}'
JSON.SET expense:4 $ '{"id": "4", "title": "Car rental", "expense": 189, "paid_by": "Joe", "sharers": ["Alex", "Joe"], "date": "2024-12-16"}'
```

---

## 4. Print Values on CLI

Retrieve the full JSON object or a specific field:

```bash
JSON.GET expense:2
JSON.GET expense:2 $.paid_by
```

---

## 5. Create an Index for Querying on CLI

Before querying, create an index using **RediSearch**.

```bash
FT.CREATE idx:expense ON JSON PREFIX 1 "expense:" SCHEMA \
  $.expense     AS expense  NUMERIC SORTABLE \
  $.paid_by     AS paid_by  TAG \
  $.sharers[*]  AS sharers  TAG \
  $.title       AS title    TEXT \
  $.date        AS date     TAG
```

---

## 6. Query Examples on CLI

### Expenses greater than 300
```bash
FT.SEARCH idx:expense '@expense:[(300 +inf]'
```

### Expenses paid by Joe
```bash
FT.SEARCH idx:expense '@paid_by:{Joe}'
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
- Add a numeric timestamp field (`date_ts`) if you plan to run range queries on dates.

---

**Date:** October 2025

