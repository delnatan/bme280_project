import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH

class SensorDB:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.lock = threading.Lock()
        # Ensure data directory exists
        db_path.parent.mkdir(exist_ok=True)
        self._create_table()
    
    @contextmanager
    def get_connection(self):
        with self.lock:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def _create_table(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    pressure REAL NOT NULL,
                    humidity REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON readings(timestamp)")
    
    def insert_reading(self, temp, pressure, humidity):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO readings (timestamp, temperature, pressure, humidity) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), temp, pressure, humidity)
            )
    
    def get_recent_readings(self, hours=24):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM readings 
                WHERE timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours))
            return [dict(row) for row in cursor.fetchall()]
