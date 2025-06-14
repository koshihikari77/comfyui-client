import sqlite3
import json
from pathlib import Path
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str = "results/index.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables_if_not_exists()

    def _create_tables_if_not_exists(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                config TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                filepath TEXT,
                workflow TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        ''')
        self.conn.commit()

    def create_job(self, job_name: str, config_data: dict) -> int:
        cursor = self.conn.cursor()
        now = datetime.now()
        cursor.execute(
            "INSERT INTO jobs (name, config, status, created_at) VALUES (?, ?, ?, ?)",
            (job_name, json.dumps(config_data), 'running', now)
        )
        self.conn.commit()
        return cursor.lastrowid

    def complete_job(self, job_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", ('completed', job_id))
        self.conn.commit()

    def create_image_record(self, job_id: int, workflow: dict) -> int:
        cursor = self.conn.cursor()
        now = datetime.now()
        cursor.execute(
            "INSERT INTO images (job_id, workflow, status, created_at) VALUES (?, ?, ?, ?)",
            (job_id, json.dumps(workflow), 'pending', now)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_image_record(self, image_id: int, filepath: str, status: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE images SET filepath = ?, status = ? WHERE id = ?", (filepath, status, image_id))
        self.conn.commit()
        
    def get_images_by_job_id(self, job_id: int) -> list[sqlite3.Row]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM images WHERE job_id = ? AND status = 'success' ORDER BY id", (job_id,))
        return cursor.fetchall()
        
    def close(self):
        self.conn.close()