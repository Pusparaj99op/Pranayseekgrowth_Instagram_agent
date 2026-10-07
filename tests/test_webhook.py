import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app import claude_reply, config, handlers, instagram, main, store

SECRET = "test-secret"


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "META_APP_SECRET", SECRET)
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "vt")
    monkeypatch.setattr(config, "IG_USER_ID", "ME")
    monkeypatch.setattr(config, "DRY_RUN", True)
    store.reset(str(tmp_path / "t.db"))
    sent = []
    monkeypatch.setattr(instagram, "_post", lambda path, payload: sent.append((path, payload)))
    monkeypatch.setattr(claude_reply, "generate_reply", lambda kind, text, history=None: f"reply:{text}")
    return sent


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


client = TestClient(main.app)


def test_verify_handshake():
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"})
    assert r.status_code == 200 and r.text == "42"
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "42"})
    assert r.status_code == 403


def test_bad_signature_rejected():
    r = client.post("/webhook", content=b"{}", headers={"x-hub-signature-256": "sha256=bad"})
    assert r.status_code == 401


def dm_payload(text, sender="U1", mid="m1", echo=False):
    return {"entry": [{"messaging": [{
        "sender": {"id": sender}, "timestamp": time.time() * 1000,
        "message": {"mid": mid, "text": text, "is_echo": echo},
    }]}]}


def test_dm_reply_and_dedupe(setup):
    body = json.dumps(dm_payload("hi")).encode()
    for _ in range(2):
        assert client.post("/webhook", content=body, headers={"x-hub-signature-256": sign(body)}).status_code == 200
    assert setup == [("ME/messages", {"recipient": {"id": "U1"}, "message": {"text": "reply:hi"}})]


def test_echo_and_self_ignored(setup):
    handlers.handle_payload(dm_payload("x", echo=True))
    handlers.handle_payload(dm_payload("x", sender="ME", mid="m2"))
    assert setup == []


def test_comment_reply_and_keyword(setup):
    handlers.handle_payload({"entry": [{"changes": [{"field": "comments", "value": {
        "id": "c1", "text": "love this", "from": {"id": "U2", "username": "fan"}}}]}]})
    handlers.handle_payload({"entry": [{"changes": [{"field": "comments", "value": {
        "id": "c2", "text": "guide please", "from": {"id": "U3", "username": "lead"}}}]}]})
    assert setup[0] == ("c1/replies", {"message": "reply:love this"})
    assert setup[1][0] == "ME/messages" and setup[1][1]["recipient"] == {"comment_id": "c2"}
