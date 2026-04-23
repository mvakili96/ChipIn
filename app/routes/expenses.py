from flask import Blueprint, request, jsonify
from typing import Any
from models.expense import Expense
from models.settlement import Settlement
from services.redis_service import redis_service
from redis.commands.search.query import Query
from redis.commands.json.path import Path

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@expenses_bp.route("/", methods=["POST"])
def create_expense():
    data: dict[str, Any] | None = request.get_json()

    # sharers could be all the group users by default, or otherwise defined
    required_fields = ["name", "group", "amount", "payer"] 

    if data is None:
        return jsonify({"error": "Invalid request: invalid JSON"}), 400

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Invalid request: missing {field}"}), 400
        
    group_dict = redis_service.get_group_by_name(data["group"])

    if group_dict is None:
        return jsonify({"error": "Group linked to this expense is not found"}), 404
    
    if data["payer"] not in group_dict["users"]:
        return jsonify({"error": "Payer is not found in the linked Group"}), 404
    
    if "sharers" not in data:
        data["sharers"] = group_dict["users"]
    else:
        for name in data["sharers"]:
            if name not in group_dict["users"]:
                return jsonify({"error": "One or more sharers not found in the linked Group"}), 404

    expense = Expense(
            name=data["name"],
            group=data["group"],
            amount=data["amount"],
            payer=data["payer"],
            sharers=data["sharers"]
        )
    saved_expense = redis_service.save_expense(expense.to_dict())

    tx_prev = redis_service.get_group_settlements(group_dict['id'])

    tx_hist: list[tuple] | None = None
    if tx_prev is not None:
        tx_hist = [tuple(x) for x in tx_prev]

    group_users: list[str] = group_dict["users"]

    if tx_hist is None:
        group_expenses = redis_service.get_group_expenses(group_dict['id'])
        tx = Settlement(group_expenses, group_users)
    else:
        group_expenses = [expense.to_dict()]
        tx = Settlement(group_expenses, group_users, tx_hist)

    tx_json = [list(t) for t in tx]
    settlement_key = f"settlement-group:{group_dict['id']}"
    redis_service.save_group_settlements(tx_json, settlement_key)

    return jsonify({
    "saved_expense": saved_expense,
    "group_settlement": tx_json,
    }), 201


@expenses_bp.route("/", methods=["GET"])
def get_expenses():
    expenses = redis_service.get_all_expenses()

    return jsonify(expenses), 200


@expenses_bp.route("/<expense_id>", methods=["GET"])
def get_expense(expense_id):
    expense = redis_service.get_expense(expense_id)

    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    return jsonify(expense), 200


@expenses_bp.route("/<expense_id>/<key>", methods=["GET"])
def get_expense_attr(expense_id, key):
    attribute = redis_service.get_expense_attr(expense_id, key)

    if not attribute:
        return jsonify({"error": "Expense or key not found"}), 404

    return jsonify(attribute), 200


@expenses_bp.route("/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    success = redis_service.delete_expense(expense_id)

    if not success:
        return jsonify({"error": "Expense not found"}), 404

    return jsonify({"message": f"Expense {expense_id} deleted successfully"}), 200


@expenses_bp.route("/group/<group_id>", methods=["GET"])
def get_group_expenses(group_id):
    group_dict  = redis_service.get_group(group_id)
    if not group_dict:
        return jsonify({"error": "Group not found"}), 404
    
    group_expenses = redis_service.get_group_expenses(group_id)

    return jsonify(group_expenses), 200


@expenses_bp.route("/user/paid/<user_id>", methods=["GET"])
def get_user_paid_expenses(user_id):
    user_dict = redis_service.get_user(user_id)
    if not user_dict:
        return jsonify({"error": "User not found"}), 404

    user_expenses = redis_service.get_user_paid_expenses(user_id)

    return jsonify(user_expenses), 200
