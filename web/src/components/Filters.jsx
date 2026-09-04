import React, { useEffect, useState } from 'react'

export default function Filters({ userId, onUserId, day, onDay, onPrevious, onNext }) {
  const [draftUserId, setDraftUserId] = useState(userId)
  useEffect(() => setDraftUserId(userId), [userId])
  const applyUser = () => { const value = draftUserId.trim(); if (value && value !== userId) onUserId(value) }
  return <div className="filters"><div className="daynav"><button type="button" aria-label="Предыдущий день" onClick={onPrevious}>‹</button><input aria-label="Дата отчёта" type="date" value={day} onChange={(event) => onDay(event.target.value)} /><button type="button" aria-label="Следующий день" onClick={onNext}>›</button></div><label className="analyst">Аналитик<input value={draftUserId} onChange={(event) => setDraftUserId(event.target.value)} onBlur={applyUser} onKeyDown={(event) => { if (event.key === 'Enter') { applyUser(); event.currentTarget.blur() } }} /></label></div>
}
