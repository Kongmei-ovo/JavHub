import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const panel = readFileSync(new URL('./Open115SettingsPanel.vue', import.meta.url), 'utf8')
const api = readFileSync(new URL('../../api/index.js', import.meta.url), 'utf8')
const config = readFileSync(new URL('../../views/Config.vue', import.meta.url), 'utf8')
const defaults = readFileSync(new URL('./configDefaults.js', import.meta.url), 'utf8')

test('115 settings panel supports sanitized status, qr polling, import, test and unbind', () => {
  assert.match(panel, /name:\s*'Open115SettingsPanel'/)
  assert.match(panel, /api\.getOpen115Status\(\)/)
  assert.match(panel, /api\.startOpen115Auth\(\)/)
  assert.match(panel, /api\.pollOpen115Auth\(this\.authUid\)/)
  assert.match(panel, /api\.importOpen115Token\(this\.refreshToken\)/)
  assert.match(panel, /api\.testOpen115\(\)/)
  assert.match(panel, /api\.unbindOpen115\(\)/)
  assert.match(panel, /qrcode_image_url/)
  assert.doesNotMatch(panel, /status\.(?:access_token|refresh_token)/)
})

test('api exposes the dedicated 115 management contract', () => {
  assert.match(api, /getOpen115Status\(\)[\s\S]*\/v1\/open115\/status/)
  assert.match(api, /startOpen115Auth\(\)[\s\S]*\/v1\/open115\/auth\/start/)
  assert.match(api, /pollOpen115Auth\(uid\)[\s\S]*\/v1\/open115\/auth\//)
  assert.match(api, /importOpen115Token\(refreshToken\)[\s\S]*refresh_token:\s*refreshToken/)
  assert.match(api, /testOpen115\(\)[\s\S]*\/v1\/open115\/test/)
  assert.match(api, /unbindOpen115\(\)[\s\S]*\/v1\/open115\/unbind/)
})

test('settings mounts native 115 management and has no OpenList defaults', () => {
  assert.match(config, /<Open115SettingsPanel/)
  assert.match(config, /import Open115SettingsPanel/)
  assert.doesNotMatch(config, /const \{ downloaders, openlist,/)
  assert.match(defaults, /open115:\s*\{\s*app_id:\s*'',\s*root_path:\s*'\/JavHub'/)
  assert.doesNotMatch(defaults, /openlist:/)
  assert.doesNotMatch(defaults, /default_id:\s*'openlist'/)
})
