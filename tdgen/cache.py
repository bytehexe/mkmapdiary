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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            self.__conn.commit()

    def __getitem__(self, key):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute('SELECT value FROM cache WHERE key = ?', (json.dumps(key),))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(key)
            return json.loads(row[0])
        
    def __setitem__(self, key, value):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute('REPLACE INTO cache (key, value) VALUES (?, ?)', (json.dumps(key), json.dumps(value)))
            self.__conn.commit()

    def __delitem__(self, key):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute('DELETE FROM cache WHERE key = ?', (json.dumps(key),))
            if cursor.rowcount == 0:
                raise KeyError(key)
            self.__conn.commit()

    def __iter__(self):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute('SELECT key FROM cache')
            rows = cursor.fetchall()
            for row in rows:
                yield json.loads(row[0])

    def __len__(self):
        with lock:
            cursor = self.__conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM cache')
            return cursor.fetchone()[0]
        
    def with_cache(self, key, compute_func, *args, **kwargs):
        """Get the value from cache or compute it if not present."""
        
        full_key = (key, args, list(sorted(kwargs.items())))

        try:
            return self[full_key]
        except KeyError:
            value = compute_func(*args, **kwargs)
            self[full_key] = value
            return value