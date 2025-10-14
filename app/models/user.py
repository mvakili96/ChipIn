import uuid  # universally unique identifier (UUID) is a 128-bit number designed to be unique identifier for objects
from datetime import datetime


class User:
    def __init__(self, name: str, email: str, uid: str | None = None):
        self.name: str = name
        self.email: str = email
        self.uid: str = uid or str(uuid.uuid4())
        self.created_at: str = datetime.now().isoformat()
        # TODO: what if user is in a different timezone?
        # TODO: Add password later

    def __repr__(self) -> str:
        return f"User(name={self.name}, email={self.email}, uid={self.uid}, created_at={self.created_at})"

    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "id": self.uid,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict[str, str]):
        return User(name=data["name"], email=data["email"], uid=data["id"])
