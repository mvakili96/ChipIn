from datetime import datetime
from typing import Any

from models.expense import Expense
from services.redis_service import redis_service
from services.service_errors import ServiceError
from services.settlement_service import parse_positive_amount, save_recomputed_group_settlements


def create_expense_for_user(
    user_name: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    for field in ["group_id", "name", "amount"]:
        if field not in data:
            raise ServiceError(f"Invalid request: missing {field}", 400)

    group = redis_service.get_group(data["group_id"])
    if not group:
        raise ServiceError("Group not found", 404)

    group_users = group.get("users") or []
    if user_name not in group_users:
        raise ServiceError("You are not a member of this group", 403)

    amount = parse_positive_amount(data["amount"])
    sharers = validate_sharers(data.get("sharers") or group_users, group_users)
    expense_name = validate_expense_name(data["name"])

    expense = Expense(
        name=expense_name,
        group=group["name"],
        amount=amount,
        payer=user_name,
        sharers=sharers,
    )
    expense_dict = expense.to_dict()
    expense_dict["group_id"] = group["id"]
    saved_expense = redis_service.save_expense(expense_dict)
    settlements = save_recomputed_group_settlements(group)

    return {
        "group": group,
        "saved_expense": saved_expense,
        "settlements": settlements,
    }


def update_expense_for_user(
    expense_id: str,
    user_name: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    expense = redis_service.get_expense(expense_id)
    if not expense:
        raise ServiceError("Expense not found", 404)

    group = require_expense_access_group(user_name, expense, require_payer=True)

    if "name" in data:
        expense["name"] = validate_expense_name(data["name"])

    if "amount" in data:
        expense["amount"] = parse_positive_amount(data["amount"])

    if "sharers" in data:
        expense["sharers"] = validate_sharers(
            data.get("sharers"),
            group.get("users") or [],
        )

    expense["updated_at"] = now_iso()
    saved_expense = redis_service.save_expense(expense)
    settlements = save_recomputed_group_settlements(group)

    return {
        "group": group,
        "saved_expense": saved_expense,
        "settlements": settlements,
    }


def delete_expense_for_user(
    expense_id: str,
    user_name: str,
) -> dict[str, Any]:
    expense = redis_service.get_expense(expense_id)
    if not expense:
        raise ServiceError("Expense not found", 404)

    group = require_expense_access_group(user_name, expense, require_payer=True)
    redis_service.delete_expense_record(expense_id)
    settlements = save_recomputed_group_settlements(group)

    return {"group": group, "settlements": settlements}


def expenses_with_permissions(
    expenses: list[dict[str, Any]],
    user_name: str | None,
) -> list[dict[str, Any]]:
    return [expense_with_permissions(expense, user_name) for expense in expenses]


def expense_with_permissions(
    expense: dict[str, Any],
    user_name: str | None,
) -> dict[str, Any]:
    can_change = bool(user_name and expense.get("payer") == user_name)
    return {
        **expense,
        "can_edit": can_change,
        "can_delete": can_change,
    }


def require_expense_access_group(
    user_name: str,
    expense: dict[str, Any],
    require_payer: bool = False,
) -> dict[str, Any]:
    group = expense_group(expense)
    if not group:
        raise ServiceError("Group not found", 404)

    group_users = group.get("users") or []
    if user_name not in group_users:
        raise ServiceError("You are not a member of this group", 403)

    if require_payer and expense.get("payer") != user_name:
        raise ServiceError("Only the payer can change this expense", 403)

    return group


def expense_group(expense: dict[str, Any]) -> dict[str, Any] | None:
    group_id = expense.get("group_id")
    if group_id:
        return redis_service.get_group(group_id)
    return redis_service.get_group_by_name(expense.get("group", ""))


def validate_expense_name(raw_name: Any) -> str:
    expense_name = str(raw_name).strip()
    if not expense_name:
        raise ServiceError("Expense name is required", 400)
    return expense_name


def validate_sharers(sharers: Any, group_users: list[str]) -> list[str]:
    if not isinstance(sharers, list) or not sharers:
        raise ServiceError("Sharers must be a non-empty list", 400)
    for name in sharers:
        if name not in group_users:
            raise ServiceError("One or more sharers are not in this group", 404)
    return sharers


def now_iso() -> str:
    return datetime.now().isoformat()
