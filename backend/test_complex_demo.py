#!/usr/bin/env python3
"""
Test script for the complex demo scenario
"""

import asyncio
import aiohttp
import json

async def test_complex_demo():
    """Test the complex demo scenario endpoints"""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Complex Demo Scenario...")
        
        # Test 1: Check system status
        print("\n1. Checking system status...")
        async with session.get(f"{base_url}/status") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ System running: {data['total_connections']} charge points connected")
            else:
                print(f"❌ System not responding: {response.status}")
                return
        
        # Test 2: Get resolution steps
        print("\n2. Getting resolution steps...")
        async with session.get(f"{base_url}/demo/resolution_steps") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Resolution steps available: {len(data['steps'])} steps")
                print(f"   First step: {data['steps'][0]['description']}")
            else:
                print(f"❌ Failed to get resolution steps: {response.status}")
        
        # Test 3: Trigger scenario
        print("\n3. Triggering charging profile mismatch scenario...")
        async with session.post(f"{base_url}/demo/trigger/charging_profile_mismatch") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Scenario triggered: {data['message']}")
            else:
                error = await response.text()
                print(f"❌ Failed to trigger scenario: {error}")
        
        # Test 4: Check progress
        print("\n4. Checking scenario progress...")
        async with session.get(f"{base_url}/demo/progress/EVSE001") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Progress: {data['progress']}")
            else:
                print(f"❌ Failed to get progress: {response.status}")
        
        # Test 5: List scenarios
        print("\n5. Listing available scenarios...")
        async with session.get(f"{base_url}/demo/scenarios") as response:
            if response.status == 200:
                data = await response.json()
                scenarios = data['available_scenarios']
                print(f"✅ Available scenarios: {list(scenarios.keys())}")
                for name, desc in scenarios.items():
                    print(f"   - {name}: {desc}")
            else:
                print(f"❌ Failed to list scenarios: {response.status}")
        
        print("\n🎉 Complex demo test completed!")

if __name__ == "__main__":
    asyncio.run(test_complex_demo())
