import React, { useEffect, useState } from 'react'
import Filters from './components/Filters.jsx'
import ReportTable from './components/ReportTable.jsx'
import { fetchReport, fetchQueueStats, currentUserId } from './api.js'

export default function App() {
  const [userId, setUserId] = useState(currentUserId())
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10))
  const [report, setReport] = useState(null)
  const [queue, setQueue] = useState({})
  const [tick, setTick] = useState(0)

  useEffect(() => {
    fetchReport(userId, day).then(setReport)
    fetchQueueStats().then(setQueue)
  }, [userId, day, tick])

  const items = report ? report.items : []
  const total = items.reduce((acc, row) => acc + parseFloat(row.amount || 0), 0)

  return (
    <div className="app">
      <h1>Скоринг</h1>
      <p className="sub">
        Суточная сводка по аккаунтам. Очередь: {queue.pending || 0} в ожидании,{' '}
        {queue.done || 0} обработано.
      </p>

      <Filters
        userId={userId}
        onUserId={setUserId}
        day={day}
        onDay={setDay}
        onReload={() => setTick(tick + 1)}
      />

      <div className="totals">
        <div>
          Сумма<b>{total.toLocaleString('ru-RU')} ₸</b>
        </div>
        <div>
          Событий<b>{report ? report.total_events : 0}</b>
        </div>
        <div>
          Аккаунтов<b>{items.length}</b>
        </div>
      </div>

      <ReportTable items={items} />
    </div>
  )
}
