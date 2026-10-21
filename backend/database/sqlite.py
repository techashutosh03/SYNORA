import sqlite3
import json
import os
import uuid
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "synora.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default',
            turn_index INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_prompt TEXT NOT NULL,
            final_response TEXT NOT NULL,
            task_type TEXT,
            complexity TEXT,
            models_used TEXT,
            total_time_ms REAL,
            memory_rss_mb REAL DEFAULT 0.0,
            orchestration_trace TEXT
        )
    """)
    # Check for existing table schema and migrate missing columns
    cursor.execute("PRAGMA table_info(chat_history)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    if "session_id" not in existing_cols:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN session_id TEXT DEFAULT 'default'")
    if "turn_index" not in existing_cols:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN turn_index INTEGER DEFAULT 0")
    if "memory_rss_mb" not in existing_cols:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN memory_rss_mb REAL DEFAULT 0.0")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON chat_history(session_id)")
    conn.commit()
    conn.close()

def save_chat_record(
    user_prompt: str,
    final_response: str,
    task_type: str,
    complexity: str,
    models_used: List[str],
    total_time_ms: float,
    orchestration_trace: Dict[str, Any],
    session_id: Optional[str] = None,
    memory_rss_mb: float = 0.0
) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    sid = session_id or str(uuid.uuid4())
    
    # Calculate turn index within session
    cursor.execute("SELECT COUNT(*) FROM chat_history WHERE session_id = ?", (sid,))
    turn_index = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO chat_history (
            session_id, turn_index, user_prompt, final_response, task_type, complexity, models_used, total_time_ms, memory_rss_mb, orchestration_trace
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sid,
        turn_index,
        user_prompt,
        final_response,
        task_type,
        complexity,
        json.dumps(models_used),
        total_time_ms,
        memory_rss_mb,
        json.dumps(orchestration_trace)
    ))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def get_session_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves chronological conversation turns for a given session."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, session_id, turn_index, timestamp, user_prompt, final_response, task_type, complexity, models_used, total_time_ms, memory_rss_mb, orchestration_trace
        FROM chat_history
        WHERE session_id = ?
        ORDER BY turn_index ASC
        LIMIT ?
    """, (session_id, limit))
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "session_id": row["session_id"],
            "turn_index": row["turn_index"],
            "timestamp": row["timestamp"],
            "user_prompt": row["user_prompt"],
            "final_response": row["final_response"],
            "task_type": row["task_type"],
            "complexity": row["complexity"],
            "models_used": json.loads(row["models_used"]) if row["models_used"] else [],
            "total_time_ms": row["total_time_ms"],
            "memory_rss_mb": row["memory_rss_mb"],
            "orchestration_trace": json.loads(row["orchestration_trace"]) if row["orchestration_trace"] else {}
        })
    conn.close()
    return results

def get_all_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves active sessions with latest message preview and turn counts."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT session_id, COUNT(*) as turn_count, MAX(timestamp) as last_updated,
               (SELECT user_prompt FROM chat_history c2 WHERE c2.session_id = c1.session_id ORDER BY id ASC LIMIT 1) as first_prompt,
               (SELECT final_response FROM chat_history c3 WHERE c3.session_id = c1.session_id ORDER BY id DESC LIMIT 1) as latest_response
        FROM chat_history c1
        GROUP BY session_id
        ORDER BY last_updated DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results

def get_recent_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, session_id, turn_index, timestamp, user_prompt, final_response, task_type, complexity, models_used, total_time_ms, memory_rss_mb, orchestration_trace
        FROM chat_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "session_id": row["session_id"] if "session_id" in row.keys() else "legacy",
            "turn_index": row["turn_index"] if "turn_index" in row.keys() else 0,
            "timestamp": row["timestamp"],
            "user_prompt": row["user_prompt"],
            "final_response": row["final_response"],
            "task_type": row["task_type"],
            "complexity": row["complexity"],
            "models_used": json.loads(row["models_used"]) if row["models_used"] else [],
            "total_time_ms": row["total_time_ms"],
            "memory_rss_mb": row["memory_rss_mb"] if "memory_rss_mb" in row.keys() else 0.0,
            "orchestration_trace": json.loads(row["orchestration_trace"]) if row["orchestration_trace"] else {}
        })
    conn.close()
    return results

init_db()
