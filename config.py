import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database
DATABASE_PATH = BASE_DIR / "data" / "sensor_data.db"

# Sensor settings
I2C_ADDRESS = 0x77
I2C_BUS = 1
READING_INTERVAL_MINUTES = 5 

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_LEVEL = "INFO"

# Data retention
CLEANUP_DAYS = 90
