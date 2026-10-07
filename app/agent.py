import logging
import shlex
import subprocess
import sys

from app import claude_reply, config, skills

log = logging.getLogger("agent")

MAX_TURNS = 8
SCRIPT_TIMEOUT = 30

SYSTEM = """You are running the Instagram skill "{name}" for @pranayseekgrowth.
Follow the skill playbook below exactly. Where it tells you to run a script in its folder,
call the run_skill_script tool instead of guessing the result. Available scripts: {scripts}.
Files the playbook says live in ~/.claude/instagram/ are not available here; the voice profile is included below.
Never publish anything. Return the finished output for the user to review.

VOICE PROFILE:
{voice}

SKILL PLAYBOOK:
{playbook}
"""

TOOL = {
    "name": "run_skill_script",
    "description": "Run one of this skill's own Python scripts and return its output. "
                   "Pass text files' contents via stdin and use '-' as the file argument when the script accepts it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "e.g. hookscore.py"},
            "args": {"type": "string", "description": "command-line arguments, e.g. --hook \"one line\""},
            "stdin": {"type": "string", "description": "text piped to the script"},
        },
        "required": ["script"],
    },
}


def run_skill_script(skill: str, script: str, args: str = "", stdin: str = "") -> str:
    if script not in skills.list_scripts(skill):
        return f"error: {script!r} is not a script of {skill}. Available: {skills.list_scripts(skill)}"
    folder = skills.skill_dir(skill)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(folder / script), *shlex.split(args or "")],
            input=stdin or "",
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT,
            cwd=folder,
        )
    except subprocess.TimeoutExpired:
        return "error: script timed out"
    except ValueError as e:
        return f"error: bad args: {e}"
    return (proc.stdout + ("\n[stderr]\n" + proc.stderr if proc.stderr else ""))[-8000:]


def run_skill(name: str, user_input: str) -> str:
    system = SYSTEM.format(
        name=name,
        scripts=", ".join(skills.list_scripts(name)) or "none",
        voice=skills.voice(),
        playbook=skills.load_skill(name),
    )
    messages = [{"role": "user", "content": user_input}]
    tools = [TOOL] if skills.list_scripts(name) else []

    for _ in range(MAX_TURNS):
        resp = claude_reply.client().messages.create(
            model=config.CLAUDE_MODEL, max_tokens=4000, system=system,
            messages=messages, **({"tools": tools} if tools else {}),
        )
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip()
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                inp = block.input or {}
                log.info("%s runs %s %s", name, inp.get("script"), inp.get("args", ""))
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": run_skill_script(name, inp.get("script", ""), inp.get("args", ""), inp.get("stdin", "")),
                })
        messages.append({"role": "user", "content": results})
    return "Stopped after too many tool calls; try a more specific request."
