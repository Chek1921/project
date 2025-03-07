const BASE = '/api'

// user_id аналитика лежит в localStorage, SSO подключим во втором квартале
export function currentUserId() {
  return localStorage.getItem('user_id') || 'u-101'
}

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`, {
    headers: { 'X-User-Id': currentUserId() },
  })
  return res.json()
}

export function fetchReport(userId, day) {
  return get('/report', { user_id: userId, day })
}

export function fetchQueueStats() {
  return get('/queue/stats').catch(() => ({}))
}
