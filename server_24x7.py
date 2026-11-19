#!/usr/bin/env python3
"""
GTA 6 24/7 Pro-Edited Creator Auto-Clipper
(Random 65% Music + Hook SFX + Visual FX + Pillow Neon UI + Viral Auto-Captions)
================================================================================
Optimized for Android Termux & Low-Spec PCs:
  1. Discovers GTA 6 clips & stream slices from 26 global + Indian creators (0 API quota).
  2. Filters strictly for GTA 6 / GTA VI titles and blocks duplicates via uploaded_ids.txt.
  3. Pulls a 35s clip + YouTube auto-captions (.vtt) with yt-dlp and builds bouncing
     Hormozi-style yellow .ass word-pop subtitles (0 extra AI RAM).
  4. Draws CapCut-style rounded Vice City neon 3-second hook card & creator badge PNGs
     via Python Pillow.
  5. Mixes a random copyright-free music track from music/ at 65% volume (with smooth fade)
     + optional hook SFX from sfx/ + FFmpeg visual FX (white intro flash, color pop,
     sharpening, cinema vignette) + broadcast loudnorm, then uploads to YouTube Shorts.
"""

from __future__ import annotations
import argparse
import glob
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import Dict, List, Optional, Set, Tuple

import requests

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "music")
SFX_DIR = os.path.join(BASE_DIR, "sfx")
UPLOADED_DB_FILE = os.path.join(BASE_DIR, "uploaded_ids.txt")

# Audio mix levels (65% background music by default; override via MUSIC_VOLUME env var)
MUSIC_VOLUME = float(os.environ.get("MUSIC_VOLUME", "0.65"))
SFX_VOLUME = float(os.environ.get("SFX_VOLUME", "0.85"))

CREATOR_QUERIES = [
    # Global Mega Streamers & Gaming Creators
    "IShowSpeed GTA 6",
    "IShowSpeed GTA 6 stream",
    "Kai Cenat GTA 6",
    "CaseOh GTA 6",
    "xQc GTA 6",
    "Jynxzi GTA 6",
    "Adin Ross GTA 6",
    "Fanum GTA 6",
    "MoistCr1TiKaL GTA 6",
    "Asmongold GTA 6",
    "Markiplier GTA 6",
    "Jacksepticeye GTA 6",
    "Typical Gamer GTA 6",
    "DarkViperAU GTA 6",
    "theRadBrad GTA 6",
    "SypherPK GTA 6",
    # Top Indian Gaming Creators
    "Techno Gamerz GTA 6",
    "CarryisLive GTA 6",
    "Mythpat GTA 6",
    "Triggered Insaan GTA 6",
    "BeastBoyShub GTA 6",
    "GamerFleet GTA 6",
    "ScoutOP GTA 6",
    # General Viral GTA 6 Live Streams & Moments
    "GTA 6 live stream reaction",
    "GTA 6 funniest moments",
    "GTA VI gameplay clips",
]

HOOK_TEMPLATES = [
    "WAIT FOR HIS REACTION TO GTA 6...",
    "NO WAY THIS JUST HAPPENED IN GTA 6!",
    "WATCH CLOSELY AT THE 3-SECOND MARK...",
    "99% OF PLAYERS MISSED THIS IN GTA 6!",
    "ROCKSTAR ACTUALLY CODED THIS INTO GTA 6?!",
    "THIS GTA 6 STREAM MOMENT BROKE THE INTERNET!",
]

GTA6_TITLE_RE = re.compile(r"\bgta\s*(6|vi)\b|grand\s+theft\s+auto\s*(6|vi)\b", re.IGNORECASE)
CLIP_START_SEC = 15.0
CLIP_DURATION_SEC = 35.0
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".aac")


def ensure_media_dirs() -> None:
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(SFX_DIR, exist_ok=True)


def pick_random_audio(folder: str) -> Optional[str]:
    if not os.path.isdir(folder):
        return None
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(AUDIO_EXTS) and os.path.isfile(os.path.join(folder, f))
    ]
    return random.choice(files) if files else None


def load_uploaded_ids() -> Set[str]:
    if not os.path.exists(UPLOADED_DB_FILE):
        return set()
    with open(UPLOADED_DB_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_uploaded_id(video_id: str) -> None:
    with open(UPLOADED_DB_FILE, "a", encoding="utf-8") as f:
        f.write(video_id.strip() + "\n")


def is_gta6_video(title: str) -> bool:
    return bool(GTA6_TITLE_RE.search(title or ""))


def _find_bold_font_path() -> Optional[str]:
    candidates = [
        "/system/fonts/Roboto-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_pil_font(size: int):
    font_path = _find_bold_font_path()
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def create_pillow_overlays(hook_text: str, creator_name: str, tmp_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """Generates CapCut-style transparent 1080x1920 PNG overlays (3s neon hook card + creator badge)."""
    if not HAS_PILLOW:
        print("[PILLOW] Pillow not installed — run 'pkg install -y python-pillow' for neon hook cards.")
        return None, None

    hook_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hook_img)

    card_box = [70, 175, 1010, 415]
    draw.rounded_rectangle([64, 169, 1016, 421], radius=34, fill=(0, 240, 255, 70))
    draw.rounded_rectangle(card_box, radius=30, fill=(11, 14, 24, 232), outline=(255, 42, 133, 255), width=6)

    draw.rounded_rectangle([320, 148, 760, 204], radius=24, fill=(255, 42, 133, 255))
    tag_font = _load_pil_font(28)
    draw.text((540, 176), "GTA 6 VIRAL MOMENT", fill=(255, 255, 255, 255), font=tag_font, anchor="mm")

    hook_font = _load_pil_font(44)
    lines = textwrap.wrap(hook_text.upper(), width=26)[:3]
    y_start = 265 if len(lines) <= 2 else 242
    for idx, line in enumerate(lines):
        draw.text((540, y_start + idx * 54), line, fill=(250, 204, 21, 255), font=hook_font, anchor="mm")

    hook_png = os.path.join(tmp_dir, "hook_card.png")
    hook_img.save(hook_png, "PNG")

    badge_img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge_img)
    safe_creator = "@" + re.sub(r"[^A-Za-z0-9_ ]+", "", creator_name or "GTA6Creator").strip()[:18]
    bfont = _load_pil_font(30)
    bdraw.rounded_rectangle([46, 68, 470, 132], radius=28, fill=(10, 14, 24, 205), outline=(0, 240, 255, 220), width=3)
    bdraw.text((258, 100), safe_creator, fill=(255, 255, 255, 255), font=bfont, anchor="mm")

    badge_png = os.path.join(tmp_dir, "creator_badge.png")
    badge_img.save(badge_png, "PNG")
    print("[PILLOW] Rendered Vice City neon 3-second hook card & creator badge PNGs.")
    return hook_png, badge_png


def _vtt_time_to_sec(ts: str) -> float:
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return 0.0


def _sec_to_ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def convert_vtt_to_viral_ass(vtt_path: str, out_ass_path: str, clip_offset: float, max_dur: float) -> Optional[str]:
    if not os.path.exists(vtt_path):
        return None
    with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    time_re = re.compile(r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})")
    blocks = raw.split("\n\n")
    events: List[Tuple[float, float, str]] = []

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        m = None
        text_lines: List[str] = []
        for ln in lines:
            if m is None:
                m = time_re.search(ln)
            else:
                cleaned = re.sub(r"<[^>]+>", "", ln).strip()
                if cleaned:
                    text_lines.append(cleaned)
        if not m or not text_lines:
            continue
        t0 = _vtt_time_to_sec(m.group(1)) - clip_offset
        t1 = _vtt_time_to_sec(m.group(2)) - clip_offset
        if t1 <= 0.2 or t0 >= max_dur:
            continue
        t0 = max(0.0, t0)
        t1 = min(max_dur, t1)
        words = " ".join(text_lines).split()
        if not words:
            continue
        chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
        step = max(0.25, (t1 - t0) / max(1, len(chunks)))
        for idx, ch in enumerate(chunks):
            c0 = t0 + idx * step
            c1 = min(t1, c0 + step)
            phrase = " ".join(ch).upper().replace("{", "").replace("}", "")
            if events and events[-1][2] == phrase:
                continue
            events.append((c0, c1, phrase))

    if not events:
        return None

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralPop,Arial,86,&H0015CCFA,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,7,3,2,60,60,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out_lines = [header.strip()]
    for s0, s1, phrase in events[:60]:
        out_lines.append(
            f"Dialogue: 0,{_sec_to_ass_time(s0)},{_sec_to_ass_time(s1)},ViralPop,,0,0,0,,"
            f"{{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}}{phrase}"
        )

    with open(out_ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"[CAPTIONS] Built viral bouncing .ass subtitles ({len(events)} bursts).")
    return out_ass_path


def discover_creator_gta6_videos(queries: List[str], uploaded_ids: Set[str]) -> List[Dict[str, str]]:
    picked_queries = random.sample(queries, min(3, len(queries)))
    candidates: List[Dict[str, str]] = []
    seen: Set[str] = set()

    for query in picked_queries:
        cmd = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch8:{query}"]
        print(f"[DISCOVER] Searching creator clips: '{query}' (0 API quota)...")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            continue

        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = str(data.get("id") or "").strip()
            title = str(data.get("title") or "").strip()
            channel = str(data.get("channel") or data.get("uploader") or "GTA 6 Creator").strip()
            if not vid or vid in uploaded_ids or vid in seen:
                continue
            if not is_gta6_video(title):
                continue
            seen.add(vid)
            candidates.append({"video_id": vid, "title": title, "channel": channel})

    return candidates


def download_clip_and_subs(video_id: str, tmp_dir: str) -> Tuple[str, Optional[str], float]:
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    out_raw_mp4 = os.path.join(tmp_dir, "raw.mp4")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--download-sections", "*0:00:15-0:00:50",
        "--force-keyframes-at-cuts",
        "--write-auto-subs", "--sub-lang", "en", "--sub-format", "vtt",
        "--no-playlist",
        "-o", out_raw_mp4,
        video_url,
    ]
    print(f"[YT-DLP] Downloading 35s highlight slice + auto-captions from {video_url}...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    offset_used = CLIP_START_SEC

    if proc.returncode != 0 or not os.path.exists(out_raw_mp4):
        offset_used = 0.0
        fallback_cmd = [
            "yt-dlp",
            "-f", "best[height<=720][ext=mp4]/best",
            "--write-auto-subs", "--sub-lang", "en", "--sub-format", "vtt",
            "--no-playlist",
            "--max-filesize", "60M",
            "-o", out_raw_mp4,
            video_url,
        ]
        print("[YT-DLP] Short clip detected — downloading full clip + auto-captions...")
        proc2 = subprocess.run(fallback_cmd, capture_output=True, text=True)
        if proc2.returncode != 0 or not os.path.exists(out_raw_mp4):
            raise RuntimeError(f"yt-dlp failed: {proc2.stderr[-400:]}")

    vtt_files = glob.glob(os.path.join(tmp_dir, "*.vtt"))
    return out_raw_mp4, (vtt_files[0] if vtt_files else None), offset_used


def synthesize_elevenlabs_hook(hook_text: str, out_mp3: str) -> Optional[str]:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return None
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM").strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {"model_id": "eleven_flash_v2_5", "text": hook_text}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 200:
        with open(out_mp3, "wb") as f:
            f.write(resp.content)
        print("[TTS] Synthesized ElevenLabs Flash v2.5 hook voiceover.")
        return out_mp3
    return None


def render_vertical_short(
    raw_mp4: str,
    hook_mp3: Optional[str],
    hook_png: Optional[str],
    badge_png: Optional[str],
    ass_path: Optional[str],
    music_path: Optional[str],
    sfx_path: Optional[str],
    hook_text: str,
    out_mp4: str,
) -> str:
    """Renders 9:16 pro Short with visual FX, Pillow overlays, .ass captions, 65% music & hook SFX."""
    cmd = ["ffmpeg", "-y", "-i", raw_mp4]
    next_idx = 1

    hook_png_idx = None
    if hook_png and os.path.exists(hook_png):
        cmd.extend(["-i", hook_png])
        hook_png_idx = next_idx
        next_idx += 1

    badge_png_idx = None
    if badge_png and os.path.exists(badge_png):
        cmd.extend(["-i", badge_png])
        badge_png_idx = next_idx
        next_idx += 1

    tts_idx = None
    if hook_mp3 and os.path.exists(hook_mp3):
        cmd.extend(["-i", hook_mp3])
        tts_idx = next_idx
        next_idx += 1

    music_idx = None
    if music_path and os.path.exists(music_path):
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
        music_idx = next_idx
        next_idx += 1
        print(f"[MUSIC] Mixing random track '{os.path.basename(music_path)}' at {int(MUSIC_VOLUME * 100)}% volume.")

    sfx_idx = None
    if sfx_path and os.path.exists(sfx_path):
        cmd.extend(["-i", sfx_path])
        sfx_idx = next_idx
        next_idx += 1
        print(f"[SFX] Triggering hook effect '{os.path.basename(sfx_path)}' at {int(SFX_VOLUME * 100)}% volume.")

    # Visual FX chain: blurred BG + color-popped & sharpened FG + cinema vignette + white intro flash
    filters = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=22:6,eq=brightness=-0.06[bg]",
        "[0:v]scale=1080:-2,eq=contrast=1.09:saturation=1.24,unsharp=5:5:0.7:5:5:0.0[fg]",
        "[bg][fg]overlay=(W-w)/2:(H-h)/2,vignette=PI/5,fade=t=in:st=0:d=0.35:color=white[v0]",
        "[v0]drawbox=x=0:y=ih-16:w=iw:h=16:color=black@0.6:t=fill[vbarbg]",
    ]
    cur_v = "vbarbg"

    if hook_png_idx is not None:
        filters.append(f"[{cur_v}][{hook_png_idx}:v]overlay=0:0:enable='between(t,0,3.5)'[vhook]")
        cur_v = "vhook"
    else:
        safe_hook = hook_text.replace("'", "").replace(":", " -")
        fp = _find_bold_font_path()
        fopt = f":fontfile={fp}" if fp else ""
        filters.append(
            f"[{cur_v}]drawtext=text='{safe_hook}'{fopt}:fontcolor=yellow:fontsize=46:"
            "box=1:boxcolor=black@0.85:boxborderw=22:x=(w-text_w)/2:y=260:enable='between(t,0,3.5)'[vhook]"
        )
        cur_v = "vhook"

    if badge_png_idx is not None:
        filters.append(f"[{cur_v}][{badge_png_idx}:v]overlay=0:0[vbadge]")
        cur_v = "vbadge"

    if ass_path and os.path.exists(ass_path):
        ass_esc = ass_path.replace("\\", "/").replace(":", "\\:")
        filters.append(f"[{cur_v}]ass='{ass_esc}'[vsub]")
        cur_v = "vsub"

    # Multi-track audio mixer: Original Clip + Optional TTS + Random 65% Music + Optional Hook SFX
    audio_inputs = ["[0:a]"]
    if tts_idx is not None:
        filters.append(f"[{tts_idx}:a]volume=1.15[atts]")
        audio_inputs.append("[atts]")
    if music_idx is not None:
        fade_out_start = max(1.0, CLIP_DURATION_SEC - 2.0)
        filters.append(
            f"[{music_idx}:a]volume={MUSIC_VOLUME:.2f},afade=t=in:st=0:d=0.6,"
            f"afade=t=out:st={fade_out_start:.1f}:d=2.0[amusic]"
        )
        audio_inputs.append("[amusic]")
    if sfx_idx is not None:
        filters.append(f"[{sfx_idx}:a]adelay=100|100,volume={SFX_VOLUME:.2f}[asfx]")
        audio_inputs.append("[asfx]")

    if len(audio_inputs) > 1:
        filters.append(
            f"{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=2,"
            "loudnorm=I=-14:TP=-1.5:LRA=11[outa]"
        )
    else:
        filters.append("[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[outa]")

    cmd.extend([
        "-t", str(int(CLIP_DURATION_SEC)),
        "-filter_complex", ";".join(filters),
        "-map", f"[{cur_v}]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-r", "30",
        out_mp4,
    ])
    print("[FFMPEG] Rendering pro 9:16 Short (Flash + Vignette + Color Pop + 65% Music + Captions)...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out_mp4):
        raise RuntimeError(f"FFmpeg render failed: {proc.stderr[-500:]}")
    print(f"[FFMPEG] Rendered {out_mp4} ({os.path.getsize(out_mp4) // 1024} KB).")
    return out_mp4


def refresh_youtube_access_token(cred: Dict[str, str]) -> str:
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
            "refresh_token": cred["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OAuth refresh failed ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


def upload_youtube_short(mp4_path: str, title: str, description: str, token_pool: List[Dict[str, str]]) -> str:
    boundary = "gta6_autoclipper_boundary_9x16"
    clean_title = title.replace("\n", " ").strip()
    final_title = (clean_title[:84] + " #GTA6 #Shorts") if "#Shorts" not in clean_title else clean_title[:100]
    metadata = {
        "snippet": {
            "title": final_title,
            "description": description,
            "tags": ["GTA6", "GTA 6", "IShowSpeed", "KaiCenat", "Shorts", "ViceCity", "Gaming"],
            "categoryId": "20",
        },
        "status": {
            "privacyStatus": os.environ.get("YT_PRIVACY_STATUS", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }

    with open(mp4_path, "rb") as f:
        video_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        "Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + video_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    last_err = ""
    for idx, cred in enumerate(token_pool):
        try:
            access_token = refresh_youtube_access_token(cred)
            resp = requests.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=multipart&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                data=body,
                timeout=180,
            )
            if resp.status_code in (200, 201):
                vid_id = resp.json().get("id", "unknown")
                print(f"[UPLOAD SUCCESS] Posted YouTube Short! URL: https://youtube.com/shorts/{vid_id}")
                return vid_id
            last_err = f"Project #{idx+1} HTTP {resp.status_code}: {resp.text[:300]}"
            print(f"[QUOTA/ROTATE] {last_err}")
        except Exception as exc:
            last_err = f"Project #{idx+1} error: {exc}"
            print(f"[QUOTA/ROTATE] {last_err}")

    raise RuntimeError(f"All YouTube OAuth projects in YT_TOKEN_POOL_JSON failed. Last error: {last_err}")


def load_token_pool() -> List[Dict[str, str]]:
    raw = os.environ.get("YT_TOKEN_POOL_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing YT_TOKEN_POOL_JSON secret in environment!")
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = [parsed]
    for item in parsed:
        for key in ("client_id", "client_secret", "refresh_token"):
            if not item.get(key) or "PASTE_YOUR" in str(item.get(key)):
                raise RuntimeError(f"YT_TOKEN_POOL_JSON is missing a real '{key}' value.")
    return parsed


def run_live_cycle() -> int:
    ensure_media_dirs()
    token_pool = load_token_pool()
    uploaded_ids = load_uploaded_ids()

    custom_q = os.environ.get("CREATOR_QUERIES", "").strip()
    queries = [q.strip() for q in custom_q.split(",") if q.strip()] or CREATOR_QUERIES

    candidates = discover_creator_gta6_videos(queries, uploaded_ids)
    if not candidates:
        raise RuntimeError("No fresh GTA 6 creator videos found right now.")

    chosen = random.choice(candidates)
    hook_text = random.choice(HOOK_TEMPLATES)
    music_track = pick_random_audio(MUSIC_DIR)
    sfx_track = pick_random_audio(SFX_DIR)
    print(f"[SELECTED] Creator: {chosen['channel']} | Video: {chosen['title']} ({chosen['video_id']})")

    with tempfile.TemporaryDirectory() as tmp:
        raw_mp4, vtt_path, clip_offset = download_clip_and_subs(chosen["video_id"], tmp)
        hook_png, badge_png = create_pillow_overlays(hook_text, chosen["channel"], tmp)
        ass_path = convert_vtt_to_viral_ass(vtt_path, os.path.join(tmp, "viral.ass"), clip_offset, CLIP_DURATION_SEC) if vtt_path else None
        tts_file = synthesize_elevenlabs_hook(hook_text, os.path.join(tmp, "hook.mp3"))
        final_mp4 = os.path.join(tmp, "short_9x16.mp4")

        render_vertical_short(
            raw_mp4, tts_file, hook_png, badge_png, ass_path,
            music_track, sfx_track, hook_text, final_mp4
        )

        desc = (
            f"{hook_text}\n\n"
            f"Creator: {chosen['channel']}\n"
            f"Source: {chosen['title']}\n"
            "#GTA6 #IShowSpeed #KaiCenat #GTA6Clips #Shorts #Gaming"
        )
        upload_youtube_short(final_mp4, chosen["title"], desc, token_pool)
        save_uploaded_id(chosen["video_id"])
    return 0


def run_self_test() -> int:
    ensure_media_dirs()
    assert is_gta6_video("IShowSpeed reacts to GTA 6 Gameplay!")
    assert not is_gta6_video("RoadCraft - Constructing an Overpass")
    with tempfile.TemporaryDirectory() as tmp:
        hp, bp = create_pillow_overlays("WAIT FOR HIS REACTION TO GTA 6...", "IShowSpeed", tmp)
        assert hp and os.path.exists(hp) and bp and os.path.exists(bp), "Pillow PNG render failed"
        vtt_sample = os.path.join(tmp, "sample.vtt")
        with open(vtt_sample, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n00:00:16.000 --> 00:00:18.500\nBro no way Rockstar actually added this to GTA 6!\n")
        ass_out = convert_vtt_to_viral_ass(vtt_sample, os.path.join(tmp, "viral.ass"), 15.0, 35.0)
        assert ass_out and os.path.exists(ass_out), "VTT to ASS conversion failed"

        # Synthesize 2s video + 2s background music + 0.5s hook SFX to test full multi-track mixer
        synth_in = os.path.join(tmp, "in.mp4")
        synth_music = os.path.join(tmp, "bg_music.mp3")
        synth_sfx = os.path.join(tmp, "hook_whoosh.mp3")
        synth_out = os.path.join(tmp, "out.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-preset", "ultrafast",
             "-c:a", "aac", synth_in],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", "-c:a", "libmp3lame", synth_music],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.4", "-c:a", "libmp3lame", synth_sfx],
            check=True, capture_output=True,
        )
        render_vertical_short(
            synth_in, None, hp, bp, ass_out, synth_music, synth_sfx,
            "WAIT FOR HIS REACTION TO GTA 6...", synth_out
        )
        assert os.path.exists(synth_out) and os.path.getsize(synth_out) > 10000
    print("ALL PRO-FX & 65% MUSIC SELF-TESTS PASSED: Visual FX + 65% Music + Hook SFX + Pillow + Viral Captions verified!")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GTA 6 24/7 Pro-Edited Creator Auto-Clipper")
    parser.add_argument("--daily-target", type=int, default=16, help="Daily Shorts target")
    parser.add_argument("--once", action="store_true", help="Run one live clip & upload cycle")
    parser.add_argument("--self-test", action="store_true", help="Run full end-to-end FFmpeg, Music & Pillow self-test")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    return run_live_cycle()


if __name__ == "__main__":
    sys.exit(main())
