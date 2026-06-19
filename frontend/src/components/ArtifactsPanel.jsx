import { useNavigate } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'

export default function ArtifactsPanel({ artifacts = {}, jobId, jobStatus }) {
  const navigate = useNavigate()
  const { thumbnails = [], title, description, chapters = [], short_clips = [] } = artifacts

  return (
    <aside className="w-72 flex-shrink-0 border-l border-band-border bg-band-bg overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-3 border-b border-band-border">
        <h2 className="font-semibold text-sm">Artifacts</h2>
        {jobStatus === 'awaiting_approval' && (
          <span className="text-[10px] font-mono text-band-purple-light bg-band-purple-dim px-2 py-0.5 rounded animate-pulse-dot">
            UPDATING
          </span>
        )}
      </div>

      <div className="px-4 py-4 space-y-5">
        {/* Thumbnails */}
        {thumbnails.length > 0 && (
          <section>
            <p className="text-[10px] uppercase tracking-widest text-band-muted font-semibold mb-2">
              Thumbnail Options
            </p>
            <div className="flex gap-2 flex-wrap">
              {thumbnails.map((src, i) => (
                <div key={i} className="w-20 h-12 rounded overflow-hidden border border-band-border flex-shrink-0">
                  <img src={src} alt={`Thumbnail ${i + 1}`} className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Title */}
        {title && (
          <section>
            <p className="text-[10px] uppercase tracking-widest text-band-muted font-semibold mb-1.5">Title</p>
            <div className="bg-band-card border border-band-border rounded px-3 py-2 text-sm text-band-text">
              {title}
            </div>
          </section>
        )}

        {/* Description */}
        {description && (
          <section>
            <p className="text-[10px] uppercase tracking-widest text-band-muted font-semibold mb-1.5">Description</p>
            <p className="text-xs text-band-text-dim leading-relaxed">{description}</p>
          </section>
        )}

        {/* Chapters */}
        {chapters.length > 0 && (
          <section>
            <p className="text-[10px] uppercase tracking-widest text-band-muted font-semibold mb-2">Chapters</p>
            <ul className="space-y-1">
              {chapters.map((ch, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="font-mono text-xs text-band-purple-light w-10 flex-shrink-0">{ch.time}</span>
                  <span className="text-xs text-band-text">{ch.title}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Short Clips */}
        {short_clips.length > 0 && (
          <section>
            <p className="text-[10px] uppercase tracking-widest text-band-muted font-semibold mb-2">Short Clips</p>
            <div className="flex gap-2 flex-wrap">
              {short_clips.map((clip, i) => (
                <div key={i} className="w-20 flex flex-col gap-1">
                  <div className="w-20 h-14 rounded overflow-hidden border border-band-border bg-band-card flex items-center justify-center">
                    {clip.thumbnail ? (
                      <img src={clip.thumbnail} alt={`Clip ${i + 1}`} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-band-muted text-xs">▶</span>
                    )}
                  </div>
                  <p className="text-[10px] text-band-text-dim leading-tight text-center line-clamp-2">
                    {clip.label || clip.hook_text || `Clip ${i + 1}`}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Approval CTA */}
        {jobStatus === 'awaiting_approval' && jobId && (
          <div className="pt-2">
            <button
              onClick={() => navigate(`/jobs/${jobId}/approve`)}
              className="w-full flex items-center justify-center gap-2 bg-band-purple hover:bg-purple-700 text-white rounded-md py-2.5 text-sm font-medium transition-colors"
            >
              <CheckCircle2 className="w-4 h-4" />
              Review & Approve
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
