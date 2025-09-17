# cp_sim.py
import asyncio
import logging
import websockets
import json
from datetime import datetime
from ocpp.v16 import call
from ocpp.v16.enums import ChargePointStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def connect_to_csms():
    """Connect to CSMS with retry logic"""
    uri = "ws://csms:9000/EVSE001"  # Use 'csms' hostname for Docker
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to CSMS (attempt {attempt + 1}/{max_retries})")
            async with websockets.connect(uri, subprotocols=["ocpp1.6"]) as ws:
                logger.info("Connected to CSMS!")
                await run_ocpp_protocol(ws)
                return
        except websockets.exceptions.ConnectionRefused:
            logger.warning(f"Connection refused. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Connection error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
    
    logger.error("Failed to connect to CSMS after all retries")

async def run_ocpp_protocol(ws):
    """Run the OCPP protocol with the CSMS"""
    try:
        # 1) BootNotification
        boot_payload = {
            "chargePointVendor": "Demo", 
            "chargePointModel": "Sim"
        }
        ocpp_msg = [2, "unique_id_1", "BootNotification", boot_payload]
        await ws.send(json.dumps(ocpp_msg))
        logger.info("Sent BootNotification")
        response = await ws.recv()
        logger.info(f"Received: {response}")

        # 2) StatusNotification
        status_payload = {
            "connectorId": 1, 
            "errorCode": "NoError", 
            "status": "Available",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        ocpp_msg = [2, "unique_id_2", "StatusNotification", status_payload]
        await ws.send(json.dumps(ocpp_msg))
        logger.info("Sent StatusNotification")
        response = await ws.recv()
        logger.info(f"Received: {response}")

        # 3) Heartbeats
        heartbeat_id = 3
        while True:
            heartbeat_payload = {}
            ocpp_msg = [2, f"unique_id_{heartbeat_id}", "Heartbeat", heartbeat_payload]
            await ws.send(json.dumps(ocpp_msg))
            logger.info(f"Sent Heartbeat #{heartbeat_id}")
            response = await ws.recv()
            logger.info(f"Received: {response}")
            heartbeat_id += 1
            await asyncio.sleep(30)
            
    except websockets.exceptions.ConnectionClosed:
        logger.warning("Connection closed by CSMS")
    except Exception as e:
        logger.error(f"Error in OCPP protocol: {e}")

async def main():
    logger.info("Starting Charge Point Simulator...")
    await connect_to_csms()

if __name__ == "__main__":
    asyncio.run(main())
