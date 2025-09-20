import os
import json
from typing import Optional

from fastapi import FastAPI, WebSocket, Request
from starlette.responses import HTMLResponse
from dotenv import load_dotenv

# Pipecat imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

# Services
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService

# FastAPI Websocket transport and Twilio serializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer

# Project prompt/tools
from csms_tools import get_tools, register_csms_function_handlers, start_call_logging_session, end_call_logging_session
from csms_system_prompt import CSMS_SYSTEM_PROMPT


load_dotenv(override=True)

app = FastAPI()


def _ws_url_from_env(request: Request) -> str:
    # Prefer explicit URL; e.g., wss://<your-domain>/ws
    explicit_url = os.getenv("TWILIO_WS_URL")
    if explicit_url:
        return explicit_url

    # Derive from request as a fallback (best-effort; ensure HTTPS/WSS in production)
    scheme = "wss" if request.url.scheme == "https" else "ws"
    return f"{scheme}://{request.url.netloc}/ws"


@app.post("/")
async def twilio_entrypoint(request: Request):
    """Respond to Twilio with TwiML that instructs it to connect a Media Stream to our WebSocket."""
    ws_url = _ws_url_from_env(request)
    twiml = (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        f"<Response>\n"
        f"  <Connect>\n"
        f"    <Stream url=\"{ws_url}\"></Stream>\n"
        f"  </Connect>\n"
        f"  <Pause length=\"40\"/>\n"
        f"</Response>\n"
    )
    return HTMLResponse(content=twiml, media_type="application/xml")


async def run_bot_twilio(websocket_client: WebSocket, stream_sid: str, call_sid: str, testing: bool):
    # Twilio serializer handles protocol details and optional call cleanup via REST API
    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )

    # AI services (use ones declared in pyproject extras)
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"), audio_passthrough=True)
    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-2-andromeda-en")

    messages = [
        {
            "role": "system",
            "content": CSMS_SYSTEM_PROMPT,
        }
    ]

    # Tools/context
    tools = get_tools()
    register_csms_function_handlers(llm)
    context = OpenAILLMContext(messages, tools=tools)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,  # Twilio media streams are 8kHz
            audio_out_sample_rate=8000,
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Start a new per-call log file
        try:
            path = start_call_logging_session(session_name=f"twilio_{call_sid}")
            if path:
                print(f"API call log file: {path}")
        except Exception:
            pass
        # Kick off conversation
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        try:
            end_call_logging_session()
        except Exception:
            pass
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Twilio sends a text frame with event "connected", then "start" with call details
    text_iter = websocket.iter_text()
    try:
        await text_iter.__anext__()  # connected
        call_data = json.loads(await text_iter.__anext__())  # start
    except Exception:
        await websocket.close()
        return

    start_info: Optional[dict] = call_data.get("start") if isinstance(call_data, dict) else None
    if not start_info:
        await websocket.close()
        return

    stream_sid = start_info.get("streamSid", "")
    call_sid = start_info.get("callSid", "")
    testing = os.getenv("TESTING", "false").lower() == "true"

    await run_bot_twilio(websocket, stream_sid, call_sid, testing)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8765")))


