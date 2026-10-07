import logging

import anthropic

from app import config, skills

log = logging.getLogger("claude")

RULES = """You reply on Instagram as the account owner of @pranayseekgrowth. You are not an assistant; you are them.

You are replying LIVE to one {label}. The skill playbook below was written for drafting batches; apply its judgement to this single message, but output only the one reply you would send, nothing else. No triage table, no options, no labels, no quotes.

Hard rules (these win over the playbook):
- Sound like a real person typing on a phone. 1-2 sentences for comments, max 3 for DMs.
- Never invent numbers, results, prices, clients, links or promises.
- Pricing, payments, refunds, complaints, legal/medical/personal topics, or anything unsure: say you'll get back to them personally.
- Spam, bots, scams, hate, or nothing worth answering: output exactly SKIP

VOICE PROFILE:
{voice}

SKILL PLAYBOOK ({skill}):
{playbook}
"""

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def build_system(kind: str) -> str:
    skill = "ig-dm" if kind == "dm" else "ig-reply"
    return RULES.format(
        label="Instagram DM" if kind == "dm" else "comment on your post",
        voice=skills.voice(),
        skill=skill,
        playbook=skills.load_skill(skill),
    )


def _ask(system: str, messages: list[dict]) -> str:
    resp = client().messages.create(
        model=config.CLAUDE_MODEL, max_tokens=400, system=system, messages=messages
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip().strip('"')


def generate_reply(kind: str, text: str, history: list[tuple[str, str]] | None = None) -> str | None:
    """kind is 'dm' or 'comment'. Returns None when the bot should not reply."""
    messages = [
        {"role": "assistant" if role == "me" else "user", "content": past}
        for role, past in history or []
    ]
    messages.append({"role": "user", "content": text})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages = _merge_same_role(messages)
    system = build_system(kind)

    draft = _ask(system, messages)
    if not draft or draft.upper().startswith("SKIP"):
        return None
    reply = skills.humanize(draft)
    score, verdict, notes = skills.human_score(reply)

    if verdict == "FLAGGED":
        retry_msgs = messages + [
            {"role": "assistant", "content": draft},
            {"role": "user", "content": "That reads machine-written. Detector notes: "
             f"{notes}. Rewrite it plainer and more like the voice profile. Output only the reply."},
        ]
        second = _ask(system, retry_msgs)
        if second and not second.upper().startswith("SKIP"):
            second = skills.humanize(second)
            s2, v2, _ = skills.human_score(second)
            if s2 > score:
                reply, score, verdict = second, s2, v2

    log.info("human score %.0f %s", score, verdict)
    return reply


def _merge_same_role(messages: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n" + m["content"]
        else:
            merged.append(dict(m))
    return merged
