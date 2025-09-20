"""
Demo Scenarios for Voice4EVs CSMS
Complex diagnostic scenario requiring multi-step resolution
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from shared_store import STORE
from complex_demo_scenario import COMPLEX_DEMO

logger = logging.getLogger(__name__)

class DemoScenarioManager:
    """Manages complex demo scenarios requiring diagnostic steps"""
    
    def __init__(self):
        self.active_scenarios = {}
        self.transaction_tracker = {}
        self.power_monitor = {}
        self.auth_list = {"USER123": "Accepted", "DEMO001": "Accepted"}  # Whitelist
        
    async def trigger_scenario(self, scenario_name: str, cp_id: str = "EVSE001"):
        """Trigger a specific demo scenario"""
        if scenario_name == "charging_profile_mismatch":
            await COMPLEX_DEMO.trigger_charging_profile_mismatch(cp_id)
            self.active_scenarios[cp_id] = {
                "type": "charging_profile_mismatch",
                "state": "diagnostic_required",
                "started_at": datetime.now()
            }
        elif scenario_name == "stuck_charging":
            # Simple scenario: force CP into Charging state and ignore stop requests
            logger.info(f"🎭 DEMO: Triggering stuck_charging for {cp_id}")
            # Mark scenario active
            self.active_scenarios[cp_id] = {
                "type": "stuck_charging",
                "state": "charging",
                "started_at": datetime.now()
            }
            # Fake a transaction id for visibility
            self.transaction_tracker[cp_id] = {"transaction_id": 4242}
            # Ensure CP appears as Charging in status
            STORE.status[cp_id] = {
                "connector_id": 1,
                "status": "Charging",
                "error_code": "NoError",
            }
        else:
            logger.error(f"Unknown scenario: {scenario_name}. Available: charging_profile_mismatch")
    
    async def _simulate_charging_profile_mismatch(self, cp_id: str):
        """Complex scenario: Charging profile configuration mismatch causing low power delivery"""
        logger.info(f"🎭 COMPLEX DEMO: Triggering charging profile mismatch for {cp_id}")
        await COMPLEX_DEMO.trigger_charging_profile_mismatch(cp_id)
    
    def get_scenario_status(self, cp_id: str) -> Optional[Dict[str, Any]]:
        """Get current scenario status for a charge point"""
        return self.active_scenarios.get(cp_id)
    
    def clear_scenario(self, cp_id: str):
        """Clear active scenario for a charge point"""
        if cp_id in self.active_scenarios:
            scenario_type = self.active_scenarios[cp_id].get("type")
            del self.active_scenarios[cp_id]
            logger.info(f"🎭 DEMO: Cleared scenario for {cp_id}")
            # Reset basic status if this was the stuck_charging scenario
            if scenario_type == "stuck_charging":
                STORE.status[cp_id] = {
                    "connector_id": 1,
                    "status": "Available",
                    "error_code": "NoError",
                }
    
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
            "trigger_charging_profile_mismatch": "Complex scenario requiring diagnostic steps and multi-command resolution",
            "trigger_stuck_charging": "Simple scenario: EVSE stays in Charging and ignores stop",
            "clear_scenario": "Clear all active demo scenarios",
            "list_scenarios": "Show active demo scenarios",
            "get_scenario_progress": "Get current progress of active scenario",
            "get_resolution_steps": "Get the specific steps needed to resolve the scenario"
        }

# Global demo manager instance
DEMO_MANAGER = DemoScenarioManager()
