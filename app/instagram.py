import logging

import httpx

from app import config

log = logging.getLogger("instagram")


def _post(path: str, payload: dict) -> dict:
    if config.DRY_RUN:
        log.info("[DRY_RUN] POST %s %s", path, payload)
        return {"dry_run": True}
    r = httpx.post(
        f"{config.GRAPH_API_BASE}/{path}",
        json=payload,
        headers={"Authorization": f"Bearer {config.IG_ACCESS_TOKEN}"},
        timeout=20,
    )
    if r.status_code >= 400:
        log.error("Graph API error %s: %s", r.status_code, r.text)
    r.raise_for_status()
    return r.json()


def send_dm(recipient_id: str, text: str) -> dict:
    return _post(
        f"{config.IG_USER_ID}/messages",
        {"recipient": {"id": recipient_id}, "message": {"text": text[:1000]}},
    )


def send_private_reply(comment_id: str, text: str) -> dict:
    """DM the person who left a comment (used by keyword triggers)."""
    return _post(
        f"{config.IG_USER_ID}/messages",
        {"recipient": {"comment_id": comment_id}, "message": {"text": text[:1000]}},
    )


def reply_comment(comment_id: str, text: str) -> dict:
    return _post(f"{comment_id}/replies", {"message": text[:2200]})
