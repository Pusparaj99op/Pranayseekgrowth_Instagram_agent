import importlib.util
import json
import re
from functools import lru_cache
from types import ModuleType

from app import config

SKILLS_DIR = config.ROOT / ".claude" / "skills"
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def skill_dir(name: str):
    path = (SKILLS_DIR / name).resolve()
    if path.parent != SKILLS_DIR.resolve() or not (path / "SKILL.md").is_file():
        raise KeyError(f"unknown skill: {name}")
    return path


@lru_cache
def load_skill(name: str) -> str:
    text = (skill_dir(name) / "SKILL.md").read_text(encoding="utf-8")
    return _FRONTMATTER.sub("", text, count=1).strip()


def list_skills() -> list[dict]:
    out = []
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        m = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
        meta = m.group(1) if m else ""
        desc = re.search(r"description:\s*>?-?\s*(.*?)(?:\n\S|\Z)", meta, re.S)
        out.append({
            "name": path.parent.name,
            "description": " ".join(desc.group(1).split()) if desc else "",
        })
    return out


def list_scripts(name: str) -> list[str]:
    return sorted(p.name for p in skill_dir(name).glob("*.py"))


@lru_cache
def _module(filename: str) -> ModuleType:
    path = SKILLS_DIR / "ig-human" / filename
    spec = importlib.util.spec_from_file_location(f"ig_human_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@lru_cache
def _lexicon() -> dict:
    return json.loads((SKILLS_DIR / "ig-human" / "slop.json").read_text(encoding="utf-8"))


def humanize(text: str) -> str:
    cleaned, _report = _module("humanize.py").humanize(text, _lexicon())
    return cleaned.strip()


def human_score(text: str) -> tuple[float, str, dict]:
    results, overall, verdict = _module("detect.py").run(text, _lexicon())
    notes = {k: v[1] for k, v in results.items()}
    return overall, verdict, notes


def voice() -> str:
    try:
        return config.VOICE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "(no voice profile yet: keep it casual, friendly, direct)"
