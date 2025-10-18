import sqlite3
import threading
import datetime
from pathlib import PosixPath
from typing import Dict, List, Tuple, Union, Any


class Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.create_tables()
        self.lock = threading.Lock()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                datetime TIMESTAMP,
                latitude REAL,
                longitude REAL,
                approx INTEGER DEFAULT NULL
            )
        """
        )
        self.conn.commit()

    def add_asset(self, path: Union[str, PosixPath], type: str, meta: Dict[str, Any]):
        assert (
            "date" not in meta
            or meta["date"] is None
            or isinstance(meta["date"], datetime.datetime)
        ), "Meta 'date' must be a datetime object or None"

        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO assets (path, type, datetime, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(path),
                    type,
                    meta.get("date"),
                    meta.get("latitude"),
                    meta.get("longitude"),
                ),
            )

            self.conn.commit()

    def count_assets(self) -> int:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assets")
            return cursor.fetchone()[0]

    def count_assets_by_date(self):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT DATE(datetime) as date, COUNT(*) as count
                FROM assets
                GROUP BY DATE(datetime)
                ORDER BY DATE(datetime) ASC
            """
            )
            return dict(cursor.fetchall())

    def get_all_assets(self) -> List[str]:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT path FROM assets ORDER BY datetime ASC")
            return list(row[0] for row in cursor.fetchall())

    def get_all_dates(self) -> List[str]:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT DISTINCT DATE(datetime) as date FROM assets ORDER BY DATE(datetime) ASC"
            )
            return list(row[0] for row in cursor.fetchall())

    def get_assets_by_type(self, asset_type):
        if type(asset_type) in (list, tuple):
            asset_placeholder = ",".join("?" for _ in asset_type)
        else:
            asset_type = [asset_type]
            asset_placeholder = "?"

        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                f"SELECT path, type FROM assets WHERE type IN ({asset_placeholder}) ORDER BY datetime ASC",
                tuple(asset_type),
            )
            return list(cursor.fetchall())

    def get_assets_by_date(self, date, asset_type):
        if type(asset_type) in (list, tuple):
            asset_placeholder = ",".join("?" for _ in asset_type)
        else:
            asset_type = [asset_type]
            asset_placeholder = "?"

        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                f"SELECT path, type FROM assets WHERE DATE(datetime) = ? AND type IN ({asset_placeholder}) ORDER BY datetime ASC",
                (date, *asset_type),
            )
            return list(cursor.fetchall())

    def get_geo_by_name(self, name):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT path, latitude, longitude FROM assets WHERE path = ? AND latitude IS NOT NULL AND longitude IS NOT NULL",
                (name,),
            )
            row = cursor.fetchone()
            if row:
                return {"name": row[0], "latitude": row[1], "longitude": row[2]}
            return None

    def dump(self, asset_type: None = None) -> Tuple[List[Any], List[str]]:
        headers = ["ID", "Path", "Type", "DateTime", "Latitude", "Longitude", "approx"]
        with self.lock:
            cursor = self.conn.cursor()
            if asset_type:
                cursor.execute("SELECT * FROM assets WHERE type = ?", (asset_type,))
            else:
                cursor.execute("SELECT * FROM assets")

            return list(cursor.fetchall()), headers

    def get_unpositioned_assets(self):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT id, datetime FROM assets WHERE latitude IS NULL OR longitude IS NULL AND type != "gpx"'
            )
            return list(row for row in cursor.fetchall())

    def update_asset_position(self, asset_id, latitude, longitude, approx):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE assets
                SET latitude = ?, longitude = ?, approx = ?
                WHERE id = ?
            """,
                (latitude, longitude, approx, asset_id),
            )
            self.conn.commit()

    def get_geotagged_journals(self) -> List[str]:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT DISTINCT DATE(datetime) as date FROM assets WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND type IN ("markdown", "audio")'
            )
            return list(row[0] for row in cursor.fetchall())

    def get_metadata(self, asset_path):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, datetime, latitude, longitude FROM assets WHERE path = ?",
                (asset_path,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "timestamp": row[1],
                    "latitude": row[2],
                    "longitude": row[3],
                }
            return None
