import test from 'node:test'
import assert from 'node:assert/strict'
import { parseMagnetInput, decodeMagnetName, countInputLines } from './magnetParse.js'

test('parses valid magnets, decoding the display name', () => {
  const { parsed, duplicates, invalid } = parseMagnetInput(
    'magnet:?xt=urn:btih:ABCDEF0123456789&dn=Some+Cool+Movie'
  )
  assert.equal(parsed.length, 1)
  assert.equal(parsed[0].hash, 'ABCDEF0123456789')
  assert.equal(parsed[0].name, 'Some Cool Movie')
  assert.equal(duplicates, 0)
  assert.equal(invalid.length, 0)
})

test('counts duplicate hashes once and does not re-add them', () => {
  const text = [
    'magnet:?xt=urn:btih:AAAA1111&dn=first',
    'magnet:?xt=urn:btih:aaaa1111&dn=dup-different-case',
    'magnet:?xt=urn:btih:BBBB2222',
  ].join('\n')
  const { parsed, duplicates } = parseMagnetInput(text)
  assert.equal(parsed.length, 2)
  assert.equal(duplicates, 1)
})

test('collects invalid lines with 1-based index, ignoring blanks', () => {
  const text = ['', 'not a magnet', '', 'magnet:?xt=urn:btih:CCCC3333'].join('\n')
  const { parsed, invalid } = parseMagnetInput(text)
  assert.equal(parsed.length, 1)
  assert.equal(invalid.length, 1)
  assert.equal(invalid[0].index, 2)
  assert.equal(invalid[0].text, 'not a magnet')
})

test('decodeMagnetName tolerates malformed encodings', () => {
  assert.equal(decodeMagnetName('a%2Fb'), 'a/b')
  assert.equal(decodeMagnetName('%E0%A4%A'), '%E0%A4%A')
  assert.equal(decodeMagnetName(''), '')
})

test('countInputLines ignores blank lines', () => {
  assert.equal(countInputLines('a\n\n b \n'), 2)
  assert.equal(countInputLines('   '), 0)
})
