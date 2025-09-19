"""
Complex Demo Scenario: Charging Profile Mismatch
Requires diagnostic steps and specific command sequence to resolve
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from shared_store import STORE

logger = logging.getLogger(__name__)

class ComplexDemoScenario:
    """Complex demo scenario requiring multi-step diagnosis and resolution"""
    
    def __init__(self):
        self.active_scenario = None
        self.diagnostic_data = {}
        self.step_counter = 0
        
    async def trigger_charging_profile_mismatch(self, cp_id: str = "EVSE001"):
        """Trigger complex charging profile mismatch scenario"""
        logger.info(f"🎭 COMPLEX DEMO: Triggering charging profile mismatch for {cp_id}")
        
        self.active_scenario = {
            "type": "charging_profile_mismatch",
            "cp_id": cp_id,
            "state": "diagnostic_required",
            "started_at": datetime.now(),
            "steps_completed": [],
            "diagnostic_data": {
                "charging_profile_active": True,
                "profile_id": 1,
                "max_power": 22.0,  # kW
                "current_power": 3.5,  # kW - much lower than expected
                "connector_status": "Charging",
                "error_codes": ["PowerDeliveryFailure"],
                "configuration_issues": {
                    "ChargingProfileMaxStackLevel": "8",  # Should be 1
                    "ChargingScheduleMaxPeriods": "500",  # Should be 100
                    "MaxChargingProfilesInstalled": "10"  # Should be 1
                }
            }
        }
        
        # Simulate the issue by modifying the charge point behavior
        if cp_id in STORE.charge_points:
            # The simulator will need to be enhanced to support this scenario
            logger.info(f"🎭 COMPLEX DEMO: Charging profile mismatch active for {cp_id}")
    
    def get_diagnostic_questions(self) -> Dict[str, str]:
        """Get diagnostic questions for the agent to ask"""
        return {
            "power_flow": "What power level is the charger currently delivering?",
            "profile_status": "Is there a charging profile active on the charger?",
            "configuration": "What are the current charging profile configuration settings?",
            "error_codes": "Are there any error codes showing on the charger display?"
        }
    
    def get_resolution_steps(self) -> list:
        """Get the specific sequence of commands needed to resolve the issue"""
        return [
            {
                "step": 1,
                "action": "get_status",
                "description": "Check current charger status and power delivery",
                "expected_result": "Confirm low power delivery (3.5kW vs expected 22kW)"
            },
            {
                "step": 2,
                "action": "change_configuration",
                "parameters": {"key": "ChargingProfileMaxStackLevel", "value": "1"},
                "description": "Fix charging profile stack level configuration",
                "expected_result": "Configuration updated successfully"
            },
            {
                "step": 3,
                "action": "change_configuration", 
                "parameters": {"key": "ChargingScheduleMaxPeriods", "value": "100"},
                "description": "Fix charging schedule periods configuration",
                "expected_result": "Configuration updated successfully"
            },
            {
                "step": 4,
                "action": "change_configuration",
                "parameters": {"key": "MaxChargingProfilesInstalled", "value": "1"},
                "description": "Fix maximum charging profiles configuration",
                "expected_result": "Configuration updated successfully"
            },
            {
                "step": 5,
                "action": "reset_charge_point",
                "parameters": {"type": "Soft"},
                "description": "Reset charger to apply new configuration",
                "expected_result": "Charger reset successfully"
            },
            {
                "step": 6,
                "action": "get_status",
                "description": "Verify power delivery is now at expected level",
                "expected_result": "Power delivery increased to 22kW"
            }
        ]
    
    def get_scenario_description(self) -> str:
        """Get human-readable description of the scenario"""
        return """
        CHARGING PROFILE MISMATCH SCENARIO
        
        Issue: Charger is delivering only 3.5kW instead of expected 22kW due to 
        incorrect charging profile configuration settings.
        
        Root Cause: Multiple configuration parameters are set incorrectly:
        - ChargingProfileMaxStackLevel: 8 (should be 1)
        - ChargingScheduleMaxPeriods: 500 (should be 100) 
        - MaxChargingProfilesInstalled: 10 (should be 1)
        
        Resolution: Requires diagnostic check, configuration updates, and reset.
        This simulates a real-world issue where charging profiles conflict and
        cause power delivery problems.
        """
    
    def get_agent_guidance(self) -> str:
        """Get guidance for the voice agent on how to handle this scenario"""
        return """
        VOICE AGENT GUIDANCE FOR CHARGING PROFILE MISMATCH
        
        When user reports: "Charging is very slow" or "Not getting full power"
        
        DIAGNOSTIC PHASE:
        1. Check status to confirm low power delivery
        2. Ask user about charging profile settings if visible
        3. Look for error codes on charger display
        
        RESOLUTION PHASE:
        1. Update ChargingProfileMaxStackLevel to 1
        2. Update ChargingScheduleMaxPeriods to 100  
        3. Update MaxChargingProfilesInstalled to 1
        4. Perform soft reset to apply changes
        5. Verify power delivery is restored
        
        COMMUNICATION:
        - "I can see the issue - your charger's profile settings are conflicting"
        - "Let me fix the configuration and reset the charger"
        - "The charger should now deliver full power"
        - "Please try charging again and let me know the power level"
        """
    
    def is_scenario_active(self, cp_id: str = "EVSE001") -> bool:
        """Check if scenario is active for a charge point"""
        return (self.active_scenario and 
                self.active_scenario.get("cp_id") == cp_id and
                self.active_scenario.get("type") == "charging_profile_mismatch")
    
    def mark_step_completed(self, step: int, cp_id: str = "EVSE001"):
        """Mark a resolution step as completed"""
        if self.is_scenario_active(cp_id):
            if step not in self.active_scenario["steps_completed"]:
                self.active_scenario["steps_completed"].append(step)
                logger.info(f"🎭 COMPLEX DEMO: Step {step} completed for {cp_id}")
    
    def get_progress(self, cp_id: str = "EVSE001") -> Dict[str, Any]:
        """Get current progress of scenario resolution"""
        if not self.is_scenario_active(cp_id):
            return {"status": "not_active"}
        
        total_steps = len(self.get_resolution_steps())
        completed_steps = len(self.active_scenario["steps_completed"])
        
        return {
            "status": "active",
            "scenario_type": "charging_profile_mismatch",
            "progress": f"{completed_steps}/{total_steps}",
            "completed_steps": self.active_scenario["steps_completed"],
            "next_step": completed_steps + 1 if completed_steps < total_steps else None
        }
    
    def clear_scenario(self, cp_id: str = "EVSE001"):
        """Clear the active scenario"""
        if self.active_scenario and self.active_scenario.get("cp_id") == cp_id:
            self.active_scenario = None
            logger.info(f"🎭 COMPLEX DEMO: Cleared scenario for {cp_id}")

# Global complex demo instance
COMPLEX_DEMO = ComplexDemoScenario()
