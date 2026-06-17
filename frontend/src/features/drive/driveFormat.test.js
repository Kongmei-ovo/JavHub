import test from 'node:test'
import assert from 'node:assert/strict'
import { kindOf, formatSize, formatDate, typeLabel, sortFilesByType } from './driveFormat.js'

test('kindOf classifies folders, video, image, and other files', () => {
  assert.equal(kindOf({ is_dir: true }), 'folder')
  assert.equal(kindOf({ is_dir: false, extension: 'MKV' }), 'video')
  assert.equal(kindOf({ is_dir: false, extension: 'png' }), 'image')
  assert.equal(kindOf({ is_dir: false, extension: 'txt' }), 'file')
})

test('formatSize is human-readable with no false zero', () => {
  assert.equal(formatSize(0), '—')
  assert.equal(formatSize(512), '512 B')
  assert.equal(formatSize(1536), '1.5 KB')
})

test('formatDate renders epoch seconds and tolerates missing values', () => {
  assert.equal(formatDate(0), '—')
  assert.match(formatDate(1779763119), /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
})

test('typeLabel prefers folder then uppercase extension', () => {
  assert.equal(typeLabel({ is_dir: true }), '文件夹')
  assert.equal(typeLabel({ is_dir: false, extension: 'mp4' }), 'MP4')
  assert.equal(typeLabel({ is_dir: false, extension: '' }), '文件')
})

test('sortFilesByType keeps folders first then groups by extension', () => {
  const files = [
    { is_dir: false, extension: 'mp4', name: 'b' },
    { is_dir: true, name: 'zfolder' },
    { is_dir: false, extension: 'ass', name: 'a' },
  ]
  const sorted = sortFilesByType(files, true)
  assert.equal(sorted[0].is_dir, true)
  assert.deepEqual(sorted.slice(1).map((f) => f.extension), ['ass', 'mp4'])
})
