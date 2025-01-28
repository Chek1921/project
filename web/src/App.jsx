import React, { useEffect, useState } from 'react'
import { fetchReport, fetchQueueStats, currentUserId } from './api.js'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export default function App() {
  const [userId, setUserId] = useState(currentUserId())
  const [day, setDay] = useState(todayIso())
  const [report, setReport] = useState(null)
  const [queue, setQueue] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    fetchReport(userId, day)
      .then((data) => !cancelled && setReport(data))
      .catch((e) => !cancelled && setError(e.message))
    fetchQueueStats()
      .then((data) => !cancelled && setQueue(data))
      .catch(() => {})
    return () => { cancelled = true }
  }, [userId, day])

  const items = report?.items ?? []

  return (
    <div className="app">
      <h1>Скоринг — панель аналитика</h1>
      <p className="sub">Суточная сводка по аккаунтам. Очередь: {queue.pending ?? 0} в ожидании, {queue.done ?? 0} обработано.</p>

      <div className="controls">
        <div>
          <label htmlFor="user">Аналитик</label>
          <input id="user" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </div>
        <div>
          <label htmlFor="day">Дата</label>
          <input id="day" type="date" value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
      </div>

      {error && <p className="err">Не удалось загрузить отчёт: {error}</p>}

      {report && (
        <div className="totals">
          <div>Сумма<b>{report.total_amount.toLocaleString('ru-RU')} ₸</b></div>
          <div>Событий<b>{report.total_events}</b></div>
          <div>Аккаунтов<b>{items.length}</b></div>
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>Аккаунт</th>
            <th className="num">События</th>
            <th className="num">Сумма</th>
            <th className="num">Средний скор</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.account_id}>
              <td>{row.account_name || row.account_id}</td>
              <td className="num">{row.events}</td>
              <td className="num">{Number(row.amount || 0).toLocaleString('ru-RU')}</td>
              <td className="num">{Number(row.avg_score || 0).toFixed(3)}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={4} style={{ color: '#6a737d' }}>За выбранные сутки данных нет</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
