from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


DEDUP_WINDOW_SECONDS = 20.0


async def ensure_message_ingress_dedupe_table(db) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS message_ingress_dedupe (
            dedupe_key TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_message_ingress_dedupe_created "
        "ON message_ingress_dedupe(created_at)"
    )


def _stable_json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_message_dedupe_key(
    *,
    target_type: str,
    target_id: str,
    sender: str,
    content: str,
    attachments: list[Any] | None = None,
) -> str:
    payload = {
        "target_type": (target_type or "").strip().lower(),
        "target_id": (target_id or "").strip(),
        "sender": (sender or "").strip().lower(),
        "content": (content or "").strip(),
        "attachments": json.loads(_stable_json(attachments or [])),
    }
    raw = _stable_json(payload).encode("utf-8")
    return "msg-ingress-v1:" + hashlib.sha256(raw).hexdigest()


async def reserve_message_ingress(
    db,
    *,
    dedupe_key: str,
    target_type: str,
    target_id: str,
    message_id: str,
    now: float,
    window_seconds: float = DEDUP_WINDOW_SECONDS,
) -> dict[str, Any] | None:
    await ensure_message_ingress_dedupe_table(db)
    cutoff = float(now) - max(1.0, float(window_seconds or DEDUP_WINDOW_SECONDS))
    await db.execute("DELETE FROM message_ingress_dedupe WHERE created_at < ?", (cutoff,))
    try:
        await db.execute(
            "INSERT INTO message_ingress_dedupe (dedupe_key, target_type, target_id, message_id, created_at) "
            "VALUES (?,?,?,?,?)",
            (
                dedupe_key,
                (target_type or "").strip().lower(),
                (target_id or "").strip(),
                (message_id or "").strip(),
                float(now),
            ),
        )
    except sqlite3.IntegrityError:
        cur = await db.execute(
            "SELECT target_type, target_id, message_id, created_at FROM message_ingress_dedupe WHERE dedupe_key=?",
            (dedupe_key,),
        )
        row = await cur.fetchone()
        if not row:
            return {"message_id": ""}
        return {
            "target_type": row[0],
            "target_id": row[1],
            "message_id": row[2],
            "created_at": row[3],
        }
    return None
