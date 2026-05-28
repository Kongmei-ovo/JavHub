import assert from 'node:assert/strict'
import test from 'node:test'

import {
  coveragePercent,
  durationText,
  formatNumber,
  jobProgressValue,
  jobStatusClass,
  jobTypeLabel,
  percentValue,
  statusLabel,
  workbenchStatusClass,
  workbenchStatusLabel,
} from './translationJobPresentation.js'

test('translation job presentation formats coverage and counts safely', () => {
  assert.equal(percentValue({ translated: 2, total: 3 }), 67)
  assert.equal(percentValue({ translated: 99, total: 0 }), 0)
  assert.equal(percentValue({ translated: -5, total: 10 }), 0)
  assert.equal(percentValue({ translated: 12, total: 10 }), 100)
  assert.equal(coveragePercent({ translated: 1, total: 4 }), '25%')
  assert.equal(formatNumber(1234567), '1,234,567')
  assert.equal(formatNumber(null), '0')
})

test('translation job presentation labels known job and review states', () => {
  assert.equal(jobTypeLabel('library_titles'), '库内影片标题')
  assert.equal(jobTypeLabel('metadata_makers'), '厂商名称')
  assert.equal(jobTypeLabel('custom_job'), 'custom_job')
  assert.equal(jobTypeLabel(''), '未知作业')
  assert.equal(workbenchStatusLabel('machine_translated'), '机翻')
  assert.equal(workbenchStatusLabel('reviewed'), '已校对')
  assert.equal(workbenchStatusLabel('unknown'), '未翻译')
  assert.equal(workbenchStatusClass('failed'), 'status-failed')
  assert.equal(workbenchStatusClass(''), 'status-untranslated')
})

test('translation job presentation labels status and progress display values', () => {
  assert.equal(statusLabel('running'), '运行中')
  assert.equal(statusLabel('paused'), '已暂停')
  assert.equal(statusLabel('unknown'), '空闲')
  assert.equal(jobStatusClass('completed'), 'status-completed')
  assert.equal(jobStatusClass(''), 'status-idle')
  assert.equal(jobProgressValue({ progress_percent: 66.6 }), 67)
  assert.equal(jobProgressValue({ progress_percent: 150 }), 100)
  assert.equal(jobProgressValue({ progress_percent: Number.NaN }), 0)
})

test('translation job presentation formats durations compactly', () => {
  assert.equal(durationText(null), '—')
  assert.equal(durationText(45), '45s')
  assert.equal(durationText(60), '1m')
  assert.equal(durationText(75), '1m 15s')
  assert.equal(durationText(3600), '1h')
  assert.equal(durationText(3660), '1h 1m')
})
