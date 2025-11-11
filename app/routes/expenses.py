from flask import Blueprint, request, jsonify
from typing import Any
from models.expense import Expense
from services.redis_service import redis_service


expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@expenses_bp.route("/", methods=["POST"])
def create_expense():
    data: dict[str, Any] | None = request.get_json()

    required_fields = ["name", "group", "amount", "payer", "sharers"]

    if data is None:
        return jsonify({"error": "Invalid request: invalid JSON"}), 400

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Invalid request: missing {field}"}), 400
    #TODO: if sharers is missing, we can default to all group members
    #TODO: group must be a valid group name that is previously defined
    #TODO: payer and sharers must be among the group's users

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
