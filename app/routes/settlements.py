from flask import Blueprint, jsonify
from services.redis_service import redis_service
from models.settlement import Settlement


settlements_bp = Blueprint("settlements", __name__, url_prefix="/settlements")

@settlements_bp.route("/group/", methods=["GET"])
def get_groups_settlements():
    def add_names_to_tx(tx: list[tuple], users: list[str]):
        return [(users[i], users[j], amt) for i, j, amt in tx]

    groups_settlements = redis_service.get_all_group_settlements()
    prefix = "settlement-group:"

    for key in list(groups_settlements.keys()):
        group_id = key[len(prefix):]
        group_dict = redis_service.get_group(group_id)
        group_users = group_dict["users"]
        groups_settlements[key] = add_names_to_tx(groups_settlements[key], group_users)

    return jsonify(groups_settlements), 200


@settlements_bp.route("/group/<group_id>", methods=["GET"])
def get_group_settlements(group_id):
    def add_names_to_tx(tx: list[tuple], users: list[str]):
        return [(users[i], users[j], amt) for i, j, amt in tx]

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


@settlements_bp.route("/user/<user_id>", methods=["GET"])
def get_user_settlements(user_id):
    def add_names_to_tx(tx: list[tuple], users: list[str]):
        return [(users[i], users[j], amt) for i, j, amt in tx]

    def get_named_groups_settlements():
        groups_settlements = redis_service.get_all_group_settlements()
        prefix = "settlement-group:"

        for key in list(groups_settlements.keys()):
            group_id = key[len(prefix):]
            group_dict = redis_service.get_group(group_id)
            group_users = group_dict["users"]
            groups_settlements[key] = add_names_to_tx(groups_settlements[key], group_users)

        return groups_settlements

    def merge_redundant_settlements(settlements: list[tuple[str, str, float]]):
        merged_balances: dict[tuple[str, str], float] = {}

        for debtor, creditor, amount in settlements:
            pair = tuple(sorted((debtor, creditor)))
            signed_amount = amount if debtor == pair[0] else -amount
            merged_balances[pair] = merged_balances.get(pair, 0) + signed_amount

        merged_settlements = []
        for pair, balance in merged_balances.items():
            if abs(balance) < 1e-9:
                continue

            if balance > 0:
                merged_settlements.append((pair[0], pair[1], balance))
            else:
                merged_settlements.append((pair[1], pair[0], -balance))

        return merged_settlements

    user_dict = redis_service.get_user(user_id)
    if not user_dict:
        return jsonify({"error": "User not found"}), 404

    user_name = user_dict["name"]
    groups_settlements = get_named_groups_settlements()

    user_settlements = []
    for settlements in groups_settlements.values():
        for debtor, creditor, amount in settlements:
            if debtor == user_name or creditor == user_name:
                user_settlements.append((debtor, creditor, amount))

    return jsonify({"settlements_this_user": merge_redundant_settlements(user_settlements)}), 200
