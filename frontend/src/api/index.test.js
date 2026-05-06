import test from 'node:test'
import assert from 'node:assert/strict'
import axios from 'axios'
import { ElMessage } from 'element-plus'

function installRejectingAdapter(t, status = 404, detail = 'Not Found') {
  const originalAdapter = axios.defaults.adapter
  axios.defaults.adapter = async (config) => Promise.reject({
    config,
    response: { status, data: { detail } },
    message: `Request failed with status code ${status}`,
    isAxiosError: true,
    toJSON: () => ({}),
  })
  t.after(() => {
    axios.defaults.adapter = originalAdapter
  })
}

test('getVideoMetadata failure does not show global error toast', async (t) => {
  installRejectingAdapter(t)
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?metadata-suppress-${Date.now()}`)

  await assert.rejects(() => api.getVideoMetadata('miaa405'))

  assert.equal(errorMock.mock.callCount(), 0)
})

test('main path API failure still shows global error toast', async (t) => {
  installRejectingAdapter(t, 500, '服务器内部错误')
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?main-error-${Date.now()}`)

  await assert.rejects(() => api.getVideo('miaa405'))

  assert.equal(errorMock.mock.callCount(), 1)
  assert.equal(errorMock.mock.calls[0].arguments[0], '服务器内部错误')
})
