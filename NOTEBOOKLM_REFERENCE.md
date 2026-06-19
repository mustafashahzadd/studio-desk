# Studio Desk — Complete Reference Document for NotebookLM
## (Use this to generate a pitch deck / presentation)

---

## PROJECT OVERVIEW

**Name:** Studio Desk
**Tagline:** Drop a video. Approve the output. Publish.
**Category:** AI-Powered Content Production Automation
**Built at:** Band Hackathon, June 2026
**Platform:** Band (multi-agent AI coordination platform)

Studio Desk is an end-to-end podcast-to-video production pipeline powered by autonomous AI agents. A creator submits a single video or audio URL. Within minutes, Studio Desk produces: a timestamped transcript, 3 AI-generated thumbnail options, a video title and description, YouTube chapters with accurate timestamps, 3 short vertical clips (Reels/TikTok/Shorts) with captions burned in, and a human approval interface to review, approve, or request changes before publishing.

---

## THE PROBLEM

### Pain Point
Podcasters and video creators record 1–2 hours of content per episode. Turning that raw recording into a publishable, multi-platform product requires:

- Manual transcription and editing
- Thumbnail design
- Writing titles, descriptions, and show notes
- Identifying and cutting short clips for social media
- Adding captions and text overlays
- Uploading and scheduling to multiple platforms

**This post-production work takes 6–10 hours per episode.** Most solo creators either skip it entirely (losing reach) or pay $200–$500 per episode to a video editor.

### Scale of the Problem
- 4+ million active podcasts globally
- Average podcast releases 2 episodes/week
- Top creators spend more time editing than recording
- Small creators simply cannot afford professional post-production
- Agencies and media networks managing 10–50 shows face this problem at massive scale

### What Exists Today
- Descript: manual editing tool, not automated
- Opus Clip: clips only, no full pipeline
- Riverside.fm: recording only
- Adobe Podcast: audio enhancement only
- None of them deliver a complete, observable, multi-agent automated pipeline

---

## THE SOLUTION

### Studio Desk in One Sentence
An AI agent pipeline that takes a raw video URL as input and produces publication-ready content — thumbnails, clips, chapters, title, description — with a human-in-the-loop approval step before anything goes live.

### Key Value Propositions

**1. One Input, Everything Out**
Paste a URL (YouTube, direct MP3/MP4, local file). That single action triggers the entire pipeline. No configuration, no templates to fill, no tools to chain manually.

**2. Multi-Agent, Not Monolithic**
Different AI agents handle different jobs in parallel. The Transcriber runs simultaneously with nothing else. Once the transcript is ready, the Creator and Repurposer agents run in parallel — one builds the thumbnail and metadata, the other cuts the clips. A Validator checks everything before it reaches the human. This parallelism cuts total processing time dramatically.

**3. Fully Observable**
Every agent action is visible in real time in the Band Room feed — a live log of all inter-agent communication. Creators see exactly what the AI is doing and why. This is not a black box.

**4. Human-in-the-Loop**
Nothing publishes without human approval. The creator sees a full preview — video player, chapters, clips, thumbnails — and can approve in one click or send feedback back to any stage of the pipeline with a rework instruction.

**5. Rework Loops**
If the output isn't right, the creator writes feedback and routes it back to any agent (e.g., "Re-cut clip 2 starting at 4:30 not 3:00" → routes to Repurposer only). The pipeline re-runs only the necessary stages, not everything from scratch.

---

## TECHNICAL ARCHITECTURE

### System Components

**Frontend**
- React + Vite + Tailwind CSS
- Three screens: Dashboard, Job Detail (Band Room), Approval
- Real-time updates via WebSocket connection to backend
- Fully responsive dark-mode interface

**Backend**
- FastAPI (Python) REST API + WebSocket server
- In-memory job state management
- yt-dlp for video metadata extraction (title, duration, thumbnails)
- ffprobe fallback for local file duration detection
- Band SDK integration for creating chat rooms and triggering agents
- ZIP packaging and streaming for clip downloads

**Agent Layer (Band Platform)**
Three autonomous Python agents running as persistent Band workers:

1. **Transcriber Agent** (Agent ID: 1b8b7fb0)
   - Listens for video URLs in its Band room
   - Downloads audio using yt-dlp
   - Runs OpenAI Whisper v3 via Groq API for fast transcription
   - Produces full JSON transcript with word-level timestamps and 312 segments
   - Hands off to @Creator and @Repurposer simultaneously

2. **Thumbnailer Agent** (Agent ID: 9a348c22)
   - Receives transcript JSON from Transcriber
   - Analyzes transcript for topic detection and hook identification
   - Generates thumbnail image using Pollinations AI (free) or Stability AI
   - Produces: thumbnail image, title, caption, hashtags, clip timestamps
   - Forwards complete package to Editor Agent

3. **Editor Agent** (Agent ID: 05e2f506)
   - Receives clip suggestions and thumbnail data from Thumbnailer
   - Downloads full video using yt-dlp
   - Cuts up to 3 clips using ffmpeg (each 15–45 seconds)
   - Burns text overlays with hook quotes using ffmpeg drawtext filter
   - Saves reel_*.mp4 files to disk
   - Reports completion back to the Band room

**Communication Layer: Band Platform**
- All agents communicate through Band rooms (shared coordination channels)
- Messages use @mentions for routing (e.g., "@Transcriber please process this URL")
- REST API: AsyncRestClient for room creation, participant management, message sending
- WebSocket: Real-time event streaming for live Band Room feed in UI
- The backend creates one Band room per job and adds the relevant agents as participants

### Data Flow

```
1. User pastes URL → POST /api/jobs
2. Backend calls yt-dlp/ffprobe to get real video metadata (title, duration)
3. Backend creates Band chat room via Band REST API
4. Backend adds Transcriber agent to room
5. Backend sends "@Transcriber please transcribe: <url>"
6. Transcriber agent downloads audio, runs Whisper, produces transcript
7. Transcriber @mentions Creator and Repurposer — parallel handoff
8. Creator: analyzes transcript → generates thumbnail → title/description
9. Repurposer: identifies clip timestamps → ffmpeg cuts → burns captions
10. Validator: checks audio consistency across segments
11. All agents emit timestamped JSON events back to the Band room
12. Backend WebSocket relays all room events to the browser in real time
13. UI shows live Band Room feed + filling Artifacts panel
14. Status → "Awaiting Approval" → human reviews and approves/rejects
15. On approval: publishes (marks done, clips downloadable as ZIP)
16. On rejection: feedback routes back to specified agent → rework loop
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + Vite 5 |
| UI styling | Tailwind CSS |
| Frontend routing | React Router v6 |
| Icons | Lucide React |
| Backend framework | FastAPI + Uvicorn |
| Real-time comms | WebSocket (native FastAPI) |
| Agent platform | Band SDK (PydanticAI adapter) |
| Transcription | OpenAI Whisper v3 via Groq |
| LLM analysis | LLaMA 3.1 8B via AIML API |
| Image generation | Pollinations AI (free) / Stability AI |
| Video processing | ffmpeg + ffmpeg-python |
| Video download | yt-dlp |
| Metadata extraction | yt-dlp + ffprobe |

---

## PRODUCT SCREENS

### Screen 1: Dashboard
- Clean dark interface with "Studio Desk" branding
- File drag-and-drop zone for local audio/video files
- URL paste input for YouTube, direct media links
- "Start Job" button triggers the pipeline
- Recent Jobs table with live status badges:
  - Green: Published
  - Purple: Running
  - Yellow: Awaiting Approval
  - Red: Failed
- Columns: Job Name, Status, Date, Duration

### Screen 2: Job Detail (Band Room View)
Three-panel layout:

**Left Panel — Pipeline Sidebar**
- Live stage indicators: Transcribe → [Create + Repurpose parallel] → Validate → Approval → Publish
- Each stage shows: Done (green check), Running (purple spinner), Queued (grey dot)
- "Rework → Create" badge with "LOOP ACTIVE" indicator when rework is triggered

**Center Panel — Band Room Feed**
- Live scrolling event log labeled "Band Room • LIVE powered by Band"
- Log lines in monospace font: timestamp, sender, message, tool label (via Whisper / via ffmpeg / via AI/ML API)
- Special styled cards for:
  - Handoff messages (speech bubble with @mention tags)
  - Rework/rejection events (red-bordered card with rework route)
  - Approval ready events (purple highlighted line)
- Event counter in top right

**Right Panel — Artifacts**
- "UPDATING" badge when pipeline is active
- Thumbnail Options: 3 image previews
- Title: editable text field showing real video title
- Description: multi-line text
- Chapters: list with accurate timestamps and section titles
- Short Clips: 3 preview thumbnails with caption labels

### Screen 3: Approval Page
- Full-width video player with play button and progress bar
- Displays real video duration
- Episode Title and Description sections
- Chapters list with clickable timestamps
- Short Clips grid (3 clips with thumbnails)
- Download Clips section:
  - Lists all reel_*.mp4 files found on disk
  - Individual Download button per clip
  - "Download All as ZIP" button
  - Auto-polls every 4 seconds for new clip files
- Action buttons:
  - ✅ Approve & Publish (green) → marks job published, pipeline complete
  - ❌ Request Changes (red) → expands feedback form
- Request Changes form:
  - Free text field for feedback
  - Radio buttons: "Send to Transcriber" or "Send to Repurposer"
  - Submit Feedback → triggers rework loop

---

## DEMO SCRIPT (3 minutes)

### Hook [0:00–0:20]
"Every week, podcasters record an hour of gold — and then spend another 8 hours turning it into thumbnails, clips, captions, and posts. That's not creating. That's editing. Studio Desk kills that 8 hours."

### Problem [0:20–0:45]
"The problem isn't making the content. It's the pipeline after. Thumbnail, title, short clips for TikTok and Reels, captions, chapters for YouTube — all manually. Most creators either skip it or pay an editor $300 an episode."

### Demo [0:45–1:30]
"I drop a video URL and hit Start Job. This is the Band Room — a live coordination channel between our AI agents. The Transcriber picks up the video, runs Whisper v3, and produces a full timestamped transcript. That gets handed off simultaneously to the Creator agent — which generates thumbnails and metadata — and the Repurposer agent — which identifies and cuts the best 15-second clips. Watch the Artifacts panel fill in on the right in real time."

### Approval Loop [1:30–2:00]
"When it's done, the creator gets one approval screen. Preview the video, check the chapters, see the clips. Approve in one click. Or write feedback and route it back to any stage — the rework loop kicks off automatically."

### Why Band [2:00–2:30]
"The reason this works is Band. Each agent is a standalone worker listening on the Band platform. They communicate through a shared room, passing structured JSON as messages with @mentions for routing. The pipeline is observable — you see every agent action live. And it's extensible — drop in a new agent for subtitles, translations, or YouTube upload without touching anything else."

### Value + Close [2:30–3:00]
"For an independent podcaster: 8 hours of editing becomes 20 minutes of review. For a media company running 20 shows a week: that's one editor's entire salary — automated. Studio Desk. Drop a video, approve the output, publish. This is what AI-native production looks like."

---

## BUSINESS MODEL

### Target Customers
- **Tier 1:** Independent podcasters (1–10 episodes/month)
- **Tier 2:** Content agencies managing multiple shows
- **Tier 3:** Media companies and networks (10–100 shows/week)

### Pricing Model (proposed)
| Plan | Price | Jobs/month | Features |
|---|---|---|---|
| Creator | $29/mo | 10 jobs | All formats, download clips |
| Studio | $99/mo | 50 jobs | + Custom agent prompts, priority processing |
| Enterprise | Custom | Unlimited | + White-label, custom integrations, SLA |

### Unit Economics
- Average editor charges $200–$500/episode
- Studio Desk at $29/mo handles 10 episodes = **$2.90/episode vs $300/episode**
- 100x cost reduction for the creator

---

## COMPETITIVE DIFFERENTIATION

| Feature | Studio Desk | Descript | Opus Clip | Riverside |
|---|---|---|---|---|
| Full pipeline (transcript → clips → thumbnail) | ✅ | ❌ | ❌ | ❌ |
| Multi-agent parallel processing | ✅ | ❌ | ❌ | ❌ |
| Observable agent communication | ✅ | ❌ | ❌ | ❌ |
| Human approval / rework loop | ✅ | ❌ | ❌ | ❌ |
| Extensible agent architecture | ✅ | ❌ | ❌ | ❌ |
| Local file support | ✅ | ✅ | ❌ | ✅ |
| Real-time live feed | ✅ | ❌ | ❌ | ❌ |

---

## WHAT BAND ENABLES

Band is the coordination layer that makes the multi-agent architecture possible:

1. **Shared Rooms:** Each job gets its own Band chat room. All agents join it and communicate through structured messages — like a project channel dedicated to one episode.

2. **@Mention Routing:** Agents are triggered by @mentions in messages. The backend sends "@Transcriber please process this URL" and Band routes it to the correct running agent.

3. **Parallel Handoff:** The Transcriber sends one message mentioning both @Creator and @Repurposer. Band delivers it to both simultaneously — enabling true parallel processing.

4. **Observable by Default:** Every message, every tool call, every agent response flows through the Band room. The Studio Desk UI subscribes to this stream and renders it live.

5. **Decoupled Architecture:** Each agent is an independent Python process that can be deployed anywhere. Adding a new capability (e.g., an agent that posts to Instagram) requires writing one new agent script — nothing else changes.

---

## FUTURE ROADMAP

### v1.1 (Next 30 days)
- Direct YouTube upload via YouTube Data API v3
- TikTok and Instagram Reels auto-posting
- Custom prompt templates per creator/show

### v1.2 (60 days)
- Transcript editor with clip timeline scrubber
- A/B thumbnail testing with engagement prediction
- Multi-language transcript and caption support

### v2.0 (90 days)
- Scheduling queue with platform-specific optimal posting times
- Analytics dashboard (views, engagement per clip)
- White-label for agencies
- Webhook support for custom integrations

---

## KEY METRICS TO HIGHLIGHT

- **Time saved:** 8 hours → 20 minutes per episode (95% reduction)
- **Cost saved:** $300/episode editor → $2.90/episode (100x cheaper)
- **Parallelism:** Creator + Repurposer agents run simultaneously (not sequentially)
- **Pipeline stages:** 6 (Transcribe → Create → Repurpose → Validate → Approval → Publish)
- **Output artifacts per job:** 3 thumbnails + 3 short clips + title + description + chapters
- **Supported inputs:** YouTube URLs, direct MP3/MP4, local files
- **Supported formats:** MP3, WAV, FLAC, M4A, MP4

---

## TEAM / HACKATHON CONTEXT

Built at the Band Hackathon, June 2026. The project demonstrates the Band platform's multi-agent coordination capabilities applied to a high-value, real-world production workflow. The architecture is intentionally extensible — every agent is a standalone Band worker, and new capabilities can be added by writing one new agent script without modifying the existing pipeline.
