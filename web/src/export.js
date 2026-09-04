const escapeCell = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`

export function buildReportCsv(items, { day, userId }) {
  const rows = [
    ['Дата', 'Аналитик', 'ID аккаунта', 'Аккаунт', 'События', 'Сумма, ₸', 'Средний скор'],
    ...items.map((row) => [day, userId, row.account_id, row.account_name || '', row.events,
      Number(row.amount).toFixed(2), Number(row.avg_score).toFixed(3)]),
  ]
  return '\uFEFF' + rows.map((row) => row.map(escapeCell).join(';')).join('\r\n')
}

export function downloadReportCsv(items, context) {
  const url = URL.createObjectURL(new Blob([buildReportCsv(items, context)], { type: 'text/csv;charset=utf-8' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: `scoring-${context.day}.csv` })
  link.click()
  URL.revokeObjectURL(url)
}
