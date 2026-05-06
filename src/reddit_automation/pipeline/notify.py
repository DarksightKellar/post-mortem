import json
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


def send_run_notification(status: str, message: str, config: dict) -> dict[str, object]:
    """Send run notifications when enabled by configuration without raising."""
    alerts = config.get("alerts", {}) if isinstance(config, dict) else {}
    should_send = (
        (status == "success" and alerts.get("telegram_on_success"))
        or (status == "failure" and alerts.get("telegram_on_failure"))
    )

    if not should_send:
        return {"sent": False, "error": None}

    missing_credentials = [
        key for key in ("telegram_bot_token", "telegram_chat_id") if not alerts.get(key)
    ]
    if missing_credentials:
        return {
            "sent": False,
            "error": f"Missing Telegram credentials: {', '.join(missing_credentials)}",
        }

    try:
        _deliver_notification(message, config)
    except Exception as exc:
        return {"sent": False, "error": str(exc)}

    return {"sent": True, "error": None}
