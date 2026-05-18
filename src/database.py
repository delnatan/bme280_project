import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


class SensorDB:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
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
                (_now_utc(), temp, pressure, humidity),
            )

    def get_latest_reading(self):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_readings(self, hours=24, max_points=None):
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            if max_points is None:
                cursor = conn.execute(
                    "SELECT * FROM readings WHERE timestamp > datetime('now', ?) ORDER BY timestamp",
                    (f"-{hours} hours",),
                )
                return [dict(row) for row in cursor.fetchall()]

            # Bucket-average to target approximately max_points.
            # REPLACE normalises old ISO-format timestamps (T separator) for strftime('%s').
            bucket_seconds = max(300, (hours * 3600) // max_points)
            cursor = conn.execute("""
                SELECT
                    datetime(
                        CAST(strftime('%s', REPLACE(timestamp, 'T', ' ')) / ? AS INTEGER) * ?,
                        'unixepoch'
                    ) AS timestamp,
                    ROUND(AVG(temperature), 2) AS temperature,
                    ROUND(AVG(pressure),    2) AS pressure,
                    ROUND(AVG(humidity),    2) AS humidity
                FROM readings
                WHERE timestamp > datetime('now', ?)
                GROUP BY CAST(strftime('%s', REPLACE(timestamp, 'T', ' ')) / ? AS INTEGER)
                ORDER BY 1
            """, (bucket_seconds, bucket_seconds, f"-{hours} hours", bucket_seconds))
            return [dict(row) for row in cursor.fetchall()]

    def delete_old_readings(self, days=90) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM readings WHERE timestamp < datetime('now', ?)",
                (f"-{days} days",),
            )
            return cursor.rowcount
