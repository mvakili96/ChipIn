import os
import redis
import uuid
from datetime import datetime
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
                TagField("$.telegram_id", as_name="telegram_id"),
                TextField("$.created_at", as_name="created_at"),
            )
            users_def = IndexDefinition(prefix=["user:"], index_type=IndexType.JSON)

            # Group index
            groups_schema = (
                TextField("$.name", as_name="name"),
                TagField("$.users[*]", as_name="users"),
                TagField("$.id", as_name="id"),
                TagField("$.source", as_name="source"),
                TagField("$.telegram_chat_id", as_name="telegram_chat_id"),
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

    @staticmethod
    def _escape_tag_value(value: str) -> str:
        special_chars = r',.<>{}[]"\'\\:;!@#$%^&*()-+=~ '
        return "".join(f"\\{char}" if char in special_chars else char for char in str(value))

    @staticmethod
    def _expense_summary(expense: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": expense.get("id"),
            "name": expense.get("name"),
            "group": expense.get("group"),
            "group_id": expense.get("group_id"),
            "amount": expense.get("amount"),
            "payer": expense.get("payer"),
            "sharers": expense.get("sharers"),
        }

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

    def get_user_by_telegram_id(self, telegram_id: int | str) -> dict[str, Any] | None:
        target_id = str(telegram_id)
        for user in self.get_all_users():
            if str(user.get("telegram_id")) == target_id:
                return user
        return None

    def get_user_by_name(self, name: str) -> dict[str, Any] | None:
        target_name = name.strip()
        for user in self.get_all_users():
            if user.get("name") == target_name:
                return user
        return None

    def upsert_telegram_user(self, telegram_user: dict[str, Any]) -> dict[str, Any]:
        telegram_id = str(telegram_user["id"])
        existing = self.get_user_by_telegram_id(telegram_id)

        if existing:
            existing.update(self._telegram_identity_fields(telegram_user))
            existing["updated_at"] = datetime.now().isoformat()
            return self.save_user(existing)

        display_name = self._telegram_display_name(telegram_user)
        matching_user = self.get_user_by_name(display_name)
        if matching_user and not matching_user.get("telegram_id"):
            return self.link_telegram_user(matching_user["id"], telegram_user)

        user_dict = {
            "name": self._unique_telegram_user_name(display_name, telegram_id),
            "email": f"telegram-{telegram_id}@telegram.local",
            "id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "source": "telegram",
            **self._telegram_identity_fields(telegram_user),
        }
        return self.save_user(user_dict)

    def link_telegram_user(
        self, user_id: str, telegram_user: dict[str, Any]
    ) -> dict[str, Any] | None:
        user = self.get_user(user_id)
        if not user:
            return None

        telegram_id = str(telegram_user["id"])
        existing = self.get_user_by_telegram_id(telegram_id)
        if existing and existing.get("id") != user_id:
            return existing

        user.update(self._telegram_identity_fields(telegram_user))
        user["telegram_linked_at"] = datetime.now().isoformat()
        user["updated_at"] = datetime.now().isoformat()
        return self.save_user(user)

    def _telegram_identity_fields(self, telegram_user: dict[str, Any]) -> dict[str, Any]:
        return {
            "telegram_id": str(telegram_user["id"]),
            "telegram_username": telegram_user.get("username"),
            "telegram_first_name": telegram_user.get("first_name"),
            "telegram_last_name": telegram_user.get("last_name"),
            "telegram_photo_url": telegram_user.get("photo_url"),
            "telegram_language_code": telegram_user.get("language_code"),
        }

    def _telegram_display_name(self, telegram_user: dict[str, Any]) -> str:
        first_name = (telegram_user.get("first_name") or "").strip()
        last_name = (telegram_user.get("last_name") or "").strip()
        username = (telegram_user.get("username") or "").strip()
        telegram_id = str(telegram_user["id"])

        display_name = " ".join(part for part in [first_name, last_name] if part).strip()
        if display_name:
            return display_name

        return f"@{username}" if username else f"Telegram User {telegram_id}"

    def _unique_telegram_user_name(self, base_name: str, telegram_id: str) -> str:
        existing_names = set(self.get_all_user_names())
        if base_name not in existing_names:
            return base_name

        candidate = f"{base_name} ({telegram_id})"
        counter = 2
        while candidate in existing_names:
            candidate = f"{base_name} ({telegram_id}-{counter})"
            counter += 1
        return candidate

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
        
        for key in self.client.keys("expense:*"):
            expense = self.client.json().get(key)
            if not expense:
                continue

            is_group_expense = expense.get("group_id") == group_id
            is_legacy_group_expense = (
                not expense.get("group_id") and expense.get("group") == group_name
            )
            if is_group_expense or is_legacy_group_expense:
                self.client.delete(key)

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

    def get_group_by_telegram_chat_id(
        self, telegram_chat_id: int | str
    ) -> dict[str, Any] | None:
        target_id = str(telegram_chat_id)
        for group in self.get_all_groups():
            if str(group.get("telegram_chat_id")) == target_id:
                return group
        return None

    def ensure_telegram_group(self, chat: dict[str, Any]) -> dict[str, Any]:
        chat_id = str(chat["id"])
        existing = self.get_group_by_telegram_chat_id(chat_id)
        if existing:
            existing["telegram_chat_title"] = chat.get("title") or existing.get("telegram_chat_title")
            existing["telegram_chat_type"] = chat.get("type") or existing.get("telegram_chat_type")
            existing["updated_at"] = datetime.now().isoformat()
            return self.save_group(existing)

        name = self._unique_telegram_group_name(chat)
        group_dict = {
            "name": name,
            "users": [],
            "id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "source": "telegram",
            "telegram_chat_id": chat_id,
            "telegram_chat_title": chat.get("title"),
            "telegram_chat_type": chat.get("type"),
        }
        return self.save_group(group_dict)

    def add_user_to_group(self, group_id: str, user_name: str) -> dict[str, Any] | None:
        group = self.get_group(group_id)
        if not group:
            return None

        users = group.get("users") or []
        if user_name not in users:
            users.append(user_name)
            group["users"] = users
            group["updated_at"] = datetime.now().isoformat()
            self.save_group(group)

        return group

    def get_groups_for_user(self, user_name: str) -> list[dict[str, Any]]:
        return [
            group
            for group in self.get_all_groups()
            if user_name in (group.get("users") or [])
        ]

    def _unique_telegram_group_name(self, chat: dict[str, Any]) -> str:
        title = (chat.get("title") or chat.get("username") or "").strip()
        chat_id = str(chat["id"])
        base_name = title or f"Telegram Group {chat_id}"

        existing_names = {group.get("name") for group in self.get_all_groups()}
        if base_name not in existing_names:
            return base_name

        candidate = f"{base_name} ({chat_id})"
        counter = 2
        while candidate in existing_names:
            candidate = f"{base_name} ({chat_id}-{counter})"
            counter += 1
        return candidate
    
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
        
        group_id = expense_dict.get("group_id")
        group_dict = self.get_group(group_id) if group_id else None
        if not group_dict:
            group_name = expense_dict["group"]
            group_dict = self.get_group_by_name(group_name)
        if not group_dict:
            return False
        
        group_id = group_dict["id"]
        group_users = group_dict["users"]

        result = self.client.delete(redis_key)

        group_expenses = self.get_group_expenses(group_id)
        tx = Settlement(group_expenses,group_users)

        settlement_key = f"settlement-group:{group_dict['id']}"
        tx_json = [list(t) for t in tx]
        self.client.json().set(settlement_key, Path.root_path(), tx_json)
        return result == 1

    def delete_expense_record(self, expense_id: str) -> bool:
        redis_key = f"expense:{expense_id}"
        result = self.client.delete(redis_key)
        return result == 1
    
    def get_group_expenses(self, group_id: str):
        group_dict  = self.client.json().get(f"group:{group_id}")
        if not group_dict:
            return []
        
        group_expenses: list[dict[str, Any]] = []
        for key in self.client.keys("expense:*"):
            exp = self.client.json().get(key)
            if not exp:
                continue

            is_group_expense = exp.get("group_id") == group_id
            is_legacy_group_expense = (
                not exp.get("group_id") and exp.get("group") == group_dict["name"]
            )
            if not is_group_expense and not is_legacy_group_expense:
                continue

            group_expenses.append(self._expense_summary(exp))
        return group_expenses

    def get_user_paid_expenses(self, user_id: str):
        user_dict = self.client.json().get(f"user:{user_id}")
        if not user_dict:
            return []

        payer = self._escape_tag_value(user_dict["name"])
        q = Query(f"@payer:{{{payer}}}").paging(0, 10_000)
        res = self.client.ft("idx:expenses").search(q)

        user_expenses: list[dict[str, Any]] = []
        for doc in res.docs:
            exp = self.client.json().get(doc.id)
            if not exp:
                continue

            user_expenses.append(self._expense_summary(exp))
        return user_expenses

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

    def save_settlement_payment(
        self, group_id: str, payment_dict: dict[str, Any]
    ) -> dict[str, Any]:
        payment_key = f"settlement-payment-group:{group_id}"
        payments = self.client.json().get(payment_key) or []

        if "id" not in payment_dict:
            payment_dict["id"] = str(uuid.uuid4())
        if "created_at" not in payment_dict:
            payment_dict["created_at"] = datetime.now().isoformat()

        payments.append(payment_dict)
        self.client.json().set(payment_key, Path.root_path(), payments)
        return payment_dict

    def get_group_settlement_payments(self, group_id: str) -> list[dict[str, Any]]:
        payment_key = f"settlement-payment-group:{group_id}"
        return self.client.json().get(payment_key) or []
    



# Singleton instance
redis_service = RedisService()
