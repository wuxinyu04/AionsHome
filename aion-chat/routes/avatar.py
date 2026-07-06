"""
头像上传路由

聊天/朋友圈/陪伴阅读/小剧场等多个页面前端都写死引用
/public/UserIcon.png（用户）和 /public/AIIcon.png（AI）。
本路由保持这两个文件名不变，上传时直接覆盖；浏览器侧靠
版本号（文件 mtime）破缓存，WS 广播 avatar_changed 让已打开的页面实时刷新。
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from config import PUBLIC_DIR
from ws import manager

router = APIRouter(prefix="/api/avatar", tags=["avatar"])

# kind → 文件名映射
_AVATAR_FILES = {
    "user": "UserIcon.png",
    "ai": "AIIcon.png",
    "connor": "codexicon.png",
}

# PNG 文件头（比 content_type 可靠，content_type 浏览器可能不传或传错）
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# 上传后图片会被前端 canvas 转成 PNG 传上来，统一存成 .png
_AVATAR_EXTS = {".png"}


def _avatar_path(kind: str) -> Path:
    name = _AVATAR_FILES.get(kind)
    if not name:
        raise HTTPException(status_code=400, detail=f"未知头像类型：{kind}")
    return PUBLIC_DIR / name


def _default_path(kind: str) -> Path:
    """默认头像备份路径（首次上传时把当前文件备份过来，重置时还原）"""
    name = _AVATAR_FILES.get(kind)
    if not name:
        raise HTTPException(status_code=400, detail=f"未知头像类型：{kind}")
    stem, _, ext = name.rpartition(".")
    return PUBLIC_DIR / f"{stem}.default.{ext}"


def _version_of(path: Path) -> int:
    """用文件 mtime 作版本号，覆盖后会变化，前端据此破缓存"""
    try:
        return int(path.stat().st_mtime * 1000)
    except OSError:
        return 0


def _info(kind: str) -> dict:
    path = _avatar_path(kind)
    return {
        "kind": kind,
        "url": f"/public/{path.name}",
        "version": _version_of(path),
    }


def _backup_default_if_absent(kind: str):
    """首次上传前把当前头像备份成 *.default.png，供"重置默认"还原。"""
    cur = _avatar_path(kind)
    default = _default_path(kind)
    if default.exists():
        return
    if cur.exists():
        default.write_bytes(cur.read_bytes())


@router.get("")
async def get_avatars():
    """返回两个头像的 URL + 版本号，前端启动时拉来破缓存。"""
    return {"avatars": {k: _info(k) for k in _AVATAR_FILES}}


@router.post("/upload")
async def upload_avatar(kind: str = Form(...), file: UploadFile = File(...)):
    """上传头像，覆盖 public/UserIcon.png 或 public/AIIcon.png。

    前端用 canvas 把任意格式图片裁成正方形并转成 PNG 再上传，
    所以这里只接受 PNG。
    """
    if kind not in _AVATAR_FILES:
        raise HTTPException(status_code=400, detail="kind 必须是 user 或 ai")

    content = await file.read()
    if not content.startswith(_PNG_MAGIC):
        raise HTTPException(status_code=400, detail="仅支持 PNG 图片（前端会自动转换）")

    _backup_default_if_absent(kind)
    target = _avatar_path(kind)
    target.write_bytes(content)

    version = _version_of(target)
    # 广播给所有已打开的页面，让它们把头像 src 换成带新版本号的 URL
    await manager.broadcast({
        "type": "avatar_changed",
        "data": {"kind": kind, "version": version},
    })
    return {"ok": True, **_info(kind)}


@router.post("/reset")
async def reset_avatar(kind: str = Form(...)):
    """用首次上传前的备份还原默认头像。从未备份过（没人换过）则不操作。"""
    if kind not in _AVATAR_FILES:
        raise HTTPException(status_code=400, detail="kind 必须是 user 或 ai")

    default = _default_path(kind)
    if not default.exists():
        raise HTTPException(status_code=404, detail="没有默认头像备份（从未换过头像）")

    target = _avatar_path(kind)
    target.write_bytes(default.read_bytes())

    version = _version_of(target)
    await manager.broadcast({
        "type": "avatar_changed",
        "data": {"kind": kind, "version": version},
    })
    return {"ok": True, **_info(kind)}
