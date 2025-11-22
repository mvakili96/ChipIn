from flask import Blueprint, request, jsonify
from typing import Any
from models.expense import Expense
from services.redis_service import redis_service


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

    return jsonify(saved_expense), 201


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
