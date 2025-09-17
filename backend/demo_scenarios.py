"""
Demo Scenarios for Voice4EVs CSMS
Simulates real-world EV charging issues for voice agent demos
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from shared_store import STORE

logger = logging.getLogger(__name__)

class DemoScenarioManager:
    """Manages demo scenarios and issue simulation"""
    
    def __init__(self):
        self.active_scenarios = {}
        self.transaction_tracker = {}
        self.power_monitor = {}
        self.auth_list = {"USER123": "Accepted", "DEMO001": "Accepted"}  # Whitelist
        
    async def trigger_scenario(self, scenario_name: str, cp_id: str = "EVSE001"):
        """Trigger a specific demo scenario"""
        if scenario_name == "session_start_failure":
            await self._simulate_session_start_failure(cp_id)
        elif scenario_name == "stuck_connector":
            await self._simulate_stuck_connector(cp_id)
        elif scenario_name == "offline_charger":
            await self._simulate_offline_charger(cp_id)
        elif scenario_name == "auth_failure":
            await self._simulate_auth_failure(cp_id)
        elif scenario_name == "slow_charging":
            await self._simulate_slow_charging(cp_id)
        else:
            logger.error(f"Unknown scenario: {scenario_name}")
    
    async def _simulate_session_start_failure(self, cp_id: str):
        """Scenario 1: Charger shows Available but won't start transactions"""
        logger.info(f"🎭 DEMO: Triggering session start failure for {cp_id}")
        self.active_scenarios[cp_id] = {
            "type": "session_start_failure",
            "state": "authorize_ok_no_start",
            "started_at": datetime.now()
        }
        # The simulator will need to be modified to not send StartTransaction after Authorize
    
    async def _simulate_stuck_connector(self, cp_id: str):
        """Scenario 2: Connector won't unlock after charging"""
        logger.info(f"🎭 DEMO: Triggering stuck connector for {cp_id}")
        self.active_scenarios[cp_id] = {
            "type": "stuck_connector", 
            "state": "occupied_with_lock_failure",
            "started_at": datetime.now()
        }
        # Simulate StatusNotification with ConnectorLockFailure
        if cp_id in STORE.charge_points:
            status_payload = {
                "connectorId": 1,
                "errorCode": "ConnectorLockFailure",
                "status": "Occupied",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            # This would be sent by the simulator
    
    async def _simulate_offline_charger(self, cp_id: str):
        """Scenario 3: Charger goes offline (no heartbeats)"""
        logger.info(f"🎭 DEMO: Triggering offline charger for {cp_id}")
        self.active_scenarios[cp_id] = {
            "type": "offline_charger",
            "state": "no_heartbeat",
            "started_at": datetime.now()
        }
        # The simulator will stop sending heartbeats
    
    async def _simulate_auth_failure(self, cp_id: str):
        """Scenario 4: Invalid card authorization"""
        logger.info(f"🎭 DEMO: Triggering auth failure for {cp_id}")
        self.active_scenarios[cp_id] = {
            "type": "auth_failure",
            "state": "invalid_card",
            "started_at": datetime.now()
        }
        # Modify Authorize handler to return Invalid for certain cards
    
    async def _simulate_slow_charging(self, cp_id: str):
        """Scenario 5: Very slow charging power"""
        logger.info(f"🎭 DEMO: Triggering slow charging for {cp_id}")
        self.active_scenarios[cp_id] = {
            "type": "slow_charging",
            "state": "low_power",
            "started_at": datetime.now()
        }
        # Simulate low power MeterValues
    
    def get_scenario_status(self, cp_id: str) -> Optional[Dict[str, Any]]:
        """Get current scenario status for a charge point"""
        return self.active_scenarios.get(cp_id)
    
    def clear_scenario(self, cp_id: str):
        """Clear active scenario for a charge point"""
        if cp_id in self.active_scenarios:
            del self.active_scenarios[cp_id]
            logger.info(f"🎭 DEMO: Cleared scenario for {cp_id}")
    
    def is_card_valid(self, id_tag: str) -> bool:
        """Check if a card is in the whitelist"""
        return id_tag in self.auth_list and self.auth_list[id_tag] == "Accepted"
    
    def add_card_to_whitelist(self, id_tag: str):
        """Add a card to the whitelist (for auth failure demo resolution)"""
        self.auth_list[id_tag] = "Accepted"
        logger.info(f"🎭 DEMO: Added {id_tag} to whitelist")
    
    def get_demo_commands(self) -> Dict[str, str]:
        """Get available demo commands for REST API"""
        return {
            "trigger_session_start_failure": "Simulate charger that won't start sessions",
            "trigger_stuck_connector": "Simulate connector that won't unlock", 
            "trigger_offline_charger": "Simulate charger going offline",
            "trigger_auth_failure": "Simulate invalid card authorization",
            "trigger_slow_charging": "Simulate very slow charging power",
            "clear_scenario": "Clear all active demo scenarios",
            "list_scenarios": "Show active demo scenarios"
        }

# Global demo manager instance
DEMO_MANAGER = DemoScenarioManager()
