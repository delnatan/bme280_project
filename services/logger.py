import schedule
import time
import socket
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from sensor import BME280Sensor
from database import SensorDB
from config import READING_INTERVAL_MINUTES

def get_local_ip():
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "Unknown"

def log_reading():
    sensor = BME280Sensor()
    db = SensorDB()
    
    try:
        reading = sensor.read_sensor()
        db.insert_reading(
            reading['temperature'],
            reading['pressure'], 
            reading['humidity']
        )
        print(f"Logged: {reading['temperature']}°C, {reading['humidity']}% RH, {reading['pressure']} hPa")
        
        # Log network info occasionally (every 10 readings)
        if time.time() % (600 * READING_INTERVAL_MINUTES) < (60 * READING_INTERVAL_MINUTES):
            ip = get_local_ip()
            print(f"Dashboard available at: http://{ip}:8000")
            
    except Exception as e:
        print(f"Error logging: {e}")

# Schedule every N minutes based on config
schedule.every(READING_INTERVAL_MINUTES).minutes.do(log_reading)

if __name__ == "__main__":
    print("Starting BME280 sensor logger...")
    print(f"Logging interval: {READING_INTERVAL_MINUTES} minutes")
    print(f"Dashboard will be available at: http://{get_local_ip()}:8000")
    
    # Take an initial reading
    log_reading()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
