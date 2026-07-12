"""
待办清单管理器
- 清单型任务：增删改查 + 勾选完成，不自动到点响（要响用日程闹铃）
- AI 通过 [TODO:...] 等文本指令操作，指令解析在 AI 回复完成后调用
- 当前未完成待办注入 prompt，让 AI 能主动跟进
- 所有待办持久化在 SQLite todos 表，重启后自动恢复
"""

import json, time, logging, re

import aiosqlite

from config import DB_PATH, load_worldbook
from database import get_db
from ws import manager

log = logging.getLogger("todos")


# ── 文本指令正则 ──────────────────────────────────
# [TODO:内容] / [TODO:内容|优先级] / [TODO:内容|优先级|分类]
TODO_CMD = re.compile(r"\[TODO:([^\]]+)\]")
TODO_DONE_CMD = re.compile(r"\[TODO_DONE:(.+?)\]")
TODO_UNDO_CMD = re.compile(r"\[TODO_UNDO:(.+?)\]")
TODO_DEL_CMD = re.compile(r"\[TODO_DEL:(.+?)\]")
# [TODO_EDIT:id|新内容]
TODO_EDIT_CMD = re.compile(r"\[TODO_EDIT:(.+?)\|([^\]]+)\]")

VALID_PRIORITIES = ("low", "normal", "high")


def get_todo_origin_name(origin: str | None) -> str:
    """返回待办创建者的显示名（与日程一致）"""
    wb = load_worldbook()
    origin = (origin or "aion").strip().lower()
    if origin == "connor":
        try:
            from chatroom import load_chatroom_config
            cfg = load_chatroom_config()
            return (cfg.get("connor_name") or "AI").strip() or "AI"
        except Exception:
            return "AI"
    if origin == "user":
        return (wb.get("user_name") or "用户").strip() or "用户"
    return (wb.get("ai_name") or "AI").strip() or "AI"


# ── 指令解析（在 AI 回复完成后调用） ──────────────
async def process_todo_commands(
    full_text: str,
    conv_id: str | None = None,
    origin: str = "aion",
    origin_room_id: str = "",
    after_msg_id: str | None = None,
) -> str:
    """
    检测并处理 AI 回复中的待办指令，返回 strip 后的文本。
    即使 AI 格式有误也不抛异常，静默跳过。
    origin: 'aion' | 'connor' | 'user'
    """
    text = full_text
    actor_name = get_todo_origin_name(origin)

    # [TODO:内容] / [TODO:内容|优先级] / [TODO:内容|优先级|分类]
    for match in TODO_CMD.finditer(full_text):
        try:
            raw = match.group(1).strip()
            parts = raw.split("|")
            content = parts[0].strip()
            priority = parts[1].strip() if len(parts) > 1 else "normal"
            if priority not in VALID_PRIORITIES:
                priority = "normal"
            category = parts[2].strip() if len(parts) > 2 else ""
            if content:
                await _add_todo(content, priority=priority, category=category, origin=origin)
                cat_str = f"（{category}）" if category else ""
                if conv_id:
                    await _sys_msg(conv_id, f"【{actor_name}】添加了待办：{content}{cat_str}", after_msg_id=after_msg_id)
        except Exception as e:
            log.error("TODO processing error: %s", e)
    text = TODO_CMD.sub("", text)

    # [TODO_DONE:id]
    for match in TODO_DONE_CMD.finditer(full_text):
        try:
            tid = match.group(1).strip()
            if tid:
                info = await _get_todo_info(tid)
                await _done_todo(tid)
                if conv_id and info:
                    await _sys_msg(conv_id, f"【{actor_name}】完成了待办：{info['content']}", after_msg_id=after_msg_id)
        except Exception as e:
            log.error("TODO_DONE processing error: %s", e)
    text = TODO_DONE_CMD.sub("", text)

    # [TODO_UNDO:id]
    for match in TODO_UNDO_CMD.finditer(full_text):
        try:
            tid = match.group(1).strip()
            if tid:
                info = await _get_todo_info(tid)
                await _undo_todo(tid)
                if conv_id and info:
                    await _sys_msg(conv_id, f"【{actor_name}】重新打开了待办：{info['content']}", after_msg_id=after_msg_id)
        except Exception as e:
            log.error("TODO_UNDO processing error: %s", e)
    text = TODO_UNDO_CMD.sub("", text)

    # [TODO_DEL:id]
    for match in TODO_DEL_CMD.finditer(full_text):
        try:
            tid = match.group(1).strip()
            if tid:
                info = await _get_todo_info(tid)
                await _del_todo(tid)
                if conv_id and info:
                    await _sys_msg(conv_id, f"【{actor_name}】删除了待办：{info['content']}", after_msg_id=after_msg_id)
        except Exception as e:
            log.error("TODO_DEL processing error: %s", e)
    text = TODO_DEL_CMD.sub("", text)

    # [TODO_EDIT:id|新内容]
    for match in TODO_EDIT_CMD.finditer(full_text):
        try:
            tid = match.group(1).strip()
            new_content = match.group(2).strip()
            if tid and new_content:
                await _edit_todo(tid, new_content)
                if conv_id:
                    await _sys_msg(conv_id, f"【{actor_name}】修改了待办 #{tid}：{new_content}", after_msg_id=after_msg_id)
        except Exception as e:
            log.error("TODO_EDIT processing error: %s", e)
    text = TODO_EDIT_CMD.sub("", text)

    return text.strip()


async def _sys_msg(conv_id: str, content: str, after_msg_id: str | None = None):
    """插入一条系统消息并广播（与日程 _sys_msg 一致）"""
    now = time.time()
    msg_id = f"msg_{int(now*1000)}_st"
    order_atts = [{"type": "system_notice_order", "after_msg_id": after_msg_id}] if after_msg_id else []
    att_json = json.dumps(order_atts, ensure_ascii=False) if order_atts else "[]"
    async with get_db() as db:
        await db.execute(
            "INSERT INTO messages (id, conv_id, role, content, created_at, attachments) VALUES (?,?,?,?,?,?)",
            (msg_id, conv_id, "system", content, now, att_json),
        )
        await db.commit()
    msg = {"id": msg_id, "conv_id": conv_id, "role": "system",
           "content": content, "created_at": now, "attachments": order_atts}
    await manager.broadcast({"type": "msg_created", "data": msg})


# ── CRUD ──────────────────────────────────────────
async def _add_todo(content: str, priority: str = "normal", category: str = "",
                    due_at: str = "", origin: str = "user") -> str:
    tid = f"todo_{int(time.time()*1000)}"
    now = time.time()
    due_at = due_at.replace("T", " ") if due_at else ""
    if priority not in VALID_PRIORITIES:
        priority = "normal"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO todos (id, content, priority, category, status, due_at, origin, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (tid, content, priority, category, "pending", due_at, origin, now),
        )
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})
    return tid


async def _done_todo(tid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE todos SET status='done', completed_at=? WHERE id=?", (time.time(), tid))
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})


async def _undo_todo(tid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE todos SET status='pending', completed_at=NULL WHERE id=?", (tid,))
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})


async def _del_todo(tid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM todos WHERE id=?", (tid,))
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})


async def _edit_todo(tid: str, new_content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE todos SET content=? WHERE id=?", (new_content, tid))
        await db.commit()
    await manager.broadcast({"type": "todos_changed"})


async def _get_todo_info(tid: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT content, status FROM todos WHERE id=?", (tid,))
        row = await cur.fetchone()
        return dict(row) if row else None


# ── 获取待办（供 prompt 注入） ────────────────────
async def get_active_todos() -> list[dict]:
    """未完成待办，按优先级 → 截止时间 → 创建时间排序"""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, content, priority, category, status, due_at, origin, created_at FROM todos "
            "WHERE status='pending' "
            "ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, due_at, created_at"
        )
        return [dict(r) for r in await cur.fetchall()]


def build_todo_prompt(todos: list[dict]) -> str:
    """构建注入 prompt 的待办列表文本"""
    if not todos:
        return "暂无待办"
    priority_map = {"high": ("🔴", "高"), "normal": ("🟡", "中"), "low": ("⚪", "低")}
    lines = []
    for t in todos:
        icon, label = priority_map.get(t["priority"], ("🟡", "中"))
        origin_name = get_todo_origin_name(t.get("origin"))
        due = f" 截止{t['due_at'].replace('T', ' ')}" if t.get("due_at") else ""
        cat = f" [{t['category']}]" if t.get("category") else ""
        lines.append(f"- [ ] {icon} 【{origin_name}】#{t['id']}: {t['content']}{cat}{due}")
    return "\n".join(lines)
