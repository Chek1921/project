const BASE = '/api'
export function currentUserId() { return localStorage.getItem('user_id') || 'u-101' }
async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json', 'X-User-Id': currentUserId(), ...options.headers }, ...options })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
export const fetchReport = (userId, day) => request(`/report?${new URLSearchParams({ user_id: userId, day })}`)
export const fetchActivity = (userId, day) => request(`/report/activity?${new URLSearchParams({ user_id: userId, day })}`)
export const fetchQueueStats = () => request('/queue/stats')
export const createEvent = (event) => request('/ingest', { method: 'POST', body: JSON.stringify(event) })
