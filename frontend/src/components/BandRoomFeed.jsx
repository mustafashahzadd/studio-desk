import { useEffect, useRef } from 'react'

const SENDER_COLORS = {
  Transcriber: 'text-blue-400',
  Creator:     'text-band-purple-light',
  Repurposer:  'text-purple-400',
  Validator:   'text-yellow-400',
  System:      'text-band-muted',
}

const VIA_LABELS = {
  Whisper:   'via Whisper',
  'AI/ML API': 'via AI/ML API',
  ffmpeg:    'via ffmpeg',
  Featherless: 'via Featherless',
}

function EventRow({ event }) {
  const senderColor = SENDER_COLORS[event.sender] || 'text-band-muted'

  if (event.type === 'handoff') {
    /* Speech-bubble style card */
    return (
      <div className="animate-fade-in my-3 bg-band-card border border-band-border rounded-lg px-4 py-3">
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`w-7 h-7 rounded-full bg-band-surface border border-band-border flex items-center justify-center text-xs font-bold ${senderColor}`}>
            {event.sender[0]}
          </span>
          <span className={`text-xs font-semibold ${senderColor}`}>{event.sender}</span>
          <span className="text-xs text-band-muted font-mono">{event.timestamp}</span>
        </div>
        <p className="text-sm text-band-text">{event.message}</p>
        {event.mentions && (
          <div className="flex gap-2 mt-2">
            {event.mentions.map((m) => (
              <span key={m} className="text-xs text-band-purple-light bg-band-purple-dim px-2 py-0.5 rounded">
                {m}
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (event.type === 'rework') {
    return (
      <div className="animate-fade-in my-3 bg-red-950 bg-opacity-40 border border-red-800 border-opacity-50 rounded-lg px-4 py-3">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-7 h-7 rounded-full bg-red-900 border border-red-700 flex items-center justify-center text-xs font-bold text-red-400">
            {event.sender[0]}
          </span>
          <span className="text-xs font-semibold text-red-400">{event.sender}</span>
          <span className="bg-red-800 text-red-200 text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider font-semibold">
            Rework
          </span>
          <span className="text-xs text-band-muted font-mono">{event.timestamp}</span>
        </div>
        <p className="text-sm text-red-200">{event.message}</p>
        {event.route && (
          <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
            <span>→</span>
            <span className="bg-red-900 bg-opacity-50 px-1.5 py-0.5 rounded">{event.route}</span>
          </p>
        )}
      </div>
    )
  }

  if (event.type === 'approval') {
    return (
      <div className="animate-fade-in my-2 py-2 border-t border-band-border">
        <p className="text-xs text-band-purple-light font-mono">{event.timestamp} — {event.message}</p>
      </div>
    )
  }

  /* Default: log line */
  return (
    <div className="animate-fade-in flex items-start gap-3 py-1">
      <span className="font-mono text-xs text-band-muted w-10 flex-shrink-0">{event.timestamp}</span>
      <span className={`font-mono text-xs font-semibold flex-shrink-0 ${senderColor}`}>
        {event.sender}:
      </span>
      <span className="font-mono text-xs text-band-text-dim flex-1">{event.message}</span>
      {event.via && (
        <span className="font-mono text-[10px] text-band-muted flex-shrink-0 italic">{event.via}</span>
      )}
    </div>
  )
}

export default function BandRoomFeed({ events = [], eventCount }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Feed header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-band-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">Band Room</span>
          <span className="flex items-center gap-1 text-xs text-band-red font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-band-red animate-pulse-dot" />
            LIVE
          </span>
          <span className="text-xs text-band-muted">powered by Band</span>
        </div>
        <span className="text-xs text-band-muted font-mono">{eventCount ?? events.length} events</span>
      </div>

      {/* Event feed */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-0.5">
        {events.map((ev) => (
          <EventRow key={ev.id || ev.timestamp + ev.message} event={ev} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
