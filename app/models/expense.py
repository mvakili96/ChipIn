import uuid  
from datetime import datetime

class Expense:
    def __init__(self, name: str, group: str, amount: float, payer: str, sharers: list[str], uid: str | None = None):
        self.name: str          = name
        self.group: str         = group
        self.amount: float      = amount
        self.payer:str          = payer
        self.sharers: list[str] = sharers
        self.uid : str          = uid or str(uuid.uuid4())
        self.created_at: str    = datetime.now().isoformat()

        # TODO: what if user is in a different timezone?

    def __repr__(self) -> str:
        return (
            f"Expense(name={self.name}, group={self.group}, amount={self.amount}, "
            f"payer={self.payer}, sharers={self.sharers}, uid={self.uid}, "
            f"created_at={self.created_at})"
        )

    def to_dict(self):
        return {
            "name": self.name,
            "group": self.group, 
            "amount": self.amount,
            "payer": self.payer,
            "sharers": self.sharers,
            "id": self.uid,
            "created_at": self.created_at,
        }
    
    @staticmethod
    def from_dict(data: dict):
        return Expense(
            name=data["name"],
            group=data["group"],
            amount=data["amount"],
            payer=data["payer"],
            sharers=data["sharers"],
            uid=data["id"],
        )

