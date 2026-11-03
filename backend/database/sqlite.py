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

    # Approvals table for cross-worker durable approvals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_approvals (
            action_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT DEFAULT 'default_user',
            workspace_root TEXT DEFAULT '.',
            tool_name TEXT NOT NULL,
            arguments TEXT,
            reason TEXT,
            diff_preview TEXT,
            command_preview TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_session ON pending_approvals(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_approval_status ON pending_approvals(status)")

    # Routing telemetry table to measure routing accuracy and track overrides
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routing_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            selected_workflow TEXT NOT NULL,
            confidence REAL NOT NULL,
            reason TEXT,
            user_override TEXT,
            is_correct INTEGER DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_routing_session ON routing_telemetry(session_id)")

    # Model tool-calling success rate metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_tool_metrics (
            model_id TEXT PRIMARY KEY,
            calls_attempted INTEGER DEFAULT 0,
            calls_succeeded INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

def save_pending_approval_db(
    action_id: str,
    session_id: str,
    user_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    reason: str,
    created_at: float,
    expires_at: float,
    workspace_root: str = ".",
    diff_preview: Optional[str] = None,
    command_preview: Optional[str] = None
) -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO pending_approvals (
            action_id, session_id, user_id, workspace_root, tool_name, arguments, reason,
            diff_preview, command_preview, status, created_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (
        action_id, session_id, user_id, workspace_root, tool_name,
        json.dumps(arguments), reason, diff_preview, command_preview,
        created_at, expires_at
    ))
    conn.commit()
    conn.close()

def update_approval_status_db(action_id: str, status: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE pending_approvals SET status = ? WHERE action_id = ?", (status, action_id))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def get_approval_record_db(action_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_approvals WHERE action_id = ?", (action_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("arguments"):
        try:
            d["arguments"] = json.loads(d["arguments"])
        except Exception:
            pass
    return d

def get_active_pending_approvals_db(session_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM pending_approvals WHERE status = 'pending'"
    params = []
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    query += " ORDER BY created_at DESC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("arguments"):
            try:
                d["arguments"] = json.loads(d["arguments"])
            except Exception:
                pass
        results.append(d)
    return results

def cleanup_pending_approvals_db(session_id: Optional[str] = None, reason: str = "cancelled") -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if session_id:
        cursor.execute("UPDATE pending_approvals SET status = ? WHERE session_id = ? AND status = 'pending'", (reason, session_id))
    else:
        cursor.execute("UPDATE pending_approvals SET status = ? WHERE status = 'pending'", (reason,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

# -------------------------------------------------------------
# Routing Telemetry & Feedback
# -------------------------------------------------------------

def record_routing_telemetry(
    session_id: str,
    prompt: str,
    selected_workflow: str,
    confidence: float,
    reason: str,
    user_override: Optional[str] = None
) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO routing_telemetry (
            session_id, prompt, selected_workflow, confidence, reason, user_override, is_correct
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, prompt, selected_workflow, confidence, reason, user_override,
        0 if user_override and user_override != selected_workflow else 1
    ))
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id

def update_routing_feedback(session_id: str, user_override: Optional[str], is_correct: bool = True) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE routing_telemetry
        SET user_override = ?, is_correct = ?
        WHERE session_id = ?
    """, (user_override, 1 if is_correct else 0, session_id))
    changed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def get_routing_accuracy_metrics() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(is_correct) FROM routing_telemetry")
    total, correct = cursor.fetchone()
    total = total or 0
    correct = correct or 0

    cursor.execute("""
        SELECT selected_workflow, COUNT(*) as cnt, SUM(is_correct) as correct_cnt
        FROM routing_telemetry
        GROUP BY selected_workflow
    """)
    workflow_stats = {}
    for wf, cnt, c_cnt in cursor.fetchall():
        c_cnt = c_cnt or 0
        workflow_stats[wf] = {
            "total": cnt,
            "correct": c_cnt,
            "accuracy": round((c_cnt / cnt) * 100, 2) if cnt > 0 else 100.0
        }

    conn.close()
    overall_acc = round((correct / total) * 100, 2) if total > 0 else 100.0
    return {
        "total_routes_recorded": total,
        "correct_routes": correct,
        "overall_accuracy_pct": overall_acc,
        "workflows": workflow_stats
    }

# -------------------------------------------------------------
# Model Tool Calling Empirical Metrics
# -------------------------------------------------------------

def record_model_tool_call(model_id: str, success: bool) -> float:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT calls_attempted, calls_succeeded FROM model_tool_metrics WHERE model_id = ?", (model_id,))
    row = cursor.fetchone()
    if row:
        attempted, succeeded = row[0] + 1, row[1] + (1 if success else 0)
        rate = round(succeeded / attempted, 3)
        cursor.execute("""
            UPDATE model_tool_metrics
            SET calls_attempted = ?, calls_succeeded = ?, success_rate = ?, last_updated = CURRENT_TIMESTAMP
            WHERE model_id = ?
        """, (attempted, succeeded, rate, model_id))
    else:
        attempted = 1
        succeeded = 1 if success else 0
        rate = 1.0 if success else 0.0
        cursor.execute("""
            INSERT INTO model_tool_metrics (model_id, calls_attempted, calls_succeeded, success_rate)
            VALUES (?, ?, ?, ?)
        """, (model_id, attempted, succeeded, rate))
    conn.commit()
    conn.close()
    return rate

def get_model_tool_stats(model_id: Optional[str] = None) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if model_id:
        cursor.execute("SELECT model_id, calls_attempted, calls_succeeded, success_rate FROM model_tool_metrics WHERE model_id = ?", (model_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"model_id": row[0], "attempted": row[1], "succeeded": row[2], "success_rate": row[3]}
        return {"model_id": model_id, "attempted": 0, "succeeded": 0, "success_rate": 0.95}

    cursor.execute("SELECT model_id, calls_attempted, calls_succeeded, success_rate FROM model_tool_metrics ORDER BY success_rate DESC")
    rows = cursor.fetchall()
    conn.close()
    return {
        r[0]: {"attempted": r[1], "succeeded": r[2], "success_rate": r[3]}
        for r in rows
    }

# -------------------------------------------------------------
# Sensitive Data Redaction
# -------------------------------------------------------------

SENSITIVE_PATTERNS = [
    (r"(Bearer\s+)[A-Za-z0-9_\-\.]{15,}", r"\1[REDACTED]"),
    (r"(sk-[a-zA-Z0-9_\-]{15,})", r"[REDACTED_API_KEY]"),
    (r"(ghp_[a-zA-Z0-9]{20,})", r"[REDACTED_GITHUB_TOKEN]"),
    (r"(\b(?:password|passwd|secret|api_key|token)\s*[:=]\s*['\"])[^'\"]+(['\"])", r"\1[REDACTED]\2"),
    (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----", r"[PRIVATE_KEY_REDACTED]")
]

def redact_sensitive_data(text: str) -> str:
    """Sanitizes text by masking API keys, bearer tokens, passwords, and private keys."""
    if not text or not isinstance(text, str):
        return text
    import re
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

init_db()
