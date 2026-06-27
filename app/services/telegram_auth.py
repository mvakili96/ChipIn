import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramInitData:
    raw: dict[str, str]
    user: dict
    chat: dict | None
    auth_date: int | None


def _data_check_string(fields: dict[str, str], exclude_signature: bool = False) -> str:
    excluded = {"hash"}
    if exclude_signature:
        excluded.add("signature")

    pairs = [
        f"{key}={value}"
        for key, value in sorted(fields.items())
        if key not in excluded
    ]
    return "\n".join(pairs)


def _calculate_hash(data_check_string: str, bot_token: str) -> str:
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int | None = 24 * 60 * 60,
) -> TelegramInitData:
    if not bot_token:
        raise TelegramAuthError("Telegram bot token is not configured")

    if not init_data:
        raise TelegramAuthError("Missing Telegram init data")

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.get("hash")
    if not received_hash:
        raise TelegramAuthError("Missing Telegram hash")

    data_check_string = _data_check_string(fields)
    expected_hash = _calculate_hash(data_check_string, bot_token)

    if not hmac.compare_digest(expected_hash, received_hash):
        # Newer init data can include a third-party signature field. Some clients
        # still validate the bot-token hash without it, so support that shape too.
        data_check_string = _data_check_string(fields, exclude_signature=True)
        expected_hash = _calculate_hash(data_check_string, bot_token)
        if not hmac.compare_digest(expected_hash, received_hash):
            raise TelegramAuthError("Invalid Telegram hash")

    auth_date = _parse_auth_date(fields.get("auth_date"))
    if max_age_seconds is not None and auth_date is not None:
        if int(time.time()) - auth_date > max_age_seconds:
            raise TelegramAuthError("Telegram init data is too old")

    user = _parse_json_field(fields, "user")
    if not user or "id" not in user:
        raise TelegramAuthError("Missing Telegram user")

    chat = _parse_json_field(fields, "chat")

    return TelegramInitData(
        raw=fields,
        user=user,
        chat=chat,
        auth_date=auth_date,
    )


def _parse_auth_date(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TelegramAuthError("Invalid Telegram auth date") from exc


def _parse_json_field(fields: dict[str, str], key: str) -> dict | None:
    raw = fields.get(key)
    if not raw:
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError(f"Invalid Telegram {key}") from exc

    if not isinstance(parsed, dict):
        raise TelegramAuthError(f"Invalid Telegram {key}")

    return parsed
