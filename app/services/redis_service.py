import os
import redis
from redis.commands.json.path import Path
from redis.commands.search.field import TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from typing import Any


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
        """Create RediSearch indexes for efficient querying"""
        try:
            # User index
            try:
                self.client.ft("idx:users").info()
            except Exception as e:
                print(f"Warning: Could not get user indexes information: {e}")
                schema: tuple[TextField, TextField, TextField, TextField] = (
                    TextField("$.name", as_name="name"),
                    TextField("$.email", as_name="email"),
                    TextField("$.id", as_name="id"),
                    TextField("$.created_at", as_name="created_at"),
                )
                self.client.ft("idx:users").create_index(
                    schema,
                    definition=IndexDefinition(
                        prefix=["user:"], index_type=IndexType.JSON
                    ),
                )
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

    def get_all_users(self) -> list:
        res = self.client.ft("idx:users").search("*")
        users = [r.__dict__ for r in res.docs]
        return users


# Singleton instance
redis_service = RedisService()
