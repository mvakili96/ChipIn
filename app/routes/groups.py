from flask import Blueprint, request, jsonify
from models.group import Group
from services.redis_service import redis_service


groups_bp = Blueprint("groups", __name__, url_prefix="/groups")

@groups_bp.route("/", methods=["POST"])
def create_group():
    data: dict[str,str] | None = request.get_json()

    if data is None:
        return jsonify({"error": "Invalid request: Invalid JSON"}), 400
    if "name" not in data or "users" not in data:
        return jsonify({"error": "Invalid request: missing name or users"}), 400

    #TO DO: if invalid users picked

    group       = Group(name=data["name"], users=data["users"])
    saved_group = redis_service.save_group(group.to_dict())

    return jsonify(saved_group), 201


@groups_bp.route("/", methods=["GET"])
def get_groups():
    groups = redis_service.get_all_groups()
    
    return jsonify(groups), 200


@groups_bp.route("/<group_id>", methods=["GET"])
def get_group(group_id):
    group = redis_service.get_group(group_id)

    if not group:
        return jsonify({"error": "Group not found"}), 404

    return jsonify(group), 200

