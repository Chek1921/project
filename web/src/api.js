const BASE = '/api'
export function currentUserId() { return localStorage.getItem('user_id') || 'u-101' }
async function get(path, params = {}) { const qs = new URLSearchParams(params).toString(), res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`, { headers: { 'X-User-Id': currentUserId() } }); if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json() }
export const fetchReport = (userId, day) => get('/report', { user_id: userId, day })
export const fetchQueueStats = () => get('/queue/stats')
