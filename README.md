<div align="center">

# 🎬 Studio Desk

### Drop a video. Approve the output. Publish.

**An AI-powered multi-agent pipeline that turns raw podcast recordings into fully published, multi-platform content — thumbnails, short clips, chapters, and descriptions — in minutes instead of hours.**

[![Built with Band](https://img.shields.io/badge/Built%20with-Band-7c3aed?style=flat-square)](https://band.ai)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018-61dafb?style=flat-square)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square)](https://python.org)

</div>

---

## ✨ What It Does

Creators record. Editors spend 8 hours turning that into publishable content. Studio Desk kills those 8 hours.

Submit a single YouTube URL, direct audio link, or local video file. Studio Desk's multi-agent pipeline handles everything else:

| Output | How |
|---|---|
| 📝 Full transcript with timestamps | Whisper v3 via Groq |
| 🖼️ 3 AI-generated thumbnail options | Pollinations AI |
| ✏️ Title, description, hashtags | LLaMA 3.1 via AIML API |
| 🕐 YouTube chapters (accurate timestamps) | Proportional from real video duration |
| ✂️ 3 short vertical clips (Reels/TikTok/Shorts) | ffmpeg with text overlays |
| ✅ Human approval before anything publishes | Built-in review UI with rework loops |

---

## 🏗️ Architecture

```
React Frontend (Vite + Tailwind)
       │
       │  REST + WebSocket
       ▼
FastAPI Backend  ──────────────────────────────────────┐
       │                                               │
       │  Band REST API                                │ WebSocket
       │  (create room, add agent, send @mention)      │ (live event stream)
       ▼                                               │
Band Platform  ◄───────────────────────────────────────┘
       │
       ├──► Transcriber Agent   (Whisper v3 → JSON transcript)
       │         │
       │         ▼ parallel handoff via @mention
       ├──► Thumbnailer Agent   (thumbnail + title + clip plan)
       │         │
       │         ▼
       └──► Editor Agent        (ffmpeg cuts → reel_*.mp4 files)
```

Every agent communicates through a **shared Band room** — observable, real-time, and extensible. Adding a new capability (e.g. auto-posting to TikTok) means writing one new agent script.

---

## 🖥️ Screenshots

### Dashboard — Start a new job
Drop a file or paste any URL. See all recent jobs with live status.

### Job Detail — Band Room feed
Watch agents coordinate in real time. Artifacts appear in the right panel as they're generated.

### Approval — Review before publishing
Full video preview, chapters, short clips, and a download button. Approve in one click or request changes with routing to any pipeline stage.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- ffmpeg installed and in PATH
- Band platform agent credentials (see [band.ai](https://band.ai))

### 1. Clone the repo
```bash
git clone https://github.com/mustafashahzadd/studio-desk.git
cd studio-desk
```

### 2. Set up environment variables
```bash
cp env.template .env
# Edit .env with your credentials
```

Required `.env` values:
```env
TRANSCRIBER_AGENT_ID=your-transcriber-agent-id
TRANSCRIBER_API_KEY=your-transcriber-api-key

THUMBNAILER_AGENT_ID=your-thumbnailer-agent-id
THUMBNAILER_API_KEY=your-thumbnailer-api-key

EDITOR_AGENT_ID=your-editor-agent-id
EDITOR_API_KEY=your-editor-api-key

BAND_HUMAN_API_KEY=your-human-api-key   # from app.band.ai → Settings

GROQ_API_KEY=your-groq-api-key          # for Whisper transcription
OPENAI_BASE_URL=https://api.aimlapi.com/v1
OPENAI_API_KEY=your-aiml-api-key        # for LLM analysis
```

### 3. Install Python dependencies
```bash
pip install -r backend/requirements.txt
pip install -r pyproject.toml  # or: pip install band-sdk[pydanticai] groq yt-dlp ffmpeg-python
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 5. Start everything

**Terminal 1 — Backend**
```bash
cd backend
python main.py
# → http://localhost:8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
# → http://localhost:5173
```

**Terminal 3 — Thumbnailer Agent** *(optional — for real pipeline)*
```bash
python thumbnailer_agent.py
```

**Terminal 4 — Editor Agent** *(optional — for real pipeline)*
```bash
python editor_agent.py
```

### 6. Open the app
Navigate to **http://localhost:5173**, paste any YouTube URL, and click **Start Job**.

> **No agents?** No problem. The backend includes a full demo simulation — paste any URL and watch the complete pipeline animate with realistic events, real video metadata, and proportional timestamps.

---

## 📁 Project Structure

```
studio-desk/
├── backend/
│   ├── main.py              # FastAPI server — REST API + WebSocket
│   ├── band_service.py      # Band SDK integration (rooms, agents, events)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Screen 1: job list + start new job
│   │   │   ├── JobDetail.jsx    # Screen 2: Band Room live feed
│   │   │   └── Approval.jsx     # Screen 3: review + download + publish
│   │   ├── components/
│   │   │   ├── PipelineSidebar.jsx  # Live pipeline stage indicators
│   │   │   ├── BandRoomFeed.jsx     # Real-time agent event log
│   │   │   └── ArtifactsPanel.jsx   # Thumbnails, chapters, clips
│   │   ├── api.js               # All fetch/WebSocket calls
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── thumbnailer_agent.py     # Band agent: transcript → thumbnail + clip plan
├── editor_agent.py          # Band agent: clip plan → ffmpeg cuts → reel_*.mp4
├── env.template             # Environment variable template
├── pyproject.toml
└── NOTEBOOKLM_REFERENCE.md  # Full reference doc for pitch deck generation
```

---

## 🔄 How the Pipeline Works

```
1.  User pastes URL → POST /api/jobs
2.  Backend calls yt-dlp/ffprobe → gets real title, duration, thumbnail
3.  Backend creates Band chat room via Band REST API
4.  Backend adds Transcriber agent as participant
5.  Backend sends "@Transcriber please transcribe: <url>"
6.  Transcriber downloads audio → runs Whisper v3 → JSON transcript
7.  Transcriber @mentions @Creator and @Repurposer simultaneously
8.  Thumbnailer: transcript → topic detection → thumbnail → title/clips plan
9.  Editor: clip plan → yt-dlp download → ffmpeg cuts → reel_*.mp4
10. Validator: consistency checks across segments
11. All events stream to browser via WebSocket in real time
12. Status → "Awaiting Approval" → human reviews
13. Approve → published ✅  |  Reject → rework loop with agent routing
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS, React Router v6, Lucide React |
| Backend | FastAPI, Uvicorn, Python 3.11 |
| Agent platform | Band SDK with PydanticAI adapter |
| Transcription | OpenAI Whisper v3 via Groq |
| LLM analysis | LLaMA 3.1 8B Instant via AIML API |
| Image generation | Pollinations AI (free) |
| Video processing | ffmpeg, ffmpeg-python |
| Video/audio download | yt-dlp |
| Metadata extraction | yt-dlp + ffprobe |
| Real-time comms | WebSocket (native FastAPI) |

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/jobs` | Create job, trigger pipeline |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/:id` | Get job details + artifacts |
| `POST` | `/api/jobs/:id/approve` | Approve or reject with feedback |
| `GET` | `/api/jobs/:id/clips` | List generated reel_*.mp4 files |
| `GET` | `/api/clips/:filename` | Download a single clip |
| `GET` | `/api/jobs/:id/clips/download-all` | Download all clips as ZIP |
| `WS` | `/ws/:id` | Real-time job event stream |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ at the **Band Hackathon, June 2026**

[band.ai](https://band.ai) · [Report Bug](https://github.com/mustafashahzadd/studio-desk/issues) · [Request Feature](https://github.com/mustafashahzadd/studio-desk/issues)

</div>
