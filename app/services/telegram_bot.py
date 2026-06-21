import json
import os
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


class TelegramBotClient:
    def __init__(self, bot_token: str | None = None):
        self.bot_token = bot_token if bot_token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict | None:
        if not self.bot_token:
            return None

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        return self._post("sendMessage", payload)

    def _post(self, method: str, payload: dict) -> dict | None:
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"https://api.telegram.org/bot{self.bot_token}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlrequest.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except OSError:
                body = str(exc)
            print(f"Warning: Telegram Bot API request failed: {body}")
            return None
        except (OSError, URLError, json.JSONDecodeError) as exc:
            print(f"Warning: Telegram Bot API request failed: {exc}")
            return None


telegram_bot_client = TelegramBotClient()
