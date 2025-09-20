#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Pipecat Quickstart Example.

The example runs a simple voice AI bot that you can connect to using your
browser and speak with it. You can also deploy this bot to Pipecat Cloud.

Required AI services:
- Deepgram (Speech-to-Text)
- OpenAI (LLM)
- Cartesia (Text-to-Speech)

Run the bot using::

    uv run bot.py
"""

import asyncio
import os
import logging
import sys

from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import LLMRunFrame

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds first run only)\n")

logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")
logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
#from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.assemblyai.stt import AssemblyAISTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.mistral.llm import MistralLLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from csms_tools import get_tools, register_csms_function_handlers
from csms_system_prompt import CSMS_SYSTEM_PROMPT

from pipecat.transports.base_transport import BaseTransport, TransportParams

# class TwilioTransport(BaseTransport):
#     def __init__(self, params: TransportParams):
#         super().__init__(params)
#         # here you’ll manage Twilio websocket/media stream connections

#     async def input(self):
#         # Receive Twilio audio (base64 PCM) and pass it into pipeline
#         pass

#     async def output(self):
#         # Send pipeline’s TTS audio back to Twilio in the right format
#         pass
import base64
import numpy as np
import io
from pydub import AudioSegment

class TwilioTransport(BaseTransport):
    def __init__(self, params: TransportParams):
        super().__init__(params)
        self._input_queue = asyncio.Queue()
        self._output_queue = asyncio.Queue()

    async def input(self):
        # Wait for audio frames from Twilio
        audio_bytes = await self._input_queue.get()  # raw PCM bytes
        # Convert to float32 numpy array if needed
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    async def feed_audio_from_twilio(self, base64_payload: str):
        # Decode base64 PCM and put in input queue
        audio_bytes = base64.b64decode(base64_payload)
        await self._input_queue.put(audio_bytes)

    async def output(self):
        # Wait for TTS frames from the pipeline
        tts_audio_bytes = await self._output_queue.get()  # raw PCM bytes
        payload = base64.b64encode(tts_audio_bytes).decode("ascii")
        # You can now send this payload over your WebSocket to Twilio
        return payload

    async def send_audio_to_twilio(self, audio_bytes: bytes):
        await self._output_queue.put(audio_bytes)


# from fastapi import FastAPI, WebSocket, Request
# from fastapi.responses import Response
# from dotenv import load_dotenv
# import os
# import base64
# import asyncio

# load_dotenv()

# app = FastAPI()
# NGROK_URL = os.getenv("NGROK_URL")

# # -------------------
# # Twilio POST webhook
# # -------------------
# @app.post("/")
# async def twilio_webhook(request: Request):
#     twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
# <Response>
#     <Connect>
#         <Stream url="{NGROK_URL}/stream"/>
#     </Connect>
# </Response>"""
#     return Response(content=twiml, media_type="application/xml")

# # -------------------
# # WebSocket for Twilio Media Stream
# # -------------------
# @ws.websocket("/stream")
# async def stream_endpoint(ws: WebSocket):
#     await ws.accept()
#     transport = TwilioTransport(transport_params["twilio"]())

    
#     try:
#         while True:
#             data = await ws.receive_json()
#             media_payload = data.get("media", {}).get("payload")
#             if media_payload:
#                 # Feed audio into transport
#                 await transport.feed_audio_from_twilio(media_payload)
                
#                 # Get TTS response from transport
#                 tts_payload = await transport.output()
#                 await ws.send_json({
#                     "event": "media",
#                     "media": {"payload": tts_payload}
#                 })
#     except Exception as e:
#         print("WebSocket closed:", e)


# @app.get("/")
# async def test_get():
#     twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
# <Response>
#     <Connect>
#         <Stream url="{NGROK_URL}/stream"/>
#     </Connect>
# </Response>"""
#     return Response(content=twiml, media_type="application/xml")


logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)

# Reduce verbose logs: suppress DEBUG to avoid full LLM context dumps, keep INFO+ (tool call logs)
from loguru import logger as _loguru_logger
_loguru_logger.remove()
_loguru_logger.add(sys.stderr, level="INFO")

# Additionally down-level specific noisy namespaces
logging.getLogger("pipecat.services.openai.base_llm").setLevel(logging.WARNING)
logging.getLogger("pipecat.services.openai").setLevel(logging.WARNING)
logging.getLogger("pipecat.services").setLevel(logging.INFO)
logging.getLogger("pipecat.processors.metrics").setLevel(logging.WARNING)
logging.getLogger("pipecat.transports").setLevel(logging.INFO)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    tts = DeepgramTTSService(api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-2-andromeda-en")

    stt = AssemblyAISTTService(
        api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    )
    # tts = CartesiaTTSService(
    #     api_key=os.getenv("CARTESIA_API_KEY"),
    #     voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    # )

    # llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")
    llm = MistralLLMService(api_key=os.getenv("MISTRAL_API_KEY"))

    # Register CSMS function handlers and provide tool schemas to the LLM
    register_csms_function_handlers(llm)

    messages = [
        {
            "role": "system",
            "content": CSMS_SYSTEM_PROMPT,
        },
    ]

    tools = get_tools()
    context = OpenAILLMContext(messages, tools=tools)
    context_aggregator = llm.create_context_aggregator(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
        "twilio": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        )
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
