import json
import urllib.error
import urllib.request


def _deliver_notification(message: str, config: dict) -> None:
    """Send a notification via the Telegram Bot API."""
    alerts = config.get("alerts", {}) if isinstance(config, dict) else {}
    token = alerts.get("telegram_bot_token")
    chat_id = alerts.get("telegram_chat_id")

    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
        if not body.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {body.get('description', body)}"
            )


def send_run_notification(status: str, message: str, config: dict) -> None:
    """Send run notifications when enabled by configuration."""
    alerts = config.get("alerts", {}) if isinstance(config, dict) else {}

    if status == "success" and alerts.get("telegram_on_success"):
        _deliver_notification(message, config)

    if status == "failure" and alerts.get("telegram_on_failure"):
        _deliver_notification(message, config)
