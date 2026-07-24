"""
kb/__init__.py - 知识库初始化与 Schema 管理
"""
import sqlite3
from pathlib import Path

KB_DIR = Path(__file__).parent
DB_PATH = str(KB_DIR / "travel_kb.db")


def get_connection() -> sqlite3.Connection:
    """获取知识库连接（自动建表）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """建表 + FTS5 全文索引"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kb_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('attraction','food','hotel','transport','general')),
            title TEXT DEFAULT '',
            content_md TEXT NOT NULL,
            summary TEXT DEFAULT '',
            images TEXT DEFAULT '[]',
            source_domain TEXT DEFAULT '',
            crawled_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            content_hash TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS kb_crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            category TEXT,
            success INTEGER NOT NULL DEFAULT 1,
            error_msg TEXT DEFAULT '',
            crawled_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)
    # 兼容旧表：如果 images 列不存在则添加
    try:
        conn.execute("ALTER TABLE kb_items ADD COLUMN images TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
                title, content_md, summary,
                content='kb_items',
                content_rowid='id',
                tokenize='unicode61 remove_diacritics 2'
            )
        """)
    except sqlite3.OperationalError:
        pass


def get_db_path() -> str:
    return DB_PATH
