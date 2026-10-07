# pranayseekgrowth Instagram agent

- The 13 `ig-*` skills in `.claude/skills/` come from github.com/Jakeschincariol/instagram-agent-skill (MIT). Keep them unmodified so upstream updates can be copied over.
- In this repo, the voice profile lives at `config/voice.md`, not `~/.claude/instagram/voice.md`. Read it from there. Write `swipe.md` (from ig-viral) and `log.md` (from ig-reel and the other skills) to `config/` as well.
- The auto-reply bot (`app/`) uses ig-dm, ig-reply and ig-human at runtime through `app/skills.py`. `app/agent.py` runs any skill with its own scripts as tools.
- Run tests with `pytest`.
