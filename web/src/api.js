const BASE = '/api'

// user_id аналитика хранится в localStorage — SSO подключим во втором квартале
export function currentUserId() {
  return localStorage.getItem('user_id') || 'u-101'
}

async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}${path}${qs ? `?${qs}` : ''}`, {
    headers: { 'X-User-Id': currentUserId() },
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const fetchReport = (userId, day) => get('/report', day ? { user_id: userId, day } : { user_id: userId })
export const fetchAccounts = () => get('/accounts')
export const fetchQueueStats = () => get('/queue/stats')
