import smbus2
import bme280
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))
from config import I2C_ADDRESS, I2C_BUS

class BME280Sensor:
    def __init__(self, i2c_address=I2C_ADDRESS, bus_number=I2C_BUS):
        self.bus = smbus2.SMBus(bus_number)
        self.address = i2c_address
        self.calibration_params = bme280.load_calibration_params(
            self.bus, self.address
        )
    
    def read_sensor(self):
        """Return temperature (°C), pressure (hPa), humidity (%)"""
        data = bme280.sample(self.bus, self.address, self.calibration_params)
        return {
            'temperature': round(data.temperature, 2),
            'pressure': round(data.pressure, 2),
            'humidity': round(data.humidity, 2),
            'timestamp': data.timestamp
        }
    
    def __del__(self):
        self.bus.close()
