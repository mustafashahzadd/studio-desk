"""
main.py — Studio Desk FastAPI Backend
Provides REST API + WebSocket for the podcast-to-video pipeline UI.
"""
import os
import asyncio
import json
import uuid
import logging
import re
import glob
import zipfile
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from band_service import BandService

# Where editor_agent.py saves reel_*.mp4 files (repo root, one level up from backend/)
CLIPS_DIR = Path(__file__).parent.parent.resolve()


def _find_clips(job_id: str) -> list[dict]:
    """
    Scan CLIPS_DIR for reel_*.mp4 files. If the job has a known run_id prefix
    stored in artifacts, filter by it; otherwise return all found reels.
    Returns list of {name, path, size_mb}.
    """
    pattern = str(CLIPS_DIR / "reel_*.mp4")
    files = sorted(glob.glob(pattern))

    # Try to narrow down to clips for THIS job via stored prefix
    prefix = None
    if job_id in jobs:
        prefix = jobs[job_id].get("editor_run_id")

    results = []
    for f in files:
        name = Path(f).name
        if prefix and prefix not in name:
            continue
        size = Path(f).stat().st_size
        results.append({
            "name": name,
            "path": f,
            "size_mb": round(size / 1_048_576, 2),
            "size_bytes": size,
        })
    return results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# ─── Lifespan ──────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_app):
    logger.info("🎬 Studio Desk API started")
    logger.info(f"   Transcriber: {os.environ.get('TRANSCRIBER_AGENT_ID', 'not set')}")
    logger.info(f"   Editor:      {os.environ.get('EDITOR_AGENT_ID', 'not set')}")
    yield
# ─── App Setup ───────────────────────────────────────────────────────────────

app = FastAPI(title="Studio Desk API", version="1.0.0", lifespan=lifespan)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-Memory State (hackathon) ─────────────────────────────────────────────

jobs: Dict[str, dict] = {}
job_events: Dict[str, List[dict]] = {}
ws_clients: Dict[str, List[WebSocket]] = {}
pipeline_tasks: Dict[str, asyncio.Task] = {}

band_service = BandService()

# ─── Pydantic Models ─────────────────────────────────────────────────────────


class CreateJobRequest(BaseModel):
    url: str
    title: Optional[str] = None


class ApproveJobRequest(BaseModel):
    action: str  # "approve" | "reject"
    feedback: Optional[str] = None
    route_to: Optional[str] = None  # "transcriber" | "repurposer"


# ─── Helpers ─────────────────────────────────────────────────────────────────

DEMO_PIPELINE_STEPS = [
    # (delay, sender, message, event_type, stage, stage_status, via)
    (2.0,  "Transcriber", "audio received — 48m stereo, 44.1kHz",                  "info",    "transcribe", "running", "Whisper"),
    (4.0,  "Transcriber", "running whisper-v3 on audio",                            "info",    "transcribe", "running", "Whisper"),
    (7.0,  "Transcriber", "transcript complete — 6,847 words, 312 segments",        "info",    "transcribe", "done",    "Whisper"),
    (8.0,  "Transcriber", "Transcript complete. Handoff @Creator @Repurposer — full transcript with timestamps attached.", "handoff", "create", "running", None),
    (10.0, "Creator",     "analyzing transcript for key moments",                   "info",    "create",     "running", "AI/ML API"),
    (11.0, "Repurposer",  "identifying clip candidates",                            "info",    "repurpose",  "running", "Featherless"),
    (13.0, "Creator",     "generating thumbnail options (3 variants)",              "info",    "create",     "running", "AI/ML API"),
    (14.0, "Repurposer",  "extracting 3 short clips for social",                   "info",    "repurpose",  "running", "ffmpeg"),
    (15.0, "Creator",     "running ffmpeg — cut list ready",                       "info",    "create",     "running", "ffmpeg"),
    (16.0, "Repurposer",  "adding captions to short clips",                        "info",    "repurpose",  "running", "Featherless"),
    (18.0, "Validator",   "checking audio consistency across segments",             "info",    "validate",   "running", "AI/ML API"),
    (20.0, "Validator",   "✓ all checks passed — pipeline complete",               "success", "validate",   "done",    "AI/ML API"),
    (21.0, "System",      "Pipeline ready for your approval.",                     "approval","approval",   "pending", None),
]

# ── Video info cache (populated at job-create time) ──────────────────────────
video_info_cache: Dict[str, dict] = {}  # job_id → {duration_s, title, channel, thumbnail_url}


def _fmt_time(seconds: int) -> str:
    """Format seconds → MM:SS or H:MM:SS."""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _make_chapters(duration_s: float) -> list:
    """Generate chapter list proportional to actual video duration."""
    chapter_templates = [
        "Introduction & Welcome",
        "Main Discussion",
        "Key Moments",
        "Deep Dive",
        "Takeaways & Wrap-up",
    ]
    n = 5 if duration_s > 300 else (3 if duration_s > 60 else 2)
    chapters = []
    for i in range(n):
        frac = i / n
        t = int(duration_s * frac)
        chapters.append({"time": _fmt_time(t), "title": chapter_templates[i]})
    return chapters


def _make_demo_artifacts(job_id: str, seed: str) -> dict:
    """Build demo artifacts using real video metadata where available."""
    info = video_info_cache.get(job_id, {})
    duration_s = info.get("duration_s", 0)
    video_title = info.get("title", "")

    # Use real YouTube thumbnail if available, else picsum
    yt_thumb = info.get("thumbnail_url", "")
    thumbs = [
        yt_thumb if yt_thumb else f"https://picsum.photos/seed/{seed}a/576/324",
        f"https://picsum.photos/seed/{seed}b/576/324",
        f"https://picsum.photos/seed/{seed}c/576/324",
    ]

    # Scale clip timestamps to actual duration
    clip_starts = [0.10, 0.35, 0.65] if duration_s > 30 else [0, 0.3, 0.6]
    clips = []
    labels = [
        f'"Best moment from {video_title[:30]}"' if video_title else '"Top moment"',
        '"This changes everything"',
        '"You need to hear this"',
    ]
    for i, frac in enumerate(clip_starts):
        t = int(duration_s * frac)
        clips.append({
            "label": labels[i],
            "thumbnail": f"https://picsum.photos/seed/{seed}clip{i}/300/200",
            "start": t,
            "end": t + 15,
        })

    return {
        "thumbnails": thumbs,
        "short_clips": clips,
        # Always generate real proportional chapters; if duration unknown assume 5 min
        "chapters": _make_chapters(duration_s if duration_s else 300),
    }


async def _fetch_video_info(url: str) -> dict:
    """
    Fetch real video metadata.
    - Remote URLs (YouTube etc.): uses yt-dlp (no download, just metadata)
    - Local files (file:// or plain path): tries yt-dlp then ffprobe
    Returns dict with duration_s, title, channel, thumbnail_url.
    Falls back to {} on failure.
    """
    loop = asyncio.get_event_loop()

    # Resolve local file paths
    local_path: Optional[str] = None
    clean_url = url.strip()
    if clean_url.startswith("file://"):
        local_path = clean_url[7:]
    elif Path(clean_url).exists():
        local_path = clean_url

    partial: dict = {}

    # ── Try yt-dlp first (works for YouTube, direct MP3/MP4 URLs, and local files) ──
    try:
        import yt_dlp

        def _ytdlp_blocking():
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": False,
            }
            target = local_path if local_path else clean_url
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target, download=False)
                return {
                    "duration_s": int(info.get("duration") or 0),
                    "title":      info.get("title", "") or "",
                    "channel":    info.get("uploader", "") or "",
                    "thumbnail_url": info.get("thumbnail", "") or "",
                    "view_count": info.get("view_count", 0) or 0,
                }

        partial = await loop.run_in_executor(None, _ytdlp_blocking)
        if partial.get("duration_s"):
            return partial          # Full info — we're done
    except Exception as exc:
        logger.warning(f"yt-dlp info fetch failed ({clean_url!r}): {exc}")

    # ── Fallback: ffprobe for duration (great for local MP4/MP3 files) ──
    try:
        import subprocess
        target = local_path if local_path else clean_url

        def _ffprobe_blocking():
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                target,
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if out.returncode != 0:
                return 0.0
            data = json.loads(out.stdout)
            return float(data.get("format", {}).get("duration", 0) or 0)

        duration = await loop.run_in_executor(None, _ffprobe_blocking)
        if duration:
            partial["duration_s"] = int(duration)
    except Exception as exc:
        logger.warning(f"ffprobe fallback failed: {exc}")

    # Derive a clean title from filename if we still don't have one
    if not partial.get("title") and local_path:
        partial["title"] = Path(local_path).stem.replace("_", " ").replace("-", " ")

    return partial


def emit_event(
    job_id: str,
    sender: str,
    message: str,
    event_type: str = "info",
    via: Optional[str] = None,
) -> dict:
    """Store an event and broadcast it to all connected WebSocket clients."""
    event = {
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "sender": sender,
        "message": message,
        "type": event_type,
        "via": via,
        "timestamp": datetime.utcnow().strftime("%H:%M"),
    }

    job_events.setdefault(job_id, []).append(event)

    if job_id in jobs:
        jobs[job_id]["events"].append(event)

    # Broadcast to all connected WS clients
    for ws in ws_clients.get(job_id, [])[:]:
        asyncio.create_task(_safe_send(ws, json.dumps(event)))

    return event


async def _safe_send(ws: WebSocket, data: str):
    try:
        await ws.send_text(data)
    except Exception:
        pass


def _update_pipeline(job_id: str, stage: str, status: str):
    """Update a single pipeline stage status."""
    if job_id in jobs:
        jobs[job_id]["pipeline"][stage] = status
        # Broadcast pipeline update
        payload = {
            "type": "pipeline_update",
            "job_id": job_id,
            "stage": stage,
            "status": status,
        }
        for ws in ws_clients.get(job_id, [])[:]:
            asyncio.create_task(_safe_send(ws, json.dumps(payload)))


# ─── Pipeline Runner ──────────────────────────────────────────────────────────


async def run_pipeline(job_id: str, video_url: str):
    """Kick off the pipeline: try Band API first, then run demo steps."""
    logger.info(f"[{job_id}] Starting pipeline for {video_url}")

    # Try to trigger real Band pipeline
    room_id, initial_events = await band_service.start_pipeline(job_id, video_url)

    if room_id:
        jobs[job_id]["band_room_id"] = room_id
        for ev in initial_events:
            emit_event(job_id, ev["sender"], ev["message"], ev.get("type", "info"))
        # Real Band WebSocket subscription would go here
        # For now, run demo steps as well for UI feedback
    else:
        for ev in initial_events:
            emit_event(job_id, ev["sender"], ev["message"], ev.get("type", "info"))

    # Run demo pipeline steps for UI demonstration
    await _run_demo_steps(job_id, video_url)


async def _run_demo_steps(job_id: str, video_url: str):
    """Simulate pipeline progress for the UI (used when real agents aren't running)."""
    start_time = asyncio.get_event_loop().time()
    info = video_info_cache.get(job_id, {})
    duration_s = info.get("duration_s", 0)
    real_title = info.get("title", "")
    channel = info.get("channel", "")

    # Build accurate transcript stats from real duration
    # ~150 words/min average spoken, Whisper produces ~2.5 segments/min
    wpm = 150
    if duration_s:
        words    = max(100, int(duration_s / 60 * wpm))
        segments = max(10,  int(duration_s / 60 * 2.5))
        audio_fmt = f"{int(duration_s // 60)}m {int(duration_s % 60)}s stereo, 44.1kHz"
    else:
        # Duration unknown (unsupported URL / no ffprobe) — show neutral values
        words     = "unknown"
        segments  = "unknown"
        audio_fmt = "stereo, 44.1kHz"

    # Patch the first two Transcriber messages with real values
    live_steps = list(DEMO_PIPELINE_STEPS)
    live_steps[0] = (live_steps[0][0], "Transcriber", f"audio received — {audio_fmt}",                              "info", "transcribe", "running", "Whisper")
    word_str = f"{words:,}" if isinstance(words, int) else words
    seg_str  = f"{segments}" if isinstance(segments, int) else segments
    live_steps[2] = (live_steps[2][0], "Transcriber", f"transcript complete — {word_str} words, {seg_str} segments", "info", "transcribe", "done",    "Whisper")
    demo_seed = job_id[:8]

    for delay, sender, message, event_type, stage, stage_status, via in live_steps:
        if job_id not in jobs:
            return

        sleep_for = max(0.2, delay - (asyncio.get_event_loop().time() - start_time))
        await asyncio.sleep(sleep_for)

        if job_id not in jobs:
            return

        # Update pipeline stage
        _update_pipeline(job_id, stage, stage_status)
        ev = emit_event(job_id, sender, message, event_type, via=via)

        # Attach @mention tags for handoff events so UI can render badge chips
        if event_type == "handoff":
            ev["mentions"] = ["@Creator", "@Repurposer"]
            # Patch the stored event too
            for stored in job_events.get(job_id, []):
                if stored["id"] == ev["id"]:
                    stored["mentions"] = ev["mentions"]
                    break

        # Inject artifact data at the right points
        if sender == "Transcriber" and "transcript complete" in message:
            dynamic = _make_demo_artifacts(job_id, demo_seed)
            display_title = real_title or jobs[job_id].get("title", "Episode")
            desc = f"A video by {channel}." if channel else "Video content processed by Studio Desk."
            if duration_s:
                desc += f" Runtime: {_fmt_time(duration_s)}."
            jobs[job_id]["artifacts"].update({
                "title": display_title,
                "description": desc,
                "chapters": dynamic["chapters"],
            })
            jobs[job_id]["title"] = display_title
            _broadcast_artifacts(job_id)
            _broadcast_job_update(job_id)

        elif sender == "Creator" and "thumbnail" in message:
            dynamic = _make_demo_artifacts(job_id, demo_seed)
            jobs[job_id]["artifacts"]["thumbnails"] = dynamic["thumbnails"]
            _broadcast_artifacts(job_id)

        elif sender == "Repurposer" and "adding captions" in message:
            dynamic = _make_demo_artifacts(job_id, demo_seed)
            jobs[job_id]["artifacts"]["short_clips"] = dynamic["short_clips"]
            _broadcast_artifacts(job_id)

        elif event_type == "approval":
            jobs[job_id]["status"] = "awaiting_approval"
            _broadcast_job_update(job_id)


def _broadcast_artifacts(job_id: str):
    if job_id not in jobs:
        return
    payload = json.dumps({
        "type": "artifacts_update",
        "job_id": job_id,
        "artifacts": jobs[job_id]["artifacts"],
    })
    for ws in ws_clients.get(job_id, [])[:]:
        asyncio.create_task(_safe_send(ws, payload))


def _broadcast_job_update(job_id: str):
    if job_id not in jobs:
        return
    payload = json.dumps({
        "type": "job_update",
        "job": jobs[job_id],
    })
    for ws in ws_clients.get(job_id, [])[:]:
        asyncio.create_task(_safe_send(ws, payload))


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {"status": "ok", "service": "Studio Desk API"}


@app.post("/api/jobs")
async def create_job(request: CreateJobRequest):
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Fetch real video info (non-blocking, best-effort)
    info = await _fetch_video_info(request.url)
    if info:
        video_info_cache[job_id] = info

    # Use real title from video, then request param, then fallback
    title = request.title or info.get("title") or None
    if not title:
        url_tail = request.url.rstrip("/").split("/")[-1]
        title = f"Episode — {url_tail[:40]}" if url_tail else f"Episode {now.strftime('%b %d')}"

    # Format real duration
    real_duration = None
    if info.get("duration_s"):
        real_duration = _fmt_time(info["duration_s"])

    job = {
        "id": job_id,
        "url": request.url,
        "title": title,
        "status": "running",
        "created_at": now.isoformat(),
        "date": now.strftime("%b %d, %Y"),
        "duration": None,
        "band_room_id": None,
        "pipeline": {
            "transcribe": "running",
            "create": "queued",
            "repurpose": "queued",
            "validate": "queued",
            "approval": "queued",
            "publish": "queued",
        },
        "artifacts": {
            "thumbnails": [],
            "title": title,
            "description": "",
            "chapters": [],
            "short_clips": [],
        },
        "events": [],
        "video_info": info,
    }
    if real_duration:
        job["duration"] = real_duration

    jobs[job_id] = job
    job_events[job_id] = []

    # Start pipeline in background
    task = asyncio.create_task(run_pipeline(job_id, request.url))
    pipeline_tasks[job_id] = task

    return job


@app.get("/api/jobs")
async def list_jobs():
    return sorted(jobs.values(), key=lambda j: j["created_at"], reverse=True)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.post("/api/jobs/{job_id}/approve")
async def approve_job(job_id: str, request: ApproveJobRequest):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if request.action == "approve":
        job["status"] = "published"
        job["pipeline"]["approval"] = "done"
        job["pipeline"]["publish"] = "running"
        emit_event(job_id, "System", "✅ Episode approved — publishing to all platforms...", "success")
        await asyncio.sleep(2)
        job["pipeline"]["publish"] = "done"
        emit_event(job_id, "System", "🚀 Episode published successfully!", "success")
        _broadcast_job_update(job_id)

    elif request.action == "reject":
        route = request.route_to or "transcriber"
        feedback = request.feedback or "Please review and re-render."

        job["status"] = "running"
        job["pipeline"]["approval"] = "queued"

        if route == "transcriber":
            job["pipeline"].update({"transcribe": "running", "create": "queued", "repurpose": "queued", "validate": "queued"})
            stage_label = "Transcribe"
        else:
            job["pipeline"].update({"create": "running", "repurpose": "queued", "validate": "queued"})
            stage_label = "Create"

        emit_event(
            job_id,
            "Validator",
            f"↩️ Rework requested — sending back to {stage_label} stage. Feedback: {feedback}",
            "rework",
        )
        _broadcast_job_update(job_id)

        # Re-run demo steps
        asyncio.create_task(_run_demo_steps(job_id, job["url"]))

    return job


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    task = pipeline_tasks.pop(job_id, None)
    if task:
        task.cancel()
    jobs.pop(job_id)
    job_events.pop(job_id, None)
    return {"deleted": job_id}


@app.get("/api/jobs/{job_id}/clips")
async def list_clips(job_id: str):
    """List reel_*.mp4 files on disk for this job."""
    clips = _find_clips(job_id)
    return {"job_id": job_id, "clips": clips, "count": len(clips)}


@app.get("/api/clips/{filename}")
async def download_clip(filename: str):
    """Stream a single reel_*.mp4 file."""
    # Safety: only allow reel_*.mp4 filenames, no path traversal
    if not re.match(r'^reel_[\w\-]+\.mp4$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = CLIPS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(
        path=str(path),
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/jobs/{job_id}/clips/download-all")
async def download_all_clips(job_id: str):
    """Return all clips for a job as a single ZIP file."""
    clips = _find_clips(job_id)
    if not clips:
        raise HTTPException(status_code=404, detail="No clips found for this job")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for clip in clips:
            zf.write(clip["path"], arcname=clip["name"])
    buf.seek(0)

    zip_name = f"studio_desk_clips_{job_id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
    )


# ─── WebSocket ────────────────────────────────────────────────────────────────


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()

    ws_clients.setdefault(job_id, []).append(websocket)
    logger.info(f"WS connected for job {job_id}")

    try:
        # Replay existing events so the client catches up
        for event in job_events.get(job_id, []):
            await websocket.send_text(json.dumps(event))

        # Send current job state
        if job_id in jobs:
            await websocket.send_text(json.dumps({
                "type": "job_update",
                "job": jobs[job_id],
            }))

        # Keep the connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))

    except WebSocketDisconnect:
        logger.info(f"WS disconnected for job {job_id}")
    finally:
        clients = ws_clients.get(job_id, [])
        if websocket in clients:
            clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BACKEND_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
