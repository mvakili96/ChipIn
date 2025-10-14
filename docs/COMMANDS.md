# Commands

## Docker Compose
docker compose up --build

## User Commands
In order to add a user:
```bash
curl -X POST http://localhost/users/ \
     -H "Content-Type: application/json" \
     -d '{"name": "Moe", "email": "moe@example.com"}
```
it returns a Dictionary containing the user's information.
