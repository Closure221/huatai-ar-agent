"""SQLite 存储（MVP 版）

标准库 sqlite3，建表 + 轻量 CRUD。表结构见 docs/DATA_MODEL.md 的简化版。
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone

from app.core.config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS scripts (
        id TEXT PRIMARY KEY,
        title TEXT, content TEXT, source TEXT,
        status TEXT DEFAULT 'draft',
        created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS storyboards (
        id TEXT PRIMARY KEY,
        script_id TEXT, title TEXT,
        key_points TEXT, shots TEXT,
        total_duration_sec INTEGER, status TEXT DEFAULT 'draft',
        created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS scenes (
        id TEXT PRIMARY KEY,
        source_image TEXT, ocr_text TEXT,
        culture_attributes TEXT, semantic_summary TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        storyboard_id TEXT, scene_id TEXT,
        path TEXT, status TEXT DEFAULT 'generating',
        audit_status TEXT DEFAULT 'pending',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_records (
        id TEXT PRIMARY KEY,
        target_type TEXT, target_id TEXT,
        auto_check TEXT, final_status TEXT,
        created_at TEXT
    );
    """)
    # 轻量迁移：旧库补 videos.error 列（渲染失败原因透出给前端）
    try:
        conn.execute("ALTER TABLE videos ADD COLUMN error TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.close()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------- scripts ----------

def insert_script(title: str, content: str, source: str) -> dict:
    sid, ts = new_id(), now()
    conn = _conn()
    conn.execute(
        "INSERT INTO scripts VALUES (?,?,?,?,?,?,?)",
        (sid, title, content, source, "draft", ts, ts),
    )
    conn.commit()
    conn.close()
    return get_script(sid)


def get_script(sid: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM scripts WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_scripts() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM scripts ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_script_status(sid: str, status: str) -> None:
    conn = _conn()
    conn.execute("UPDATE scripts SET status=?, updated_at=? WHERE id=?",
                 (status, now(), sid))
    conn.commit()
    conn.close()


# ---------- storyboards ----------

def _parse_sb(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["key_points"] = json.loads(d["key_points"] or "[]")
    d["shots"] = json.loads(d["shots"] or "[]")
    return d


def insert_storyboard(script_id: str, title: str, key_points: list,
                      shots: list, duration: int) -> dict:
    sid, ts = new_id(), now()
    conn = _conn()
    conn.execute(
        "INSERT INTO storyboards VALUES (?,?,?,?,?,?,?,?,?)",
        (sid, script_id, title, json.dumps(key_points, ensure_ascii=False),
         json.dumps(shots, ensure_ascii=False), duration, "draft", ts, ts),
    )
    conn.commit()
    conn.close()
    return get_storyboard(sid)


def get_storyboard(sid: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM storyboards WHERE id=?", (sid,)).fetchone()
    conn.close()
    if not row:
        return None
    return _parse_sb(row)


def list_storyboards() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM storyboards ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_parse_sb(r) for r in rows]


def update_storyboard_status(sid: str, status: str) -> None:
    conn = _conn()
    conn.execute("UPDATE storyboards SET status=?, updated_at=? WHERE id=?",
                 (status, now(), sid))
    conn.commit()
    conn.close()


# ---------- scenes ----------

def insert_scene(source_image: str, ocr_text: str, culture_attributes: dict,
                 semantic_summary: str) -> dict:
    sid, ts = new_id(), now()
    conn = _conn()
    conn.execute(
        "INSERT INTO scenes VALUES (?,?,?,?,?,?)",
        (sid, source_image, ocr_text,
         json.dumps(culture_attributes, ensure_ascii=False),
         semantic_summary, ts),
    )
    conn.commit()
    conn.close()
    return get_scene(sid)


def get_scene(sid: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM scenes WHERE id=?", (sid,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["culture_attributes"] = json.loads(d["culture_attributes"] or "{}")
    return d


def list_scenes() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM scenes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- videos ----------

def insert_video(storyboard_id: str, scene_id: str, path: str = "") -> dict:
    vid, ts = new_id(), now()
    conn = _conn()
    conn.execute(
        "INSERT INTO videos (id, storyboard_id, scene_id, path, status, audit_status, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (vid, storyboard_id, scene_id, path, "generating", "pending", ts),
    )
    conn.commit()
    conn.close()
    return get_video(vid)


def get_video(vid: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_videos() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_video(vid: str, **fields) -> None:
    if not fields:
        return
    keys = ", ".join(f"{k}=?" for k in fields)
    conn = _conn()
    conn.execute(f"UPDATE videos SET {keys} WHERE id=?", (*fields.values(), vid))
    conn.commit()
    conn.close()


# ---------- audit ----------

def insert_audit(target_type: str, target_id: str, auto_check: dict,
                 final_status: str) -> dict:
    aid, ts = new_id(), now()
    conn = _conn()
    conn.execute(
        "INSERT INTO audit_records VALUES (?,?,?,?,?,?)",
        (aid, target_type, target_id,
         json.dumps(auto_check, ensure_ascii=False), final_status, ts),
    )
    conn.commit()
    conn.close()
    return {"id": aid, "target_type": target_type, "target_id": target_id,
            "auto_check": auto_check, "final_status": final_status,
            "created_at": ts}


def list_audits() -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM audit_records ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
