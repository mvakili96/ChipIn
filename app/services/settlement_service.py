from typing import Any

from models.settlement import Settlement
from services.redis_service import redis_service
from services.service_errors import ServiceError


def save_recomputed_group_settlements(group: dict[str, Any]) -> list[list]:
    tx_json = calculate_group_settlements(group, use_saved_fallback=False)
    redis_service.save_group_settlements(tx_json, f"settlement-group:{group['id']}")
    return tx_json


def calculate_group_settlements(
    group: dict[str, Any],
    use_saved_fallback: bool = True,
) -> list[list]:
    group_users = group.get("users") or []
    group_expenses = redis_service.get_group_expenses(group["id"])
    if not group_expenses or not group_users:
        if use_saved_fallback:
            return redis_service.get_group_settlements(group["id"]) or []
        return []

    base_settlements = Settlement(group_expenses, group_users)
    balances = [0.0 for _ in group_users]

    for debtor_idx, creditor_idx, amount in base_settlements:
        balances[int(debtor_idx)] -= float(amount)
        balances[int(creditor_idx)] += float(amount)

    user_indexes = {name: idx for idx, name in enumerate(group_users)}
    for payment in redis_service.get_group_settlement_payments(group["id"]):
        debtor_idx = user_indexes.get(payment.get("debtor"))
        creditor_idx = user_indexes.get(payment.get("creditor"))
        if debtor_idx is None or creditor_idx is None:
            continue

        amount = float(payment.get("amount") or 0)
        balances[debtor_idx] += amount
        balances[creditor_idx] -= amount

    return settlements_from_balances(balances)


def settlements_from_balances(balances: list[float]) -> list[list]:
    debtors = [
        (idx, -balance)
        for idx, balance in enumerate(balances)
        if balance < -0.005
    ]
    creditors = [
        (idx, balance)
        for idx, balance in enumerate(balances)
        if balance > 0.005
    ]

    settlements = []
    debtor_idx = creditor_idx = 0

    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor_user_idx, debtor_amount = debtors[debtor_idx]
        creditor_user_idx, creditor_amount = creditors[creditor_idx]

        amount = min(debtor_amount, creditor_amount)
        settlements.append([debtor_user_idx, creditor_user_idx, amount])

        debtor_amount -= amount
        creditor_amount -= amount

        if debtor_amount <= 0.005:
            debtor_idx += 1
        else:
            debtors[debtor_idx] = (debtor_user_idx, debtor_amount)

        if creditor_amount <= 0.005:
            creditor_idx += 1
        else:
            creditors[creditor_idx] = (creditor_user_idx, creditor_amount)

    return settlements


def mark_settlement_paid_for_user(
    group_id: str,
    user_name: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    group = redis_service.get_group(group_id)
    if not group:
        raise ServiceError("Group not found", 404)

    group_users = group.get("users") or []
    if user_name not in group_users:
        raise ServiceError("You are not a member of this group", 403)

    for field in ["debtor", "creditor", "amount"]:
        if field not in data:
            raise ServiceError(f"Invalid request: missing {field}", 400)

    debtor = data["debtor"]
    creditor = data["creditor"]
    if debtor not in group_users or creditor not in group_users:
        raise ServiceError("Settlement users must be group members", 400)

    if user_name not in {debtor, creditor}:
        raise ServiceError("Only settlement participants can mark it paid", 403)

    amount = parse_positive_amount(data["amount"])
    open_amount = open_settlement_amount(group, debtor, creditor)
    if open_amount is None:
        raise ServiceError("Settlement is not open", 400)
    if amount - open_amount > 0.005:
        raise ServiceError("Payment amount exceeds the open settlement", 400)

    payment = redis_service.save_settlement_payment(
        group_id,
        {
            "debtor": debtor,
            "creditor": creditor,
            "amount": amount,
            "recorded_by": user_name,
        },
    )
    settlements = save_recomputed_group_settlements(group)
    return {"group": group, "payment": payment, "settlements": settlements}


def open_settlement_amount(
    group: dict[str, Any],
    debtor: str,
    creditor: str,
) -> float | None:
    users = group.get("users") or []
    for open_debtor, open_creditor, amount in named_settlements(
        calculate_group_settlements(group),
        users,
    ):
        if open_debtor == debtor and open_creditor == creditor:
            return float(amount)
    return None


def named_settlements(settlements: list, users: list[str]) -> list[list]:
    named = []
    for debtor_idx, creditor_idx, amount in settlements:
        debtor_idx = int(debtor_idx)
        creditor_idx = int(creditor_idx)
        if debtor_idx >= len(users) or creditor_idx >= len(users):
            continue
        named.append([users[debtor_idx], users[creditor_idx], float(amount)])
    return named


def settlements_with_permissions(
    settlements: list[list],
    user_name: str | None,
) -> list[dict[str, Any]]:
    enriched = []
    for debtor, creditor, amount in settlements:
        enriched.append(
            {
                "debtor": debtor,
                "creditor": creditor,
                "amount": float(amount),
                "can_mark_paid": user_name in {debtor, creditor},
            }
        )
    return enriched


def user_settlements_payload(user: dict[str, Any]) -> dict[str, Any]:
    user_name = user["name"]
    grouped = []
    aggregate: dict[str, float] = {}

    for group in redis_service.get_groups_for_user(user_name):
        group_settlements = named_settlements(
            calculate_group_settlements(group),
            group.get("users") or [],
        )
        user_settlements = []
        for debtor, creditor, amount in group_settlements:
            amount = float(amount)
            if debtor == user_name:
                user_settlements.append([debtor, creditor, amount])
                aggregate[creditor] = aggregate.get(creditor, 0) - amount
            elif creditor == user_name:
                user_settlements.append([debtor, creditor, amount])
                aggregate[debtor] = aggregate.get(debtor, 0) + amount

        if user_settlements:
            grouped.append(
                {
                    "group_id": group["id"],
                    "group_name": group["name"],
                    "settlements": user_settlements,
                }
            )

    return {
        "aggregate": aggregate_settlements_payload(aggregate),
        "groups": grouped,
    }


def aggregate_settlements_payload(
    aggregate: dict[str, float],
) -> list[dict[str, Any]]:
    rows = []
    for name, balance in sorted(aggregate.items()):
        if abs(balance) < 1e-9:
            continue
        rows.append(
            {
                "name": name,
                "amount": abs(balance),
                "direction": "owes_you" if balance > 0 else "you_owe",
            }
        )
    return rows


def parse_positive_amount(raw_amount: Any) -> float:
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        raise ServiceError("Amount must be a number", 400)

    if amount <= 0:
        raise ServiceError("Amount must be greater than zero", 400)

    return amount
