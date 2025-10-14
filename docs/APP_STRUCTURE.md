# File Structure
The suggested file structure for the ChipIn application is as follows:

```bash
chipin/
├── docker-compose.yml
├── Dockerfile
└── app/
    ├── main.py
    ├── requirements.txt
    ├── uwsgi.ini
    ├── models/
    │   ├── user.py
    │   ├── group.py
    │   └── expense.py
    ├── routes/
    │   ├── users.py
    │   ├── groups.py
    │   └── expenses.py
    └── services/
        └── redis_service.py
```
