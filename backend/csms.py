# Accepts connections at ws://0.0.0.0:9000/<ChargeBoxId> and implements the standard OCPP message framing.

import asyncio
import json
import logging
import websockets
from websockets.server import serve
from ocpp.v16 import ChargePoint as CP, call, call_result
from ocpp.routing import on
from ocpp.v16.enums import RegistrationStatus, ChargePointStatus

logging.basicConfig(level=logging.INFO)

from shared_store import STORE
from demo_scenarios import DEMO_MANAGER


class CentralSystemCP(CP):
    """One instance per connected charge point."""
    def __init__(self, id, connection):
        super().__init__(id, connection)

    # ----- Incoming messages from the charge point -----
    @on('BootNotification')
    async def on_boot_notification(self, charge_point_vendor, charge_point_model, **kwargs):
        logging.info(f"[{self.id}] BootNotification: {charge_point_vendor=} {charge_point_model=}")
        # Accept the charger and set heartbeat interval (seconds)
        return call_result.BootNotification(
            current_time="2025-01-01T00:00:00Z",  # RFC3339 timestamp
            interval=60,
            status=RegistrationStatus.accepted
        )

    @on('Heartbeat')
    async def on_heartbeat(self):
        logging.info(f"[{self.id}] Heartbeat")
        STORE.heartbeat[self.id] = asyncio.get_event_loop().time()
        # CSMS responds with current_time (RFC3339 in real impl)
        return call_result.Heartbeat(current_time="2025-01-01T00:00:00Z")

    @on('StatusNotification')
    async def on_status_notification(self, connector_id, error_code, status, **kwargs):
        logging.info(f"[{self.id}] Status: connector={connector_id} status={status} error={error_code}")
        STORE.status[self.id] = {"connector_id": connector_id, "status": status, "error_code": error_code}
        return call_result.StatusNotification()

    @on('MeterValues')
    async def on_meter_values(self, connector_id, meter_value, **kwargs):
        logging.info(f"[{self.id}] MeterValues: samples={len(meter_value)}")
        
        # Check if charging profile mismatch scenario is active
        scenario = DEMO_MANAGER.get_scenario_status(self.id)
        if scenario and scenario.get("type") == "charging_profile_mismatch":
            logging.info(f"🎭 DEMO: Simulating low power delivery for charging profile mismatch")
            # In a real implementation, we would modify the meter values here
            # For now, we just log the scenario is active
        
        return call_result.MeterValues()

    @on('Authorize')
    async def on_authorize(self, id_tag, **kwargs):
        logging.info(f"[{self.id}] Authorize: idTag={id_tag}")
        
        # Check if we're in auth failure demo scenario
        scenario = DEMO_MANAGER.get_scenario_status(self.id)
        if scenario and scenario["type"] == "auth_failure":
            logging.info(f"🎭 DEMO: Simulating auth failure for {id_tag}")
            return call_result.Authorize(id_tag_info={"status": "Invalid"})
        
        # Check if card is in whitelist
        if DEMO_MANAGER.is_card_valid(id_tag):
            return call_result.Authorize(id_tag_info={"status": "Accepted"})
        else:
            return call_result.Authorize(id_tag_info={"status": "Invalid"})

    @on('StartTransaction')
    async def on_start_transaction(self, connector_id, id_tag, meter_start, timestamp, **kwargs):
        logging.info(f"[{self.id}] StartTransaction on connector {connector_id}")
        # Return a transaction id (any positive int)
        return call_result.StartTransaction(
            transaction_id=1,
            id_tag_info={"status": "Accepted"}
        )

    @on('StopTransaction')
    async def on_stop_transaction(self, meter_stop, timestamp, transaction_id, **kwargs):
        logging.info(f"[{self.id}] StopTransaction id={transaction_id}")
        return call_result.StopTransaction(id_tag_info={"status": "Accepted"})

    # ----- Commands from CSMS to Charge Point -----
    @on('Reset')
    async def on_reset(self, type, **kwargs):
        logging.info(f"[{self.id}] Reset command received: type={type}")
        return call_result.Reset(status="Accepted")

    @on('ChangeAvailability')
    async def on_change_availability(self, type, connector_id=None, **kwargs):
        logging.info(f"[{self.id}] ChangeAvailability: type={type}, connector={connector_id}")
        return call_result.ChangeAvailability(status="Accepted")

    @on('ChangeConfiguration')
    async def on_change_configuration(self, key, value, **kwargs):
        logging.info(f"[{self.id}] ChangeConfiguration: {key}={value}")
        return call_result.ChangeConfiguration(status="Accepted")

    @on('RemoteStartTransaction')
    async def on_remote_start_transaction(self, id_tag, connector_id=None, **kwargs):
        logging.info(f"[{self.id}] RemoteStartTransaction: idTag={id_tag}, connector={connector_id}")
        return call_result.RemoteStartTransaction(status="Accepted")

    @on('RemoteStopTransaction')
    async def on_remote_stop_transaction(self, transaction_id, **kwargs):
        logging.info(f"[{self.id}] RemoteStopTransaction: transactionId={transaction_id}")
        return call_result.RemoteStopTransaction(status="Accepted")

    @on('UnlockConnector')
    async def on_unlock_connector(self, connector_id, **kwargs):
        logging.info(f"[{self.id}] UnlockConnector: connector={connector_id}")
        return call_result.UnlockConnector(status="Unlocked")

async def on_connect(websocket, path):
    """
    A charge point connects to: ws://host:9000/<ChargeBoxId>
    The `path` is like '/EVSE001' → cp_id='EVSE001'.
    """
    cp_id = path.strip("/").split("/")[0] or "UNKNOWN_CP"
    logging.info(f"Incoming connection from charge point id={cp_id}")
    
    # Create the charge point handler
    cp = CentralSystemCP(cp_id, websocket)
    
    # Store the connection
    STORE.charge_points[cp_id] = websocket
    logging.info(f"Charge point {cp_id} connected. Total connections: {len(STORE.charge_points)}")
    
    try:
        await cp.start()  # handle messages until disconnect
    except Exception as e:
        logging.error(f"Error in charge point {cp_id}: {e}")
    finally:
        logging.info(f"Disconnected: {cp_id}")
        STORE.charge_points.pop(cp_id, None)
        logging.info(f"Remaining connections: {len(STORE.charge_points)}")

async def main():
    from config import CSMS_HOST, CSMS_PORT
    import uvicorn
    import threading
    
    # Start REST API in a separate thread
    def start_rest_api():
        uvicorn.run("rest_api:app", host="0.0.0.0", port=8000, log_level="info")
    
    rest_thread = threading.Thread(target=start_rest_api, daemon=True)
    rest_thread.start()
    logging.info("REST API started on http://0.0.0.0:8000")
    
    # Start WebSocket server
    async with serve(on_connect, CSMS_HOST, CSMS_PORT, subprotocols=["ocpp1.6"]):
        logging.info(f"CSMS listening on ws://{CSMS_HOST}:{CSMS_PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
