from flask import Blueprint, jsonify
from services.redis_service import redis_service
from models.settlement import Settlement


settlements_bp = Blueprint("settlements", __name__, url_prefix="/settlements")

def add_names_to_tx(tx: list[tuple], users: list[str]):
    return [(users[i], users[j], amt) for i, j, amt in tx]


@settlements_bp.route("/group/", methods=["GET"])
def get_groups_settlements():
    groups_settlements = redis_service.get_all_group_settlements()

    PREFIX = "settlement-group:"

    for key in list(groups_settlements.keys()):
        group_id = key[len(PREFIX):]
        group_dict = redis_service.get_group(group_id)       
        group_users = group_dict["users"]                    
        groups_settlements[key] = add_names_to_tx(groups_settlements[key], group_users)               

    return jsonify(groups_settlements), 200


@settlements_bp.route("/group/<group_id>", methods=["GET"])
def get_group_settlements(group_id):
    group_dict  = redis_service.get_group(group_id)

    settlements_hist = redis_service.get_group_settlements(group_id)
    if settlements_hist:
        settlements = settlements_hist

    else:
        if not group_dict:
            return jsonify({"error": "Group and its settlements not found"}), 404

        group_expenses = redis_service.get_group_expenses(group_id)
        if len(group_expenses) > 0:
            settlements = Settlement(group_expenses, group_dict["users"])
        else:
            return jsonify({"warning": "There are no expenses linked to this group"}), 404

    return jsonify({"settlements_this_group": add_names_to_tx(settlements, group_dict["users"])}), 200

