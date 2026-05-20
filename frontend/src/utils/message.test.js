import test from 'node:test'
import assert from 'node:assert/strict'
import { ElMessage } from './message.js'

test('ElMessage proxy dispatches lightweight app message events', () => {
  const originalWindow = globalThis.window
  const originalCustomEvent = globalThis.CustomEvent
  const events = []

  globalThis.CustomEvent = class CustomEvent {
    constructor(type, init = {}) {
      this.type = type
      this.detail = init.detail
    }
  }
  globalThis.window = {
    dispatchEvent(event) {
      events.push(event)
    },
  }

  try {
    ElMessage.error('网络错误')
  } finally {
    globalThis.window = originalWindow
    globalThis.CustomEvent = originalCustomEvent
  }

  assert.equal(events.length, 1)
  assert.equal(events[0].type, 'javhub-message')
  assert.deepEqual(events[0].detail, { type: 'error', message: '网络错误' })
})
