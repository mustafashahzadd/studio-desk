import { Check, Loader2, Circle, RotateCcw } from 'lucide-react'

const STAGES = [
  { key: 'transcribe', label: 'Transcribe' },
  { key: 'create',     label: 'Create' },
  { key: 'repurpose',  label: 'Repurpose' },
  { key: 'validate',   label: 'Validate' },
  { key: 'approval',   label: 'Approval' },
  { key: 'publish',    label: 'Publish' },
]

/* Parallel group: Create + Repurpose run together */
const PARALLEL_KEYS = new Set(['create', 'repurpose'])

function StageIcon({ status }) {
  if (status === 'done')    return <Check className="w-3 h-3 text-band-green" />
  if (status === 'running') return <Loader2 className="w-3 h-3 text-band-purple animate-spin" />
  return <Circle className="w-3 h-3 text-band-muted opacity-40" />
}

function StageLabel({ status }) {
  if (status === 'done')    return <span className="text-xs text-band-green">Done</span>
  if (status === 'running') return <span className="text-xs text-band-purple-light">Running</span>
  if (status === 'pending') return <span className="text-xs text-band-yellow">Pending</span>
  if (status === 'failed')  return <span className="text-xs text-band-red">Failed</span>
  return <span className="text-xs text-band-muted">Queued</span>
}

export default function PipelineSidebar({ pipeline = {}, reworkStage }) {
  return (
    <aside className="w-52 flex-shrink-0 border-r border-band-border bg-band-bg pt-4 pb-6 flex flex-col gap-1">
      <p className="px-4 text-[10px] font-semibold uppercase tracking-widest text-band-muted mb-2">
        Pipeline
      </p>

      {STAGES.map((stage, idx) => {
        const status = pipeline[stage.key] || 'queued'
        const isParallel = PARALLEL_KEYS.has(stage.key)
        const prevIsParallel = idx > 0 && PARALLEL_KEYS.has(STAGES[idx - 1].key)

        return (
          <div key={stage.key}>
            {/* "PARALLEL" label before the first parallel stage */}
            {isParallel && !prevIsParallel && (
              <p className="px-4 text-[10px] font-semibold uppercase tracking-widest text-band-muted mt-3 mb-1">
                Parallel
              </p>
            )}

            <div
              className={`flex items-center justify-between px-4 py-2 rounded mx-2 ${
                status === 'running'
                  ? 'bg-band-purple-dim border border-band-purple border-opacity-30'
                  : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <StageIcon status={status} />
                <span className={`text-sm ${status === 'running' ? 'text-band-text' : 'text-band-muted'}`}>
                  {stage.label}
                </span>
              </div>
              <StageLabel status={status} />
            </div>
          </div>
        )
      })}

      {/* Rework button */}
      {reworkStage && (
        <div className="mx-2 mt-4 border border-band-red border-opacity-60 rounded px-3 py-2 bg-red-950 bg-opacity-30">
          <div className="flex items-center gap-1.5 text-band-red text-xs font-medium">
            <RotateCcw className="w-3 h-3" />
            Rework → {reworkStage}
          </div>
          <p className="text-[10px] text-red-400 mt-0.5 uppercase tracking-wider">Loop Active</p>
        </div>
      )}
    </aside>
  )
}
