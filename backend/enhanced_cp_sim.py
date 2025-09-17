"""
Enhanced Charge Point Simulator with Demo Scenario Support
Supports scriptable demo scenarios for voice agent testing
"""

import asyncio
import logging
import websockets
import json
from datetime import datetime
from ocpp.v16 import call
from ocpp.v16.enums import ChargePointStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedChargePointSimulator:
    """Enhanced simulator that can trigger demo scenarios"""
    
    def __init__(self, cp_id: str = "EVSE001"):
        self.cp_id = cp_id
        self.websocket = None
        self.demo_mode = False
        self.active_scenario = None
        self.transaction_id = 0
        self.heartbeat_task = None
        self.is_charging = False
        
    async def connect_to_csms(self):
        """Connect to CSMS with retry logic"""
        uri = "ws://csms:9000/EVSE001"  # Use 'csms' hostname for Docker
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to CSMS (attempt {attempt + 1}/{max_retries})")
                async with websockets.connect(uri, subprotocols=["ocpp1.6"]) as self.websocket:
                    logger.info("Connected to CSMS!")
                    await self.run_ocpp_protocol()
                    return
            except websockets.exceptions.ConnectionRefused:
                logger.warning(f"Connection refused. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Connection error: {e}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        
        logger.error("Failed to connect to CSMS after all retries")

    async def run_ocpp_protocol(self):
        """Run the OCPP protocol with the CSMS"""
        try:
            # 1) BootNotification
            await self.send_boot_notification()
            
            # 2) StatusNotification
            await self.send_status_notification("Available", "NoError")
            
            # 3) Start heartbeats
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            # 4) Listen for commands
            await self.listen_for_commands()
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by CSMS")
        except Exception as e:
            logger.error(f"Error in OCPP protocol: {e}")
        finally:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()

    async def send_boot_notification(self):
        """Send BootNotification"""
        boot_payload = {
            "chargePointVendor": "Demo",
            "chargePointModel": "Sim"
        }
        await self.send_ocpp_message("BootNotification", boot_payload)
        response = await self.recv_ocpp_message()
        logger.info(f"BootNotification response: {response}")

    async def send_status_notification(self, status: str, error_code: str = "NoError"):
        """Send StatusNotification"""
        status_payload = {
            "connectorId": 1,
            "errorCode": error_code,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_ocpp_message("StatusNotification", status_payload)
        response = await self.recv_ocpp_message()
        logger.info(f"StatusNotification response: {response}")

    async def heartbeat_loop(self):
        """Send heartbeats every 30 seconds"""
        heartbeat_id = 1
        while True:
            try:
                heartbeat_payload = {}
                await self.send_ocpp_message("Heartbeat", heartbeat_payload)
                response = await self.recv_ocpp_message()
                logger.info(f"Heartbeat #{heartbeat_id} response: {response}")
                heartbeat_id += 1
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def listen_for_commands(self):
        """Listen for incoming commands from CSMS"""
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                await self.handle_incoming_command(data)
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                logger.error(f"Error handling command: {e}")

    async def handle_incoming_command(self, data):
        """Handle incoming OCPP commands"""
        if len(data) != 4:
            return
            
        message_type, unique_id, action, payload = data
        
        if action == "Reset":
            await self.handle_reset(payload, unique_id)
        elif action == "ChangeAvailability":
            await self.handle_change_availability(payload, unique_id)
        elif action == "RemoteStartTransaction":
            await self.handle_remote_start_transaction(payload, unique_id)
        elif action == "RemoteStopTransaction":
            await self.handle_remote_stop_transaction(payload, unique_id)
        elif action == "UnlockConnector":
            await self.handle_unlock_connector(payload, unique_id)
        elif action == "ChangeConfiguration":
            await self.handle_change_configuration(payload, unique_id)

    async def handle_reset(self, payload, unique_id):
        """Handle Reset command"""
        reset_type = payload.get("type", "Soft")
        logger.info(f"Reset command received: {reset_type}")
        
        # Simulate reset behavior
        await asyncio.sleep(1)  # Simulate reset delay
        
        # Send BootNotification after reset
        await self.send_boot_notification()
        await self.send_status_notification("Available", "NoError")
        
        # Send response
        response = [3, unique_id, {"status": "Accepted"}]
        await self.websocket.send(json.dumps(response))

    async def handle_change_availability(self, payload, unique_id):
        """Handle ChangeAvailability command"""
        availability_type = payload.get("type", "Operative")
        connector_id = payload.get("connectorId")
        logger.info(f"ChangeAvailability: {availability_type}, connector: {connector_id}")
        
        # Update status based on availability
        if availability_type == "Inoperative":
            await self.send_status_notification("Unavailable", "NoError")
        else:
            await self.send_status_notification("Available", "NoError")
        
        response = [3, unique_id, {"status": "Accepted"}]
        await self.websocket.send(json.dumps(response))

    async def handle_remote_start_transaction(self, payload, unique_id):
        """Handle RemoteStartTransaction command"""
        id_tag = payload.get("idTag", "UNKNOWN")
        connector_id = payload.get("connectorId", 1)
        logger.info(f"RemoteStartTransaction: {id_tag}, connector: {connector_id}")
        
        # Check if we're in demo mode with session start failure
        if self.active_scenario == "session_start_failure":
            logger.info("🎭 DEMO: Simulating session start failure - not starting transaction")
            response = [3, unique_id, {"status": "Accepted"}]
            await self.websocket.send(json.dumps(response))
            return
        
        # Normal behavior - start transaction
        self.transaction_id += 1
        self.is_charging = True
        
        # Send StartTransaction
        start_payload = {
            "connectorId": connector_id,
            "idTag": id_tag,
            "meterStart": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_ocpp_message("StartTransaction", start_payload)
        response = await self.recv_ocpp_message()
        
        # Update status to Charging
        await self.send_status_notification("Charging", "NoError")
        
        # Send response
        response = [3, unique_id, {"status": "Accepted"}]
        await self.websocket.send(json.dumps(response))

    async def handle_remote_stop_transaction(self, payload, unique_id):
        """Handle RemoteStopTransaction command"""
        transaction_id = payload.get("transactionId")
        logger.info(f"RemoteStopTransaction: {transaction_id}")
        
        if self.is_charging:
            # Send StopTransaction
            stop_payload = {
                "meterStop": 1000,  # Simulate some energy consumed
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "transactionId": transaction_id
            }
            await self.send_ocpp_message("StopTransaction", stop_payload)
            response = await self.recv_ocpp_message()
            
            # Check if we're in stuck connector demo
            if self.active_scenario == "stuck_connector":
                logger.info("🎭 DEMO: Simulating stuck connector - staying Occupied")
                await self.send_status_notification("Occupied", "ConnectorLockFailure")
            else:
                # Normal behavior - go back to Available
                await self.send_status_notification("Available", "NoError")
            
            self.is_charging = False
        
        response = [3, unique_id, {"status": "Accepted"}]
        await self.websocket.send(json.dumps(response))

    async def handle_unlock_connector(self, payload, unique_id):
        """Handle UnlockConnector command"""
        connector_id = payload.get("connectorId", 1)
        logger.info(f"UnlockConnector: {connector_id}")
        
        # Simulate unlock delay
        await asyncio.sleep(0.5)
        
        # Update status to Available
        await self.send_status_notification("Available", "NoError")
        
        response = [3, unique_id, {"status": "Unlocked"}]
        await self.websocket.send(json.dumps(response))

    async def handle_change_configuration(self, payload, unique_id):
        """Handle ChangeConfiguration command"""
        key = payload.get("key")
        value = payload.get("value")
        logger.info(f"ChangeConfiguration: {key}={value}")
        
        response = [3, unique_id, {"status": "Accepted"}]
        await self.websocket.send(json.dumps(response))

    async def send_ocpp_message(self, action: str, payload: dict):
        """Send OCPP message to CSMS"""
        message_id = f"{action}_{datetime.now().timestamp()}"
        ocpp_msg = [2, message_id, action, payload]
        await self.websocket.send(json.dumps(ocpp_msg))
        logger.info(f"Sent {action}")

    async def recv_ocpp_message(self):
        """Receive OCPP message from CSMS"""
        response = await self.websocket.recv()
        data = json.loads(response)
        logger.info(f"Received: {data}")
        return data

    def set_demo_scenario(self, scenario: str):
        """Set active demo scenario"""
        self.active_scenario = scenario
        logger.info(f"🎭 DEMO: Set scenario to {scenario}")

    def clear_demo_scenario(self):
        """Clear active demo scenario"""
        self.active_scenario = None
        logger.info("🎭 DEMO: Cleared scenario")

async def main():
    logger.info("Starting Enhanced Charge Point Simulator...")
    simulator = EnhancedChargePointSimulator()
    await simulator.connect_to_csms()

if __name__ == "__main__":
    asyncio.run(main())
