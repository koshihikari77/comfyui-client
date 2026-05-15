import sqlite3
import json
from pathlib import Path
from datetime import datetime
from .interfaces import IDatabaseManager

class DatabaseManager(IDatabaseManager):
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
                parameters TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        ''')
        
        # 既存のDBにparameters列が無い場合は追加（マイグレーション）
        cursor.execute("PRAGMA table_info(images)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'parameters' not in columns:
            cursor.execute("ALTER TABLE images ADD COLUMN parameters TEXT")
            self.conn.commit()
        # tags_json 列のマイグレーション (WD14Tagger 出力用、JSON 文字列で保存)
        if 'tags_json' not in columns:
            cursor.execute("ALTER TABLE images ADD COLUMN tags_json TEXT")
            self.conn.commit()

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

    def create_image_record(self, job_id: int, workflow: dict, parameters: dict = None) -> int:
        """
        画像レコードを作成
        
        Args:
            job_id: ジョブID
            workflow: ワークフローデータ（JSON化される）
            parameters: 適用されたパラメータ（JSON化される、オプション）
            
        Returns:
            作成された画像レコードのID
        """
        cursor = self.conn.cursor()
        now = datetime.now()
        parameters_json = json.dumps(parameters) if parameters is not None else None
        cursor.execute(
            "INSERT INTO images (job_id, workflow, parameters, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, json.dumps(workflow), parameters_json, 'pending', now)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_image_record(self, image_id: int, filepath: str, status: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE images SET filepath = ?, status = ? WHERE id = ?", (filepath, status, image_id))
        self.conn.commit()

    def update_image_tags(self, image_id: int, tags: list[str], model: str = None):
        """WD14Tagger の出力タグを images.tags_json に保存する。
        tags: タグ文字列のリスト (例: ["1girl", "long hair", ...])
        model: 使用したタガーモデル名 (例: "wd-vit-tagger-v3")
        """
        cursor = self.conn.cursor()
        payload = {"model": model, "tags": list(tags)} if model else {"tags": list(tags)}
        cursor.execute(
            "UPDATE images SET tags_json = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), image_id),
        )
        self.conn.commit()
        
    def get_images_by_job_id(self, job_id: int) -> list[sqlite3.Row]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM images WHERE job_id = ? AND status = 'success' ORDER BY id", (job_id,))
        return cursor.fetchall()
        
    def close(self):
        self.conn.close()