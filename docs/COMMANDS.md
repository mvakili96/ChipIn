# Commands

## Docker Compose
docker compose up --build

## User Commands
In order to add a user:
```bash
curl -X POST http://localhost/users/ \
     -H "Content-Type: application/json" \
     -d '{"name": "Moe", "email": "moe@example.com"}'
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

To get an attribute of a user:
```bash
curl -s http://localhost/users/<user_id>/<key>
```
where key is an attribute like the name, email, and so on.

## Group Commands
In order to add a group:
```bash
curl -X POST http://localhost/groups/ \
     -H "Content-Type: application/json" \
     -d '{"name": "Calgary", "users": ["Moein","Mostafa","Mohammadjavad"]}'
```
it returns a Dictionary containing the group's information. Note that users must be valid, previously defined users.

To get all groups:
```bash
curl -s http://localhost/groups/
```
it returns a list of Dictionaries containing the groups' information.

To get a group:
```bash
curl -s http://localhost/groups/<group_id>
```
it returns a Dictionary containing the group's information.

To get an attribute of a group:
```bash
curl -s http://localhost/groups/<group_id>/<key>
```
where key is an attribute like the name, users, and so on.

To delete a group:
```bash
curl -X DELETE http://localhost/groups/<group_id>
```
it deletes the entire group, its corresponding expenses, and all associated settlements from the database.

## Expense Commands
In order to add an expense:
```bash
curl -X POST http://localhost/expenses/ \
     -H "Content-Type: application/json" \
     -d '{"name": "Costco", "group": "Calgary", "amount": 63.74, "payer": "Moein", "sharers": ["Moein","Mostafa"]}'
```
it returns a Dictionary containing the expenses's information. It also creates/updates settlements.

To get all expenses:
```bash
curl -s http://localhost/expenses/
```
it returns a list of Dictionaries containing the expenses' information.

To get an expense:
```bash
curl -s http://localhost/expenses/<expense_id>
```
it returns a Dictionary containing the expense's information.

To get an attribute of an expense:
```bash
curl -s http://localhost/expenses/<expense_id>/<key>
```
where key is an attribute like the name, payer, and so on.

To delete an expense:
```bash
curl -X DELETE http://localhost/expenses/<expense_id>
```
it deletes the entire expense from database followed by updating settlements.

To get the expenses of a group:
```bash
curl -s http://localhost/expenses/group/<group_id>
```
it returns a list of Dictionaries containing each expense's information. 

To get all the expenses paid by a user within all groups:
```bash
curl -s http://localhost/expenses/user/paid/<user_id>
```
it returns a list of Dictionaries containing each expense whose payer is the user with the given ID.

## Settlement Commands
To get settlements of all groups within the database:
```bash
curl -s http://localhost/settlements/group/
```
it returns a Dictionary where each value is a list that represents the settlements of its corresponding group. The keys are in the format of "settlement-group:group_id".

To get the settlements of a group:
```bash
curl -s http://localhost/settlements/group/<group_id>
```
it returns a list of settlements where each settlement is a list of 3 elements. First element is the debtor, second is the creditor, and the third is the amount of money. 

To get the settlements involving a user:
```bash
curl -s http://localhost/settlements/user/<user_id>
```
it returns a list of settlements where the user is either the debtor or the creditor. The format is the same 3-element settlement format already used for groups.


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
