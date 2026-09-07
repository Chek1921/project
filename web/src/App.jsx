import React, { useEffect, useMemo, useState } from 'react'
import Filters from './components/Filters.jsx'
import ReportTable from './components/ReportTable.jsx'
import { fetchActivity, fetchQueueStats, fetchReport, currentUserId } from './api.js'
import { downloadReportCsv } from './export.js'

const number = new Intl.NumberFormat('ru-RU')
const money = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const localDay = (date = new Date()) => new Date(date - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
const changeDay = (day, shift) => { const next = new Date(`${day}T12:00:00`); next.setDate(next.getDate() + shift); return localDay(next) }

export default function App() {
  const [userId, setUserId] = useState(currentUserId()), [day, setDay] = useState(localDay()), [report, setReport] = useState(null), [previousReport, setPreviousReport] = useState(null), [activity, setActivity] = useState([]), [queue, setQueue] = useState(null), [state, setState] = useState('loading'), [error, setError] = useState(''), [sort, setSort] = useState('amount'), [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true; setState('loading'); setError(''); setReport(null); setPreviousReport(null); setActivity([]); setQueue(null)
    fetchReport(userId, day).then((nextReport) => { if (active) { setReport(nextReport); setState('ready') } }).catch((nextError) => { if (active) { setError(nextError.message); setState('error') } })
    Promise.allSettled([fetchReport(userId, changeDay(day, -1)), fetchActivity(userId, day), fetchQueueStats()]).then(([previous, nextActivity, nextQueue]) => { if (!active) return; if (previous.status === 'fulfilled') setPreviousReport(previous.value); if (nextActivity.status === 'fulfilled') setActivity(nextActivity.value.hours); if (nextQueue.status === 'fulfilled') setQueue(nextQueue.value) })
    return () => { active = false }
  }, [userId, day, reload])
  const items = useMemo(() => [...(report?.items || [])].sort((a, b) => sort === 'amount' ? Number(b.amount) - Number(a.amount) : Number(b.avg_score) - Number(a.avg_score)), [report, sort])
  const average = averageScore(report), previousAverage = averageScore(previousReport), changeUser = (value) => { localStorage.setItem('user_id', value); setUserId(value) }
  const exportReport = () => downloadReportCsv(items, { day, userId })
  return <main className="page"><header className="masthead"><div><p className="eyebrow">Analytics / lead scoring</p><h1>Скоринг</h1><p className="meta">Общая очередь сервиса: <b className="num">{queue ? number.format(queue.pending || 0) : '—'}</b> в ожидании, <b className="num">{queue ? number.format(queue.done || 0) : '—'}</b> обработано</p></div><Filters userId={userId} onUserId={changeUser} day={day} onDay={setDay} onPrevious={() => setDay(changeDay(day, -1))} onNext={() => setDay(changeDay(day, 1))} /></header>
    <Pulse activity={activity} day={day} state={state} queue={queue} />
    <section className="metrics" aria-label="Ключевые показатели" aria-busy={state === 'loading'}><Metric label="Сумма" value={state === 'ready' ? <>{money.format(report?.total_amount || 0)}<small>₸</small></> : '—'} current={report?.total_amount} previous={previousReport?.total_amount} /><Metric label="События" value={state === 'ready' ? number.format(report?.total_events || 0) : '—'} current={report?.total_events} previous={previousReport?.total_events} /><Metric label="Средний скор" value={state === 'ready' ? average.toFixed(3).replace('.', ',') : '—'} current={average} previous={previousAverage} difference /></section>
    <section className="panel"><div className="panelHead"><div><p className="eyebrow">По аккаунтам</p><span className="count num">{number.format(items.length)} строк</span></div><div className="actions"><button className="chip" type="button" aria-pressed={sort === 'amount'} onClick={() => setSort('amount')}>По сумме</button><button className="chip" type="button" aria-pressed={sort === 'score'} onClick={() => setSort('score')}>По скору</button><button className="btn" type="button" disabled={!items.length} onClick={exportReport}>Экспорт CSV</button></div></div><ReportTable items={items} state={state} day={day} error={error} onRetry={() => setReload((value) => value + 1)} /></section>
  </main>
}
function averageScore(value) { return value?.total_events ? value.items.reduce((sum, item) => sum + Number(item.avg_score) * item.events, 0) / value.total_events : 0 }
function Metric({ label, value, current = 0, previous = 0, difference = false }) { const delta = Number(current || 0) - Number(previous || 0), direction = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat', comparable = Number(previous) !== 0, shown = comparable ? difference ? Math.abs(delta).toFixed(3).replace('.', ',') : `${Math.abs(delta / previous * 100).toFixed(1).replace('.', ',')}%` : ''; return <article className="metric"><span className="eyebrow">{label}</span><strong className="num">{value}</strong><span className={`delta ${comparable ? direction : 'flat'}`}>{comparable ? <><span aria-hidden="true">{direction === 'up' ? '▲' : direction === 'down' ? '▼' : '●'}</span><span className="num">{shown}</span><span>ко вчера</span></> : 'Нет данных за вчера'}</span></article> }
function QueueProgress({ queue }) {
  if (!queue) return <span>статус общей очереди неизвестен</span>
  const unfinished = (queue.pending || 0) + (queue.processing || 0), failed = queue.failed || 0
  if (unfinished || failed) return <span>общая очередь: {unfinished > 0 && <>осталось <b className="num">{number.format(unfinished)}</b></>}{unfinished > 0 && failed > 0 && ', '}{failed > 0 && <>ошибок <b className="num">{number.format(failed)}</b></>}</span>
  return <span>{queue.done ? 'общая очередь обработана полностью' : 'общая очередь пуста'}</span>
}
function Pulse({ activity, day, state, queue }) { const max = Math.max(...activity, 1), peak = activity.indexOf(max), peakCount = activity[peak] || 0, now = new Date(), currentHour = day === now.toISOString().slice(0, 10) ? now.getUTCHours() : -1, summary = activity.map((count, hour) => `${hour}:00 — ${count || 0}`).join(', '), note = state === 'loading' ? 'Обновляем почасовую активность…' : peakCount ? <>Пик в <b className="num">{String(peak).padStart(2, '0')}:00</b> · <b className="num">{number.format(peakCount)}</b> событий</> : 'За выбранный день активности нет'; return <section className="pulse" aria-busy={state === 'loading'}><div className="pulseTop"><p className="eyebrow">Пульс суток</p><span className="pulseNote">{note}{state !== 'loading' && <> · <QueueProgress queue={queue} /></>}</span></div><div className="bars" role="img" aria-label={`Почасовая активность: ${summary}`}>{Array.from({ length: 24 }, (_, hour) => <span aria-hidden="true" className={`bar ${hour === peak && activity[hour] ? 'peak ' : ''}${hour === currentHour ? 'now' : ''}`} style={{ '--bar-height': `${Math.max(activity[hour] ? 8 : 3, activity[hour] / max * 100)}%`, '--bar-delay': `${hour * 12}ms` }} key={hour} title={`${hour}:00 — ${activity[hour] || 0} событий`} />)}</div><div className="hours"><span>00</span><span>06</span><span>12</span><span>18</span><span>23</span></div></section> }
