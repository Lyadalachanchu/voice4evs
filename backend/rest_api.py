from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import asyncio
import json
import logging
from shared_store import STORE
from demo_scenarios import DEMO_MANAGER
from complex_demo_scenario import COMPLEX_DEMO
from datetime import datetime
import time
from config import (
    ALLOW_GENERIC_CHANGE_CONFIG,
    ALLOWED_CONFIG_KEYS,
    POWER_LIMIT_MIN_KW,
    POWER_LIMIT_MAX_KW,
    POWER_CHANGE_RATE_LIMIT_WINDOW_SEC,
    POWER_CHANGE_RATE_LIMIT_MAX,
    CONFIG_CHANGE_RATE_LIMIT_WINDOW_SEC,
    CONFIG_CHANGE_RATE_LIMIT_MAX,
    AUDIT_ENABLED,
)

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

class SetPowerLimitRequest(BaseModel):
    limit_kw: float
    connector_id: Optional[int] = None

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
            "POST /commands/set_power_limit/{cp_id} - Safely set power limit (kW)",
            "POST /commands/remote_start/{cp_id} - Start charging remotely",
            "POST /commands/remote_stop/{cp_id} - Stop charging remotely",
            "POST /commands/unlock_connector/{cp_id} - Unlock connector",
            "POST /commands/send_local_list/{cp_id} - Add card to whitelist",
            "POST /demo/trigger/charging_profile_mismatch - Trigger complex diagnostic scenario",
            "POST /demo/trigger/stuck_charging - Trigger simple scenario where CP stays in Charging",
            "GET /demo/scenarios - List available demo scenarios",
            "GET /demo/progress/{cp_id} - Get scenario resolution progress",
            "GET /demo/resolution_steps - Get required resolution steps",
            "POST /demo/clear - Clear all demo scenarios"
        ]
    }

@app.get("/status")
async def get_status():
    # Check for active complex demo scenarios
    active_scenarios = {}
    diagnostic_info = {}
    
    for cp_id in STORE.charge_points.keys():
        scenario = DEMO_MANAGER.get_scenario_status(cp_id)
        if scenario and scenario.get("type") == "charging_profile_mismatch":
            active_scenarios[cp_id] = scenario
            # Add diagnostic information for the voice agent
            diagnostic_info[cp_id] = {
                "issue": "Low power delivery detected",
                "current_power": "3.5kW",
                "expected_power": "22kW", 
                "root_cause": "Charging profile configuration conflicts",
                "requires_diagnostic": True,
                "configuration_issues": {
                    "ChargingProfileMaxStackLevel": "8 (should be 1)",
                    "ChargingScheduleMaxPeriods": "500 (should be 100)",
                    "MaxChargingProfilesInstalled": "10 (should be 1)"
                }
            }
        elif scenario and scenario.get("type") == "stuck_charging":
            active_scenarios[cp_id] = scenario
            # Force status to Charging for visibility
            STORE.status[cp_id] = {
                "connector_id": 1,
                "status": "Charging",
                "error_code": "NoError",
            }
        # Check for EVSE003 specifically - it has the configuration issue
        elif cp_id == "EVSE003" and cp_id not in STORE.resolved_diagnostics:
            diagnostic_info[cp_id] = {
                "issue": "Low power delivery detected",
                "current_power": "3.5kW",
                "expected_power": "22kW", 
                "root_cause": "Charging profile configuration conflicts",
                "requires_diagnostic": True,
                "configuration_issues": {
                    "ChargingProfileMaxStackLevel": "8 (should be 1)",
                    "ChargingScheduleMaxPeriods": "500 (should be 100)",
                    "MaxChargingProfilesInstalled": "10 (should be 1)"
                }
            }
    
    return {
        "connected_charge_points": list(STORE.charge_points.keys()),
        "status": STORE.status,
        "heartbeats": STORE.heartbeat,
        "total_connections": len(STORE.charge_points),
        "active_scenarios": active_scenarios,
        "diagnostic_info": diagnostic_info
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
        # If stuck_charging demo is active and a Hard reset is issued, clear the scenario to simulate resolution
        scenario = DEMO_MANAGER.get_scenario_status(cp_id)
        if scenario and scenario.get("type") == "stuck_charging" and request.type == "Hard":
            DEMO_MANAGER.clear_scenario(cp_id)
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
        # If stuck_charging demo is active and we set Inoperative, clear the scenario to simulate breaking the stuck state
        scenario = DEMO_MANAGER.get_scenario_status(cp_id)
        if scenario and scenario.get("type") == "stuck_charging" and request.type == "Inoperative":
            DEMO_MANAGER.clear_scenario(cp_id)
        return {"message": f"ChangeAvailability command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/change_configuration/{cp_id}")
async def change_configuration(cp_id: str, request: ChangeConfigurationRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    # Guardrail: allowlist + rate limit
    now = time.time()
    STORE.config_change_events.setdefault(cp_id, [])
    # Drop old timestamps
    STORE.config_change_events[cp_id] = [t for t in STORE.config_change_events[cp_id] if now - t <= CONFIG_CHANGE_RATE_LIMIT_WINDOW_SEC]
    if len(STORE.config_change_events[cp_id]) >= CONFIG_CHANGE_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many configuration changes. Please wait and try again.")
    STORE.config_change_events[cp_id].append(now)

    if not ALLOW_GENERIC_CHANGE_CONFIG and request.key not in ALLOWED_CONFIG_KEYS:
        raise HTTPException(status_code=403, detail=f"Configuration key '{request.key}' is not allowed.")

    websocket = STORE.charge_points[cp_id]
    payload = {
        "key": request.key,
        "value": request.value
    }
    ocpp_msg = [2, f"config_{cp_id}", "ChangeConfiguration", payload]
    
    try:
        await websocket.send(json.dumps(ocpp_msg))
        
        # Check if this configuration change resolves the diagnostic issue for EVSE003
        if cp_id == "EVSE003" and request.key in ["ChargingProfileMaxStackLevel", "ChargingScheduleMaxPeriods", "MaxChargingProfilesInstalled"]:
            # Track configuration changes for diagnostic resolution
            if cp_id not in STORE.diagnostic_config_changes:
                STORE.diagnostic_config_changes[cp_id] = {}
            
            # Store the configuration change
            STORE.diagnostic_config_changes[cp_id][request.key] = request.value
            
            # Check if all three diagnostic configuration keys have been set to correct values
            required_changes = {
                "ChargingProfileMaxStackLevel": "1",
                "ChargingScheduleMaxPeriods": "100", 
                "MaxChargingProfilesInstalled": "1"
            }
            
            if all(STORE.diagnostic_config_changes[cp_id].get(key) == value 
                   for key, value in required_changes.items()):
                STORE.resolved_diagnostics.add(cp_id)
                print(f"Diagnostic issue resolved for {cp_id} - all configuration changes completed")
        # Audit log
        if AUDIT_ENABLED:
            STORE.audit_log.append({
                "ts": datetime.utcnow().isoformat() + "Z",
                "cp_id": cp_id,
                "actor": "api",
                "action": "change_configuration",
                "details": {"key": request.key, "value": request.value}
            })
        
        return {"message": f"ChangeConfiguration command sent to {cp_id}", "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}")

@app.post("/commands/set_power_limit/{cp_id}")
async def set_power_limit(cp_id: str, request: SetPowerLimitRequest):
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")

    # Validate range
    limit_kw = float(request.limit_kw)
    if limit_kw < POWER_LIMIT_MIN_KW or limit_kw > POWER_LIMIT_MAX_KW:
        raise HTTPException(status_code=400, detail=f"limit_kw must be between {POWER_LIMIT_MIN_KW} and {POWER_LIMIT_MAX_KW} kW")

    # Rate limit power changes
    now = time.time()
    STORE.power_change_events.setdefault(cp_id, [])
    STORE.power_change_events[cp_id] = [t for t in STORE.power_change_events[cp_id] if now - t <= POWER_CHANGE_RATE_LIMIT_WINDOW_SEC]
    if len(STORE.power_change_events[cp_id]) >= POWER_CHANGE_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many power limit changes. Please wait and try again.")
    STORE.power_change_events[cp_id].append(now)

    # Persist desired limit in store (simulation)
    STORE.power_limits.setdefault(cp_id, {"default_kw": None, "per_connector": {}})
    if request.connector_id is not None:
        STORE.power_limits[cp_id]["per_connector"][int(request.connector_id)] = limit_kw
    else:
        STORE.power_limits[cp_id]["default_kw"] = limit_kw

    # In a real implementation, this would build and send a SetChargingProfile OCPP message.
    # For the simulator, we just acknowledge and audit.
    if AUDIT_ENABLED:
        STORE.audit_log.append({
            "ts": datetime.utcnow().isoformat() + "Z",
            "cp_id": cp_id,
            "actor": "api",
            "action": "set_power_limit",
            "details": {"limit_kw": limit_kw, "connector_id": request.connector_id}
        })

    return {
        "message": f"Power limit set for {cp_id}",
        "cp_id": cp_id,
        "limit_kw": limit_kw,
        "connector_id": request.connector_id,
        "applied": True
    }

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
    
    # If simple "stuck_charging" demo is active, ignore stop requests to simulate refusal
    scenario = DEMO_MANAGER.get_scenario_status(cp_id)
    if scenario and scenario.get("type") == "stuck_charging":
        # Keep status as Charging and return an informational message
        STORE.status[cp_id] = {
            "connector_id": 1,
            "status": "Charging",
            "error_code": "NoError",
        }
        return {
            "message": f"RemoteStopTransaction ignored for {cp_id} due to 'stuck_charging' demo scenario",
            "scenario": "stuck_charging",
            "status": STORE.status.get(cp_id)
        }

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
    valid_scenarios = ["charging_profile_mismatch", "stuck_charging"]
    
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
        "charge_point": cp_id,
        "description": (
            COMPLEX_DEMO.get_scenario_description() if scenario == "charging_profile_mismatch" else
            "Simple scenario: EVSE stays in Charging state and ignores RemoteStop"
        )
    }

@app.get("/demo/scenarios")
async def list_demo_scenarios():
    """List available demo scenarios and their descriptions"""
    return {
        "available_scenarios": {
            "charging_profile_mismatch": "Complex diagnostic scenario requiring multi-step resolution. Charger delivers low power due to configuration conflicts.",
            "stuck_charging": "Simple scenario: Charger remains in Charging and ignores stop commands."
        },
        "demo_commands": DEMO_MANAGER.get_demo_commands(),
        "active_scenarios": {
            cp_id: DEMO_MANAGER.get_scenario_status(cp_id) 
            for cp_id in STORE.charge_points.keys()
        }
    }

@app.get("/demo/progress/{cp_id}")
async def get_scenario_progress(cp_id: str):
    """Get current progress of scenario resolution"""
    if cp_id not in STORE.charge_points:
        raise HTTPException(status_code=404, detail=f"Charge point {cp_id} not connected")
    
    progress = COMPLEX_DEMO.get_progress(cp_id)
    return {
        "charge_point": cp_id,
        "progress": progress,
        "resolution_steps": COMPLEX_DEMO.get_resolution_steps() if progress.get("status") == "active" else None
    }

@app.get("/demo/resolution_steps")
async def get_resolution_steps():
    """Get the specific steps needed to resolve the charging profile mismatch scenario"""
    return {
        "scenario": "charging_profile_mismatch",
        "steps": COMPLEX_DEMO.get_resolution_steps(),
        "diagnostic_questions": COMPLEX_DEMO.get_diagnostic_questions(),
        "agent_guidance": COMPLEX_DEMO.get_agent_guidance()
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

@app.post("/demo/reset_diagnostics")
async def reset_diagnostics():
    """Reset diagnostic resolution status for testing"""
    STORE.resolved_diagnostics.clear()
    STORE.diagnostic_config_changes.clear()
    return {"message": "Diagnostic resolution status reset"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
