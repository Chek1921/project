import React, { useEffect, useState } from 'react'
import { fetchAnalysts } from '../api.js'

export default function Filters({ userId, onUserId, day, onDay, onPrevious, onNext }) {
  const [analysts, setAnalysts] = useState([])
  const [status, setStatus] = useState('loading')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setStatus('loading')
    fetchAnalysts().then((users) => {
      if (!active) return
      setAnalysts(users)
      setStatus('ready')
    }).catch(() => { if (active) setStatus('error') })
    return () => { active = false }
  }, [retry])
  const selected = analysts.some((analyst) => analyst.id === userId)
  useEffect(() => {
    if (status === 'ready' && analysts.length && !selected) onUserId(analysts[0].id)
  }, [analysts, selected, status, onUserId])
  return <div className="filters">
    <div className="daynav"><button type="button" aria-label="Предыдущий день" onClick={onPrevious}>‹</button><input aria-label="Дата отчёта" type="date" value={day} onChange={(event) => onDay(event.target.value)} /><button type="button" aria-label="Следующий день" onClick={onNext}>›</button></div>
    <label className="analyst">Аналитик
      <select value={selected ? userId : ''} disabled={status !== 'ready' || !analysts.length} onChange={(event) => onUserId(event.target.value)}>
        {(!selected || status !== 'ready') && <option value="">{status === 'loading' ? 'Загрузка…' : status === 'error' ? 'Не удалось загрузить' : analysts.length ? 'Выберите аналитика' : 'Нет аналитиков'}</option>}
        {analysts.map((analyst) => <option key={analyst.id} value={analyst.id}>{analyst.name || analyst.id}</option>)}
      </select>
    </label>
    {status === 'error' && <button type="button" className="btn" onClick={() => setRetry((value) => value + 1)}>Повторить загрузку аналитиков</button>}
  </div>
}
