import os
import redis
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from typing import Any
import json
from redis.commands.search.query import Query
from models.settlement import Settlement


class RedisService:
    def __init__(self):
        self.client: redis.Redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
        )
        self._create_indexes()

    def _create_indexes(self):
        rebuild = os.getenv("REBUILD_INDEXES", "0") == "1"

        try:
            # User index
            users_schema = (
                TextField("$.name", as_name="name"),
                TagField("$.email", as_name="email"),
                TagField("$.id", as_name="id"),
                TextField("$.created_at", as_name="created_at"),
            )
            users_def = IndexDefinition(prefix=["user:"], index_type=IndexType.JSON)

            # Group index
            groups_schema = (
                TextField("$.name", as_name="name"),
                TagField("$.users[*]", as_name="users"),
                TagField("$.id", as_name="id"),
                TextField("$.created_at", as_name="created_at"),
            )
            groups_def = IndexDefinition(prefix=["group:"], index_type=IndexType.JSON)

            # Expense index
            expenses_schema = (
                TextField("$.name", as_name="name"),
                TagField("$.group", as_name="group"),
                NumericField("$.amount", as_name="amount"),
                TagField("$.payer", as_name="payer"),
                TagField("$.sharers[*]", as_name="sharers"),
                TagField("$.id", as_name="id"),
                TextField("$.created_at", as_name="created_at"),
            )
            expenses_def = IndexDefinition(prefix=["expense:"], index_type=IndexType.JSON)

            def ensure(index_name: str, schema, definition: IndexDefinition):
                if rebuild:
                    try:
                        self.client.ft(index_name).dropindex(delete_documents=False)
                    except Exception:
                        pass

                # Create index if missing (or after drop)
                try:
                    self.client.ft(index_name).info()
                except Exception:
                    self.client.ft(index_name).create_index(schema, definition=definition)
            
            ensure("idx:users", users_schema, users_def)
            ensure("idx:groups", groups_schema, groups_def)
            ensure("idx:expenses", expenses_schema, expenses_def)
         
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")

    # User operations
    def save_user(self, user_dict: dict[str, str]) -> dict[str, str]:
        key = f"user:{user_dict['id']}"
        _ = self.client.json().set(key, Path.root_path(), user_dict)
        return user_dict

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        key = f"user:{user_id}"
        return self.client.json().get(key)

    def get_all_users(self) -> list[dict]:
        keys = self.client.keys("user:*")
        users = []
        for key in keys:
            user = self.client.json().get(key)
            if user:
                users.append(user)
        return users

    def get_user_attr(self, user_id: str, key: str) -> Any | None:
        redis_key = f"user:{user_id}"
        user = self.client.json().get(redis_key)
        return user.get(key, None)

    def get_all_user_names(self) -> list[str]:
        res = self.client.ft("idx:users").search("*")

        names = []
        for r in res.docs:
            raw_json = getattr(r, "json", None)

            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            name_val = parsed.get("name")
            names.append(name_val)

        return names

    # Group operations
    def save_group(
        self, group_dict: dict[str, str | list[str]]
    ) -> dict[str, str | list[str]]:
        key = f"group:{group_dict['id']}"
        _ = self.client.json().set(key, Path.root_path(), group_dict)
        return group_dict

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        key = f"group:{group_id}"
        return self.client.json().get(key)

    def get_all_groups(self) -> list:
        keys = self.client.keys("group:*")
        groups = []
        for key in keys:
            group = self.client.json().get(key)
            if group:
                groups.append(group)
        return groups

    def get_group_attr(self, group_id: str, key: str) -> Any | None:
        redis_key = f"group:{group_id}"
        group = self.client.json().get(redis_key)
        return group.get(key, None)

    def delete_group(self, group_id: str) -> bool:
        redis_key = f"group:{group_id}"
        group_dict = self.client.json().get(redis_key)
        if not group_dict:
            return False
        
        group_name = group_dict["name"]
        if not group_name:
            return False
        
        q = Query(f"@group:{{{group_name}}}").paging(0, 10_000)
        res = self.client.ft("idx:expenses").search(q)

        for doc in res.docs:
            self.client.delete(doc.id)  

        self.client.delete(f"settlement-group:{group_id}")

        result = self.client.delete(redis_key)
        return result == 1
        
    def get_group_by_name(self, name: str) -> dict[str, Any] | None:
        q = Query(f'@name:"{name}"')
        res = self.client.ft("idx:groups").search(q)

        if res.total == 0:
            return None

        doc = res.docs[0]
        key = doc.id
        return self.client.json().get(key)
    
    # Expense operations
    def save_expense(
        self, expense_dict: dict[str, Any]
    ) -> dict[str, Any]:
        key = f"expense:{expense_dict['id']}"
        _ = self.client.json().set(key, Path.root_path(), expense_dict)
        return expense_dict
    
    def get_all_expenses(self) -> list:
        keys = self.client.keys("expense:*")
        expenses = []
        for key in keys:
            expense = self.client.json().get(key)
            if expense:
                expenses.append(expense)
        return expenses
    
    def get_expense(self, expense_id: str) -> dict[str, Any] | None:
        key = f"expense:{expense_id}"
        return self.client.json().get(key)
    
    def get_expense_attr(self, expense_id: str, key: str) -> Any | None:
        redis_key = f"expense:{expense_id}"
        expense = self.client.json().get(redis_key)
        return expense.get(key, None)
    
    def delete_expense(self, expense_id: str) -> bool:
        redis_key = f"expense:{expense_id}"
        expense_dict = self.client.json().get(redis_key)
        if not expense_dict:
            return False
        
        group_name = expense_dict["group"]
        group_dict = self.get_group_by_name(group_name)
        if not group_dict:
            return False
        
        group_id =  group_dict["id"]
        group_users = group_dict["users"]

        result = self.client.delete(redis_key)

        group_expenses = self.get_group_expenses(group_id)
        tx = Settlement(group_expenses,group_users)

        settlement_key = f"settlement-group:{group_dict['id']}"
        tx_json = [list(t) for t in tx]
        self.client.json().set(settlement_key, Path.root_path(), tx_json)
        return result == 1
    
    def get_group_expenses(self, group_id: str):
        group_dict  = self.client.json().get(f"group:{group_id}")
        
        q = Query(f'@group:{{{group_dict["name"]}}}').paging(0, 10_000)
        res = self.client.ft("idx:expenses").search(q)

        group_expenses: list[dict[str, Any]] = []
        for doc in res.docs:
            exp = self.client.json().get(doc.id)
            if not exp:
                continue

            group_expenses.append({
                "name": exp.get("name"),
                "group": exp.get("group"),
                "amount": exp.get("amount"),
                "payer": exp.get("payer"),
                "sharers": exp.get("sharers"),
            })
        return group_expenses

    # Settlement operations
    def save_group_settlements(self, settlement: list[list], key: str) -> list[list]:
        _ = self.client.json().set(key, Path.root_path(), settlement)
        return settlement
    
    def get_all_group_settlements(self) -> list:
        keys = self.client.keys("settlement-group:*")
        groups_settlements = {}
        for key in keys:
            settlement = self.client.json().get(key)
            if settlement:
                groups_settlements[key] = settlement
        return groups_settlements

    def get_group_settlements(self, group_id: str) -> list[list]:
        settlement_key = f"settlement-group:{group_id}"
        return self.client.json().get(settlement_key)
    



# Singleton instance
redis_service = RedisService()
