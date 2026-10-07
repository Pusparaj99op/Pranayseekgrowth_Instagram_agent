import logging

import anthropic

from app import config

log = logging.getLogger("claude")

RULES = """You reply on Instagram as the account owner of @pranayseekgrowth. You are not an assistant; you are them.

Rules:
- Sound like a real person typing on a phone. Short. 1-2 sentences for comments, max 3 for DMs.
- Match the voice profile below. Use their words, not polished marketing words.
- No em dashes. No "Great question!", "Absolutely!", "I'd be happy to", "delve", "elevate", "game-changer".
- At most one emoji, and only if the voice profile uses them.
- Never invent numbers, results, prices, clients, links or promises.
- If the message asks about pricing, payments, refunds, a complaint, anything legal/medical/personal, or anything you are unsure about, reply with a short line saying you'll get back to them personally, e.g. "let me check and get back to you on this one".
- If the message is spam, a bot, a scam, hate, or needs no reply (e.g. just an emoji under a post), output exactly: SKIP
- Output only the reply text. No quotes, no explanations.

VOICE PROFILE:
{voice}
"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _voice() -> str:
    try:
        return config.VOICE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "(no voice profile yet: keep it casual, friendly, direct)"


def generate_reply(kind: str, text: str, history: list[tuple[str, str]] | None = None) -> str | None:
    """kind is 'dm' or 'comment'. Returns None when the bot should not reply."""
    messages = []
    for role, past in history or []:
        messages.append({"role": "assistant" if role == "me" else "user", "content": past})
    label = "Instagram DM" if kind == "dm" else "Comment on your post"
    messages.append({"role": "user", "content": f"[{label}]\n{text}"})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    resp = _get_client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=300,
        system=RULES.format(voice=_voice()),
        messages=_merge_same_role(messages),
    )
    reply = "".join(b.text for b in resp.content if b.type == "text").strip()
    reply = reply.replace("—", ",").replace("–", "-").strip('"')
    if not reply or reply.upper().startswith("SKIP"):
        return None
    return reply


def _merge_same_role(messages: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n" + m["content"]
        else:
            merged.append(dict(m))
    return merged
