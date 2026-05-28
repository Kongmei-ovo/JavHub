import test from 'node:test'
import assert from 'node:assert/strict'
import axios from 'axios'

import { installAxiosAdapter } from './axiosAdapter.js'

test('installAxiosAdapter restores the previous adapter after the test', (t) => {
  const originalAdapter = axios.defaults.adapter
  const adapter = async (config) => ({ config, status: 200, statusText: 'OK', headers: {}, data: {} })

  installAxiosAdapter(t, adapter)
  assert.equal(axios.defaults.adapter, adapter)

  t.after(() => {
    assert.equal(axios.defaults.adapter, originalAdapter)
  })
})
