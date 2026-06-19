import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Play, Link, Clock, ChevronRight } from 'lucide-react'
import { createJob, listJobs } from '../api'

/* ── Status badge ─────────────────────────────────────────────── */
function StatusBadge({ status }) {
  const map = {
    running:           { dot: 'bg-band-purple',  text: 'text-band-purple-light', label: 'Running' },
    published:         { dot: 'bg-band-green',   text: 'text-band-green',        label: 'Published' },
    awaiting_approval: { dot: 'bg-band-yellow',  text: 'text-band-yellow',       label: 'Awaiting Approval' },
    failed:            { dot: 'bg-band-red',      text: 'text-band-red',          label: 'Failed' },
    queued:            { dot: 'bg-band-muted',    text: 'text-band-muted',        label: 'Queued' },
  }
  const s = map[status] || map.queued
  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-xs ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} animate-pulse-dot`} />
      {s.label}
    </span>
  )
}

/* ── Recent jobs row ──────────────────────────────────────────── */
function JobRow({ job, onClick }) {
  return (
    <tr
      className="border-b border-band-border hover:bg-band-card cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3 text-sm text-band-text font-medium">{job.title}</td>
      <td className="px-4 py-3">
        <StatusBadge status={job.status} />
      </td>
      <td className="px-4 py-3 font-mono text-xs text-band-muted">{job.date || job.created_at?.slice(0, 10)}</td>
      <td className="px-4 py-3 font-mono text-xs text-band-muted">{job.duration || '—'}</td>
    </tr>
  )
}

/* ── Dashboard ────────────────────────────────────────────────── */
export default function Dashboard() {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState([])
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef()

  /* Seed some mock jobs for the demo */
  useEffect(() => {
    fetchJobs()
    const id = setInterval(fetchJobs, 5000)
    return () => clearInterval(id)
  }, [])

  async function fetchJobs() {
    try {
      const data = await listJobs()
      setJobs(data)
    } catch (_) {}
  }

  async function handleStart(e) {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    try {
      const job = await createJob(url.trim())
      navigate(`/jobs/${job.id}`)
    } catch (err) {
      alert('Failed to start job: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      setUrl(`file://${file.name}`)
    }
  }

  /* Demo jobs shown when backend has no jobs */
  const displayJobs = jobs.length > 0 ? jobs : [
    { id: 'demo1', title: 'Ep 47 — AI Agents Deep Dive',     status: 'published',         date: 'Jun 18, 2026', duration: '1h 24m' },
    { id: 'demo2', title: 'Ep 46 — Startup Fundraising',     status: 'running',           date: 'Jun 17, 2026', duration: '52m' },
    { id: 'demo3', title: 'Ep 45 — Design Systems at Scale', status: 'awaiting_approval', date: 'Jun 15, 2026', duration: '1h 08m' },
    { id: 'demo4', title: 'Ep 44 — Remote Work Culture',     status: 'published',         date: 'Jun 12, 2026', duration: '47m' },
    { id: 'demo5', title: 'Ep 43 — Observability 101',       status: 'running',           date: 'Jun 10, 2026', duration: '1h 12m' },
  ]

  return (
    <div className="min-h-screen bg-band-bg text-band-text">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-band-border">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-full bg-band-purple flex items-center justify-center text-white text-xs font-bold">S</span>
          <span className="font-semibold text-sm">Studio Desk</span>
        </div>
        <nav className="flex items-center gap-6">
          {['Jobs', 'Templates', 'Settings'].map((item) => (
            <button key={item} className="text-sm text-band-text-dim hover:text-band-text transition-colors">
              {item}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Main ── */}
      <main className="max-w-5xl mx-auto px-6 pt-12 pb-20">
        <h1 className="text-3xl font-bold mb-2">Start a new job</h1>
        <p className="text-band-muted mb-8 text-sm">Upload audio or paste a media URL to begin your podcast-to-video pipeline</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg flex flex-col items-center justify-center py-14 gap-3 cursor-pointer transition-colors ${
              dragOver
                ? 'border-band-purple bg-band-purple-dim'
                : 'border-band-border hover:border-band-muted'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-8 h-8 text-band-muted" />
            <p className="text-sm text-band-muted">Drop audio or video file</p>
            <p className="text-xs text-band-purple-light cursor-pointer hover:underline">or click to browse</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,video/*"
              className="hidden"
              onChange={(e) => {
                if (e.target.files[0]) setUrl(`file://${e.target.files[0].name}`)
              }}
            />
          </div>

          {/* URL input */}
          <div className="flex flex-col justify-center gap-3">
            <p className="text-sm text-band-muted font-medium">Or paste a media URL</p>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStart(e)}
              placeholder="https://example.com/episode.mp3"
              className="w-full bg-band-card border border-band-border rounded-md px-3 py-2.5 text-sm text-band-text placeholder-band-muted focus:outline-none focus:border-band-purple transition-colors"
            />
            <button
              onClick={handleStart}
              disabled={loading || !url.trim()}
              className="flex items-center justify-center gap-2 bg-band-purple hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md px-5 py-2.5 text-sm font-medium transition-colors w-fit"
            >
              <Play className="w-4 h-4 fill-current" />
              {loading ? 'Starting…' : 'Start Job'}
            </button>
            <p className="text-xs text-band-muted">Supported: MP3, WAV, FLAC, M4A, MP4</p>
          </div>
        </div>

        {/* ── Recent Jobs ── */}
        <h2 className="text-xl font-semibold mb-4">Recent Jobs</h2>
        <div className="border border-band-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-band-border bg-band-surface">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-band-muted uppercase tracking-wider">Job Name</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-band-muted uppercase tracking-wider">Status</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-band-muted uppercase tracking-wider">Date</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-band-muted uppercase tracking-wider">Duration</th>
              </tr>
            </thead>
            <tbody className="bg-band-bg">
              {displayJobs.map((job) => (
                <JobRow
                  key={job.id}
                  job={job}
                  onClick={() => {
                    if (!job.id.startsWith('demo')) navigate(`/jobs/${job.id}`)
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
