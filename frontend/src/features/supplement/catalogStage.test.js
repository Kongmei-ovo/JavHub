import { test } from 'node:test'
import assert from 'node:assert/strict'
import { catalogStage, STAGE_META, STAGE_ORDER } from './catalogStage.js'

test('owned + complete => complete', () => {
  assert.equal(catalogStage({ status: 'owned', metadata_complete: true }), 'complete')
})
test('owned + gap => meta_gap', () => {
  assert.equal(catalogStage({ status: 'owned', metadata_complete: false }), 'meta_gap')
})
test('in_progress => fetching', () => {
  assert.equal(catalogStage({ status: 'in_progress' }), 'fetching')
})
test('available => downloadable', () => {
  assert.equal(catalogStage({ status: 'available' }), 'downloadable')
})
test('needs_magnet => find_source', () => {
  assert.equal(catalogStage({ status: 'needs_magnet' }), 'find_source')
})
test('unknown status => find_source', () => {
  assert.equal(catalogStage({ status: 'whatever' }), 'find_source')
})
test('STAGE_META has label+tone for every stage, STAGE_ORDER covers all', () => {
  for (const s of STAGE_ORDER) {
    assert.ok(STAGE_META[s].label && STAGE_META[s].tone, `${s} needs label+tone`)
  }
  assert.deepEqual(STAGE_ORDER, ['find_source', 'downloadable', 'fetching', 'meta_gap', 'complete'])
})
