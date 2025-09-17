from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import asyncio
import json
import logging
from shared_store import STORE
from demo_scenarios import DEMO_MANAGER

app = FastAPI()

# Pydantic models for request bodies
class ResetRequest(BaseModel):
    type: str = "Hard"  # Hard, Soft

class ChangeAvailabilityRequest(BaseModel):
    connector_id: Optional[int] = None
    type: str = "Operative"  # Operative, Inoperative

class ChangeConfigurationRequest(BaseModel):
    key: str
    value: str

class RemoteStartRequest(BaseModel):
    id_tag: str
    connector_id: Optional[int] = None

class RemoteStopRequest(BaseModel):
    transaction_id: int

class UnlockConnectorRequest(BaseModel):
    connector_id: int

class SendLocalListRequest(BaseModel):
    id_tag: str
    status: str = "Accepted"

class DemoScenarioRequest(BaseModel):
    scenario: str

@app.get("/")
async def root():
    return {
        "message": "Voice4EVs CSMS API", 
        "connected_cps": list(STORE.charge_points.keys()),
        "available_commands": [
            "GET /status - Get charge point status",
            "POST /commands/reset/{cp_id} - Reset charge point",
            "POST /commands/change_availability/{cp_id} - Change availability",
            "POST /commands/change_configuration/{cp_id} - Change configuration",
            "POST /commands/remote_start/{cp_id} - Start charging remotely",
            "POST /commands/remote_stop/{cp_id} - Stop charging remotely",
            "POST /commands/unlock_connector/{cp_id} - Unlock connector",
            "POST /commands/send_local_list/{cp_id} - Add card to whitelist",
            "POST /demo/trigger/{scenario} - Trigger demo scenario",
            "GET /demo/scenarios - List available demo scenarios",
            "POST /demo/clear - Clear all demo scenarios"
        ]
    }

@app.get("/status")
async def get_status():
    return {
        "connected_charge_points": list(STORE.charge_points.keys()),
        "status": STORE.status,
        "heartbeats": STORE.heartbeat,
        "total_connections": len(STORE.charge_points)
    }

@app.post("/commands/reset/{cp_id}")
async def reset_charge_point(cp_id: str, request: ResetRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    # Send Reset command to charge point
    websocket = STORE.charge_points[cp_id]
    reset_payload = {
        "type": request.type
    }
    ocpp_msg = [2, f"reset_{cp_id}", "Reset", reset_payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"Reset command sent to {cp_id}", "type": request.type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/change_availability/{cp_id}")
async def change_availability(cp_id: str, request: ChangeAvailabilityRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    websocket = STORE.charge_points[cp_id]
    payload = {
        "type": request.type
    }
    if request.connector_id is not None:
        payload["connectorId"] = request.connector_id
    
    ocpp_msg = [2, f"availability_{cp_id}", "ChangeAvailability", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"ChangeAvailability command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/change_configuration/{cp_id}")
async def change_configuration(cp_id: str, request: ChangeConfigurationRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    websocket = STORE.charge_points[cp_id]
    payload = {
        "key": request.key,
        "value": request.value
    }
    ocpp_msg = [2, f"config_{cp_id}", "ChangeConfiguration", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"ChangeConfiguration command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/remote_start/{cp_id}")
async def remote_start_transaction(cp_id: str, request: RemoteStartRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    websocket = STORE.charge_points[cp_id]
    payload = {
        "idTag": request.id_tag
    }
    if request.connector_id is not None:
        payload["connectorId"] = request.connector_id
    
    ocpp_msg = [2, f"start_{cp_id}", "RemoteStartTransaction", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"RemoteStartTransaction command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/remote_stop/{cp_id}")
async def remote_stop_transaction(cp_id: str, request: RemoteStopRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    websocket = STORE.charge_points[cp_id]
    payload = {
        "transactionId": request.transaction_id
    }
    ocpp_msg = [2, f"stop_{cp_id}", "RemoteStopTransaction", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"RemoteStopTransaction command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/unlock_connector/{cp_id}")
async def unlock_connector(cp_id: str, request: UnlockConnectorRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    websocket = STORE.charge_points[cp_id]
    payload = {
        "connectorId": request.connector_id
    }
    ocpp_msg = [2, f"unlock_{cp_id}", "UnlockConnector", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        return {"message": f"UnlockConnector command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/send_local_list/{cp_id}")
async def send_local_list(cp_id: str, request: SendLocalListRequest):
    """Add a card to the local authorization list (for auth failure demo resolution)"""
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")

    # Add card to whitelist
    DEMO_MANAGER.add_card_to_whitelist(request.id_tag)
    
    return {
        "message": f"Added {request.id_tag} to whitelist for {cp_id}",
        "status": request.status
    }

# Demo Scenario Endpoints
@app.post("/demo/trigger/{scenario}")
async def trigger_demo_scenario(scenario: str, cp_id: str = "EVSE001"):
    """Trigger a specific demo scenario"""
    valid_scenarios = [
        "session_start_failure",
        "stuck_connector", 
        "offline_charger",
        "auth_failure",
        "slow_charging"
    ]
    
    if scenario not in valid_scenarios:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid scenario. Valid options: {valid_scenarios}"
        )
    
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    await DEMO_MANAGER.trigger_scenario(scenario, cp_id)
    
    return {
        "message": f"Triggered {scenario} for {cp_id}",
        "scenario": scenario,
        "charge_point": cp_id
    }

@app.get("/demo/scenarios")
async def list_demo_scenarios():
    """List available demo scenarios and their descriptions"""
    return {
        "available_scenarios": {
            "session_start_failure": "Charger shows Available but won't start transactions",
            "stuck_connector": "Connector won't unlock after charging (ConnectorLockFailure)",
            "offline_charger": "Charger goes offline (no heartbeats)",
            "auth_failure": "Invalid card authorization (card not in whitelist)",
            "slow_charging": "Very slow charging power (low MeterValues)"
        },
        "demo_commands": DEMO_MANAGER.get_demo_commands(),
        "active_scenarios": {
            cp_id: DEMO_MANAGER.get_scenario_status(cp_id) 
            for cp_id in STORE.charge_points.keys()
        }
    }

@app.post("/demo/clear")
async def clear_demo_scenarios(cp_id: Optional[str] = None):
    """Clear demo scenarios for a specific charge point or all"""
    if cp_id:
        if cp_id not in STORE.charge_points:
            raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
        DEMO_MANAGER.clear_scenario(cp_id)
        return {"message": f"Cleared demo scenarios for {cp_id}"}
    else:
        for cp in STORE.charge_points.keys():
            DEMO_MANAGER.clear_scenario(cp)
        return {"message": "Cleared all demo scenarios"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
