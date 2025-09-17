#!/usr/bin/env python3
"""
Voice4EVs Demo Script Pack
Reproducible demo scenarios for voice agent testing
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

class Voice4EVsDemo:
    """Complete demo script for Voice4EVs scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_system_status(self):
        """Check if the system is running"""
        try:
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ System Status: {data['total_connections']} charge points connected")
                    return True
                else:
                    print(f"❌ System not responding: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to system: {e}")
            return False
    
    async def trigger_scenario(self, scenario: str, cp_id: str = "EVSE001"):
        """Trigger a demo scenario"""
        try:
            async with self.session.post(f"{self.base_url}/demo/trigger/{scenario}?cp_id={cp_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"🎭 Triggered {scenario}: {data['message']}")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ Failed to trigger {scenario}: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error triggering {scenario}: {e}")
            return False
    
    async def clear_scenarios(self, cp_id: str = None):
        """Clear all demo scenarios"""
        try:
            url = f"{self.base_url}/demo/clear"
            if cp_id:
                url += f"?cp_id={cp_id}"
            
            async with self.session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"🧹 Cleared scenarios: {data['message']}")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ Failed to clear scenarios: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error clearing scenarios: {e}")
            return False
    
    async def send_command(self, command: str, cp_id: str = "EVSE001", payload: Dict[str, Any] = None):
        """Send a command to a charge point"""
        try:
            url = f"{self.base_url}/commands/{command}/{cp_id}"
            data = payload or {}
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"📤 {command}: {result['message']}")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ {command} failed: {error}")
                    return False
        except Exception as e:
            print(f"❌ Error sending {command}: {e}")
            return False
    
    async def demo_scenario_1_session_start_failure(self):
        """Demo Scenario 1: 'It says it's available but nothing happens'"""
        print("\n" + "="*60)
        print("🎭 DEMO SCENARIO 1: Session Start Failure")
        print("="*60)
        print("Caller: 'Hi, I plugged in and tapped my card, but the charger")
        print("        says 'Available' and nothing's happening.'")
        print()
        
        # Step 1: Trigger the scenario
        print("🔧 Voice Agent: Let me check the charger status...")
        await self.trigger_scenario("session_start_failure")
        await asyncio.sleep(2)
        
        # Step 2: Try to start a transaction (will fail)
        print("🔧 Voice Agent: I'll try to start a charging session for you...")
        await self.send_command("remote_start", payload={"id_tag": "USER123", "connector_id": 1})
        await asyncio.sleep(3)
        
        # Step 3: Agent detects the issue and fixes it
        print("🔧 Voice Agent: I can see the issue - the charger is stuck in a weird state.")
        print("               Let me reset it for you...")
        await self.send_command("reset", payload={"type": "Soft"})
        await asyncio.sleep(3)
        
        # Step 4: Try again (should work now)
        print("🔧 Voice Agent: The reset is complete. Please try tapping your card again.")
        await self.send_command("remote_start", payload={"id_tag": "USER123", "connector_id": 1})
        await asyncio.sleep(2)
        
        print("✅ Voice Agent: Perfect! Your charging session has started successfully.")
        print("   Caller: 'Oh great, it's working now! Thank you!'")
        
        # Clean up
        await self.clear_scenarios()
    
    async def demo_scenario_2_stuck_connector(self):
        """Demo Scenario 2: 'It won't unlock, I can't unplug'"""
        print("\n" + "="*60)
        print("🎭 DEMO SCENARIO 2: Stuck Connector")
        print("="*60)
        print("Caller: 'My car is done charging, but the plug is stuck")
        print("        and won't release.'")
        print()
        
        # Step 1: Start a charging session
        print("🔧 Voice Agent: Let me check your charging session...")
        await self.send_command("remote_start", payload={"id_tag": "USER123", "connector_id": 1})
        await asyncio.sleep(2)
        
        # Step 2: Stop the session
        print("🔧 Voice Agent: I'll stop your charging session...")
        await self.send_command("remote_stop", payload={"transaction_id": 1})
        await asyncio.sleep(2)
        
        # Step 3: Trigger stuck connector scenario
        print("🎭 Simulating connector lock failure...")
        await self.trigger_scenario("stuck_connector")
        await asyncio.sleep(2)
        
        # Step 4: Agent detects the issue and fixes it
        print("🔧 Voice Agent: I can see the connector is stuck. Let me unlock it for you...")
        await self.send_command("unlock_connector", payload={"connector_id": 1})
        await asyncio.sleep(2)
        
        print("✅ Voice Agent: The connector has been unlocked! You can now remove your cable.")
        print("   Caller: 'Perfect! I can unplug it now. Thanks so much!'")
        
        # Clean up
        await self.clear_scenarios()
    
    async def demo_scenario_3_offline_charger(self):
        """Demo Scenario 3: 'The charger is offline'"""
        print("\n" + "="*60)
        print("🎭 DEMO SCENARIO 3: Offline Charger")
        print("="*60)
        print("Caller: 'I'm at station 102 but it's greyed out in the app")
        print("        and won't respond.'")
        print()
        
        # Step 1: Trigger offline scenario
        print("🔧 Voice Agent: Let me check the charger status...")
        await self.trigger_scenario("offline_charger")
        await asyncio.sleep(2)
        
        # Step 2: Agent detects offline and tries to fix
        print("🔧 Voice Agent: I can see the charger is offline. Let me try to restart it...")
        await self.send_command("reset", payload={"type": "Hard"})
        await asyncio.sleep(5)
        
        # Step 3: Check if it came back online
        print("🔧 Voice Agent: The charger should be coming back online now...")
        await asyncio.sleep(3)
        
        print("✅ Voice Agent: Great! The charger is back online. Please try using it now.")
        print("   Caller: 'It's working! Thank you!'")
        
        # Clean up
        await self.clear_scenarios()
    
    async def demo_scenario_4_auth_failure(self):
        """Demo Scenario 4: 'It keeps saying my card is invalid'"""
        print("\n" + "="*60)
        print("🎭 DEMO SCENARIO 4: Auth Failure")
        print("="*60)
        print("Caller: 'I tap my company card and it says invalid.'")
        print()
        
        # Step 1: Trigger auth failure scenario
        print("🔧 Voice Agent: Let me check your card authorization...")
        await self.trigger_scenario("auth_failure")
        await asyncio.sleep(2)
        
        # Step 2: Try to authorize (will fail)
        print("🔧 Voice Agent: I can see your card is showing as invalid.")
        print("               Let me add it to the system...")
        await self.send_command("send_local_list", payload={"id_tag": "COMPANY123", "status": "Accepted"})
        await asyncio.sleep(2)
        
        # Step 3: Reset to reload the auth list
        print("🔧 Voice Agent: Now let me reset the charger to reload the authorization list...")
        await self.send_command("reset", payload={"type": "Soft"})
        await asyncio.sleep(3)
        
        # Step 4: Try again (should work now)
        print("🔧 Voice Agent: Please try tapping your card again now.")
        await self.send_command("remote_start", payload={"id_tag": "COMPANY123", "connector_id": 1})
        await asyncio.sleep(2)
        
        print("✅ Voice Agent: Perfect! Your card is now working. Your charging session has started.")
        print("   Caller: 'Excellent! It's working now. Thank you!'")
        
        # Clean up
        await self.clear_scenarios()
    
    async def demo_scenario_5_slow_charging(self):
        """Demo Scenario 5: 'Charging is very slow'"""
        print("\n" + "="*60)
        print("🎭 DEMO SCENARIO 5: Slow Charging")
        print("="*60)
        print("Caller: 'It says it's charging, but it's super slow.'")
        print()
        
        # Step 1: Start charging
        print("🔧 Voice Agent: Let me check your charging session...")
        await self.send_command("remote_start", payload={"id_tag": "USER123", "connector_id": 1})
        await asyncio.sleep(2)
        
        # Step 2: Trigger slow charging scenario
        print("🎭 Simulating slow charging...")
        await self.trigger_scenario("slow_charging")
        await asyncio.sleep(2)
        
        # Step 3: Agent detects slow charging and explains
        print("🔧 Voice Agent: I can see the charging power is very low.")
        print("               This could be due to site load management or a charger issue.")
        print("               Let me try a soft reset to see if that helps...")
        await self.send_command("reset", payload={"type": "Soft"})
        await asyncio.sleep(3)
        
        # Step 4: Restart charging
        print("🔧 Voice Agent: Let me restart your charging session...")
        await self.send_command("remote_start", payload={"id_tag": "USER123", "connector_id": 1})
        await asyncio.sleep(2)
        
        print("✅ Voice Agent: The charging should be back to normal speed now.")
        print("               If it's still slow, it might be due to site load sharing.")
        print("   Caller: 'Much better! Thanks for the help!'")
        
        # Clean up
        await self.clear_scenarios()
    
    async def run_all_demos(self):
        """Run all demo scenarios in sequence"""
        print("🚀 Starting Voice4EVs Demo Scenarios")
        print("="*60)
        
        # Check system status first
        if not await self.check_system_status():
            print("❌ System not ready. Please start the CSMS and simulator first.")
            return
        
        # Run all scenarios
        await self.demo_scenario_1_session_start_failure()
        await asyncio.sleep(2)
        
        await self.demo_scenario_2_stuck_connector()
        await asyncio.sleep(2)
        
        await self.demo_scenario_3_offline_charger()
        await asyncio.sleep(2)
        
        await self.demo_scenario_4_auth_failure()
        await asyncio.sleep(2)
        
        await self.demo_scenario_5_slow_charging()
        
        print("\n" + "="*60)
        print("🎉 All demo scenarios completed!")
        print("="*60)

async def main():
    """Main demo runner"""
    async with Voice4EVsDemo() as demo:
        await demo.run_all_demos()

if __name__ == "__main__":
    asyncio.run(main())
