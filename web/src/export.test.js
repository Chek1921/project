import assert from 'node:assert/strict'
import test from 'node:test'
import { buildReportCsv } from './export.js'

test('CSV keeps stable identifiers, context, precision and escaped names', () => {
  const csv = buildReportCsv([{
    account_id: 'cst-0007', account_name: 'АО "Вектор"', events: 2,
    amount: 1234.5, avg_score: 0.81234,
  }], { day: '2026-09-04', userId: 'u-101' })

  assert.ok(csv.startsWith('\uFEFF'))
  assert.match(csv, /"Дата";"Аналитик";"ID аккаунта"/)
  assert.match(csv, /"2026-09-04";"u-101";"cst-0007";"АО ""Вектор"""/)
  assert.match(csv, /"1234\.50";"0\.812"/)
})
