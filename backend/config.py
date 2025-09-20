import os

# CSMS Configuration
CSMS_HOST = os.getenv("CSMS_HOST", "0.0.0.0")
CSMS_PORT = int(os.getenv("CSMS_PORT", "9000"))
CSMS_PATH = os.getenv("CSMS_PATH", "/ocpp")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Guardrail configuration
# If False, generic ChangeConfiguration is restricted to an allowlist
ALLOW_GENERIC_CHANGE_CONFIG = os.getenv("ALLOW_GENERIC_CHANGE_CONFIG", "false").lower() in ("1", "true", "yes")

# Allowed configuration keys when generic changes are restricted
ALLOWED_CONFIG_KEYS = set((
    # Diagnostic/demo-related safe keys
    "ChargingProfileMaxStackLevel",
    "ChargingScheduleMaxPeriods",
    "MaxChargingProfilesInstalled",
))

# Power limit boundaries (kW)
POWER_LIMIT_MIN_KW = float(os.getenv("POWER_LIMIT_MIN_KW", "1.0"))
POWER_LIMIT_MAX_KW = float(os.getenv("POWER_LIMIT_MAX_KW", "22.0"))

# Rate limiting for power/config changes
POWER_CHANGE_RATE_LIMIT_WINDOW_SEC = int(os.getenv("POWER_CHANGE_RATE_LIMIT_WINDOW_SEC", "60"))
POWER_CHANGE_RATE_LIMIT_MAX = int(os.getenv("POWER_CHANGE_RATE_LIMIT_MAX", "5"))
CONFIG_CHANGE_RATE_LIMIT_WINDOW_SEC = int(os.getenv("CONFIG_CHANGE_RATE_LIMIT_WINDOW_SEC", "60"))
CONFIG_CHANGE_RATE_LIMIT_MAX = int(os.getenv("CONFIG_CHANGE_RATE_LIMIT_MAX", "10"))

# Audit logging
AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", "true").lower() in ("1", "true", "yes")
