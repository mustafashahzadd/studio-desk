import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Clock, ArrowLeft, ChevronRight } from 'lucide-react'
import { getJob, openJobSocket } from '../api'
import PipelineSidebar from '../components/PipelineSidebar'
import BandRoomFeed from '../components/BandRoomFeed'
import ArtifactsPanel from '../components/ArtifactsPanel'

/* Elapsed timer display */
function ElapsedTimer({ startedAt }) {
  const [elapsed, setElapsed] = useState('00:00')

  useEffect(() => {
    const start = new Date(startedAt).getTime()
    function tick() {
      const diff = Math.floor((Date.now() - start) / 1000)
      const m = String(Math.floor(diff / 60)).padStart(2, '0')
      const s = String(diff % 60).padStart(2, '0')
      setElapsed(`${m}:${s}`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [startedAt])

  return (
    <span className="flex items-center gap-1 font-mono text-xs text-band-muted">
      <Clock className="w-3 h-3" />
      {elapsed}
    </span>
  )
}

export default function JobDetail() {
  const { jobId } = useParams()
  const navigate = useNavigate()

  const [job, setJob] = useState(null)
  const [events, setEvents] = useState([])
  const [reworkStage, setReworkStage] = useState(null)
  const wsRef = useRef(null)

  /* Initial fetch */
  useEffect(() => {
    getJob(jobId).then((j) => {
      setJob(j)
      setEvents(j.events || [])
    }).catch(() => navigate('/'))
  }, [jobId])

  /* WebSocket for real-time updates */
  useEffect(() => {
    const ws = openJobSocket(jobId, handleSocketMessage)
    wsRef.current = ws
    return () => ws.close()
  }, [jobId])

  function handleSocketMessage(msg) {
    if (!msg) return

    if (msg.type === 'job_update') {
      setJob(msg.job)
    } else if (msg.type === 'pipeline_update') {
      setJob((prev) =>
        prev ? { ...prev, pipeline: { ...prev.pipeline, [msg.stage]: msg.status } } : prev
      )
    } else if (msg.type === 'artifacts_update') {
      setJob((prev) => prev ? { ...prev, artifacts: msg.artifacts } : prev)
    } else if (msg.type === 'ping') {
      /* keep-alive */
    } else if (msg.id) {
      /* Regular event */
      setEvents((prev) => {
        if (prev.find((e) => e.id === msg.id)) return prev
        const updated = [...prev, msg]

        if (msg.type === 'rework') {
          setReworkStage('Create')
          setTimeout(() => setReworkStage(null), 10000)
        }
        return updated
      })
    }
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-band-bg flex items-center justify-center">
        <div className="text-band-muted text-sm animate-pulse">Loading…</div>
      </div>
    )
  }

  const isRunning = job.status === 'running'
  const isApproval = job.status === 'awaiting_approval'
  const isPublished = job.status === 'published'

  return (
    <div className="h-screen flex flex-col bg-band-bg text-band-text overflow-hidden">
      {/* ── Top Bar ── */}
      <header className="flex items-center justify-between px-5 py-2.5 border-b border-band-border flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <span className="w-6 h-6 rounded-full bg-band-purple flex items-center justify-center text-white text-[10px] font-bold">S</span>
            <span className="font-semibold text-xs text-band-muted">Studio Desk</span>
          </Link>
          <ChevronRight className="w-3 h-3 text-band-muted" />
          <span className="text-sm font-medium truncate max-w-xs">{job.title}</span>
        </div>

        <div className="flex items-center gap-4">
          {/* Status pill */}
          <span className={`flex items-center gap-1.5 text-xs font-medium ${
            isRunning ? 'text-band-purple-light' :
            isApproval ? 'text-band-yellow' :
            isPublished ? 'text-band-green' : 'text-band-muted'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse-dot ${
              isRunning ? 'bg-band-purple' :
              isApproval ? 'bg-band-yellow' :
              isPublished ? 'bg-band-green' : 'bg-band-muted'
            }`} />
            {isRunning ? 'Running' : isApproval ? 'Awaiting Approval' : isPublished ? 'Published' : job.status}
          </span>

          {job.created_at && <ElapsedTimer startedAt={job.created_at} />}

          {isApproval && (
            <button
              onClick={() => navigate(`/jobs/${jobId}/approve`)}
              className="text-xs bg-band-purple hover:bg-purple-700 text-white px-3 py-1.5 rounded transition-colors font-medium"
            >
              Review & Approve
            </button>
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Pipeline sidebar */}
        <PipelineSidebar pipeline={job.pipeline} reworkStage={reworkStage} />

        {/* Band Room feed */}
        <main className="flex-1 overflow-hidden">
          <BandRoomFeed events={events} eventCount={events.length} />
        </main>

        {/* Artifacts panel */}
        <ArtifactsPanel
          artifacts={job.artifacts}
          jobId={jobId}
          jobStatus={job.status}
        />
      </div>
    </div>
  )
}
