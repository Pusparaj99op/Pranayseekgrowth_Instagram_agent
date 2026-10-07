import json
import logging
import time

from app import claude_reply, config, instagram, store

log = logging.getLogger("handlers")

DM_WINDOW_SECONDS = 24 * 3600


def load_keywords() -> list[dict]:
    try:
        return json.loads(config.KEYWORDS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []


def match_keyword(text: str) -> dict | None:
    words = text.upper().split()
    for rule in load_keywords():
        if rule["keyword"].upper() in words:
            return rule
    return None


def handle_payload(payload: dict) -> None:
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            _safe(handle_dm, event)
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                _safe(handle_comment, change.get("value", {}))


def _safe(fn, arg) -> None:
    try:
        fn(arg)
    except Exception:
        log.exception("handler failed for %s", fn.__name__)


def handle_dm(event: dict) -> None:
    if not config.REPLY_TO_DMS:
        return
    msg = event.get("message") or {}
    sender = (event.get("sender") or {}).get("id")
    text = msg.get("text")
    if msg.get("is_echo") or not sender or sender == config.IG_USER_ID or not text:
        return
    if not store.mark_seen(f"dm:{msg.get('mid')}"):
        return
    ts = event.get("timestamp", time.time() * 1000) / 1000
    if time.time() - ts > DM_WINDOW_SECONDS:
        log.info("DM older than 24h, skipping (Meta messaging window)")
        return

    history = store.get_history(sender)
    store.add_history(sender, "them", text)
    if not store.can_reply(sender, config.MAX_REPLIES_PER_USER_PER_HOUR):
        log.info("rate limit hit for %s", sender)
        return

    rule = match_keyword(text)
    reply = rule["dm"] if rule else claude_reply.generate_reply("dm", text, history)
    if not reply:
        log.info("SKIP DM from %s: %r", sender, text)
        return
    log.info("DM reply to %s: %r -> %r", sender, text, reply)
    instagram.send_dm(sender, reply)
    store.add_history(sender, "me", reply)
    store.record_reply(sender)


def handle_comment(value: dict) -> None:
    if not config.REPLY_TO_COMMENTS:
        return
    comment_id = value.get("id")
    text = value.get("text")
    author = value.get("from") or {}
    if not comment_id or not text or author.get("id") == config.IG_USER_ID:
        return
    if author.get("username", "").lower() == "pranayseekgrowth":
        return
    if value.get("parent_id"):
        return
    if not store.mark_seen(f"comment:{comment_id}"):
        return
    user = author.get("id", comment_id)
    if not store.can_reply(user, config.MAX_REPLIES_PER_USER_PER_HOUR):
        return

    rule = match_keyword(text)
    if rule:
        instagram.send_private_reply(comment_id, rule["dm"])
        if rule.get("comment_reply"):
            instagram.reply_comment(comment_id, rule["comment_reply"])
        log.info("keyword %s triggered by comment %s", rule["keyword"], comment_id)
        store.record_reply(user)
        return

    reply = claude_reply.generate_reply("comment", text)
    if not reply:
        log.info("SKIP comment %s: %r", comment_id, text)
        return
    log.info("comment reply %s: %r -> %r", comment_id, text, reply)
    instagram.reply_comment(comment_id, reply)
    store.record_reply(user)
