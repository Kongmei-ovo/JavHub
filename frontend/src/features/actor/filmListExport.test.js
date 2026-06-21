import test from 'node:test'
import assert from 'node:assert/strict'
import { movieOwnKeys, sortFilmList, csvEscape, filmsToCsv } from './filmListExport.js'

const film = (over = {}) => ({ id: '', code: '', display_code: '', canonical_code: '', date: '', title: '', _raw: {}, ...over })

test('movieOwnKeys collects every identifier, trimmed and non-empty', () => {
  const keys = movieOwnKeys(film({ id: 'cid1', display_code: 'ABC-1', canonical_code: 'ABC1', _raw: { dvd_id: ' DVD-1 ', content_id: '' } }))
  assert.deepEqual(keys, ['cid1', 'ABC-1', 'ABC1', 'DVD-1'])
})

test('sortFilmList sorts by date desc/asc with undated last', () => {
  const list = [film({ date: '2020-01-01', code: 'A' }), film({ date: '', code: 'B' }), film({ date: '2022-05-01', code: 'C' })]
  assert.deepEqual(sortFilmList(list, 'date', 'desc').map(f => f.code), ['C', 'A', 'B'])
  assert.deepEqual(sortFilmList(list, 'date', 'asc').map(f => f.code), ['A', 'C', 'B'])
})

test('sortFilmList sorts by runtime numerically and code lexically', () => {
  const list = [film({ code: 'B', _raw: { runtime_mins: 120 } }), film({ code: 'A', _raw: { runtime_mins: 60 } })]
  assert.deepEqual(sortFilmList(list, 'runtime', 'asc').map(f => f.code), ['A', 'B'])
  assert.deepEqual(sortFilmList([film({ display_code: 'B-2' }), film({ display_code: 'A-1' })], 'code', 'asc').map(f => f.display_code), ['A-1', 'B-2'])
})

test('csvEscape quotes separators and neutralizes formula injection', () => {
  assert.equal(csvEscape('plain'), 'plain')
  assert.equal(csvEscape('a,b'), '"a,b"')
  assert.equal(csvEscape('he said "hi"'), '"he said ""hi"""')
  assert.equal(csvEscape('=SUM(A1)'), "'=SUM(A1)")
})

test('filmsToCsv builds header + rows with 拥有 flag', () => {
  const movies = [film({ display_code: 'ABC-1', title: 'T,1', date: '2022-01-01', _raw: { runtime_mins: 90 } })]
  const csv = filmsToCsv(movies, m => m.display_code === 'ABC-1')
  const [header, row] = csv.split('\r\n')
  assert.equal(header, '番号,片名,时长(分钟),出演时间,115拥有')
  assert.equal(row, 'ABC-1,"T,1",90,2022-01-01,是')
})
