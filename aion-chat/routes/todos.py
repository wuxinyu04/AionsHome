"""
待办路由：列表 / 手动添加 / 完成 / 编辑 / 删除
"""

import time
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

import aiosqlite
from database import get_db
from todos import get_todo_origin_name
from ws import manager

router = APIRouter()

VALID_PRIORITIES = ("low", "normal", "high")
_ORDER = "CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, due_at, created_at DESC"


class TodoCreate(BaseModel):
    content: str
    priority: str = "normal"
    category: str = ""
    due_at: str = ""


class TodoUpdate(BaseModel):
    content: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None   # 'done' / 'pending'


@router.get("/api/todos")
async def list_todos(status: Optional[str] = Query(None)):
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        if status in ("pending", "done"):
            cur = await db.execute(f"SELECT * FROM todos WHERE status=? ORDER BY {_ORDER}", (status,))
        else:
            cur = await db.execute(f"SELECT * FROM todos ORDER BY {_ORDER}")
        rows = [dict(r) for r in await cur.fetchall()]
    for row in rows:
        row["origin_name"] = get_todo_origin_name(row.get("origin"))
    return rows


@router.post("/api/todos")
async def create_todo(body: TodoCreate):
    tid = f"todo_{int(time.time()*1000)}"
    now = time.time()
    priority = body.priority if body.priority in VALID_PRIORITIES else "normal"
    due_at = body.due_at.replace("T", " ") if body.due_at else ""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO todos (id, content, priority, category, status, due_at, origin, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (tid, body.content, priority, body.category, "pending", due_at, "user", now),
        )
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})
    return {
        "id": tid, "content": body.content, "priority": priority,
        "category": body.category, "status": "pending", "due_at": due_at,
        "origin": "user", "created_at": now, "completed_at": None,
        "origin_name": get_todo_origin_name("user"),
    }


@router.patch("/api/todos/{todo_id}")
async def update_todo(todo_id: str, body: TodoUpdate):
    sets = []
    params = []
    if body.status == "done":
        sets.append("status=?"); sets.append("completed_at=?")
        params.append("done"); params.append(time.time())
    elif body.status == "pending":
        sets.append("status=?"); sets.append("completed_at=NULL")
        params.append("pending")
    if body.content is not None:
        sets.append("content=?"); params.append(body.content)
    if body.priority is not None and body.priority in VALID_PRIORITIES:
        sets.append("priority=?"); params.append(body.priority)
    if body.category is not None:
        sets.append("category=?"); params.append(body.category)
    if not sets:
        async with get_db() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM todos WHERE id=?", (todo_id,))
            row = await cur.fetchone()
        return dict(row) if row else {"ok": False, "error": "not found"}
    params.append(todo_id)
    async with get_db() as db:
        await db.execute(f"UPDATE todos SET {', '.join(sets)} WHERE id=?", params)
        await db.commit()
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM todos WHERE id=?", (todo_id,))
        row = await cur.fetchone()
    await manager.broadcast({"type": "todos_changed"})
    if not row:
        return {"ok": False, "error": "not found"}
    row = dict(row)
    row["origin_name"] = get_todo_origin_name(row.get("origin"))
    return row


@router.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM todos WHERE id=?", (todo_id,))
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})
    return {"ok": True}
