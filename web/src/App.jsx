import React, { useEffect, useMemo, useState } from 'react'
import Filters from './components/Filters.jsx'
import ReportTable from './components/ReportTable.jsx'
import { fetchQueueStats, fetchReport, currentUserId } from './api.js'

const number = new Intl.NumberFormat('ru-RU')
const money = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const localDay = (date = new Date()) => new Date(date - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
const changeDay = (day, amount) => { const date = new Date(`${day}T12:00:00`); date.setDate(date.getDate() + amount); return localDay(date) }

export default function App() {
  const [userId, setUserId] = useState(currentUserId()), [day, setDay] = useState(localDay()), [report, setReport] = useState(null), [queue, setQueue] = useState({}), [state, setState] = useState('loading'), [sort, setSort] = useState('amount'), [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true; setState('loading')
    Promise.all([fetchReport(userId, day), fetchQueueStats()]).then(([nextReport, nextQueue]) => { if (active) { setReport(nextReport); setQueue(nextQueue); setState('ready') } }).catch(() => active && setState('error'))
    return () => { active = false }
  }, [userId, day, reload])
  const items = useMemo(() => [...(report?.items || [])].sort((a, b) => sort === 'amount' ? Number(b.amount) - Number(a.amount) : Number(b.avg_score) - Number(a.avg_score)), [report, sort])
  const average = report?.total_events ? items.reduce((sum, item) => sum + Number(item.avg_score) * item.events, 0) / report.total_events : 0
  const exportReport = () => {
    const rows = [['Аккаунт', 'События', 'Сумма, ₸', 'Средний скор'], ...items.map((row) => [row.account_name || row.account_id, row.events, Number(row.amount).toFixed(2), Number(row.avg_score).toFixed(3)])]
    const data = '\uFEFF' + rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(';')).join('\n'), link = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([data], { type: 'text/csv;charset=utf-8' })), download: `scoring-${day}.csv` })
    link.click(); URL.revokeObjectURL(link.href)
  }
  return <main className="page"><header className="masthead"><div><h1>Скоринг</h1><p className="meta">Сводка по аккаунтам · очередь: <b className="num">{number.format(queue.pending || 0)}</b> в ожидании, <b className="num">{number.format(queue.done || 0)}</b> обработано</p></div><Filters userId={userId} onUserId={setUserId} day={day} onDay={setDay} onPrevious={() => setDay(changeDay(day, -1))} onNext={() => setDay(changeDay(day, 1))} /></header>
    <section className="metrics" aria-label="Ключевые показатели"><Metric label="Сумма" value={`${money.format(report?.total_amount || 0)} ₸`} /><Metric label="События" value={number.format(report?.total_events || 0)} /><Metric label="Средний скор" value={average.toFixed(3).replace('.', ',')} /></section>
    <section className="panel"><div className="panelHead"><div><p className="eyebrow">По аккаунтам</p><span className="count">{number.format(items.length)} строк</span></div><div className="actions"><button className="chip" type="button" aria-pressed={sort === 'amount'} onClick={() => setSort('amount')}>По сумме</button><button className="chip" type="button" aria-pressed={sort === 'score'} onClick={() => setSort('score')}>По скору</button><button className="btn" type="button" disabled={!items.length} onClick={exportReport}>Экспорт CSV</button></div></div><ReportTable items={items} state={state} day={day} onRetry={() => setReload((value) => value + 1)} /></section>
  </main>
}
function Metric({ label, value }) { return <div className="metric"><span className="eyebrow">{label}</span><strong className="num">{value}</strong></div> }
