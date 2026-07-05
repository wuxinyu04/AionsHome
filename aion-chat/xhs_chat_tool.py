"""聊天里 AI 自主调用小红书搜索的标记协议 + 多轮续写。

AI 在回复里输出 <xhs_search>关键词</xhs_search>，系统检测到后去小红书站内搜索，
结果以 <xhs_search_result>...</xhs_search_result> 塞回 history，再让模型续写。
标记本身不发给前端（流式过滤），只在搜索时发一条 "🔍 正在搜索…" 状态。
"""
import re

from ai_providers import stream_ai, CLI_STATUS_PREFIX


XHS_SEARCH_PATTERN = re.compile(r"<xhs_search>(.+?)</xhs_search>", re.DOTALL)

XHS_TOOL_PROMPT = (
    "[工具能力·小红书站内搜索]\n"
    "当你需要在小红书站内搜索笔记时（例如用户让你找头像、找攻略、查某个话题的帖子、看小红书上有什么），"
    "可以在回复里输出 <xhs_search>关键词</xhs_search>，系统会自动去小红书站内搜索，"
    "结果会以 <xhs_search_result>...</xhs_search_result> 形式返回给你，你再基于结果继续回复用户。\n"
    "规则：\n"
    "- 一次只搜一个关键词，放在一个 <xhs_search> 标记里\n"
    "- 标记本身用户看不到（系统会隐藏），你只需自然地说一句\"我去搜一下\"之类，然后输出标记\n"
    "- 搜索结果回来后，基于结果用你自己的话整理给用户，不要原样贴 noteId\n"
    "- 用户没要求搜索时不要乱搜\n"
    "- 小红书 cookie 没配置时结果会提示无法搜索，这时告诉用户去 /xhs-lite 页面配置 cookie"
)

_MAX_TOOL_ROUNDS = 3


class _XhsMarkerFilter:
    """流式过滤 <xhs_search>...</xhs_search>，正确处理标记跨 chunk 的情况。

    feed(chunk) 返回该 chunk 里应该让前端看到的可见部分（标记被丢弃）。
    flush() 在流结束时调用，返回剩余未确定的可见文本（未闭合标记会被丢弃）。
    """

    OPEN = "<xhs_search>"
    CLOSE = "</xhs_search>"

    def __init__(self):
        self._buf = ""        # 累积的原始文本（含标记）
        self._emit = 0        # 已决定输出的位置
        self._in_marker = False

    def feed(self, chunk: str) -> str:
        self._buf += chunk
        out = []
        while True:
            if not self._in_marker:
                idx = self._buf.find(self.OPEN, self._emit)
                if idx == -1:
                    safe_end = self._safe_emit_end()
                    if safe_end > self._emit:
                        out.append(self._buf[self._emit:safe_end])
                        self._emit = safe_end
                    break
                if idx > self._emit:
                    out.append(self._buf[self._emit:idx])
                self._emit = idx + len(self.OPEN)
                self._in_marker = True
            else:
                idx = self._buf.find(self.CLOSE, self._emit)
                if idx == -1:
                    break  # 等待更多 chunk 闭合
                # 丢弃标记内容
                self._emit = idx + len(self.CLOSE)
                self._in_marker = False
        return "".join(out)

    def _safe_emit_end(self) -> int:
        """返回可安全输出的位置：_buf 末尾若是 OPEN 的前缀，保留它不输出（等下个 chunk 判断）。"""
        max_check = min(len(self.OPEN) - 1, len(self._buf) - self._emit)
        for k in range(max_check, 0, -1):
            tail = self._buf[len(self._buf) - k:]
            if self.OPEN.startswith(tail):
                return len(self._buf) - k
        return len(self._buf)

    def flush(self) -> str:
        if self._in_marker:
            # 未闭合标记，丢弃
            self._emit = len(self._buf)
            return ""
        if self._emit < len(self._buf):
            rest = self._buf[self._emit:]
            self._emit = len(self._buf)
            return rest
        return ""


async def _do_xhs_search(keyword: str) -> str:
    """调用 xhs_lite worker 搜索小红书站内笔记，返回格式化文本。"""
    import xhs_lite

    cfg = xhs_lite.load_config()
    cookie = (cfg.get("cookie") or "").strip()
    if not cookie:
        return "小红书 cookie 未配置，无法搜索。请先在 /xhs-lite 页面配置 cookie。"
    try:
        data = await xhs_lite._run_worker(
            "search",
            {"keyword": keyword, "page": 1, "sort_by": "general"},
            cookie=cookie,
            timeout=90,
        )
        notes = xhs_lite._extract_notes(data)
        if not notes:
            return f"没有搜到「{keyword}」相关的笔记。"
        lines = []
        for n in notes[:8]:
            title = (n.get("title") or "无标题").strip()
            author = (n.get("author") or "").strip()
            likes = n.get("likes") or 0
            note_id = n.get("note_id") or ""
            desc = (n.get("desc") or "").strip()[:300]
            lines.append(f"- 《{title}》 作者:{author} 赞:{likes} noteId:{note_id} 摘:{desc}")
        return f"搜到 {len(notes)} 条「{keyword}」相关笔记：\n" + "\n".join(lines)
    except Exception as e:
        return f"搜索失败：{e}"


async def stream_ai_with_xhs_tool(history, model_key, usage_meta, *, max_tokens, cancel_event):
    """包住 stream_ai：支持 <xhs_search> 标记触发小红书搜索 + 多轮续写。

    yield 两类 chunk（与 stream_ai 接口一致，上层无需改处理逻辑）：
    - CLI_STATUS_PREFIX + "..."：状态行（含 "🔍 正在搜索..."），上层转 cli_status 事件，不进正文
    - 可见文本：正常回复内容（标记已过滤）
    """
    history = list(history)  # 浅拷贝，避免多轮 append 污染调用方的 history
    for _ in range(_MAX_TOOL_ROUNDS):
        marker_filter = _XhsMarkerFilter()
        round_text = ""
        async for chunk in stream_ai(history, model_key, usage_meta, max_tokens=max_tokens, cancel_event=cancel_event):
            if cancel_event and cancel_event.is_set():
                return
            if isinstance(chunk, str) and chunk.startswith(CLI_STATUS_PREFIX):
                yield chunk
                continue
            round_text += chunk
            visible = marker_filter.feed(chunk)
            if visible:
                yield visible
        tail = marker_filter.flush()
        if tail:
            yield tail

        matches = XHS_SEARCH_PATTERN.findall(round_text)
        if not matches:
            return

        # 有标记 → 执行搜索，结果塞回 history，下一轮让模型基于结果续写
        history.append({"role": "assistant", "content": round_text})
        for kw in matches:
            kw = kw.strip()
            if not kw:
                continue
            yield CLI_STATUS_PREFIX + f"🔍 正在搜索小红书：{kw}…"
            result_text = await _do_xhs_search(kw)
            history.append({
                "role": "user",
                "content": f'<xhs_search_result keyword="{kw}">\n{result_text}\n</xhs_search_result>',
            })
        # 循环到下一轮 stream_ai
