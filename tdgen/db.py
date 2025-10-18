
import sqlite3

class Db:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                datetime TIMESTAMP,
                latitude REAL,
                longitude REAL
            )
        ''')
        self.conn.commit()

    def add_asset(self, path, type, meta):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO assets (path, type, datetime, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
            ''', (
                str(path),
                type,
                meta.get('date'),
                meta.get('latitude'),
                meta.get('longitude')
            ))

        self.conn.commit()

    def count_assets(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM assets')
        return cursor.fetchone()[0]
    
    def count_assets_by_date(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DATE(datetime) as date, COUNT(*) as count
            FROM assets
            GROUP BY DATE(datetime)
            ORDER BY DATE(datetime) ASC
        ''')
        return dict(cursor.fetchall())
    
    def get_all_assets(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT path FROM assets ORDER BY datetime ASC')
        return list(row[0] for row in cursor.fetchall())
    
    def get_all_dates(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT DATE(datetime) as date FROM assets ORDER BY DATE(datetime) ASC')
        return list(row[0] for row in cursor.fetchall())

    def dump(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM assets')
        return list(cursor.fetchall())