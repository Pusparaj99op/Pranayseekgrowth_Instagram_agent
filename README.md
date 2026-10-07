# pranayseekgrowth Instagram auto-reply

Claude replies to your Instagram DMs and comments in your voice.

```
Instagram DM / comment -> Meta webhook -> this server -> Claude -> Instagram Graph API -> reply
```

- Replies to DMs (keeps the last 10 messages for context) and to top-level comments
- Keyword triggers: a comment with "GUIDE" gets a DM with your link (`config/keywords.json`)
- Hands pricing, complaints and sensitive topics back to you, and skips spam
- `DRY_RUN=true` by default: it logs what it would send and sends nothing

## Setup (about 30 minutes)

### 1. Make the Instagram account professional
In the Instagram app: Settings > Account type and tools > **Switch to professional account** (Creator or Business).
Then go to Settings > Messages > **Connected tools** and turn on **Allow access to messages**.

### 2. Create the Meta app
1. Go to https://developers.facebook.com/apps and click **Create app**. Choose **Other**, then **Business**.
2. Add the product **Instagram** and choose **API setup with Instagram login**.
3. Under **Generate access tokens**, add `pranayseekgrowth` and copy:
   - the **access token** -> `IG_ACCESS_TOKEN`
   - the **Instagram account ID** shown next to it -> `IG_USER_ID`
4. App settings > Basic > **App secret** -> `META_APP_SECRET`
5. Make up any random string -> `META_VERIFY_TOKEN`

### 3. Get a Claude API key
https://console.anthropic.com > API Keys -> `ANTHROPIC_API_KEY` (add a few dollars of credit).

### 4. Fill in your voice
Edit `config/voice.md`: how you talk, words you use, what you sell, and what you never say. This decides whether the replies sound like you.
Edit `config/keywords.json` and replace `{{paste your link here}}` with your real link.

### 5. Deploy (Render, free)
1. Push this repo to GitHub.
2. Go to https://render.com, click **New > Blueprint**, and pick this repo. It reads `render.yaml`.
3. Paste in the 5 secret values from steps 2 and 3. Keep `DRY_RUN=true`.
4. Once it's live, check that `https://<your-app>.onrender.com/health` returns `{"ok": true, ...}`.

> The free tier sleeps after 15 minutes idle, and Meta may time out on the first event after it wakes up. Use the $7 Starter plan for reliable replies.

### 6. Connect the webhook
In the Meta app: Instagram > API setup > **Configure webhooks**
- Callback URL: `https://<your-app>.onrender.com/webhook`
- Verify token: your `META_VERIFY_TOKEN`
- Click **Verify and save**, then subscribe to **messages** and **comments**.

### 7. Test, then go live
1. From a second Instagram account, DM `pranayseekgrowth` and comment on a post.
2. In Render > Logs, look for lines like `[DRY_RUN] POST ... reply`. Read the replies.
3. When you're happy with them, set `DRY_RUN=false` in Render's environment and it redeploys.

### 8. Going public (Meta App Review)
While the app is in **Development** mode, it only receives events from people who have a role on the app (you and your testers).
To reply to everyone, switch the app to **Live** and submit for App Review with `instagram_business_manage_messages` and `instagram_business_manage_comments`. You'll need a privacy policy URL and a short screen recording of the bot working.

## Skills in this repo
All 13 skills from [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) are installed in `.claude/skills/`. Open this repo in Claude Code and `/ig-reel`, `/ig-caption`, `/ig-carousel`, `/ig-story`, `/ig-plan`, `/ig-viral`, `/ig-human`, `/ig-audit`, `/ig-profile`, `/ig-comment`, `/ig-reply`, `/ig-dm` and `/ig-repurpose` work right away. No install step.

The live bot uses them too:
- **DM replies** follow the `ig-dm` playbook. **Comment replies** follow `ig-reply`.
- Every reply goes through `ig-human`: its `humanize.py` strips em dashes, slop words and invisible characters. `detect.py` then scores the reply, and if it gets FLAGGED, Claude rewrites it once.

## Use the AI skills (API and CLI)
Your deployed app can run any skill, including the skill's own scripts (`hookscore.py`, `beats.py`, `caption.py`, `swipe.py`, etc.). Claude runs those scripts instead of guessing their results.

```bash
# list the skills
curl -H "Authorization: Bearer $ADMIN_API_KEY" https://<your-app>.onrender.com/ai/skills

# write a reel
curl -X POST https://<your-app>.onrender.com/ai/ig-reel \
  -H "Authorization: Bearer $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d '{"input": "I helped a client go from 200 to 12k followers in 6 weeks"}'
```

From your computer:
```bash
python -m app.cli list
python -m app.cli ig-reel "I helped a client go from 200 to 12k followers in 6 weeks"
python -m app.cli ig-caption "caption for the reel above: ..."
```
These only return text. Nothing gets posted until you post it yourself. Set `ADMIN_API_KEY` in Render so nobody else can use your endpoints.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env      # fill it in
uvicorn app.main:app --reload
pytest
```
To receive real webhooks locally, run `ngrok http 8000` and use the ngrok URL as the callback.

## Limits to know
- Meta's rules only allow DM replies within **24 hours** of the person's last message. The bot follows this.
- At most 10 replies per person per hour (`MAX_REPLIES_PER_USER_PER_HOUR`).
- The bot doesn't reply to replies inside comment threads, only to top-level comments.
- Instagram access tokens expire after 60 days. Refresh yours from the Meta dashboard.
