from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agent, claude_reply, config, main, skills


def test_all_skills_installed():
    names = {s["name"] for s in skills.list_skills()}
    assert len(names) == 13 and {"ig-reel", "ig-dm", "ig-reply", "ig-human"} <= names


def test_load_skill_strips_frontmatter():
    body = skills.load_skill("ig-reel")
    assert body.startswith("# ig-reel") and "description:" not in body.splitlines()[0]


def test_unknown_or_traversal_skill_rejected():
    for bad in ["nope", "../app", "ig-reel/../../app"]:
        with pytest.raises(KeyError):
            skills.skill_dir(bad)


def test_humanize_strips_em_dash_and_slop():
    out = skills.humanize("We delve into growth — it's a game-changer.")
    assert "—" not in out and "delve" not in out.lower()
    score, verdict, notes = skills.human_score(out)
    assert verdict in {"PASS", "REVIEW", "FLAGGED"} and set(notes) >= {"VOICE"}


def test_run_skill_script_whitelist_and_real_run():
    assert agent.run_skill_script("ig-reel", "../../app/main.py").startswith("error")
    out = agent.run_skill_script("ig-reel", "hookscore.py", '--hook "Proposals took me five hours. Twenty minutes now."')
    assert "error" not in out[:10] and out.strip()


def fake_response(text):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


class FakeClient:
    def __init__(self, text):
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)
        self.text = text

    def _create(self, **kw):
        self.calls.append(kw)
        return fake_response(self.text)


def test_dm_reply_uses_ig_dm_skill(monkeypatch):
    fake = FakeClient("hey, glad it helped — what are you working on?")
    monkeypatch.setattr(claude_reply, "_client", fake)
    reply = claude_reply.generate_reply("dm", "loved your reel")
    assert "—" not in reply
    assert skills.load_skill("ig-dm")[:200] in fake.calls[0]["system"]


def test_skip(monkeypatch):
    monkeypatch.setattr(claude_reply, "_client", FakeClient("SKIP"))
    assert claude_reply.generate_reply("comment", "follow4follow") is None


def test_ai_endpoint_auth(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "k")
    monkeypatch.setattr(agent, "run_skill", lambda name, text: f"{name}:{text}")
    c = TestClient(main.app)
    assert c.post("/ai/ig-reel", json={"input": "x"}).status_code == 401
    r = c.post("/ai/ig-reel", json={"input": "x"}, headers={"Authorization": "Bearer k"})
    assert r.status_code == 200 and r.json()["output"] == "ig-reel:x"
    assert c.post("/ai/nope", json={"input": "x"}, headers={"Authorization": "Bearer k"}).status_code == 404
    assert len(c.get("/ai/skills", headers={"Authorization": "Bearer k"}).json()) == 13
