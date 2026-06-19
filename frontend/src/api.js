// In production, set VITE_API_BASE_URL to your backend URL (e.g. https://your-app.onrender.com)
const API_ORIGIN = import.meta.env.VITE_API_BASE_URL || ''
const BASE = `${API_ORIGIN}/api`

export async function createJob(url, title) {
  const res = await fetch(`${BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, title }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function listJobs() {
  const res = await fetch(`${BASE}/jobs`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getJob(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function approveJob(jobId, action, feedback, routeTo) {
  const res = await fetch(`${BASE}/jobs/${jobId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, feedback, route_to: routeTo }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function listClips(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}/clips`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()  // { clips: [{name, size_mb}], count }
}

/** Direct download URL for a single clip — use as <a href={...}> */
export function clipDownloadUrl(filename) {
  return `${BASE}/clips/${encodeURIComponent(filename)}`
}

/** Direct download URL for all clips as ZIP */
export function allClipsZipUrl(jobId) {
  return `${BASE}/jobs/${jobId}/clips/download-all`
}

/** Open a WebSocket to stream real-time events for a job. */
export function openJobSocket(jobId, onMessage) {
  const wsOrigin = API_ORIGIN
    ? API_ORIGIN.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  const ws = new WebSocket(`${wsOrigin}/ws/${jobId}`)

  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data))
    } catch (_) {}
  }

  ws.onerror = (err) => console.warn('WS error', err)

  return ws
}
