import React from 'react'

export default function Filters({ userId, onUserId, day, onDay, onReload }) {
  return (
    <div className="filters">
      <div className="field">
        <label>Аналитик</label>
        <input value={userId} onChange={(e) => onUserId(e.target.value)} />
      </div>
      <div className="field">
        <label>Дата</label>
        <input type="date" value={day} onChange={(e) => onDay(e.target.value)} />
      </div>
      <div className="presets">
        <button onClick={() => onDay(new Date().toISOString().slice(0, 10))}>Сегодня</button>
        <button onClick={onReload} className="icon">⟳</button>
      </div>
    </div>
  )
}
