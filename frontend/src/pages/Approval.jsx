import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Play, CheckCircle2, XCircle, ArrowLeft, Download, Package, Film, Loader2 } from 'lucide-react'
import { getJob, approveJob, listClips, clipDownloadUrl, allClipsZipUrl } from '../api'

export default function Approval() {
  const { jobId } = useParams()
  const navigate = useNavigate()

  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [routeTo, setRouteTo] = useState('transcriber')
  const [showReject, setShowReject] = useState(false)
  const [clips, setClips] = useState([])
  const [clipsLoading, setClipsLoading] = useState(false)

  useEffect(() => {
    getJob(jobId).then(setJob).catch(() => navigate('/'))
  }, [jobId])

  // Poll for real reel_*.mp4 files every 4s
  useEffect(() => {
    let active = true
    async function pollClips() {
      setClipsLoading(true)
      try {
        const data = await listClips(jobId)
        if (active) setClips(data.clips || [])
      } catch (_) {}
      setClipsLoading(false)
    }
    pollClips()
    const id = setInterval(pollClips, 4000)
    return () => { active = false; clearInterval(id) }
  }, [jobId])

  async function handleApprove() {
    setLoading(true)
    try {
      await approveJob(jobId, 'approve')
      navigate(`/jobs/${jobId}`)
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleReject() {
    if (!feedback.trim()) {
      alert('Please describe the changes needed.')
      return
    }
    setLoading(true)
    try {
      await approveJob(jobId, 'reject', feedback, routeTo)
      navigate(`/jobs/${jobId}`)
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-band-bg flex items-center justify-center">
        <div className="text-band-muted text-sm animate-pulse">Loading…</div>
      </div>
    )
  }

  const { artifacts = {} } = job
  const { thumbnails = [], title, description, chapters = [], short_clips = [] } = artifacts

  return (
    <div className="min-h-screen bg-band-bg text-band-text">
      {/* ── Top Bar ── */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-band-border">
        <Link
          to={`/jobs/${jobId}`}
          className="flex items-center gap-2 text-sm text-band-muted hover:text-band-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Job
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-band-yellow flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-band-yellow animate-pulse-dot" />
            Awaiting Approval
          </span>
          <span className="text-xs text-band-muted font-mono">{job.title}</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 pt-8 pb-20">
        {/* Header */}
        <div className="mb-6">
          <p className="text-xs text-band-purple-light mb-1">{job.title}</p>
          <h1 className="text-xl font-bold">Pipeline ready for your approval</h1>
        </div>

        {/* Video preview */}
        <div className="relative bg-band-surface rounded-xl border border-band-border flex items-center justify-center aspect-video mb-5 overflow-hidden">
          {thumbnails[0] ? (
            <img src={thumbnails[0]} alt="Preview" className="w-full h-full object-cover opacity-40" />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-purple-900/20 to-black" />
          )}
          <button className="absolute w-14 h-14 rounded-full bg-band-purple hover:bg-purple-600 flex items-center justify-center shadow-xl transition-colors">
            <Play className="w-6 h-6 text-white fill-current ml-0.5" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-3 mb-6">
          <span className="text-xs font-mono text-band-muted">0:00</span>
          <div className="flex-1 h-1 bg-band-border rounded-full">
            <div className="w-0 h-full bg-band-purple rounded-full" />
          </div>
          <span className="text-xs font-mono text-band-muted">{job.duration || '—'}</span>
        </div>

        {/* Metadata */}
        <section className="mb-5">
          <h2 className="text-base font-semibold mb-1">Episode Title</h2>
          <p className="text-sm text-band-text-dim">{title || job.title}</p>
        </section>

        {description && (
          <section className="mb-5">
            <h2 className="text-base font-semibold mb-1">Description</h2>
            <p className="text-sm text-band-text-dim leading-relaxed">{description}</p>
          </section>
        )}

        {/* Chapters */}
        {chapters.length > 0 && (
          <section className="mb-5">
            <h2 className="text-base font-semibold mb-2">Chapters</h2>
            <ul className="space-y-1.5">
              {chapters.map((ch, i) => (
                <li key={i} className="flex items-center gap-3">
                  <span className="font-mono text-xs text-band-purple-light w-10 flex-shrink-0">{ch.time}</span>
                  <span className="text-sm text-band-text">{ch.title}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Short clips */}
        {short_clips.length > 0 && (
          <section className="mb-6">
            <h2 className="text-base font-semibold mb-2">Short Clips</h2>
            <p className="text-xs text-band-muted mb-3">AI-generated vertical clips for social, ready to post</p>
            <div className="flex gap-3">
              {short_clips.map((clip, i) => (
                <div key={i} className="flex flex-col gap-1.5 w-28">
                  <div className="w-28 h-20 rounded-lg border border-band-border bg-band-card overflow-hidden flex items-center justify-center">
                    {clip.thumbnail ? (
                      <img src={clip.thumbnail} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <Play className="w-5 h-5 text-band-muted" />
                    )}
                  </div>
                  <p className="text-[10px] text-band-muted leading-tight text-center line-clamp-2">
                    {clip.label || clip.hook_text}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Download Clips ── */}
        <section className="mb-6 border border-band-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 bg-band-card border-b border-band-border">
            <div className="flex items-center gap-2">
              <Film className="w-4 h-4 text-band-purple-light" />
              <h2 className="text-sm font-semibold">Download Clips</h2>
              {clipsLoading && <Loader2 className="w-3 h-3 text-band-muted animate-spin" />}
            </div>
            {clips.length > 1 && (
              <a
                href={allClipsZipUrl(jobId)}
                download
                className="flex items-center gap-1.5 text-xs bg-band-purple hover:bg-purple-700 text-white px-3 py-1.5 rounded transition-colors font-medium"
              >
                <Package className="w-3.5 h-3.5" />
                Download All as ZIP
              </a>
            )}
          </div>

          {clips.length === 0 ? (
            <div className="px-4 py-6 text-center">
              <Film className="w-8 h-8 text-band-border mx-auto mb-2" />
              <p className="text-sm text-band-muted">No clip files found yet</p>
              <p className="text-xs text-band-muted mt-1 leading-relaxed">
                Start <span className="font-mono text-band-text-dim">editor_agent.py</span> and
                let it process the video — <span className="font-mono text-band-text-dim">reel_*.mp4</span> files
                will appear here automatically.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-band-border">
              {clips.map((clip, i) => (
                <li key={clip.name} className="flex items-center justify-between px-4 py-3 hover:bg-band-card transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-band-purple-dim flex items-center justify-center flex-shrink-0">
                      <Film className="w-4 h-4 text-band-purple-light" />
                    </div>
                    <div>
                      <p className="text-sm text-band-text font-mono">{clip.name}</p>
                      <p className="text-xs text-band-muted">{clip.size_mb} MB · MP4</p>
                    </div>
                  </div>
                  <a
                    href={clipDownloadUrl(clip.name)}
                    download={clip.name}
                    className="flex items-center gap-1.5 text-xs border border-band-border hover:border-band-purple text-band-text-dim hover:text-band-purple-light px-3 py-1.5 rounded transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ── Action Buttons ── */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="flex items-center gap-2 bg-band-green hover:bg-green-600 disabled:opacity-50 text-black font-semibold px-5 py-2.5 rounded-md text-sm transition-colors"
          >
            <CheckCircle2 className="w-4 h-4" />
            {loading ? 'Publishing…' : 'Approve & Publish'}
          </button>
          <button
            onClick={() => setShowReject(!showReject)}
            disabled={loading}
            className="flex items-center gap-2 bg-band-red hover:bg-red-600 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-md text-sm transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Request Changes
          </button>
        </div>

        {/* ── Request Changes Form ── */}
        {showReject && (
          <div className="border border-band-border rounded-xl p-5 bg-band-card space-y-4">
            <h3 className="font-semibold text-sm">Request Changes</h3>

            <div>
              <label className="text-xs text-band-muted mb-1.5 block">Prompt for changes</label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Describe what needs to be changed…"
                rows={3}
                className="w-full bg-band-surface border border-band-border rounded-md px-3 py-2.5 text-sm text-band-text placeholder-band-muted focus:outline-none focus:border-band-purple resize-none transition-colors"
              />
            </div>

            <div>
              <label className="text-xs text-band-muted mb-2 block">Route feedback to</label>
              <div className="flex flex-col gap-2">
                {[
                  { value: 'transcriber', label: 'Send to Transcriber' },
                  { value: 'repurposer',  label: 'Send to Repurposer' },
                ].map((opt) => (
                  <label key={opt.value} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="routeTo"
                      value={opt.value}
                      checked={routeTo === opt.value}
                      onChange={() => setRouteTo(opt.value)}
                      className="accent-band-purple"
                    />
                    <span className="text-sm text-band-text">{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={handleReject}
              disabled={loading || !feedback.trim()}
              className="flex items-center justify-center gap-2 bg-band-purple hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              {loading ? 'Submitting…' : 'Submit Feedback'}
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
