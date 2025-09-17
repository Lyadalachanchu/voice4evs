# shared_store.py
class CentralStore:
    """Super simple in-memory store. Could be replaced with a DB if needed."""
    def __init__(self):
        self.charge_points = {}      # id -> connection
        self.status = {}             # id -> latest StatusNotification payload
        self.heartbeat = {}          # id -> last heartbeat time

# Global store instance
STORE = CentralStore()
