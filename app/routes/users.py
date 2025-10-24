from flask import Blueprint, request, jsonify
from models.user import User
from services.redis_service import redis_service


users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/", methods=["POST"])
def create_user():
    data: dict[str, str] | None = request.get_json()

    if data is None:
        return jsonify({"error": "Invalid request: Invalid JSON"}), 400
    if "name" not in data or "email" not in data:
        return jsonify({"error": "Invalid request: missing name or email"}), 400

    user = User(name=data["name"], email=data["email"])
    saved_user = redis_service.save_user(user.to_dict())

    return jsonify(saved_user), 201


@users_bp.route("/", methods=["GET"])
def get_users():
    users = redis_service.get_all_users()
    return jsonify(users), 200


@users_bp.route("/<user_id>", methods=["GET"])
def get_user(user_id):
    user = redis_service.get_user(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200
