import os
import asyncio
import json
import subprocess
import textwrap
import uuid
import yt_dlp
from pydantic_ai import RunContext
from band.adapters import PydanticAIAdapter
from band import Agent
from dotenv import load_dotenv

load_dotenv()

# LLM endpoint config
os.environ["OPENAI_BASE_URL"] = os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", os.environ.get("GROQ_API_KEY", ""))


def download_video(video_url: str, output_path: str) -> bool:
    """Download video using yt-dlp. Returns True on success."""
    try:
        ydl_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def cut_clip(input_path: str, start: float, end: float, output_path: str) -> bool:
    """Cut a video clip using ffmpeg."""
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", input_path,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"❌ Cut failed: {e}")
        return False


def add_text_overlay(input_path: str, text: str, output_path: str) -> bool:
    """Add centered text overlay to video using ffmpeg."""
    # Clean and wrap text for ffmpeg
    safe_text = text.replace("'", "\'").replace(":", "\:").replace("%", "\%")
    wrapped = textwrap.fill(safe_text, width=22)

    # Use drawtext filter with box background
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf",
        f"drawtext=text='{wrapped}':fontcolor=white:fontsize=40:"
        f"box=1:boxcolor=black@0.65:boxborderw=10:"
        f"x=(w-text_w)/2:y=(h*0.72):line_spacing=10:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "-c:a", "copy",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            # Fallback without fontfile (system default)
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf",
                f"drawtext=text='{wrapped}':fontcolor=white:fontsize=36:"
                f"box=1:boxcolor=black@0.65:boxborderw=8:"
                f"x=(w-text_w)/2:y=(h*0.72):line_spacing=8",
                "-c:a", "copy",
                output_path
            ]
            result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        print(f"❌ Text overlay failed: {e}")
        return False


def edit_video_tool(ctx: RunContext[None], editor_input_json: str) -> str:
    """
    Downloads video, cuts clips from suggestions, adds text overlays.
    Returns paths to final reel files + metadata.
    """
    data = json.loads(editor_input_json)
    video_url = data.get("video_url", "")
    clip_suggestions = data.get("clip_suggestions", [])
    hook_quote = data.get("hook_quote", "")
    metadata = {
        "title": data.get("title", ""),
        "caption": data.get("caption", ""),
        "hashtags": data.get("hashtags", []),
        "topic": data.get("topic", ""),
        "thumbnail": data.get("thumbnail", {})
    }

    if not video_url:
        return json.dumps({"error": "No video_url provided", "clips": []}, indent=2)

    if not clip_suggestions:
        return json.dumps({"error": "No clip suggestions provided", "clips": []}, indent=2)

    run_id = str(uuid.uuid4())[:8]
    temp_video = f"temp_video_{run_id}.mp4"

    # Download full video
    print(f"📥 [{run_id}] Downloading video...")
    if not download_video(video_url, temp_video):
        return json.dumps({"error": "Failed to download video", "clips": []}, indent=2)

    results = []

    for i, clip in enumerate(clip_suggestions[:3]):  # Max 3 clips
        clip_id = f"{run_id}_clip{i}"
        print(f"✂️ [{run_id}] Processing clip {i+1}/{len(clip_suggestions[:3])}")

        try:
            start = float(clip.get("start", 0))
            end = float(clip.get("end", 15))
            hook_text = clip.get("hook_text", hook_quote)[:100]

            # Validate times
            if end <= start or end - start > 60:
                end = start + 15
            if end - start < 3:
                end = start + 5

            # Step 1: Cut clip
            raw_clip = f"clip_{clip_id}_raw.mp4"
            if not cut_clip(temp_video, start, end, raw_clip):
                raise RuntimeError("Failed to cut clip")

            # Step 2: Add text overlay
            final_clip = f"reel_{clip_id}.mp4"
            if not add_text_overlay(raw_clip, hook_text, final_clip):
                # If text overlay fails, use raw clip as fallback
                os.rename(raw_clip, final_clip)
                print(f"⚠️ Text overlay failed, using raw clip")

            # Cleanup raw
            if os.path.exists(raw_clip):
                os.remove(raw_clip)

            results.append({
                "file": final_clip,
                "start": start,
                "end": end,
                "duration": end - start,
                "text": hook_text,
                "status": "success"
            })
            print(f"✅ [{run_id}] Clip {i+1} saved: {final_clip}")

        except Exception as e:
            print(f"❌ [{run_id}] Clip {i+1} failed: {e}")
            results.append({
                "file": None,
                "start": clip.get("start"),
                "end": clip.get("end"),
                "error": str(e),
                "status": "failed"
            })

    # Cleanup full video
    if os.path.exists(temp_video):
        os.remove(temp_video)

    success_count = len([r for r in results if r["status"] == "success"])

    output = {
        "video_url": video_url,
        "run_id": run_id,
        "clips_produced": success_count,
        "total_requested": len(clip_suggestions[:3]),
        "clips": results,
        "metadata": metadata,
        "upload_ready": success_count > 0
    }

    return json.dumps(output, indent=2)


# =====================================================================
# EDITOR ADAPTER
# =====================================================================
adapter = PydanticAIAdapter(
    model="openai-chat:llama-3.1-8b-instant",
    system_prompt=(
        "You are a video editor for short-form content.\n"
        "When you receive editor input JSON, call `edit_video_tool` immediately.\n"
        "Return the EXACT JSON output from the tool."
    ),
    additional_tools=[edit_video_tool]
)


async def main():
    print("✂️ Starting Clip Editor Agent...")
    print("🔧 Requires: ffmpeg installed, yt-dlp")

    agent = Agent.create(
        adapter=adapter,
        agent_id=os.environ["EDITOR_AGENT_ID"],
        api_key=os.environ["EDITOR_API_KEY"],
    )

    print("🟢 Agent is LIVE! Waiting for data from @thumbnailer.")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
