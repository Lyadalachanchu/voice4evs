# shared_store.py
class CentralStore:
    """Super simple in-memory store. Could be replaced with a DB if needed."""
    def __init__(self):
        self.charge_points = {}      # id -> connection
        self.status = {}             # id -> latest StatusNotification payload
        self.heartbeat = {}          # id -> last heartbeat time
        self.resolved_diagnostics = set()  # Set of charge point IDs with resolved diagnostic issues
        self.diagnostic_config_changes = {}  # Track configuration changes for diagnostic resolution
        # Safety/guardrails state
        # Desired power limits applied via API (kW). Structure:
        #   { cp_id: { "default_kw": float | None, "per_connector": { connector_id: float } } }
        self.power_limits = {}
        # Rate limiting for power-affecting changes: { cp_id: [timestamps_sec] }
        self.power_change_events = {}
        # Rate limiting for generic configuration changes: { cp_id: [timestamps_sec] }
        self.config_change_events = {}
        # Simple in-memory audit log of sensitive actions
        # Each entry: {"ts": iso8601, "cp_id": str, "actor": str, "action": str, "details": dict}
        self.audit_log = []

# Global store instance
STORE = CentralStore()
