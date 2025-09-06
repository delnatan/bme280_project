from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from database import SensorDB
from sensor import BME280Sensor
from config import WEB_HOST, WEB_PORT

app = FastAPI(title="BME280 Environmental Dashboard")
db = SensorDB()

@app.get("/api/current")
async def get_current_reading():
    """Get current sensor reading"""
    sensor = BME280Sensor()
    return sensor.read_sensor()

@app.get("/api/history")
async def get_history(hours: int = 24):
    """Get historical readings for the specified number of hours"""
    return db.get_recent_readings(hours)

@app.get("/api/stats")
async def get_stats(hours: int = 24, temp_unit: str = "C"):
    """Get basic statistics for the specified time period"""
    readings = db.get_recent_readings(hours)
    if not readings:
        return {"error": "No data available"}
    
    temps = [r['temperature'] for r in readings]
    humidities = [r['humidity'] for r in readings]
    pressures = [r['pressure'] for r in readings]
    
    # Convert temperature stats if needed
    if temp_unit.upper() == "F":
        temps = [t * 9/5 + 32 for t in temps]
    
    return {
        "count": len(readings),
        "temperature": {
            "min": round(min(temps), 2),
            "max": round(max(temps), 2),
            "avg": round(sum(temps) / len(temps), 2),
            "unit": temp_unit.upper()
        },
        "humidity": {
            "min": min(humidities),
            "max": max(humidities),
            "avg": round(sum(humidities) / len(humidities), 2)
        },
        "pressure": {
            "min": min(pressures),
            "max": max(pressures),
            "avg": round(sum(pressures) / len(pressures), 2)
        }
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard"""
    dashboard_path = Path(__file__).parent.parent / "static" / "dashboard.html"
    return dashboard_path.read_text()

# Mount static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
