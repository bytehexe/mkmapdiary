import sqlite3
import pathlib
import threading
import collections
import json

lock = threading.Lock()


class Cache(collections.abc.MutableMapping):
    def __init__(self, cache_file: pathlib.Path):
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.__conn = sqlite3.connect(cache_file, check_same_thread=False)
        self.__initialize_db()

    def __initialize_db(self):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    section TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (section, parameters)
                )
            """
            )
            self.__conn.commit()

    def __getitem__(self, key):
        section, parameters = key
        assert type(section) is str, "Section must be a string"
        assert type(parameters) in (tuple, list), "Parameters must be a tuple or list"

        with lock:
            cursor = self.__conn.cursor()
            cursor.execute(
                "SELECT value FROM cache WHERE section = ? AND parameters = ?",
                (
                    section,
                    json.dumps(parameters),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            return json.loads(row[0])

    def __setitem__(self, key, value):
        section, parameters = key
        assert type(section) is str, "Section must be a string"
        assert type(parameters) in (tuple, list), "Parameters must be a tuple or list"

        with lock:
            cursor = self.__conn.cursor()
            cursor.execute(
                "REPLACE INTO cache (section, parameters, value) VALUES (?, ?, ?)",
                (section, json.dumps(parameters), json.dumps(value)),
            )
            self.__conn.commit()

    def __delitem__(self, key):
        section, parameters = key
        assert type(section) is str, "Section must be a string"
        assert type(parameters) in (tuple, list), "Parameters must be a tuple or list"

        with lock:
            cursor = self.__conn.cursor()
            cursor.execute(
                "DELETE FROM cache WHERE section = ? AND parameters = ?",
                (section, json.dumps(parameters)),
            )
            if cursor.rowcount == 0:
                raise KeyError(key)
            self.__conn.commit()

    def __iter__(self):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute("SELECT section, parameters FROM cache")
            rows = cursor.fetchall()
            for row in rows:
                yield row[0], json.loads(row[1])

    def __len__(self):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache")
            return cursor.fetchone()[0]
