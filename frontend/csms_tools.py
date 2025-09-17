import os
from typing import Any, Dict, Mapping, Optional

import httpx
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.frames.frames import FunctionCallResultProperties, LLMRunFrame


API_BASE = os.getenv("CSMS_API_BASE", "http://localhost:8000")


def _error_dict(message: str, *, status_code: Optional[int] = None, details: Optional[str] = None, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"error": message}
    if status_code is not None:
        err["status_code"] = status_code
    if details is not None:
        err["details"] = details
    if request is not None:
        err["request"] = request
    return err


async def _post(path: str, json: Dict[str, Any], params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{API_BASE}{path}", json=json, params=params, timeout=15)
            if r.status_code >= 400:
                body_text: Optional[str] = None
                try:
                    body_text = r.text
                except Exception:
                    body_text = None
                return _error_dict(
                    "HTTP error on POST",
                    status_code=r.status_code,
                    details=body_text,
                    request={"method": "POST", "path": path, "params": dict(params) if params else None, "json": json},
                )
            try:
                return r.json()
            except Exception:
                return {"result": r.text}
    except httpx.RequestError as e:
        return _error_dict(
            f"Network error on POST: {str(e)}",
            request={"method": "POST", "path": path, "params": dict(params) if params else None, "json": json},
        )


async def _get(path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_BASE}{path}", params=params, timeout=15)
            if r.status_code >= 400:
                body_text: Optional[str] = None
                try:
                    body_text = r.text
                except Exception:
                    body_text = None
                return _error_dict(
                    "HTTP error on GET",
                    status_code=r.status_code,
                    details=body_text,
                    request={"method": "GET", "path": path, "params": dict(params) if params else None},
                )
            try:
                return r.json()
            except Exception:
                return {"result": r.text}
    except httpx.RequestError as e:
        return _error_dict(
            f"Network error on GET: {str(e)}",
            request={"method": "GET", "path": path, "params": dict(params) if params else None},
        )


def _normalize_cp_id(args: Mapping[str, Any]) -> str:
    cp = args.get("cp_id")
    return cp if isinstance(cp, str) and cp.strip() else "EVSE001"


def _normalize_connector_id(args: Mapping[str, Any], *, default_if_missing: bool) -> Optional[int]:
    if "connector_id" in args and args["connector_id"] is not None:
        try:
            return int(args["connector_id"])  # type: ignore[arg-type]
        except Exception:
            return 1 if default_if_missing else None
    return 1 if default_if_missing else None


def _validate_non_empty_str(name: str, value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, str) or not value.strip():
        return _error_dict(f"Invalid '{name}': must be a non-empty string")
    return None


# -------------------------
# Function Schemas
# -------------------------

reset_charge_point_schema = FunctionSchema(
    name="reset_charge_point",
    description="Reset a charge point",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "type": {
            "type": "string",
            "enum": ["Hard", "Soft"],
            "description": "Reset type",
        },
    },
    required=["cp_id", "type"],
)

change_availability_schema = FunctionSchema(
    name="change_availability",
    description="Change availability of a charge point or a specific connector",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "type": {
            "type": "string",
            "enum": ["Operative", "Inoperative"],
            "description": "Availability state",
        },
        "connector_id": {
            "type": "integer",
            "description": "Optional connector ID",
        },
    },
    required=["cp_id", "type"],
)

change_configuration_schema = FunctionSchema(
    name="change_configuration",
    description="Change a configuration key on a charge point",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "key": {"type": "string", "description": "Configuration key"},
        "value": {"type": "string", "description": "Configuration value"},
    },
    required=["cp_id", "key", "value"],
)

remote_start_transaction_schema = FunctionSchema(
    name="remote_start_transaction",
    description="Start a transaction on a charge point",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "id_tag": {"type": "string", "description": "Authorization tag"},
        "connector_id": {"type": "integer", "description": "Optional connector ID"},
    },
    required=["cp_id", "id_tag"],
)

remote_stop_transaction_schema = FunctionSchema(
    name="remote_stop_transaction",
    description="Stop a transaction on a charge point",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "transaction_id": {"type": "integer", "description": "Transaction ID"},
    },
    required=["cp_id", "transaction_id"],
)

unlock_connector_schema = FunctionSchema(
    name="unlock_connector",
    description="Unlock a connector on a charge point",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "connector_id": {"type": "integer", "description": "Connector ID"},
    },
    required=["cp_id", "connector_id"],
)

send_local_list_schema = FunctionSchema(
    name="send_local_list",
    description="Add a card to the local authorization whitelist",
    properties={
        "cp_id": {"type": "string", "description": "Charge point ID"},
        "id_tag": {"type": "string", "description": "Card/tag to whitelist"},
        "status": {
            "type": "string",
            "enum": ["Accepted"],
            "description": "Status to set (demo)",
        },
    },
    required=["cp_id", "id_tag"],
)

trigger_demo_scenario_schema = FunctionSchema(
    name="trigger_demo_scenario",
    description="Trigger a demo scenario for a charge point",
    properties={
        "scenario": {
            "type": "string",
            "enum": [
                "session_start_failure",
                "stuck_connector",
                "offline_charger",
                "auth_failure",
                "slow_charging",
            ],
            "description": "Scenario to trigger",
        },
        "cp_id": {
            "type": "string",
            "description": "Charge point ID (optional; defaults to EVSE001)",
        },
    },
    required=["scenario"],
)

list_demo_scenarios_schema = FunctionSchema(
    name="list_demo_scenarios",
    description="List available demo scenarios and their status",
    properties={},
    required=[],
)

clear_demo_scenarios_schema = FunctionSchema(
    name="clear_demo_scenarios",
    description="Clear demo scenarios for a specific charge point or all",
    properties={
        "cp_id": {"type": "string", "description": "Optional charge point ID"},
    },
    required=[],
)

get_status_schema = FunctionSchema(
    name="get_status",
    description="Get overall CSMS/connected charge points status",
    properties={},
    required=[],
)


tools = ToolsSchema(
    standard_tools=[
        reset_charge_point_schema,
        change_availability_schema,
        change_configuration_schema,
        remote_start_transaction_schema,
        remote_stop_transaction_schema,
        unlock_connector_schema,
        send_local_list_schema,
        trigger_demo_scenario_schema,
        list_demo_scenarios_schema,
        clear_demo_scenarios_schema,
        get_status_schema,
    ]
)


def get_tools() -> ToolsSchema:
    return tools


# -------------------------
# Handlers
# -------------------------

# When we return tool results, the data is written into the LLM's conversation context.
# The LLM does NOT "see" the data until the next LLM pass.
# We control whether to immediately kick off that next pass (and whether to speak in between)
# using FunctionCallResultProperties + optionally pushing an LLMRunFrame.

async def _return_and_chain(params: FunctionCallParams, data: Dict[str, Any], *, chain_next: bool) -> None:
    if chain_next:
        # CHAINING MODE:
        # - run_llm=False suppresses an immediate model completion (no filler speech).
        # - on_context_updated fires after the tool result is appended to context.
        #   In that callback, we push LLMRunFrame() to explicitly trigger the next LLM pass.
        #   On that pass, the model "sees" the tool result and can decide to call another tool.

        async def on_update():
            # This triggers the next LLM turn after the context has been updated with the tool result.
            await params.llm.push_frame(LLMRunFrame())
        props = FunctionCallResultProperties(run_llm=False, on_context_updated=on_update)
        await params.result_callback(data, properties=props)
        return

    # NON-CHAIN MODE:
    # - run_llm defaults to True (no props), so the model will produce a spoken response next.
    await params.result_callback(data)


async def handle_reset_charge_point(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    reset_type = params.arguments.get("type") or "Soft"
    data = await _post(f"/commands/reset/{cp_id}", {"type": reset_type})
    await _return_and_chain(params, data, chain_next=True)


async def handle_change_availability(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    payload: Dict[str, Any] = {"type": params.arguments["type"]}
    connector_id = _normalize_connector_id(params.arguments, default_if_missing=False)
    if connector_id is not None:
        payload["connector_id"] = connector_id
    data = await _post(f"/commands/change_availability/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_change_configuration(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    key = params.arguments.get("key")
    value = params.arguments.get("value")
    err = _validate_non_empty_str("key", key) or _validate_non_empty_str("value", value)
    if err:
        await params.result_callback(err)
        return
    payload = {"key": key, "value": value}
    data = await _post(f"/commands/change_configuration/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_remote_start_transaction(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    id_tag = params.arguments.get("id_tag")
    err = _validate_non_empty_str("id_tag", id_tag)
    if err:
        await params.result_callback(err)
        return
    payload = {"id_tag": id_tag}
    connector_id = _normalize_connector_id(params.arguments, default_if_missing=True)
    if connector_id is not None:
        payload["connector_id"] = connector_id
    data = await _post(f"/commands/remote_start/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_remote_stop_transaction(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    if "transaction_id" not in params.arguments:
        await params.result_callback(_error_dict("Missing 'transaction_id'"))
        return
    payload = {"transaction_id": params.arguments["transaction_id"]}
    data = await _post(f"/commands/remote_stop/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_unlock_connector(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    connector_id = _normalize_connector_id(params.arguments, default_if_missing=True)
    payload = {"connector_id": connector_id}
    data = await _post(f"/commands/unlock_connector/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_send_local_list(params: FunctionCallParams) -> None:
    cp_id = _normalize_cp_id(params.arguments)
    id_tag = params.arguments.get("id_tag")
    err = _validate_non_empty_str("id_tag", id_tag)
    if err:
        await params.result_callback(err)
        return
    payload: Dict[str, Any] = {"id_tag": id_tag}
    status = params.arguments.get("status") or "Accepted"
    payload["status"] = status
    data = await _post(f"/commands/send_local_list/{cp_id}", payload)
    await _return_and_chain(params, data, chain_next=True)


async def handle_trigger_demo_scenario(params: FunctionCallParams) -> None:
    scenario = params.arguments["scenario"]
    cp_id = _normalize_cp_id(params.arguments) if params.arguments.get("cp_id") is not None else None
    query_params: Dict[str, Any] = {"cp_id": cp_id} if cp_id else None
    data = await _post(f"/demo/trigger/{scenario}", json={}, params=query_params)
    await _return_and_chain(params, data, chain_next=True)


async def handle_list_demo_scenarios(params: FunctionCallParams) -> None:
    data = await _get("/demo/scenarios")
    await _return_and_chain(params, data, chain_next=False)


async def handle_clear_demo_scenarios(params: FunctionCallParams) -> None:
    cp_id = params.arguments.get("cp_id")
    query_params: Dict[str, Any] = {"cp_id": cp_id} if cp_id else None
    data = await _post("/demo/clear", json={}, params=query_params)
    await _return_and_chain(params, data, chain_next=True)


async def handle_get_status(params: FunctionCallParams) -> None:
    data = await _get("/status")
    await _return_and_chain(params, data, chain_next=False)


def register_csms_function_handlers(llm) -> None:
    llm.register_function("reset_charge_point", handle_reset_charge_point)
    llm.register_function("change_availability", handle_change_availability)
    llm.register_function("change_configuration", handle_change_configuration)
    llm.register_function("remote_start_transaction", handle_remote_start_transaction)
    llm.register_function("remote_stop_transaction", handle_remote_stop_transaction)
    llm.register_function("unlock_connector", handle_unlock_connector)
    llm.register_function("send_local_list", handle_send_local_list)
    llm.register_function("trigger_demo_scenario", handle_trigger_demo_scenario)
    llm.register_function("list_demo_scenarios", handle_list_demo_scenarios)
    llm.register_function("clear_demo_scenarios", handle_clear_demo_scenarios)
    llm.register_function("get_status", handle_get_status)


