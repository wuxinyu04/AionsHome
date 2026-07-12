"""
设置、世界书、模型列表、TTS 路由
"""

import json

from fastapi import APIRouter
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

import httpx

from config import SETTINGS, save_settings, get_key, get_sentinel_config, load_worldbook, save_worldbook, load_chat_status, TTS_CACHE_DIR, TTS_CACHE_MAX_BYTES, THEATER_TTS_CACHE_DIR, normalize_custom_model_routes, normalize_antigravity_models, refresh_custom_models, iter_visible_models
from tts import cleanup_tts_cache_dir
from ws import manager

router = APIRouter()

RELAY_MODEL_PROVIDERS = {"aipro", "custom_openai"}

# ── 模型列表 ──────────────────────────────────────
@router.get("/api/models")
async def list_models():
    rows = [
        {
            "key": k,
            "provider": v["provider"],
            "custom": v.get("provider") == "custom_openai",
            "route_name": v.get("route_name", ""),
        }
        for k, v in iter_visible_models()
    ]
    return sorted(rows, key=lambda item: 1 if item["provider"] in RELAY_MODEL_PROVIDERS else 0)

# ── 设置 ──────────────────────────────────────────
class SettingsUpdate(BaseModel):
    gemini_key: Optional[str] = None
    siliconflow_key: Optional[str] = None
    gemini_free_key: Optional[str] = None
    aipro_key: Optional[str] = None
    senseaudio_key: Optional[str] = None
    minimax_key: Optional[str] = None
    tts_provider: Optional[str] = None
    netease_music_u: Optional[str] = None
    netease_uid: Optional[str] = None
    sentinel_base_url: Optional[str] = None
    sentinel_api_key: Optional[str] = None
    sentinel_model: Optional[str] = None
    embedding_base_url: Optional[str] = None
    embedding_api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    luckin_mcp_enabled: Optional[bool] = None
    luckin_mcp_token: Optional[str] = None
    luckin_default_longitude: Optional[str] = None
    luckin_default_latitude: Optional[str] = None
    luckin_default_shop_keyword: Optional[str] = None
    custom_model_routes: Optional[list[Dict[str, Any]]] = None
    antigravity_models: Optional[list[Dict[str, Any]]] = None

class HomeLayoutUpdate(BaseModel):
    version: Optional[int] = 2
    positions: Dict[str, Any] = Field(default_factory=dict)

def _normalize_home_layout(payload: Any) -> Dict[str, Any]:
    positions = payload.get("positions", {}) if isinstance(payload, dict) else {}
    normalized: Dict[str, int] = {}
    if isinstance(positions, dict):
        for app_id, cell in positions.items():
            if not isinstance(app_id, str):
                continue
            try:
                cell_index = int(cell)
            except (TypeError, ValueError):
                continue
            if 0 <= cell_index <= 4095:
                normalized[app_id] = cell_index
    return {"version": 2, "positions": normalized}

@router.get("/api/home/layout")
async def get_home_layout():
    return _normalize_home_layout(SETTINGS.get("home_layout", {}))

@router.put("/api/home/layout")
async def update_home_layout(body: HomeLayoutUpdate):
    payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    layout = _normalize_home_layout(payload)
    SETTINGS["home_layout"] = layout
    save_settings(SETTINGS)
    return {"ok": True, "layout": layout}

@router.get("/api/settings")
async def get_settings():
    def mask(k):
        if not k or len(k) < 8:
            return k
        return k[:4] + "*" * (len(k) - 8) + k[-4:]
    return {
        "gemini_key": SETTINGS.get("gemini_key", ""),
        "siliconflow_key": SETTINGS.get("siliconflow_key", ""),
        "gemini_free_key": SETTINGS.get("gemini_free_key", ""),
        "aipro_key": SETTINGS.get("aipro_key", ""),
        "senseaudio_key": SETTINGS.get("senseaudio_key", ""),
        "minimax_key": SETTINGS.get("minimax_key", ""),
        "tts_provider": SETTINGS.get("tts_provider", "siliconflow"),
        "netease_music_u": SETTINGS.get("netease_music_u", ""),
        "netease_uid": SETTINGS.get("netease_uid", ""),
        "sentinel_base_url": SETTINGS.get("sentinel_base_url", ""),
        "sentinel_api_key": SETTINGS.get("sentinel_api_key", ""),
        "sentinel_model": SETTINGS.get("sentinel_model", ""),
        "embedding_base_url": SETTINGS.get("embedding_base_url", ""),
        "embedding_api_key": SETTINGS.get("embedding_api_key", ""),
        "embedding_model": SETTINGS.get("embedding_model", ""),
        "luckin_mcp_enabled": SETTINGS.get("luckin_mcp_enabled", False),
        "luckin_mcp_token": SETTINGS.get("luckin_mcp_token", ""),
        "luckin_default_longitude": SETTINGS.get("luckin_default_longitude", ""),
        "luckin_default_latitude": SETTINGS.get("luckin_default_latitude", ""),
        "luckin_default_shop_keyword": SETTINGS.get("luckin_default_shop_keyword", ""),
        "custom_model_routes": normalize_custom_model_routes(SETTINGS.get("custom_model_routes")),
        "antigravity_models": normalize_antigravity_models(SETTINGS.get("antigravity_models")),
        "gemini_key_masked": mask(SETTINGS.get("gemini_key", "")),
        "siliconflow_key_masked": mask(SETTINGS.get("siliconflow_key", "")),
        "gemini_free_key_masked": mask(SETTINGS.get("gemini_free_key", "")),
        "aipro_key_masked": mask(SETTINGS.get("aipro_key", "")),
        "senseaudio_key_masked": mask(SETTINGS.get("senseaudio_key", "")),
        "minimax_key_masked": mask(SETTINGS.get("minimax_key", "")),
        "netease_music_u_masked": mask(SETTINGS.get("netease_music_u", "")),
        "sentinel_api_key_masked": mask(SETTINGS.get("sentinel_api_key", "")),
        "embedding_api_key_masked": mask(SETTINGS.get("embedding_api_key", "")),
    }

@router.put("/api/settings")
async def update_settings(body: SettingsUpdate):
    luckin_changed = False
    if body.gemini_key is not None:
        SETTINGS["gemini_key"] = body.gemini_key
    if body.siliconflow_key is not None:
        SETTINGS["siliconflow_key"] = body.siliconflow_key
    if body.gemini_free_key is not None:
        SETTINGS["gemini_free_key"] = body.gemini_free_key
    if body.aipro_key is not None:
        SETTINGS["aipro_key"] = body.aipro_key
    if body.senseaudio_key is not None:
        SETTINGS["senseaudio_key"] = body.senseaudio_key
    if body.minimax_key is not None:
        SETTINGS["minimax_key"] = body.minimax_key
    if body.tts_provider is not None:
        SETTINGS["tts_provider"] = body.tts_provider
    if body.sentinel_base_url is not None:
        SETTINGS["sentinel_base_url"] = body.sentinel_base_url
    if body.sentinel_api_key is not None:
        SETTINGS["sentinel_api_key"] = body.sentinel_api_key
    if body.sentinel_model is not None:
        SETTINGS["sentinel_model"] = body.sentinel_model
    if body.embedding_base_url is not None:
        SETTINGS["embedding_base_url"] = body.embedding_base_url
    if body.embedding_api_key is not None:
        SETTINGS["embedding_api_key"] = body.embedding_api_key
    if body.embedding_model is not None:
        SETTINGS["embedding_model"] = body.embedding_model
    if body.luckin_mcp_enabled is not None:
        luckin_changed = luckin_changed or SETTINGS.get("luckin_mcp_enabled") != body.luckin_mcp_enabled
        SETTINGS["luckin_mcp_enabled"] = body.luckin_mcp_enabled
    if body.luckin_mcp_token is not None:
        luckin_changed = luckin_changed or SETTINGS.get("luckin_mcp_token", "") != body.luckin_mcp_token
        SETTINGS["luckin_mcp_token"] = body.luckin_mcp_token
    if body.luckin_default_longitude is not None:
        SETTINGS["luckin_default_longitude"] = body.luckin_default_longitude
    if body.luckin_default_latitude is not None:
        SETTINGS["luckin_default_latitude"] = body.luckin_default_latitude
    if body.luckin_default_shop_keyword is not None:
        SETTINGS["luckin_default_shop_keyword"] = body.luckin_default_shop_keyword
    if body.custom_model_routes is not None:
        SETTINGS["custom_model_routes"] = normalize_custom_model_routes(body.custom_model_routes)
        refresh_custom_models()
    if body.antigravity_models is not None:
        SETTINGS["antigravity_models"] = normalize_antigravity_models(body.antigravity_models)
        refresh_custom_models()
    if body.netease_music_u is not None:
        old_mu = SETTINGS.get("netease_music_u", "")
        SETTINGS["netease_music_u"] = body.netease_music_u
        if body.netease_music_u != old_mu:
            # MUSIC_U 变更，重新登录 pyncm
            try:
                from music import reload_login
                reload_login()
            except Exception:
                pass
    if body.netease_uid is not None:
        SETTINGS["netease_uid"] = body.netease_uid
    save_settings(SETTINGS)
    if luckin_changed:
        try:
            from luckin import LUCKIN_SERVER_NAME
            from mcp_client import mcp_manager
            await mcp_manager.disconnect(LUCKIN_SERVER_NAME)
        except Exception:
            pass
    return {"ok": True}

# ── 温度设置 ──────────────────────────────────────
class TempUpdate(BaseModel):
    temperature: float

@router.put("/api/settings/temperature")
async def update_temperature(body: TempUpdate):
    SETTINGS["temperature"] = body.temperature
    save_settings(SETTINGS)
    return {"ok": True}

# ── 视频通话开关 ──────────────────────────────────
@router.get("/api/settings/video-call")
async def get_video_call_setting():
    return {"video_call_enabled": SETTINGS.get("video_call_enabled", True)}

class VideoCallToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/video-call")
async def update_video_call_setting(body: VideoCallToggle):
    SETTINGS["video_call_enabled"] = body.enabled
    save_settings(SETTINGS)
    return {"ok": True, "video_call_enabled": body.enabled}

# ── AI 生图开关 ───────────────────────────────────
@router.get("/api/settings/image-gen")
async def get_image_gen_setting():
    return {"image_gen_enabled": SETTINGS.get("image_gen_enabled", False)}

class ImageGenToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/image-gen")
async def update_image_gen_setting(body: ImageGenToggle):
    SETTINGS["image_gen_enabled"] = body.enabled
    save_settings(SETTINGS)
    return {"ok": True, "image_gen_enabled": body.enabled}

# ── CLI 工具调用开关（Gemini CLI / Antigravity CLI） ─────────────────
# ── AI song generation toggle ─────────────────────────────────
@router.get("/api/settings/song-gen")
async def get_song_gen_setting():
    return {"song_gen_enabled": SETTINGS.get("song_gen_enabled", False)}

class SongGenToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/song-gen")
async def update_song_gen_setting(body: SongGenToggle):
    SETTINGS["song_gen_enabled"] = body.enabled
    save_settings(SETTINGS)
    return {"ok": True, "song_gen_enabled": body.enabled}

@router.get("/api/settings/gemini-cli-tools")
async def get_gemini_cli_tools_setting():
    return {"gemini_cli_tools_enabled": SETTINGS.get("gemini_cli_tools_enabled", False)}

class GeminiCliToolsToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/gemini-cli-tools")
async def update_gemini_cli_tools_setting(body: GeminiCliToolsToggle):
    SETTINGS["gemini_cli_tools_enabled"] = body.enabled
    save_settings(SETTINGS)
    return {"ok": True, "gemini_cli_tools_enabled": body.enabled}

# ── 桌宠开关 ──────────────────────────────────────
@router.get("/api/settings/pet")
async def get_pet_setting():
    return {"pet_enabled": SETTINGS.get("pet_enabled", False)}

class PetToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/pet")
async def update_pet_setting(body: PetToggle):
    SETTINGS["pet_enabled"] = body.enabled
    save_settings(SETTINGS)
    return {"ok": True, "pet_enabled": body.enabled}

# ── 健康数据分享开关 ──────────────────────────────
@router.get("/api/settings/health-share")
async def get_health_share_setting():
    return {"health_share_enabled": SETTINGS.get("health_share_enabled", False)}

class HealthShareToggle(BaseModel):
    enabled: bool

@router.put("/api/settings/health-share")
async def update_health_share_setting(body: HealthShareToggle):
    SETTINGS["health_share_enabled"] = body.enabled
    save_settings(SETTINGS)
    await manager.broadcast({
        "type": "health_share_changed",
        "data": {"health_share_enabled": body.enabled},
    })
    await manager.broadcast({
        "type": "capability_config_changed",
        "data": {"key": "health_context", "enabled": body.enabled},
    })
    return {"ok": True, "health_share_enabled": body.enabled}

# ── 世界书 ────────────────────────────────────────
class WorldBookUpdate(BaseModel):
    ai_persona: str = ""
    user_persona: str = ""
    system_prompt: str = ""
    system_prompt_enabled: bool = True
    ai_name: str = "AI"
    user_name: str = "你"
    persona_schema_version: int = 1
    ai_persona_sections: Dict[str, str] = Field(default_factory=dict)
    user_persona_sections: Dict[str, str] = Field(default_factory=dict)
    creative_rules: str = ""
    persona_section_locks: Dict[str, Any] = Field(default_factory=dict)
    persona_evolution_enabled: bool = False

@router.get("/api/worldbook")
async def get_worldbook():
    return load_worldbook()

@router.put("/api/worldbook")
async def update_worldbook(body: WorldBookUpdate):
    current = load_worldbook()
    payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    current.update(payload)
    save_worldbook(current)
    return {"ok": True}

# ── 聊天状态 ──────────────────────────────────────
@router.get("/api/chat_status")
async def get_chat_status_api():
    return load_chat_status()

# ── TTS 语音合成 ──────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    voice: str = ""
    msg_id: Optional[str] = None

@router.post("/api/tts")
async def tts_synthesize(body: TTSRequest):
    key = get_key("siliconflow")
    if not key:
        return Response(content=json.dumps({"error": "未配置硅基流动 API Key"}), status_code=400, media_type="application/json")
    if not body.text.strip():
        return Response(content=json.dumps({"error": "文本不能为空"}), status_code=400, media_type="application/json")
    if not body.voice:
        return Response(content=json.dumps({"error": "未选择语音"}), status_code=400, media_type="application/json")
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/audio/speech",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "FunAudioLLM/CosyVoice2-0.5B",
                    "input": body.text.strip(),
                    "voice": body.voice,
                    "response_format": "mp3",
                    "speed": 1.0,
                    "gain": 0
                }
            )
        if resp.status_code != 200:
            return Response(content=json.dumps({"error": f"TTS API 错误: {resp.status_code}"}), status_code=502, media_type="application/json")
        audio_data = resp.content
        # 如果提供了 msg_id，将音频缓存到服务器
        if body.msg_id:
            import re
            safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', body.msg_id)
            if safe_id:
                cache_path = TTS_CACHE_DIR / f"{safe_id}.mp3"
                cache_path.write_bytes(audio_data)
                cleanup_tts_cache_dir(TTS_CACHE_DIR, TTS_CACHE_MAX_BYTES, skip={cache_path})
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        return Response(content=json.dumps({"error": str(e)}), status_code=500, media_type="application/json")

@router.head("/api/tts/audio/{msg_id}")
@router.get("/api/tts/audio/{msg_id}")
async def tts_audio(msg_id: str):
    import re
    safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', msg_id)
    if not safe_id:
        return Response(status_code=404)
    cache_path = TTS_CACHE_DIR / f"{safe_id}.mp3"
    if not cache_path.exists():
        return Response(status_code=404)
    return FileResponse(cache_path, media_type="audio/mpeg", filename=f"{safe_id}.mp3")

@router.head("/api/theater/tts/audio/{msg_id}")
@router.get("/api/theater/tts/audio/{msg_id}")
async def theater_tts_audio(msg_id: str):
    import re
    safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', msg_id)
    if not safe_id:
        return Response(status_code=404)
    cache_path = THEATER_TTS_CACHE_DIR / f"{safe_id}.mp3"
    if not cache_path.exists():
        return Response(status_code=404)
    return FileResponse(cache_path, media_type="audio/mpeg", filename=f"{safe_id}.mp3")

# CosyVoice2 系统预置音色。硅基的 /v1/audio/voice/list 只返回用户克隆音色，
# 不含系统音色——账号没克隆过时返回空，导致前端音色下拉没选项、TTS 无法触发。
# 这里作为兜底，列表为空时补上这些免费可用的系统音色（实测 alex/claire 等可直接合成）。
_COSYVOICE2_SYSTEM_VOICES = [
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:alex", "name": "Alex（男）"},
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:benjamin", "name": "Benjamin（男）"},
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:charles", "name": "Charles（男）"},
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:claire", "name": "Claire（女）"},
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:david", "name": "David（男）"},
    {"uri": "FunAudioLLM/CosyVoice2-0.5B:diana", "name": "Diana（女）"},
]

# SenseAudio Free 版（实名后默认）可调用的普通音色。当 /v1/get_voice 接口失败或返回空时兜底。
_SENSEAUDIO_FREE_VOICES = [
    {"uri": "child_0001_a", "customName": "可爱萌娃（开心）"},
    {"uri": "child_0001_b", "customName": "可爱萌娃（平稳）"},
    {"uri": "male_0004_a", "customName": "儒雅道长（平稳）"},
    {"uri": "male_0018_a", "customName": "沙哑青年（深情）"},
]


# SenseAudio Free 版（实名后默认）可直接调用的 voice_id 集合（来自官方文档音色列表页）。
# 其他音色可能需要 Plus/Pro 等更高套餐，调了会报权限错误。
_SENSEAUDIO_FREE_VOICE_IDS = {"child_0001_a", "child_0001_b", "male_0004_a", "male_0018_a"}


# MiniMax 系统音色 —— 男友陪伴向精选（8 个中文男声）
# 砍到只保留中文男声，所有显示名都是中文，下拉一目了然不再翻不到。
# 后续想扩展（克隆声/新增声）再补。
_MINIMAX_SYSTEM_VOICES = [
    {"uri": "junlang_nanyou", "customName": "⭐ 俊朗男友（名字就是男友）"},
    {"uri": "male-qn-jingying", "customName": "精英青年（磁性主流）"},
    {"uri": "male-qn-qingse", "customName": "青涩青年（清朗少年）"},
    {"uri": "male-qn-daxuesheng", "customName": "青年大学生（校园感）"},
    {"uri": "male-qn-badao", "customName": "霸道青年（强气男友）"},
    {"uri": "Chinese (Mandarin)_Gentleman", "customName": "温润男声（温柔绅士）"},
    {"uri": "Chinese (Mandarin)_Pure-hearted_Boy", "customName": "清澈邻家弟弟"},
    {"uri": "lengdan_xiongzhang", "customName": "冷淡学长（冷都男友）"},
]


async def _list_senseaudio_voices(key: str) -> dict:
    """调 SenseAudio /v1/get_voice 拉音色列表；失败/空时回退 Free 版音色。"""
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.post(
                "https://api.senseaudio.cn/v1/get_voice",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"voice_type": "system"},
            )
        if resp.status_code != 200:
            return {"voices": _SENSEAUDIO_FREE_VOICES, "note": f"获取音色列表失败({resp.status_code})，已回退免费音色"}
        data = resp.json()
        # SenseAudio 返回 {system_voice:[{voice_id,voice_name,...}], voice_cloning:[], voice_generation:[]}
        items = data.get("system_voice") or data.get("data") or data.get("result") or data.get("voices") or []
        # 同一 voice_name 有多个后缀变体(a/b/c...，对应不同情绪)，前端会显示成重复项。
        # 按 voice_name 去重：Free 版可用的变体优先，否则取第一个；标注可用/可能受限。
        by_name: dict[str, dict] = {}
        for it in items:
            if not isinstance(it, dict):
                continue
            vid = it.get("voice_id") or it.get("id") or ""
            if not vid:
                continue
            vname = it.get("voice_name") or it.get("name") or vid
            existing = by_name.get(vname)
            if existing is None:
                by_name[vname] = {"vid": vid, "free": vid in _SENSEAUDIO_FREE_VOICE_IDS}
            elif vid in _SENSEAUDIO_FREE_VOICE_IDS and not by_name[vname]["free"]:
                # 已有同名但非 Free 变体，换成 Free 版可用的
                by_name[vname] = {"vid": vid, "free": True}
        voices = []
        for vname, info in by_name.items():
            tag = "" if info["free"] else "（可能受限）"
            voices.append({"uri": info["vid"], "customName": f"{vname}{tag}"})
        # Free 版可用的音色排最前
        voices.sort(key=lambda v: 0 if "(可能受限)" not in v["customName"] else 1)
        if not voices:
            voices = _SENSEAUDIO_FREE_VOICES
        return {"voices": voices}
    except Exception as e:
        return {"voices": _SENSEAUDIO_FREE_VOICES, "note": f"音色列表请求异常：{e}，已回退免费音色"}


async def _list_minimax_voices(key: str) -> dict:
    """返回 MiniMax 男友向精选音色列表（固定 8 个中文男声）。

    不再去 /v1/get_voice 拉全量 —— 那个接口返回 327 个混合多语种，下拉翻不完，
    而且 voice_name 可能是英文。本项目的男友向场景只需要中文男声，硬编码 curated 列表
    体验更好；后续想扩展（克隆声/新增系统声）再合并即可。
    """
    # 顺手用一下 key 做个连通性检测，避免 key 失效时没有任何反馈
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            await client.post(
                "https://api.minimax.io/v1/get_voice",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"voice_type": "system"},
            )
    except Exception:
        pass  # 探测失败不影响，返回 curated 列表即可
    return {"voices": _MINIMAX_SYSTEM_VOICES}


@router.get("/api/tts/voices")
async def tts_voice_list():
    from config import get_tts_provider
    provider = get_tts_provider()
    if provider == "senseaudio":
        key = get_key("senseaudio")
        if not key:
            return {"voices": [], "error": "未配置 SenseAudio API Key"}
        return await _list_senseaudio_voices(key)
    if provider == "minimax":
        key = get_key("minimax")
        if not key:
            return {"voices": [], "error": "未配置 MiniMax API Key"}
        return await _list_minimax_voices(key)
    # 默认硅基流动
    key = get_key("siliconflow")
    if not key:
        return {"voices": [], "error": "未配置硅基流动 API Key"}
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(
                "https://api.siliconflow.cn/v1/audio/voice/list",
                headers={"Authorization": f"Bearer {key}"}
            )
        if resp.status_code != 200:
            return {"voices": [], "error": "获取音色列表失败"}
        data = resp.json()
        voices = data.get("result") or data.get("voices") or data.get("data") or []
        # 硅基接口只返回用户克隆音色；账号没克隆过时列表为空，补上系统预置音色作兜底。
        if not voices:
            voices = _COSYVOICE2_SYSTEM_VOICES
        return {"voices": voices}
    except Exception as e:
        return {"voices": [], "error": str(e)}
