import html
import os
from typing import Any
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request, send_from_directory

from services.expense_service import (
    create_expense_for_user,
    delete_expense_for_user,
    expenses_with_permissions,
    update_expense_for_user,
)
from services.redis_service import redis_service
from services.service_errors import ServiceError
from services.settlement_service import (
    calculate_group_settlements,
    mark_settlement_paid_for_user,
    named_settlements,
    settlements_with_permissions,
    user_settlements_payload,
)
from services.telegram_auth import TelegramAuthError, TelegramInitData, validate_init_data
from services.telegram_bot import telegram_bot_client


telegram_bp = Blueprint("telegram", __name__, url_prefix="/telegram")


@telegram_bp.route("/")
def telegram_client():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "telegram")
    return send_from_directory(static_dir, "index.html")


@telegram_bp.route("/auth/", methods=["POST"])
def telegram_auth():
    try:
        init_data = _init_data_from_request_body()
        launch = _authenticate_init_data(init_data)
        launch_group = None

        if _is_group_chat(launch.init_data.chat):
            launch_group = redis_service.ensure_telegram_group(launch.init_data.chat)
            launch_group = redis_service.add_user_to_group(launch_group["id"], launch.user["name"])

        return jsonify(
            {
                "user": _public_user(launch.user),
                "groups": _groups_payload(redis_service.get_groups_for_user(launch.user["name"])),
                "launch_group": _group_payload(launch_group) if launch_group else None,
                "settlements": user_settlements_payload(launch.user),
            }
        ), 200
    except TelegramAuthError as exc:
        return _auth_error_response(exc)


@telegram_bp.route("/api/groups/", methods=["GET"])
def get_my_groups():
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    groups = redis_service.get_groups_for_user(launch.user["name"])
    return jsonify({"groups": _groups_payload(groups)}), 200


@telegram_bp.route("/api/groups/<group_id>/", methods=["GET"])
def get_my_group(group_id):
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    group = redis_service.get_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    if launch.user["name"] not in (group.get("users") or []):
        return jsonify({"error": "You are not a member of this group"}), 403

    return jsonify(_group_detail_payload(group, launch.user["name"])), 200


@telegram_bp.route("/api/groups/from-chat/", methods=["POST"])
def create_group_from_chat():
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    chat = launch.init_data.chat
    if not _is_group_chat(chat):
        return jsonify({"error": "Telegram group chat context is required"}), 400

    group = redis_service.ensure_telegram_group(chat)
    group = redis_service.add_user_to_group(group["id"], launch.user["name"])

    return jsonify({"group": _group_payload(group)}), 201


@telegram_bp.route("/api/groups/<group_id>/join/", methods=["POST"])
def join_telegram_group(group_id):
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    group = redis_service.get_group(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    if group.get("source") != "telegram":
        return jsonify({"error": "Only Telegram-backed groups support self-join"}), 400
    if not _launch_matches_group_chat(launch, group):
        return jsonify({"error": "Verified Telegram group context is required"}), 403

    group = redis_service.add_user_to_group(group_id, launch.user["name"])
    return jsonify({"group": _group_payload(group)}), 200


@telegram_bp.route("/api/expenses/", methods=["POST"])
def create_telegram_expense():
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request: invalid JSON"}), 400

    try:
        result = create_expense_for_user(launch.user["name"], data)
    except ServiceError as exc:
        return _service_error_response(exc)

    group = result["group"]
    saved_expense = result["saved_expense"]
    settlements = result["settlements"]
    _notify_telegram_group_expense(group, saved_expense)

    return jsonify(
        {
            "saved_expense": saved_expense,
            "group_settlement": named_settlements(
                settlements,
                group.get("users") or [],
            ),
            "detail": _group_detail_payload(group, launch.user["name"]),
        }
    ), 201


@telegram_bp.route("/api/expenses/<expense_id>/", methods=["PUT"])
def update_telegram_expense(expense_id):
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request: invalid JSON"}), 400

    try:
        result = update_expense_for_user(expense_id, launch.user["name"], data)
    except ServiceError as exc:
        return _service_error_response(exc)

    group = result["group"]

    return jsonify(
        {
            "saved_expense": result["saved_expense"],
            "group_settlement": named_settlements(
                result["settlements"],
                group.get("users") or [],
            ),
            "detail": _group_detail_payload(group, launch.user["name"]),
        }
    ), 200


@telegram_bp.route("/api/expenses/<expense_id>/", methods=["DELETE"])
def delete_telegram_expense(expense_id):
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    try:
        result = delete_expense_for_user(expense_id, launch.user["name"])
    except ServiceError as exc:
        return _service_error_response(exc)

    group = result["group"]

    return jsonify(
        {
            "message": f"Expense {expense_id} deleted successfully",
            "group_settlement": named_settlements(
                result["settlements"],
                group.get("users") or [],
            ),
            "detail": _group_detail_payload(group, launch.user["name"]),
        }
    ), 200


@telegram_bp.route("/api/groups/<group_id>/settlements/paid/", methods=["POST"])
def mark_telegram_settlement_paid(group_id):
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}
    try:
        result = mark_settlement_paid_for_user(group_id, launch.user["name"], data)
    except ServiceError as exc:
        return _service_error_response(exc)

    group = result["group"]

    return jsonify(
        {
            "payment": result["payment"],
            "group_settlement": named_settlements(
                result["settlements"],
                group.get("users") or [],
            ),
            "detail": _group_detail_payload(group, launch.user["name"]),
        }
    ), 201


@telegram_bp.route("/api/settlements/", methods=["GET"])
def get_my_settlements():
    launch, error_response = _require_telegram_user()
    if error_response:
        return error_response

    return jsonify(user_settlements_payload(launch.user)), 200


@telegram_bp.route("/webhook/", methods=["POST"])
def telegram_webhook():
    if not _valid_webhook_secret():
        return jsonify({"error": "Invalid Telegram webhook secret"}), 403

    update = request.get_json(silent=True)
    if not update:
        return jsonify({"error": "Invalid Telegram update"}), 400

    _handle_bot_update(update)
    return jsonify({"ok": True}), 200


class TelegramLaunch:
    def __init__(self, init_data: TelegramInitData, user: dict[str, Any]):
        self.init_data = init_data
        self.user = user


def _init_data_from_request_body() -> str:
    data = request.get_json(silent=True) or {}
    return data.get("init_data") or request.headers.get("X-Telegram-Init-Data", "")


def _init_data_from_headers() -> str:
    header_value = request.headers.get("X-Telegram-Init-Data")
    if header_value:
        return header_value

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Telegram "):
        return auth_header[len("Telegram ") :]

    return ""


def _authenticate_init_data(init_data: str) -> TelegramLaunch:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    parsed = validate_init_data(init_data, bot_token)
    user = redis_service.upsert_telegram_user(parsed.user)
    return TelegramLaunch(parsed, user)


def _require_telegram_user():
    try:
        return _authenticate_init_data(_init_data_from_headers()), None
    except TelegramAuthError as exc:
        return None, _auth_error_response(exc)


def _auth_error_response(exc: TelegramAuthError):
    status = 503 if "not configured" in str(exc) else 401
    return jsonify({"error": str(exc)}), status


def _service_error_response(exc: ServiceError):
    return jsonify({"error": exc.message}), exc.status_code


def _valid_webhook_secret() -> bool:
    expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not expected:
        return False
    return request.headers.get("X-Telegram-Bot-Api-Secret-Token") == expected


def _is_group_chat(chat: dict | None) -> bool:
    return bool(chat and chat.get("type") in {"group", "supergroup"})


def _groups_payload(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_group_payload(group) for group in groups]


def _group_payload(group: dict[str, Any] | None) -> dict[str, Any] | None:
    if not group:
        return None

    expenses = redis_service.get_group_expenses(group["id"])
    return {
        "id": group.get("id"),
        "name": group.get("name"),
        "users": group.get("users") or [],
        "source": group.get("source", "manual"),
        "telegram_chat_id": group.get("telegram_chat_id"),
        "telegram_chat_title": group.get("telegram_chat_title"),
        "telegram_chat_type": group.get("telegram_chat_type"),
        "private_chat_url": _private_chat_url(group.get("id")),
        "expenses_count": len(expenses),
        "created_at": group.get("created_at"),
    }


def _group_detail_payload(
    group: dict[str, Any],
    current_user_name: str | None = None,
) -> dict[str, Any]:
    expenses = redis_service.get_group_expenses(group["id"])
    settlements = calculate_group_settlements(group)
    named_group_settlements = named_settlements(settlements, group.get("users") or [])
    payments = redis_service.get_group_settlement_payments(group["id"])

    return {
        "group": _group_payload(group),
        "expenses": expenses_with_permissions(expenses, current_user_name),
        "settlements": settlements_with_permissions(
            named_group_settlements,
            current_user_name,
        ),
        "payment_history": payments,
    }


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "telegram_id": user.get("telegram_id"),
        "telegram_username": user.get("telegram_username"),
        "telegram_first_name": user.get("telegram_first_name"),
        "telegram_last_name": user.get("telegram_last_name"),
        "telegram_photo_url": user.get("telegram_photo_url"),
    }


def _handle_bot_update(update: dict[str, Any]) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        _handle_chat_membership_update(update)
        return

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    text = message.get("text") or ""
    parts = text.split()
    command = parts[0].split("@")[0].lower() if parts else ""
    payload = parts[1] if len(parts) > 1 else ""

    user = redis_service.upsert_telegram_user(sender) if sender.get("id") else None
    group = None
    if _is_group_chat(chat):
        group = redis_service.ensure_telegram_group(chat)
        if user:
            group = redis_service.add_user_to_group(group["id"], user["name"])

    if command == "/help":
        _send_help_message(chat, group)
        return

    if command == "/groups" and user:
        _send_private_only_command(
            chat,
            group,
            _format_groups_message(user),
            _mini_app_reply_markup(),
        )
        return

    if command == "/balance" and user:
        _send_private_only_command(
            chat,
            group,
            _format_balance_message(user),
            _mini_app_reply_markup(group["id"] if group else None),
        )
        return

    if command == "/settlements" and user:
        _send_private_only_command(
            chat,
            group,
            _format_settlements_message(user),
            _mini_app_reply_markup(group["id"] if group else None),
        )
        return

    if command == "/chipin" or (command == "/start" and not _is_group_chat(chat)):
        if _is_group_chat(chat):
            group_name = html.escape(group["name"] if group else chat.get("title", "this group"))
            text = (
                f"ChipIn is ready for <b>{group_name}</b>. "
                "Open the bot privately to add expenses."
            )
            reply_markup = _private_chat_reply_markup(group["id"] if group else None)
        else:
            linked_group = _join_start_payload_group(payload, user)
            if linked_group:
                group_name = html.escape(linked_group["name"])
                text = f"You're linked to <b>{group_name}</b>. Open ChipIn to continue."
                reply_markup = _mini_app_reply_markup(linked_group["id"])
            elif payload.startswith("group_"):
                text = "I could not find that ChipIn group. Send /chipin in the Telegram group again."
                reply_markup = _mini_app_reply_markup()
            else:
                text = "Open ChipIn to see your groups, balances, expenses, and settlements."
                reply_markup = _mini_app_reply_markup()

        telegram_bot_client.send_message(
            chat["id"],
            text,
            reply_markup,
        )


def _handle_chat_membership_update(update: dict[str, Any]) -> None:
    membership = update.get("my_chat_member")
    if not membership:
        return

    chat = membership.get("chat") or {}
    if not _is_group_chat(chat):
        return

    new_status = (membership.get("new_chat_member") or {}).get("status")
    if new_status in {"member", "administrator"}:
        redis_service.ensure_telegram_group(chat)


def _notify_telegram_group_expense(group: dict[str, Any], expense: dict[str, Any]) -> None:
    telegram_chat_id = group.get("telegram_chat_id")
    if not telegram_chat_id:
        return

    telegram_bot_client.send_message(
        telegram_chat_id,
        _format_expense_notification(group, expense),
        _private_chat_reply_markup(group["id"]),
    )


def _send_help_message(chat: dict[str, Any], group: dict[str, Any] | None) -> None:
    if _is_group_chat(chat):
        text = (
            "ChipIn commands in this group:\n"
            "/chipin - link this Telegram group to ChipIn\n"
            "/balance - open private balance view\n"
            "/help - show this help"
        )
        reply_markup = _private_chat_reply_markup(group["id"] if group else None)
    else:
        text = (
            "ChipIn commands:\n"
            "/start - open the Mini App\n"
            "/groups - list your groups\n"
            "/balance - show your aggregate balance\n"
            "/settlements - show open settlements\n"
            "/help - show this help"
        )
        reply_markup = _mini_app_reply_markup(group["id"] if group else None)

    telegram_bot_client.send_message(chat["id"], text, reply_markup)


def _send_private_only_command(
    chat: dict[str, Any],
    group: dict[str, Any] | None,
    private_text: str,
    private_reply_markup: dict[str, Any] | None,
) -> None:
    if _is_group_chat(chat):
        telegram_bot_client.send_message(
            chat["id"],
            "Open ChipIn privately to view that.",
            _private_chat_reply_markup(group["id"] if group else None),
        )
        return

    telegram_bot_client.send_message(chat["id"], private_text, private_reply_markup)


def _format_balance_message(user: dict[str, Any]) -> str:
    settlements = user_settlements_payload(user)["aggregate"]
    if not settlements:
        return "You have no open ChipIn settlements."

    lines = ["Your ChipIn balance:"]
    for row in settlements:
        amount = f"${float(row['amount']):.2f}"
        other_user = html.escape(row["name"])
        if row["direction"] == "owes_you":
            lines.append(f"{other_user} owes you {amount}")
        else:
            lines.append(f"You owe {other_user} {amount}")
    return "\n".join(lines)


def _format_groups_message(user: dict[str, Any]) -> str:
    groups = redis_service.get_groups_for_user(user["name"])
    if not groups:
        return "You are not in any ChipIn groups yet."

    lines = ["Your ChipIn groups:"]
    for group in groups:
        member_count = len(group.get("users") or [])
        expense_count = len(redis_service.get_group_expenses(group["id"]))
        lines.append(
            f"- {html.escape(group['name'])}: {member_count} users, {expense_count} expenses"
        )
    return "\n".join(lines)


def _format_settlements_message(user: dict[str, Any]) -> str:
    settlements_payload = user_settlements_payload(user)
    if not settlements_payload["groups"]:
        return "You have no open ChipIn settlements."

    lines = ["Your open settlements:"]
    for group in settlements_payload["groups"]:
        lines.append(f"\n{html.escape(group['group_name'])}:")
        for debtor, creditor, amount in group["settlements"]:
            lines.append(
                f"- {html.escape(debtor)} pays {html.escape(creditor)} {_format_money(amount)}"
            )

    return "\n".join(lines)


def _format_expense_notification(group: dict[str, Any], expense: dict[str, Any]) -> str:
    payer = html.escape(expense.get("payer", "Someone"))
    name = html.escape(expense.get("name", "an expense"))
    group_name = html.escape(group.get("name", "this group"))
    amount = _format_money(expense.get("amount", 0))
    sharers_count = len(expense.get("sharers") or [])

    return (
        f"{payer} added <b>{name}</b> for <b>{amount}</b> in <b>{group_name}</b>.\n"
        f"Split with {sharers_count} users."
    )


def _format_money(amount: Any) -> str:
    return f"${float(amount or 0):.2f}"


def _join_start_payload_group(payload: str, user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user or not payload.startswith("group_"):
        return None

    group_id = payload[len("group_") :]
    group = redis_service.get_group(group_id)
    if not group or group.get("source") != "telegram":
        return None
    if user["name"] not in (group.get("users") or []):
        return None

    return redis_service.add_user_to_group(group_id, user["name"])


def _launch_matches_group_chat(
    launch: TelegramLaunch,
    group: dict[str, Any],
) -> bool:
    chat = launch.init_data.chat
    if not _is_group_chat(chat):
        return False
    return str(chat.get("id")) == str(group.get("telegram_chat_id"))


def _private_chat_reply_markup(group_id: str | None = None) -> dict[str, Any] | None:
    url = _private_chat_url(group_id)
    if not url:
        return None

    return {
        "inline_keyboard": [
            [
                {
                    "text": "Open ChipIn",
                    "url": url,
                }
            ]
        ]
    }


def _private_chat_url(group_id: str | None = None) -> str | None:
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "").lstrip("@")
    if not bot_username:
        return None

    base_url = f"https://t.me/{bot_username}"
    if not group_id:
        return base_url

    return f"{base_url}?{urlencode({'start': f'group_{group_id}'})}"


def _mini_app_reply_markup(group_id: str | None = None) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Open ChipIn",
                    "web_app": {"url": _mini_app_url(group_id)},
                }
            ]
        ]
    }


def _mini_app_url(group_id: str | None = None) -> str:
    public_base_url = os.getenv("PUBLIC_BASE_URL")
    if public_base_url:
        base_url = f"{public_base_url.rstrip('/')}/telegram/"
    else:
        base_url = f"{request.host_url.rstrip('/')}/telegram/"

    if not group_id:
        return base_url

    return f"{base_url}?{urlencode({'group_id': group_id})}"
