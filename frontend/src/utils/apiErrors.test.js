import test from 'node:test'
import assert from 'node:assert/strict'
import { apiErrorMessage } from './apiErrors.js'

test('apiErrorMessage prefers API detail over message fields', () => {
  const error = {
    response: {
      data: {
        detail: '详细错误',
        message: '接口消息',
      },
    },
    message: 'Axios message',
  }

  assert.equal(apiErrorMessage(error, 'fallback'), '详细错误')
})

test('apiErrorMessage falls back through API message, error message, then fallback', () => {
  assert.equal(apiErrorMessage({
    response: { data: { message: '接口消息' } },
    message: 'Axios message',
  }, 'fallback'), '接口消息')

  assert.equal(apiErrorMessage({ message: 'Axios message' }, 'fallback'), 'Axios message')
  assert.equal(apiErrorMessage({}, 'fallback'), 'fallback')
  assert.equal(apiErrorMessage(null, 'fallback'), 'fallback')
})

test('apiErrorMessage preserves the previous truthy fallback behavior', () => {
  assert.equal(apiErrorMessage({
    response: {
      data: {
        detail: '   ',
        message: '接口消息',
      },
    },
  }, 'fallback'), '   ')

  assert.equal(apiErrorMessage({
    response: {
      data: {
        detail: 0,
        message: null,
      },
    },
    message: false,
  }, 'fallback'), 'fallback')
})

test('apiErrorMessage preserves object values for existing call sites', () => {
  const detail = { code: 'RATE_LIMIT', wait: 30 }
  assert.equal(apiErrorMessage({
    response: {
      data: {
        detail,
      },
    },
  }, 'fallback'), detail)

  assert.equal(apiErrorMessage({
    response: {
      data: {
        detail: null,
        message: ['array-message'],
      },
    },
  }, 'fallback').at(0), 'array-message')
})
