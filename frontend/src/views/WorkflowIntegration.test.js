import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const subscription = readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8')
const normalize = readFileSync(new URL('./Normalize.vue', import.meta.url), 'utf8')
const inventory = readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8')
const inventoryActor = readFileSync(new URL('./InventoryActor.vue', import.meta.url), 'utf8')
const home = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')

test('navigation and actor page use actor mapping language', () => {
  assert.match(app, /演员映射/)
  assert.doesNotMatch(app, /演员合并/)
  assert.match(normalize, /演员映射/)
  assert.match(normalize, /listUnmappedActors/)
  assert.match(normalize, /confirmActorMapping/)
  assert.match(normalize, /ignoreActorMapping/)
  assert.match(normalize, /getActorMappingSummary/)
})

test('subscription routes missing movies into download candidates', () => {
  assert.match(subscription, /createDownloadCandidate/)
  assert.match(subscription, /查看候选/)
  assert.match(subscription, /candidate_count/)
  assert.match(subscription, /待补磁力/)
  assert.match(subscription, /新增/)
  assert.match(subscription, /existing/)
  assert.match(subscription, /include_supplement: '1'/)
  assert.doesNotMatch(subscription, /api\.createDownload\(\{ code:/)
})

test('inventory page shows mapping coverage and candidate handoff', () => {
  assert.match(inventory, /映射覆盖率/)
  assert.match(inventory, /处理未映射演员/)
  assert.match(inventory, /映射建议/)
  assert.match(inventory, /source: 'inventory'/)
  assert.match(inventory, /getActorMappingSummary/)
  assert.match(inventory, /job\.result\.unmapped/)
  assert.match(inventory, /候选/)
  assert.match(inventoryActor, /转为候选/)
  assert.match(inventoryActor, /createDownloadCandidate/)
  assert.match(inventoryActor, /查看库存下载候选/)
})

test('download page exposes candidate approval workflow', () => {
  assert.match(home, /下载候选/)
  assert.match(home, /待补磁力/)
  assert.match(home, /approveDownloadCandidate/)
  assert.match(home, /rejectDownloadCandidate/)
  assert.match(home, /updateDownloadCandidateMagnet/)
  assert.match(home, /error_msg/)
  assert.match(home, /已关联任务/)
  assert.match(home, /重试/)
})
