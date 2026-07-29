# Realtime Voice Studio

Voice-first personal companion chat app.

Current v1 focus:

- temporary login
- session history (SQLite)
- WebRTC realtime voice (browser <-> Azure OpenAI Realtime)
- realtime transcript shown in chat UI

## Project structure

- `apps/web`: frontend UI + WebRTC client
- `apps/service`: Flask API, auth, history storage, realtime ephemeral token endpoint
- `packages/shared`: reserved for shared contracts
- `docs`: product and architecture notes

## Local run

```bash
cd apps/service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5001`.

## Local smoke check

```bash
curl -s http://localhost:5001/api/health | jq

TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"localtest","password":"123456"}' | jq -r .token)

curl -s -X POST http://localhost:5001/api/realtime/session \
  -H "Authorization: Bearer ${TOKEN}" | jq
```

If `realtime_ready` is `true` and `/api/realtime/session` returns a token, backend side is ready.

## Environment variables

Create `apps/service/.env` from `apps/service/.env.example`.

Required for realtime:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT` (resource root, for example `https://<resource>.cognitiveservices.azure.com`)
- `AZURE_OPENAI_REALTIME_DEPLOYMENT` (for example `gpt-realtime-2.1`)

Optional realtime:

- `AZURE_OPENAI_REALTIME_VOICE` (default `alloy`)

Private access gate:

- `APP_ACCESS_PASSCODE` (required if you want to allow only users with a shared passcode)

Optional text fallback:

- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`

Security:

- do not commit `.env`
- frontend never receives long-lived Azure key
- frontend gets only ephemeral token from `POST /api/realtime/session`

## Prepare release to GitHub

If this folder is not yet a git repo:

```bash
cd /Users/kaynwang/Desktop/realtime-voice-studio
git init
git add .
git commit -m "feat: voice-first realtime app with azure webrtc"
```

Create a new empty GitHub repo, then:

```bash
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## Deploy to Azure App Service (self-test)

Target: personal testing, not production hardening.

1. Create App Service (Linux, Python 3.11 recommended).
2. Deploy from GitHub repo.
3. Set startup command in App Service:

```bash
gunicorn --chdir apps/service --bind 0.0.0.0:$PORT app:app
```

4. Add App Settings:

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_REALTIME_DEPLOYMENT`
- `AZURE_OPENAI_REALTIME_VOICE` (optional)
- `AZURE_OPENAI_CHAT_DEPLOYMENT` (optional)

5. Verify:

```bash
curl -s https://<your-app-name>.azurewebsites.net/api/health | jq
```

Expect:

- `realtime_ready: true`
- `missing_realtime_env: []`

Then open the site, login, click voice start, and allow microphone.

## Notes for mobile testing

- `localhost` works for desktop local dev.
- mobile device microphone requires HTTPS origin.
- for phone testing before cloud deploy, use a temporary HTTPS tunnel.