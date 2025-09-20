# Run Voice4EVs with Twilio (Media Streams over WebSockets)

This guide shows how to call your Pipecat voice agent by dialing a Twilio phone number.

## 1) Start backend containers (CSMS + simulators)

From the project root:

```bash
cd backend
docker compose up -d
```

Services exposed:
- OCPP WebSocket: `ws://localhost:9000/ocpp`
- REST API: `http://localhost:8000`

## 2) Prepare environment variables

Create `frontend/.env` with your keys (recommended for local dev). Example:

```ini
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token

# AI services
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=dg-...

# Optional overrides
# PORT=8765
# TESTING=false
# TWILIO_WS_URL=wss://<your-ngrok-subdomain>.ngrok.io/ws
```

Notes:
- The server reads these via `dotenv`. You can also export them in your shell instead of using `.env`.
- We use Deepgram STT + Deepgram TTS by default (no Cartesia key required).

## 3) Start ngrok (public URL for Twilio)

Install and authenticate ngrok (one time):

```bash
brew install ngrok
ngrok config add-authtoken <YOUR_NGROK_TOKEN>
```

Run the tunnel:

```bash
ngrok http 8765
```

Copy the HTTPS forwarding URL shown by ngrok, e.g. `https://abc123.ngrok.io`.

## 4) Start the Twilio server

In a separate terminal:

```bash
cd frontend
uv sync
uv run python twilio_server.py
```

This starts a FastAPI server on `http://0.0.0.0:8765` with:
- `POST /` → returns TwiML instructing Twilio to connect media to `wss://<host>/ws`
- `WS /ws` → Twilio Media Streams WebSocket used by Pipecat pipeline

Tip: You can test the TwiML locally:

```bash
curl -X POST http://localhost:8765/
```

## 5) Configure your Twilio phone number

In Twilio Console → Phone Numbers → Your Number → Voice & Fax:
- Set “A Call Comes In” to `HTTP POST`
- URL: `https://<your-ngrok-subdomain>.ngrok.io/`
- Save

You do NOT need to paste a TwiML document. The server will return TwiML that points to `wss://<your-ngrok-subdomain>.ngrok.io/ws` automatically. If your WS host differs, set `TWILIO_WS_URL` in `.env`.

## 6) Call the number

Dial the configured Twilio number. You should hear the agent greet you. Audio is 8kHz mono as required by Twilio Media Streams.

## Troubleshooting

- Ensure env vars are loaded (`frontend/.env` or exported).
- Verify backend is up: `docker compose ps` in `backend/`.
- Verify TwiML works locally: `curl -X POST http://localhost:8765/`.
- Check ngrok URL is HTTPS and reachable.
- Confirm Twilio number points to the ngrok HTTPS URL with HTTP POST.
- Logs: check the Twilio server terminal for connection and pipeline events.

## What’s running under the hood

- Server: `frontend/twilio_server.py` (FastAPI). It returns TwiML on `POST /` and handles Twilio Media Streams on `/ws`.
- Pipeline: Pipecat with Silero VAD, Deepgram STT, OpenAI LLM, and Deepgram TTS, configured for 8kHz I/O.


