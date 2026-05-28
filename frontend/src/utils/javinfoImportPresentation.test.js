import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatBytes,
  isJavInfoImportActive,
  javinfoImportProgress,
  javinfoImportStatusLabel,
} from './javinfoImportPresentation.js'

test('JavInfo import presentation identifies active job statuses', () => {
  assert.equal(isJavInfoImportActive({ status: 'pending' }), true)
  assert.equal(isJavInfoImportActive({ status: 'uploading' }), true)
  assert.equal(isJavInfoImportActive({ status: 'migrating' }), true)
  assert.equal(isJavInfoImportActive({ status: 'completed' }), false)
  assert.equal(isJavInfoImportActive({ status: 'failed' }), false)
  assert.equal(isJavInfoImportActive(null), false)
})

test('JavInfo import presentation labels status and stage values', () => {
  assert.equal(javinfoImportStatusLabel({ status: 'pending' }), '等待上传')
  assert.equal(javinfoImportStatusLabel({ status: 'running', stage: 'stopping' }), '停止 JavInfoApi')
  assert.equal(javinfoImportStatusLabel({ status: 'failed' }), '失败')
  assert.equal(javinfoImportStatusLabel({ status: 'custom' }), 'custom')
  assert.equal(javinfoImportStatusLabel(null), '等待上传')
})

test('JavInfo import presentation calculates bounded progress', () => {
  assert.equal(javinfoImportProgress({ job: { status: 'completed' } }), 100)
  assert.equal(javinfoImportProgress({ uploading: true, uploadProgress: 66.6 }), 67)
  assert.equal(javinfoImportProgress({ uploading: true, uploadProgress: 150 }), 100)
  assert.equal(javinfoImportProgress({ job: { file_size: 10, uploaded_bytes: 4 } }), 40)
  assert.equal(javinfoImportProgress({ job: { uploaded_bytes: 2 }, fileSize: 8 }), 25)
  assert.equal(javinfoImportProgress({ job: { status: 'restoring' } }), 10)
  assert.equal(javinfoImportProgress({ job: { status: 'failed' } }), 0)
})

test('JavInfo import presentation formats byte sizes compactly', () => {
  assert.equal(formatBytes(12), '12 B')
  assert.equal(formatBytes(1536), '1.5 KB')
  assert.equal(formatBytes(2 * 1024 ** 2), '2.0 MB')
  assert.equal(formatBytes(3 * 1024 ** 3), '3.00 GB')
  assert.equal(formatBytes(null), '0 B')
})
