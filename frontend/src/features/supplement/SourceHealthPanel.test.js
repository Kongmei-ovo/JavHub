import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./SourceHealthPanel.vue', import.meta.url), 'utf8')
const styleSource = readFileSync(new URL('./sourceHealthPanel.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${styleSource}`

function cssBlocks(selector) {
  const blocks = [...source.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(selector) {
  return cssBlocks(selector).at(0)
}

test('source health primary triad: summary + source rows + runbook', () => {
  // Wave A redesign keeps three primary layers only. Older modebar /
  // next-action / triage / repair-lane dense layers were retired into the
  // advanced disclosure (smoke + gfriends sync) or removed entirely.
  assert.match(source, /class="src-summary"/)
  assert.match(source, /v-for="card in sourceHealthSummary"/)
  assert.match(source, /class="ss-card"/)
  assert.match(source, /接入来源/)
  assert.match(source, /可参与补全/)
  assert.match(source, /降级/)
  assert.match(source, /隔离/)

  assert.match(source, /class="src-rows"/)
  assert.match(source, /v-for="source in sourceHealthRows"/)
  assert.match(source, /class="source-card"/)
  assert.match(source, /class="sc-dot"/)
  assert.match(source, /sourceDotTone\(source\)/)
  assert.match(source, /连续失败/)
  assert.match(source, /最近错误/)
  assert.match(source, /下一步/)
  assert.match(source, /sourceNextStep\(source\)/)
  assert.match(source, /sourceHealthPrimaryAction\(source\)/)

  assert.match(source, /class="src-runbook"/)
  assert.match(source, /隔离 runbook/)
})

test('source health summary counts pull from real sourceHealthRows partitions', () => {
  // 数值不要 mock —— 直接从 sourceHealthRows 派生
  assert.match(source, /healthyRows[\s\S]*runtime_status === 'healthy'/)
  assert.match(source, /degradedRows[\s\S]*'degraded',\s*'cooling_down'/)
  assert.match(source, /pausedRows[\s\S]*runtime_status === 'paused'/)
  assert.match(source, /this\.sourceHealthRows\.length/)
})

test('source rows expose consecutive_failures, last_error_type, budget binding', () => {
  assert.match(source, /source\.consecutive_failures/)
  assert.match(source, /source\.last_error_type/)
  assert.match(source, /sourceBudgetLabel\(source\.budget\)/)
  assert.match(source, /sourceActionLoading === source\.source/)
  assert.match(source, /\$emit\(sourceHealthPrimaryAction\(source\)\.event,\s*source\.source\)/)
})

test('provider smoke sampling is fully removed; replaced by a single 全局检查 + per-row 检查', () => {
  // 抽检/采样 (smoke) was retired: the page is pure health now. One 全局检查 button
  // re-probes every source's liveness (and writes health back), per-row 检查 stays.
  assert.match(source, /全局检查/)
  assert.match(source, /\$emit\('check-all'\)/)
  assert.match(source, /\$emit\('check-source',\s*source\.source\)/)

  // every trace of the smoke panel is gone
  assert.doesNotMatch(source, /provider-smoke/)
  assert.doesNotMatch(source, /来源抽检/)
  assert.doesNotMatch(source, /运行抽检/)
  assert.doesNotMatch(source, /run-smoke/)
  assert.doesNotMatch(source, /load-smoke-runs/)
  assert.doesNotMatch(source, /smokeRunLabel/)
  assert.doesNotMatch(source, /src-advanced-body/)

  // avatar / gfriends wiring is still gone from this panel
  assert.doesNotMatch(source, /头像覆盖作业/)
  assert.doesNotMatch(source, /sync-gfriends-avatars/)

  // pause-source / resume-source still dispatched through sourceHealthPrimaryAction.event
  assert.match(source, /'pause-source'/)
  assert.match(source, /'resume-source'/)
  assert.match(source, /sourceHealthPrimaryAction\(source\)\.event,\s*source\.source/)
})

test('source health styles use design tokens, not legacy bg-card / surface-control', () => {
  // 不应再有过去的旧 token；新设计走 --card / --card-2 / --hairline + 语义色
  assert.doesNotMatch(styleSource, /var\(--bg-card\b/)
  assert.doesNotMatch(styleSource, /var\(--surface-control\b/)
  assert.doesNotMatch(styleSource, /var\(--surface-input-focus\b/)

  const summaryCard = cssBlock('.ss-card')
  assert.match(summaryCard, /background:\s*var\(--card-2\)/)
  assert.match(summaryCard, /border:\s*1px solid var\(--hairline\)/)

  const sourceCard = cssBlock('.source-card')
  assert.match(sourceCard, /background:\s*var\(--card\)/)
  assert.match(sourceCard, /border:\s*1px solid var\(--hairline\)/)

  const dotOk = cssBlock('.sc-dot-ok')
  const dotWarn = cssBlock('.sc-dot-warn')
  const dotBad = cssBlock('.sc-dot-bad')
  assert.match(dotOk, /background:\s*var\(--ok\)/)
  assert.match(dotWarn, /background:\s*var\(--warn\)/)
  assert.match(dotBad, /background:\s*var\(--bad\)/)

  const runbook = cssBlock('.src-runbook')
  assert.match(runbook, /rgba\(var\(--accent-rgb\),\s*0\.08\)/)

  // health-* tones must still resolve to the badge tokens (shared with the dialog)
  const healthy = cssBlock('.health-healthy')
  const degraded = cssBlock('.health-degraded')
  assert.match(healthy, /var\(--badge-success-bg\)/)
  assert.match(degraded, /var\(--badge-warning-bg\)/)
})

test('panel still streams skeleton + empty state, not bare loading text', () => {
  assert.match(source, /<AppleSkeleton[\s\S]*label="来源状态加载中"/)
  assert.match(source, /<AppleEmptyState/)
  assert.doesNotMatch(source, /<div[^>]+class="loading-wrap"[\s\S]{0,120}<div class="spinner-large"><\/div>/)
  assert.doesNotMatch(source, />加载中\.\.\.</)
})
