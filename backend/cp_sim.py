# cp_sim.py
import asyncio
import logging
import websockets
import json
import os
from datetime import datetime
from ocpp.v16 import call
from ocpp.v16.enums import ChargePointStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def connect_to_csms():
    """Connect to CSMS with retry logic"""
    cp_id = os.environ.get("CP_ID", "EVSE001")
    uri = f"ws://csms:9000/{cp_id}"  # Use 'csms' hostname for Docker
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"[{cp_id}] Attempting to connect to CSMS (attempt {attempt + 1}/{max_retries})")
            async with websockets.connect(uri, subprotocols=["ocpp1.6"]) as ws:
                logger.info(f"[{cp_id}] Connected to CSMS!")
                await run_ocpp_protocol(ws, cp_id)
                return
        except ConnectionRefusedError:
            logger.warning(f"[{cp_id}] Connection refused. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"[{cp_id}] Connection error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
    
    logger.error(f"[{cp_id}] Failed to connect to CSMS after all retries")

async def run_ocpp_protocol(ws, cp_id):
    """Run the OCPP protocol with the CSMS"""
    try:
        # 1) BootNotification
        boot_payload = {
            "chargePointVendor": "Demo", 
            "chargePointModel": "Sim"
        }
        ocpp_msg = [2, f"{cp_id}_boot", "BootNotification", boot_payload]
        await ws.send(json.dumps(ocpp_msg))
        logger.info(f"[{cp_id}] Sent BootNotification")
        response = await ws.recv()
        logger.info(f"[{cp_id}] Received: {response}")

        # 2) StatusNotification
        status_payload = {
            "connectorId": 1, 
            "errorCode": "NoError", 
            "status": "Available",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        ocpp_msg = [2, f"{cp_id}_status", "StatusNotification", status_payload]
        await ws.send(json.dumps(ocpp_msg))
        logger.info(f"[{cp_id}] Sent StatusNotification")
        response = await ws.recv()
        logger.info(f"[{cp_id}] Received: {response}")

        # 3) Heartbeats
        heartbeat_id = 1
        while True:
            heartbeat_payload = {}
            ocpp_msg = [2, f"{cp_id}_hb_{heartbeat_id}", "Heartbeat", heartbeat_payload]
            await ws.send(json.dumps(ocpp_msg))
            logger.info(f"[{cp_id}] Sent Heartbeat #{heartbeat_id}")
            response = await ws.recv()
            logger.info(f"[{cp_id}] Received: {response}")
            heartbeat_id += 1
            await asyncio.sleep(60)
            
    except websockets.exceptions.ConnectionClosed:
        logger.warning(f"[{cp_id}] Connection closed by CSMS")
    except Exception as e:
        logger.error(f"[{cp_id}] Error in OCPP protocol: {e}")

async def main():
    cp_id = os.environ.get("CP_ID", "EVSE001")
    logger.info(f"Starting Charge Point Simulator [{cp_id}]...")
    await connect_to_csms()

if __name__ == "__main__":
    asyncio.run(main())
