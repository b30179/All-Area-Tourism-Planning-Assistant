"""
kb/store.py - 知识库 CRUD 与全文搜索
"""
import hashlib
import json
import logging
from typing import Optional
from urllib.parse import urlparse

from src.kb import get_connection

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return "unknown"


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def upsert_kb_item(
    url: str, category: str, title: str, content_md: str,
    summary: str = "", images: list | None = None,
) -> dict:
    """插入或更新条目（按 content_hash 去重），返回 {"id": int, "is_new": bool}"""
    images_json = json.dumps(images or [], ensure_ascii=False)
    conn = get_connection()
    content_hash = _compute_hash(content_md)
    source_domain = _extract_domain(url)

    existing = conn.execute(
        "SELECT id FROM kb_items WHERE content_hash = ?", (content_hash,)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE kb_items SET crawled_at = datetime('now','localtime'), images = ? WHERE id = ?",
            (images_json, existing["id"]),
        )
        conn.execute(
            "INSERT INTO kb_crawl_log (url, category, success) VALUES (?, ?, 1)",
            (url, category),
        )
        conn.commit()
        conn.close()
        return {"id": existing["id"], "is_new": False}

    cursor = conn.execute(
        """INSERT INTO kb_items (url, category, title, content_md, summary, images, source_domain, content_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (url, category, title, content_md, summary[:500], images_json, source_domain, content_hash),
    )
    new_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO kb_crawl_log (url, category, success) VALUES (?, ?, 1)",
        (url, category),
    )
    conn.commit()
    conn.close()
    return {"id": new_id, "is_new": True}


def search_kb(
    query: str, category: Optional[str] = None, limit: int = 5
) -> list:
    """全文搜索，返回 [{id, url, category, title, summary, content_md, crawled_at, source_domain}, ...]"""
    conn = get_connection()
    terms = " OR ".join(query.replace("'", "''").split())
    fts_query = f"kb_fts MATCH '{terms}'"

    try:
        if category:
            rows = conn.execute(
                f"""SELECT k.id, k.url, k.category, k.title, k.summary, k.content_md, k.images,
                           k.crawled_at, k.source_domain
                    FROM kb_items k JOIN kb_fts f ON k.id = f.rowid
                    WHERE {fts_query} AND k.category = ?
                    ORDER BY rank LIMIT ?""",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT k.id, k.url, k.category, k.title, k.summary, k.content_md, k.images,
                           k.crawled_at, k.source_domain
                    FROM kb_items k JOIN kb_fts f ON k.id = f.rowid
                    WHERE {fts_query}
                    ORDER BY rank LIMIT ?""",
                (limit,),
            ).fetchall()
    except Exception:
        rows = []
        logger.warning("FTS5 匹配失败，降级为 LIKE 搜索")

    # FTS5 + unicode61 对中文分词效果差，返回空时自动降级 LIKE
    if not rows:
        logger.info("FTS5 无结果，尝试 LIKE 搜索")
        like_q = f"%{query}%"
        if category:
            rows = conn.execute(
                """SELECT id, url, category, title, summary, content_md, images, crawled_at, source_domain
                   FROM kb_items WHERE (title LIKE ? OR content_md LIKE ?) AND category = ?
                   ORDER BY crawled_at DESC LIMIT ?""",
                (like_q, like_q, category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, url, category, title, summary, content_md, images, crawled_at, source_domain
                   FROM kb_items WHERE title LIKE ? OR content_md LIKE ?
                   ORDER BY crawled_at DESC LIMIT ?""",
                (like_q, like_q, limit),
            ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def get_kb_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM kb_items").fetchone()
    by_cat = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM kb_items GROUP BY category"
    ).fetchall()
    conn.close()
    return {
        "total_items": total["cnt"] if total else 0,
        "by_category": {r["category"]: r["cnt"] for r in by_cat},
    }


def log_crawl_error(url: str, category: str, error_msg: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO kb_crawl_log (url, category, success, error_msg) VALUES (?, ?, 0, ?)",
        (url, category, error_msg[:500]),
    )
    conn.commit()
    conn.close()
