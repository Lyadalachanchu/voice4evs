# Voice4EVs Backend

This backend provides a CSMS (Central System Management System) for OCPP 1.6 communication with charge points, including a custom OCPP simulator.

## Quick Start

### Docker Compose (Recommended)

```bash
# Start both CSMS and OCPP Simulator
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Setup

1. **Start CSMS:**
   ```bash
   pip install -r requirements.txt
   python csms.py
   ```

2. **Start REST API (optional):**
   ```bash
   python rest_api.py
   ```

3. **Start Charge Point Simulator (in another terminal):**
   ```bash
   python cp_sim.py
   ```

## What This Provides

- **CSMS WebSocket Server**: `ws://localhost:9000/EVSE001`
- **REST API**: `http://localhost:8000` - Monitor connections and send commands
- **OCPP Simulator**: Simulates a charge point with BootNotification, StatusNotification, and Heartbeat messages

## API Endpoints

### System Commands

#### 1. Check System Status
```bash
curl http://localhost:8000/status
```
**What it does:** Shows all connected charge points, their current status, heartbeat information, and total connection count.

#### 2. Get API Information
```bash
curl http://localhost:8000/
```
**What it does:** Shows the API overview, currently connected charge points, and lists all available commands.

### Charge Point Management Commands

All charge point commands follow this pattern: `POST /commands/{action}/{cp_id}` where `cp_id` is the charge point ID (currently `EVSE001`).

#### 3. Reset Charge Point
```bash
curl -X POST http://localhost:8000/commands/reset/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"type": "Hard"}'
```
**What it does:** Sends a reset command to the charge point. Options:
- `"Hard"` - Hard reset (reboots the entire system)
- `"Soft"` - Soft reset (restarts only the OCPP communication)

#### 4. Change Availability
```bash
curl -X POST http://localhost:8000/commands/change_availability/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"type": "Inoperative", "connector_id": 1}'
```
**What it does:** Changes the availability status of a charge point or specific connector. Options:
- `"Operative"` - Makes the charge point/connector available for charging
- `"Inoperative"` - Makes it unavailable for charging
- `connector_id` (optional) - Target specific connector, omit for entire charge point

#### 5. Change Configuration
```bash
curl -X POST http://localhost:8000/commands/change_configuration/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"key": "HeartbeatInterval", "value": "60"}'
```
**What it does:** Changes configuration parameters on the charge point. Common keys:
- `"HeartbeatInterval"` - Time between heartbeats (seconds)
- `"MeterValueSampleInterval"` - How often to send meter readings
- `"NumberOfConnectors"` - Number of physical connectors

#### 6. Remote Start Transaction
```bash
curl -X POST http://localhost:8000/commands/remote_start/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"id_tag": "USER123", "connector_id": 1}'
```
**What it does:** Remotely starts a charging session. Parameters:
- `id_tag` - User identification (RFID card, app ID, etc.)
- `connector_id` (optional) - Specific connector to use

#### 7. Remote Stop Transaction
```bash
curl -X POST http://localhost:8000/commands/remote_stop/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": 1}'
```
**What it does:** Stops an active charging session. Parameters:
- `transaction_id` - The transaction ID from when charging started

#### 8. Unlock Connector
```bash
curl -X POST http://localhost:8000/commands/unlock_connector/EVSE001 \
  -H "Content-Type: application/json" \
  -d '{"connector_id": 1}'
```
**What it does:** Unlocks the physical connector (releases the charging cable). Parameters:
- `connector_id` - Which connector to unlock

## Real-time Monitoring

Your system is currently running with:
- **CSMS**: WebSocket server on port 9000, REST API on port 8000
- **Charge Point Simulator**: `EVSE001` connected and sending heartbeats every 60 seconds
- **Status**: Available (ready for charging)

## System Management

### Start the system:
```bash
cd backend
docker-compose up --build
```

### Stop the system:
```bash
docker-compose down
```

### View logs:
```bash
docker-compose logs -f
```

## Testing

1. **Check connection status:**
   ```bash
   curl http://localhost:8000/status
   ```

2. **View CSMS logs** to see OCPP messages

3. **OCPP Simulator** will automatically connect and send standard OCPP messages

The system is fully functional and ready for testing OCPP 1.6 commands! The charge point simulator will continue running and responding to commands until you stop the Docker containers.

## 🎭 Complex Demo Scenario for Voice Agent Testing

The system includes a **complex diagnostic scenario** that requires multi-step analysis and specific command sequences to resolve:

### Charging Profile Mismatch Scenario

#### **Issue**: "Charging is very slow - only getting 3.5kW instead of 22kW"
- **Root Cause**: Conflicting charging profile configuration settings causing power delivery issues
- **Complexity**: Requires diagnostic steps, configuration analysis, and specific command sequence
- **Resolution Steps**: 6-step process involving status checks, configuration updates, and verification

#### **Voice Agent Diagnostic Process**:
1. **Diagnostic Phase**: Check status, ask user about power levels and error codes
2. **Configuration Analysis**: Identify specific configuration conflicts
3. **Resolution Phase**: Update 3 configuration parameters in sequence
4. **Verification Phase**: Reset charger and confirm power delivery restored

#### **Required Commands**:
```bash
# Trigger the complex scenario
curl -X POST http://localhost:8000/demo/trigger/charging_profile_mismatch

# Get resolution steps and guidance
curl http://localhost:8000/demo/resolution_steps

# Check progress during resolution
curl http://localhost:8000/demo/progress/EVSE001
```

### Demo Management Commands

```bash
# List available scenarios
curl http://localhost:8000/demo/scenarios

# Trigger the complex scenario
curl -X POST http://localhost:8000/demo/trigger/charging_profile_mismatch

# Get detailed resolution steps and agent guidance
curl http://localhost:8000/demo/resolution_steps

# Check resolution progress
curl http://localhost:8000/demo/progress/EVSE001

# Clear active scenarios
curl -X POST http://localhost:8000/demo/clear
```

### Automated Complex Demo Script

Run the complete complex diagnostic sequence automatically:

```bash
# Install demo dependencies
pip install aiohttp

# Run the complex demo scenario
python complex_demo_script.py
```

This will demonstrate the full diagnostic and resolution process, showing how a voice agent handles complex multi-step issues requiring specific command sequences.

## Troubleshooting

- Make sure ports 9000 and 8000 are available
- Check Docker logs: `docker-compose logs -f`
- For manual setup, ensure all Python dependencies are installed
