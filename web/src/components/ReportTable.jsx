import React from 'react'

export default function ReportTable({ items }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Аккаунт</th>
          <th>События</th>
          <th>Сумма</th>
          <th>Средний скор</th>
        </tr>
      </thead>
      <tbody>
        {items.map((row, index) => (
          <tr key={index}>
            <td>{row.account_name || row.account_id}</td>
            <td>{row.events}</td>
            <td>{Number(row.amount || 0).toLocaleString('ru-RU')}</td>
            <td>{row.avg_score}</td>
          </tr>
        ))}
        {items.length === 0 && (
          <tr>
            <td colSpan={4}>Нет данных</td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
