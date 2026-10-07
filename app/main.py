import hashlib
import hmac
import json
import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app import agent, config, handlers, skills

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="pranayseekgrowth auto-reply")


@app.get("/health")
def health():
    return {"ok": True, "dry_run": config.DRY_RUN}


@app.get("/webhook")
def verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == config.META_VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verification failed")


def valid_signature(body: bytes, header: str | None) -> bool:
    if not config.META_APP_SECRET or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(config.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    if not valid_signature(body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail="bad signature")
    background.add_task(handlers.handle_payload, json.loads(body))
    return {"received": True}


class SkillRequest(BaseModel):
    input: str


def require_admin(authorization: str | None) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not config.ADMIN_API_KEY or not hmac.compare_digest(token, config.ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="missing or wrong ADMIN_API_KEY")


@app.get("/ai/skills")
def ai_skills(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    return skills.list_skills()


@app.post("/ai/{name}")
def ai_run(name: str, req: SkillRequest, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    try:
        skills.skill_dir(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown skill {name}")
    return {"skill": name, "output": agent.run_skill(name, req.input)}
