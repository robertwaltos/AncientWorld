import json
import os
import sqlite3
from datetime import datetime

class SqlitePipeline:
    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect("data/assets.sqlite3")
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            query TEXT,
            title TEXT,
            page_url TEXT,
            image_url TEXT,
            local_path TEXT,
            width INTEGER,
            height INTEGER,
            mime TEXT,
            sha1 TEXT,
            license TEXT,
            artist TEXT,
            credit TEXT,
            date TEXT,
            institution TEXT,
            description TEXT,
            categories TEXT,
            raw_images_json TEXT,
            created_at TEXT
        )
        """)
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_sha1 ON assets(sha1)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_query ON assets(query)")
        self.conn.commit()

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()

    def process_item(self, item, spider):
        # Determine local file path if downloaded
        local_path = None
        image_url = None
        raw_images_json = None

        if item.get("images"):
            raw_images_json = json.dumps(item["images"], ensure_ascii=False)
            # ImagesPipeline stores results as list of dicts with "path" and "url"
            first = item["images"][0]
            local_path = first.get("path")
            image_url = first.get("url")
        else:
            # Not downloaded (filtered out or failed)
            image_url = item.get("image_urls", [None])[0]

        # Dedup: if sha1 exists, ignore insert
        sha1 = item.get("sha1")
        if not sha1:
            sha1 = None

        try:
            self.conn.execute("""
                INSERT INTO assets (
                    source, query, title, page_url, image_url, local_path,
                    width, height, mime, sha1, license, artist, credit,
                    date, institution, description, categories,
                    raw_images_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("source"),
                item.get("query"),
                item.get("title"),
                item.get("page_url"),
                image_url,
                local_path,
                item.get("width"),
                item.get("height"),
                item.get("mime"),
                sha1,
                item.get("license"),
                item.get("artist"),
                item.get("credit"),
                item.get("date"),
                item.get("institution"),
                item.get("description"),
                json.dumps(item.get("categories"), ensure_ascii=False) if item.get("categories") else None,
                raw_images_json,
                datetime.utcnow().isoformat() + "Z",
            ))
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Duplicate sha1: already captured
            pass

        return item
