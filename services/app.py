import asyncio
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import SensorDB
from sensor import BME280Sensor
from config import WEB_HOST, WEB_PORT, READING_INTERVAL_MINUTES, CLEANUP_DAYS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bme280")

_db: SensorDB = None


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "unknown"


async def _sensor_loop(sensor: BME280Sensor, db: SensorDB) -> None:
    log.info("Sensor loop started (interval: %d min)", READING_INTERVAL_MINUTES)
    reading_count = 0
    while True:
        try:
            reading = await asyncio.to_thread(sensor.read_sensor)
            await asyncio.to_thread(
                db.insert_reading,
                reading["temperature"],
                reading["pressure"],
                reading["humidity"],
            )
            reading_count += 1
            log.info(
                "%.2f°C  %.1f%% RH  %.2f hPa",
                reading["temperature"],
                reading["humidity"],
                reading["pressure"],
            )
            if reading_count % 10 == 0:
                log.info("Dashboard: http://%s:%d", _get_local_ip(), WEB_PORT)
        except Exception:
            log.exception("Failed to read sensor")
        await asyncio.sleep(READING_INTERVAL_MINUTES * 60)


async def _cleanup_loop(db: SensorDB) -> None:
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            deleted = await asyncio.to_thread(db.delete_old_readings, CLEANUP_DAYS)
            if deleted:
                log.info("Removed %d readings older than %d days", deleted, CLEANUP_DAYS)
        except Exception:
            log.exception("Cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db
    sensor = BME280Sensor()
    _db = SensorDB()

    tasks = [
        asyncio.create_task(_sensor_loop(sensor, _db)),
        asyncio.create_task(_cleanup_loop(_db)),
    ]
    log.info("Dashboard: http://%s:%d", _get_local_ip(), WEB_PORT)

    yield

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    sensor.close()
    log.info("Shutdown complete")


app = FastAPI(title="BME280 Environmental Dashboard", lifespan=lifespan)


@app.get("/api/current")
async def get_current_reading():
    reading = await asyncio.to_thread(_db.get_latest_reading)
    if reading is None:
        return {"error": "No readings yet"}
    return reading


@app.get("/api/history")
async def get_history(hours: int = 24, max_points: int | None = None):
    return await asyncio.to_thread(_db.get_recent_readings, hours, max_points)


@app.get("/api/stats")
async def get_stats(hours: int = 24, temp_unit: str = "C"):
    readings = await asyncio.to_thread(_db.get_recent_readings, hours)
    if not readings:
        return {"error": "No data available"}

    temps = [r["temperature"] for r in readings]
    humidities = [r["humidity"] for r in readings]
    pressures = [r["pressure"] for r in readings]

    if temp_unit.upper() == "F":
        temps = [t * 9 / 5 + 32 for t in temps]

    return {
        "count": len(readings),
        "temperature": {
            "min": round(min(temps), 2),
            "max": round(max(temps), 2),
            "avg": round(sum(temps) / len(temps), 2),
            "unit": temp_unit.upper(),
        },
        "humidity": {
            "min": round(min(humidities), 2),
            "max": round(max(humidities), 2),
            "avg": round(sum(humidities) / len(humidities), 2),
        },
        "pressure": {
            "min": round(min(pressures), 2),
            "max": round(max(pressures), 2),
            "avg": round(sum(pressures) / len(pressures), 2),
        },
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return (Path(__file__).parent.parent / "static" / "dashboard.html").read_text()


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent.parent / "static")), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
