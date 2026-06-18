import test from 'node:test'
import assert from 'node:assert/strict'
import { convertURL, EXTERNAL_PLAYERS, detectPlatform, playersForPlatform } from './externalPlayers.js'

const D = 'https://cdn.115.test/x.mp4?t=abc&s=1'

test('convertURL maps $durl to the raw direct link', () => {
  assert.equal(convertURL('vlc://$durl', { dUrl: D }), `vlc://${D}`)
})

test('convertURL maps $edurl to an encoded direct link (IINA/mpv)', () => {
  assert.equal(convertURL('iina://weblink?url=$edurl', { dUrl: D }), `iina://weblink?url=${encodeURIComponent(D)}`)
  assert.equal(convertURL('mpv://$edurl', { dUrl: D }), `mpv://${encodeURIComponent(D)}`)
})

test('convertURL maps $bdurl to a base64 direct link (iPlay)', () => {
  assert.equal(convertURL('iplay://play/any?type=url&url=$bdurl', { dUrl: D }), `iplay://play/any?type=url&url=${btoa(D)}`)
})

test('convertURL substitutes $name and keeps $durl raw in android intents', () => {
  const out = convertURL('intent:$durl#Intent;package=com.mxtech.videoplayer.ad;S.title=$name;end', { dUrl: D, name: 'MIAA-784' })
  assert.equal(out, `intent:${D}#Intent;package=com.mxtech.videoplayer.ad;S.title=MIAA-784;end`)
})

test('detectPlatform reads the user agent', () => {
  assert.equal(detectPlatform('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'), 'MacOS')
  assert.equal(detectPlatform('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'), 'iOS')
  assert.equal(detectPlatform('Mozilla/5.0 (Linux; Android 14)'), 'Android')
  assert.equal(detectPlatform('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'), 'Windows')
})

test('playersForPlatform filters the table by platform', () => {
  const mac = playersForPlatform('MacOS').map((p) => p.name)
  assert.ok(mac.includes('IINA'))
  assert.ok(mac.includes('Infuse'))
  assert.ok(mac.includes('SenPlayer'))
  assert.ok(!mac.includes('PotPlayer'))
  const ios = playersForPlatform('iOS').map((p) => p.name)
  assert.ok(ios.includes('nPlayer'))
  assert.ok(ios.includes('SenPlayer'))
  assert.ok(!ios.includes('IINA'))
})

test('SenPlayer uses the x-callback-url scheme with an encoded direct link', () => {
  const sen = EXTERNAL_PLAYERS.find((p) => p.name === 'SenPlayer')
  assert.ok(sen, 'SenPlayer should be in the table')
  assert.deepEqual(sen.platforms, ['MacOS', 'iOS'])
  assert.equal(
    convertURL(sen.scheme, { dUrl: D }),
    `senplayer://x-callback-url/play?url=${encodeURIComponent(D)}`,
  )
})

test('external player table is OpenList set (13) plus SenPlayer', () => {
  assert.equal(EXTERNAL_PLAYERS.length, 14)
})
