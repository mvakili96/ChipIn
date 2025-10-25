import uuid  
from datetime import datetime

class Group:
    def __init__(self, name: str, users: list[str], uid: str | None = None):
        self.name: str        = name
        self.users: list[str] = users
        self.uid : str        = uid or str(uuid.uuid4())
        self.created_at: str  = datetime.now().isoformat()

        # TODO: what if user is in a different timezone?

    def __repr__(self) -> str:
        return f"Group(name={self.name}, users={self.users}, uid={self.uid}, created_at={self.created_at})"

    def to_dict(self):
        return {
            "name": self.name,
            "users": self.users,
            "id": self.uid,
            "created_at": self.created_at,
        }
    
    @staticmethod
    def from_dict(data: dict):
        return Group(name=data["name"], users=data["users"], uid=data["id"])

