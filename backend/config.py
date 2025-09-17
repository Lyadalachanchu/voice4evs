import os

# CSMS Configuration
CSMS_HOST = os.getenv("CSMS_HOST", "0.0.0.0")
CSMS_PORT = int(os.getenv("CSMS_PORT", "9000"))
CSMS_PATH = os.getenv("CSMS_PATH", "/ocpp")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
