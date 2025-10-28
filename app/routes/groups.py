from flask import Blueprint, request, jsonify
from models.group import Group
from services.redis_service import redis_service


groups_bp = Blueprint("groups", __name__, url_prefix="/groups")

@groups_bp.route("/", methods=["POST"])
def create_group():
    data: dict[str,list[str]] | None = request.get_json()

    if data is None:
        return jsonify({"error": "Invalid request: Invalid JSON"}), 400
    if "name" not in data or "users" not in data:
        return jsonify({"error": "Invalid request: missing name or users"}), 400

    registered_names = redis_service.get_all_user_names()
    for name in data["users"]:
        if name not in registered_names:
            return jsonify({"error": "One or more names not found"}), 404

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

@groups_bp.route("/<group_id>/<key>", methods=["GET"])
def get_group_attr(group_id,key):
    attribute = redis_service.get_group_attr(group_id,key)

    if not attribute:
        return jsonify({"error": "Group or key not found"}), 404

    return attribute, 200

@groups_bp.route("/<group_id>", methods=["DELETE"])
def delete_group(group_id):
    success = redis_service.delete_group(group_id)

    if not success:
        return jsonify({"error": "Group not found"}), 404

    return jsonify({"message": f"Group {group_id} deleted successfully"}), 200
