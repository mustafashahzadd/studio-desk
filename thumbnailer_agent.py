import os
import asyncio
import json
import uuid
import requests
from pydantic_ai import RunContext
from band.adapters import PydanticAIAdapter
from band import Agent
from dotenv import load_dotenv

load_dotenv()

# LLM endpoint config (swap when API credits available)
os.environ["OPENAI_BASE_URL"] = os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", os.environ.get("GROQ_API_KEY", ""))

# Next agent in pipeline
EDITOR_AGENT_ID = os.environ.get("EDITOR_AGENT_ID", "your-editor-agent-id")

# Image generation config - swap these when you get a proper API
IMAGE_API_URL = "https://image.pollinations.ai/prompt/"
IMAGE_WIDTH = 576   # 9:16 aspect ratio for shorts/reels
IMAGE_HEIGHT = 1024
IMAGE_TIMEOUT = 60  # Pollinations can be slow on cold start


def detect_topic(text: str) -> str:
    """Detect content topic from transcript text."""
    text_lower = text.lower()
    keyword_map = {
        "tech": ["code", "software", "app", "ai", "programming", "developer", "startup", "tech"],
        "finance": ["money", "invest", "stock", "crypto", "trading", "wealth", "passive income", "rich"],
        "fitness": ["workout", "gym", "muscle", "diet", "health", "exercise", "training"],
        "motivation": ["success", "mindset", "grind", "hustle", "discipline", "never give up", "dream"],
        "gaming": ["game", "playthrough", "stream", "esports", "fortnite", "minecraft", "gaming"],
        "education": ["learn", "tutorial", "how to", "guide", "explained", "course", "study"],
        "entertainment": ["funny", "reaction", "prank", "challenge", "viral", "comedy"],
        "relationships": ["love", "dating", "girlfriend", "boyfriend", "breakup", "crush"]
    }
    for topic, keywords in keyword_map.items():
        if any(kw in text_lower for kw in keywords):
            return topic
    return "viral"


def generate_thumbnail_prompt(topic: str, hook_text: str) -> str:
    """Build a detailed image generation prompt from topic and hook."""

    topic_styles = {
        "tech": "futuristic neon blue and purple lighting, holographic interfaces, sleek modern design",
        "finance": "gold and green color grading, luxury aesthetic, money stacks subtle background, professional",
        "fitness": "dramatic gym lighting, muscular silhouette, sweat droplets, motivational energy, orange and teal",
        "motivation": "sunrise golden hour, silhouette on mountain top, cinematic wide shot, inspirational",
        "gaming": "RGB lighting, gaming setup background, headset, intense focus, neon accents",
        "education": "clean whiteboard background, books, warm lighting, intellectual aesthetic",
        "entertainment": "bright saturated colors, confetti, party lights, high energy, fun atmosphere",
        "relationships": "soft warm lighting, romantic bokeh, heart motifs subtle, emotional close-up",
        "viral": "bold high contrast, shocking expression, vibrant colors, eye-catching, dramatic shadows"
    }

    style = topic_styles.get(topic, topic_styles["viral"])

    prompt = (
        f"cinematic vertical portrait thumbnail for social media, {topic} content, "
        f"{style}, shocked or expressive face reaction, bold eye-catching composition, "
        f"high contrast dramatic lighting, 9:16 aspect ratio, professional photography, "
        f"4k quality, viral social media style, no text no words no letters, "
        f"mood: {hook_text[:50]}"
    )
    return prompt


def generate_image(prompt: str, output_path: str) -> dict:
    """
    Generate image using Pollinations free API.
    Returns {"success": True, "path": ...} or {"success": False, "error": ...}
    """
    try:
        encoded_prompt = requests.utils.quote(prompt)
        url = (
            f"{IMAGE_API_URL}{encoded_prompt}"
            f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}"
            f"&nologo=true&seed={uuid.uuid4().int % 10000}"
            f"&enhance=true"
        )

        response = requests.get(url, timeout=IMAGE_TIMEOUT)

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return {"success": True, "path": output_path, "size_bytes": len(response.content)}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Image generation timed out (60s). Service may be overloaded."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_thumbnail_data_tool(ctx: RunContext[None], transcript_json: str) -> str:
    """
    Processes transcript and returns: thumbnail image, title, caption, hashtags, clip suggestions.
    """
    data = json.loads(transcript_json)
    segments = data.get("segments", [])
    full_text = data.get("full_transcript", "")
    video_url = data.get("video_url", "")

    # Detect topic
    topic = detect_topic(full_text)

    # Pick best hooks from first 30 seconds
    hook_segments = [s for s in segments if s["start"] < 30.0][:3]
    if not hook_segments and segments:
        hook_segments = segments[:3]

    # Build clip suggestions for editor
    clip_suggestions = []
    for seg in hook_segments:
        clip_suggestions.append({
            "start": seg["start"],
            "end": min(seg["end"], seg["start"] + 15),
            "hook_text": seg["text"][:80],
            "why": f"Strong {topic} hook from opening"
        })

    # Generate thumbnail image
    hook_text = hook_segments[0]["text"] if hook_segments else "Watch this!"
    image_prompt = generate_thumbnail_prompt(topic, hook_text)

    run_id = str(uuid.uuid4())[:8]
    image_path = f"thumbnail_{run_id}.jpg"
    image_result = generate_image(image_prompt, image_path)

    # Generate title based on topic + hook
    title_templates = {
        "tech": "This AI Secret Will Change How You Code Forever 🔥",
        "finance": "How I Made $10K in 30 Days (Step-by-Step) 💰",
        "fitness": "I Tried This Workout for 7 Days... The Results 😱",
        "motivation": "The 5AM Routine That Changed My Life 🧠",
        "gaming": "This Glitch Broke The Game Completely 🎮",
        "education": "Learn This Skill in 10 Minutes (Not 10 Hours) 📚",
        "entertainment": "You Won't Believe What Happened Next 😂",
        "relationships": "She Said THIS And I Was Speechless 💔",
        "viral": "Wait For It... This Changes Everything 👀"
    }

    # Try to make title more specific using hook text
    base_title = title_templates.get(topic, title_templates["viral"])
    if len(hook_text) > 10 and len(hook_text) < 50:
        # Use actual hook as title if it's punchy
        custom_title = hook_text[:50] + (" 🔥" if topic != "viral" else " 👀")
    else:
        custom_title = base_title

    # Generate caption
    caption = f"Wait for it... {hook_text[:60]} 😱 This is INSANE! 🔥 #viral #fyp"

    # Generate hashtags
    hashtags = [
        "#fyp", "#viral", f"#{topic}", "#trending",
        "#shorts", "#reels", "#foryou", "#mustwatch",
        "#mindblown", "#tiktok", "#youtube", "#contentcreator"
    ]

    # Best quote for text overlay on video
    hook_quote = hook_text[:100] if hook_segments else "Watch this! 👀"

    output = {
        "video_url": video_url,
        "thumbnail": {
            "prompt": image_prompt,
            "image_path": image_result.get("path") if image_result.get("success") else None,
            "image_generated": image_result.get("success", False),
            "image_error": image_result.get("error") if not image_result.get("success") else None
        },
        "title": custom_title,
        "caption": caption,
        "hashtags": hashtags,
        "hook_quote": hook_quote,
        "topic": topic,
        "transcript_summary": full_text[:200],
        "clip_suggestions": clip_suggestions
    }

    return json.dumps(output, indent=2)


# =====================================================================
# AUTO-FORWARDING ADAPTER
# =====================================================================
class AutoForwardingThumbnailer(PydanticAIAdapter):
    async def on_tool_result(self, ctx, tool_call, result):
        if tool_call.tool_name == "generate_thumbnail_data_tool":
            try:
                parsed = json.loads(result)

                # Forward to editor agent
                await self.send_message(
                    recipient_agent_id=EDITOR_AGENT_ID,
                    content=result,
                    metadata={
                        "pipeline_stage": "thumbnail_complete",
                        "source_agent": "thumbnailer",
                        "video_url": parsed.get("video_url", "")
                    }
                )

                # Build user-friendly summary
                thumb_status = "✅ generated" if parsed["thumbnail"]["image_generated"] else f"❌ failed: {parsed['thumbnail'].get('image_error', 'unknown')}"

                summary = (
                    f"🎨 Thumbnail data ready! Forwarded to @editor.\n\n"
                    f"📸 Thumbnail: {thumb_status}\n"
                    f"📝 Title: {parsed['title']}\n"
                    f"💬 Caption: {parsed['caption'][:80]}...\n"
                    f"🏷️ Topic: {parsed['topic']}\n"
                    f"✂️ Clips suggested: {len(parsed['clip_suggestions'])}"
                )

                return {"text": summary}

            except Exception as e:
                return {"text": f"❌ Error forwarding to editor: {e}"}

        return await super().on_tool_result(ctx, tool_call, result)


adapter = AutoForwardingThumbnailer(
    model="openai-chat:llama-3.1-8b-instant",
    system_prompt=(
        "You are a viral content strategist and thumbnail designer.\n"
        "When you receive a transcript JSON, call `generate_thumbnail_data_tool` immediately.\n"
        "Return the EXACT JSON output from the tool. Do NOT modify it."
    ),
    additional_tools=[generate_thumbnail_data_tool]
)


async def main():
    print("🎨 Starting Thumbnailer + Image Generation Agent...")
    print(f"📤 Next agent: {EDITOR_AGENT_ID}")
    print(f"🖼️ Image API: {IMAGE_API_URL} (free tier)")

    agent = Agent.create(
        adapter=adapter,
        agent_id=os.environ["THUMBNAILER_AGENT_ID"],
        api_key=os.environ["THUMBNAILER_API_KEY"],
    )

    print("🟢 Agent is LIVE! Waiting for transcripts from @transcriber.")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
