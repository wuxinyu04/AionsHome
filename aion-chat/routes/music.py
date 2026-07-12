"""
音乐路由：搜索 + 获取歌曲信息 + 代理推流
"""

import re
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

import httpx

from music import (
    search_songs, get_song_detail, get_audio_url, get_lyrics,
    get_user_playlists, get_playlist_tracks, get_likelist, like_track,
    create_playlist, add_to_playlist, remove_from_playlist, find_playlist_by_name,
)
import playback
from config import SETTINGS


def _netease_uid() -> int | None:
    uid = (SETTINGS.get("netease_uid") or "").strip()
    if not uid:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None

router = APIRouter()

MUSIC_CMD_PATTERN = re.compile(r"\[MUSIC:(.+?)\]")
# AI 音乐管理指令：红心 / 建歌单 / 往歌单加歌
LIKE_CMD_PATTERN = re.compile(r"\[LIKE(?::([^\]]+))?\]")            # [LIKE] 或 [LIKE:歌曲名 歌手名]
PLAYLIST_NEW_PATTERN = re.compile(r"\[PLAYLIST_NEW:([^\]]+)\]")     # [PLAYLIST_NEW:歌单名]
PLAYLIST_ADD_PATTERN = re.compile(r"\[PLAYLIST_ADD:([^\]]+)\]")     # [PLAYLIST_ADD:歌单名] 或 [PLAYLIST_ADD:歌单名|歌曲名]


@router.get("/api/music/search")
async def music_search(q: str = Query(..., min_length=1, max_length=200), limit: int = Query(5, ge=1, le=20)):
    """搜索歌曲"""
    results = search_songs(q, limit=limit)
    return {"songs": results}


@router.get("/api/music/detail/{song_id}")
async def music_detail(song_id: int):
    """获取歌曲详情"""
    info = get_song_detail(song_id)
    if not info:
        return {"error": "歌曲不存在"}
    # 尝试获取在线播放 URL
    info["audio_url"] = get_audio_url(song_id)
    return info


class MusicPlayRequest(BaseModel):
    keyword: str


@router.post("/api/music/play")
async def music_play(body: MusicPlayRequest):
    """AI 点歌：搜索并返回第一个结果的完整信息"""
    results = search_songs(body.keyword, limit=5)
    if not results:
        return {"error": "没有找到相关歌曲", "keyword": body.keyword}
    song = results[0]
    song["audio_url"] = get_audio_url(song["id"])
    song["candidates"] = results[1:]  # 备选
    return song


@router.get("/api/music/lyrics/{song_id}")
async def music_lyrics(song_id: int):
    """获取歌词（带 [mm:ss] 时间戳，前端逐行滚动）"""
    return get_lyrics(song_id)


class NowPlayingRequest(BaseModel):
    song_id: int | None = None
    name: str = ""
    artist: str = ""
    state: str = "playing"
    position: float = 0
    queue_count: int = 0


@router.post("/api/music/now_playing")
async def music_now_playing(body: NowPlayingRequest):
    """前端节流上报当前播放状态，供 context_builder 注入 AI 上下文（"AI 感知"）"""
    if body.song_id is None:
        playback.clear_now_playing()
    else:
        playback.set_now_playing(body.model_dump())
    return {"ok": True}


@router.get("/api/music/now_playing")
async def music_now_playing_get():
    """读取当前播放状态（恢复/其他端读取）"""
    return playback.get_now_playing() or {}


class SharedSongRequest(BaseModel):
    song_id: int
    name: str = ""
    artist: str = ""
    cover: str = ""


@router.post("/api/music/shared")
async def music_shared_add(body: SharedSongRequest):
    """记录一首"一起听过的歌"（去重 + play_count）"""
    playback.log_shared(body.model_dump())
    return {"ok": True}


@router.get("/api/music/shared")
async def music_shared_list(limit: int = Query(50, ge=1, le=500)):
    """读取"一起听过的歌"历史"""
    return {"songs": playback.get_shared(limit=limit)}


# ── 用户曲库：歌单 / 红心 / 歌单管理 ──

@router.get("/api/music/playlists")
async def music_playlists():
    """用户的网易云歌单列表（含「我喜欢的音乐」红心歌单，通常第一个）"""
    uid = _netease_uid()
    if not uid:
        return {"error": "未配置 netease_uid（设置页填网易云 UID）"}
    playlists = get_user_playlists(uid)
    playback.set_playlists_cache(uid, playlists)  # 刷新缓存供 context_builder 注入
    return {"playlists": playlists}


@router.get("/api/music/playlist/{pid}")
async def music_playlist_tracks(pid: int):
    """歌单的全部曲目"""
    return {"songs": get_playlist_tracks(pid)}


@router.get("/api/music/favorites")
async def music_favorites():
    """红心歌单「我喜欢的音乐」的曲目"""
    uid = _netease_uid()
    if not uid:
        return {"error": "未配置 netease_uid"}
    return {"songs": get_likelist(uid)}


@router.post("/api/music/like/{song_id}")
async def music_like(song_id: int, like: bool = True):
    """红心 / 取消红心"""
    ok = like_track(song_id, like)
    return {"ok": ok, "liked": like}


class PlaylistCreateReq(BaseModel):
    name: str


@router.post("/api/music/playlist")
async def music_playlist_create(body: PlaylistCreateReq):
    """创建新歌单"""
    return create_playlist(body.name)


class PlaylistTracksReq(BaseModel):
    track_ids: list[int]


@router.post("/api/music/playlist/{pid}/add")
async def music_playlist_add(pid: int, body: PlaylistTracksReq):
    """往歌单加歌"""
    add_to_playlist(pid, body.track_ids)
    return {"ok": True}


@router.post("/api/music/playlist/{pid}/remove")
async def music_playlist_remove(pid: int, body: PlaylistTracksReq):
    """从歌单删歌"""
    remove_from_playlist(pid, body.track_ids)
    return {"ok": True}


@router.get("/api/music/playlist-by-name")
async def music_playlist_by_name(name: str = Query(..., min_length=1, max_length=100)):
    """按名查歌单（给 AI / 前端按歌单名定位）"""
    uid = _netease_uid()
    if not uid:
        return {"error": "未配置 netease_uid"}
    p = find_playlist_by_name(uid, name)
    return p or {"error": "歌单不存在"}


@router.get("/api/music/stream/{song_id}")
async def music_stream(song_id: int):
    """代理推流：后端实时获取网易云 CDN URL 并转发音频流给前端"""
    url = get_audio_url(song_id)
    if not url:
        return Response(content='{"error":"无法获取播放地址，可能是VIP歌曲且未登录"}',
                        status_code=404, media_type="application/json")

    async def _stream():
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with client.stream("GET", url, headers={
                "Referer": "https://music.163.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    # 猜测 Content-Type
    ct = "audio/mpeg"
    if ".m4a" in url or ".aac" in url:
        ct = "audio/mp4"
    elif ".flac" in url:
        ct = "audio/flac"

    return StreamingResponse(_stream(), media_type=ct, headers={
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
    })
