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

To get all users:
```bash
curl -s http://localhost/users/
```
it returns a list of Dictionaries containing the users' information.

To get a user:
```bash
curl -s http://localhost/users/<user_id>
```
it returns a Dictionary containing the user's information.

## To run tests
If you just changed the code and want to run tests, you should first rebuild the container:
```bash
# Rebuild with new dependencies
docker-compose down
docker-compose up --build -d
```
then run the tests using one of the following commands:
```bash
# Run tests inside container
docker exec -it chipin-app pytest

# Or with more verbose output
docker exec -it chipin-app pytest -v

# Run specific test file
docker exec -it chipin-app pytest tests/test_users.py
```
**NOTE:** Redis_stack was simulated for the tests so the tests run fast without needing the real Redis container.
