import { test } from 'node:test'
import assert from 'node:assert/strict'
import { catalogStage, STAGE_META, STAGE_ORDER, FUNNEL_TABS } from './catalogStage.js'

// Field-first gate: any metadata gap => meta_gap regardless of owned/acquisition.
test('missing fields => meta_gap even if owned', () => {
  assert.equal(catalogStage({ status: 'owned', metadata_complete: false }), 'meta_gap')
})
test('missing fields => meta_gap even if not owned', () => {
  assert.equal(catalogStage({ status: 'needs_magnet', metadata_complete: false }), 'meta_gap')
})
test('owned + complete => complete', () => {
  assert.equal(catalogStage({ status: 'owned', metadata_complete: true }), 'complete')
})
test('not owned + complete + needs_magnet => find_source', () => {
  assert.equal(catalogStage({ status: 'needs_magnet', metadata_complete: true }), 'find_source')
})
test('not owned + complete + available => downloadable', () => {
  assert.equal(catalogStage({ status: 'available', metadata_complete: true }), 'downloadable')
})
test('not owned + complete + in_progress => fetching', () => {
  assert.equal(catalogStage({ status: 'in_progress', metadata_complete: true }), 'fetching')
})
test('prefers explicit backend funnel_stage when present', () => {
  assert.equal(catalogStage({ funnel_stage: 'downloadable', status: 'owned', metadata_complete: false }), 'downloadable')
})
test('FUNNEL_TABS partition the acquisition stages under sources, meta_gap under fields', () => {
  assert.deepEqual(FUNNEL_TABS.fields, ['meta_gap'])
  assert.deepEqual(FUNNEL_TABS.sources, ['find_source', 'downloadable', 'fetching'])
})
test('STAGE_META covers every STAGE_ORDER entry', () => {
  for (const s of STAGE_ORDER) assert.ok(STAGE_META[s].label && STAGE_META[s].tone, `${s} needs label+tone`)
})
