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

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
}

test('source health diagnostics use shared Apple glass materials', () => {
  const filterInput = cssBlock('.filter-input')
  const filterFocus = cssBlock('.filter-input:focus')
  const avatarPanel = cssBlock('.avatar-sync-panel')
  const avatarMetric = cssBlock('.avatar-sync-metrics div')
  const smokeSummary = cssBlock('.provider-smoke-summary')
  const smokeCard = cssBlock('.provider-smoke-card')
  const smokeCardFailed = cssBlock('.provider-smoke-card.failed')
  const smokeHistory = cssBlock('.provider-smoke-history')
  const smokeRun = cssBlock('.provider-smoke-run')
  const smokeRunHover = cssBlock('.provider-smoke-run:hover')
  const smokeRunFocus = cssBlock('.provider-smoke-run:focus-visible')
  const healthCard = cssBlock('.source-health-card')
  const budgetMeter = cssBlock('.source-budget-meter')
  const miniSpinner = cssBlock('.mini-spinner')

  assert.doesNotMatch(source, /var\(--surface-card\)|var\(--surface-control\)|var\(--surface-control-hover\)|var\(--surface-input-focus\)|var\(--white-20\)|rgba\(255,\s*107,\s*135/)

  assertLayeredBackground(filterInput, '--material-glass-control', 'source health filter input')
  assert.match(filterInput, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(filterInput, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(filterInput, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(filterFocus, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(filterFocus, '--glass-active-material', 'source health focused filter input')
  assert.match(filterFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)
  assert.doesNotMatch([filterInput, filterFocus].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|glass-active-material)\);.*$/gm)

  for (const block of [avatarPanel, smokeSummary, smokeHistory, healthCard]) {
    assertLayeredBackground(block, '--material-glass-sheet', 'source health sheet')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-surface-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-surface\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  }
  assert.doesNotMatch([avatarPanel, smokeSummary, smokeHistory, healthCard].join('\n'), /^.*background:\s*var\(--material-glass-sheet\);.*$/gm)

  for (const block of [avatarMetric, smokeCard, smokeRun, budgetMeter]) {
    assertLayeredBackground(block, '--material-glass-control', 'source health control')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  }
  assert.doesNotMatch([avatarMetric, smokeCard, smokeRun, budgetMeter].join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assertLayeredBackground(smokeRunHover, '--material-glass-control-hover', 'source health hovered run')
  assert.match(smokeRunHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  assert.doesNotMatch(smokeRunHover, /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)
  assertLayeredBackground(smokeRunFocus, '--material-glass-control-hover', 'source health focused run')
  assert.match(smokeRunFocus, /outline:\s*none/)
  assert.match(smokeRunFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(smokeRunFocus, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/)
  assert.match(smokeRunFocus, /transform:\s*translateY\(-1px\)/)
  assert.doesNotMatch(smokeRunFocus, /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)
  assert.match(smokeCardFailed, /border-color:\s*var\(--badge-error-border\)/)

  assert.match(source, /<AppleSkeleton[\s\S]*label="来源状态加载中"/)
  assert.doesNotMatch(source, /<div[^>]+class="loading-wrap"[\s\S]{0,120}<div class="spinner-large"><\/div>/)
  assert.match(miniSpinner, /border:\s*2px solid var\(--glass-control-border\)/)
  assert.match(miniSpinner, /border-top-color:\s*var\(--badge-info-text\)/)
})

test('source health repair modes expose queue counts and row risk summaries', () => {
  assert.match(source, /class="mode-count"/)
  assert.match(source, /sourceHealthModeCount\(mode\.key\)/)
  assert.match(source, /sourceHealthModeCount\(mode\)/)
  assert.match(source, /sourceHealthModeCount\(mode\)[\s\S]*this\.sourceHealthRows\.length/)
  assert.match(source, /sourceHealthModeCount\(mode\)[\s\S]*this\.recoverQueueRows\.length/)
  assert.match(source, /sourceHealthModeCount\(mode\)[\s\S]*this\.isolateQueueRows\.length/)
  assert.match(source, /sourceHealthRiskItems\(source\)/)
  assert.match(source, /class="source-risk-row"/)
  assert.match(source, /sourceHealthEmptyState/)
  assert.match(source, /class="source-health-empty"/)
  assert.match(source, /:title="sourceHealthEmptyState\.title"/)
  assert.match(source, /恢复队列为空/)
  assert.match(source, /隔离队列为空/)
  assert.match(source, /暂无来源状态/)
  assert.match(source, /consecutive_failures/)
  assert.match(source, /budget\.local_active/)
  assert.match(source, /last_error_type/)

  const modeButton = cssBlock('.source-health-modebar button')
  const modeCount = cssBlock('.mode-count')
  const riskRow = cssBlock('.source-risk-row')
  const emptyState = cssBlock('.source-health-empty')

  assert.match(modeButton, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto/)
  assertLayeredBackground(modeCount, '--badge-info-bg', 'source health mode count')
  assert.match(modeCount, /font-variant-numeric:\s*tabular-nums/)
  assertLayeredBackground(riskRow, '--material-glass-control', 'source health risk row')
  assert.match(riskRow, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(emptyState, /width:\s*min\(100%,\s*520px\)/)
  assert.match(emptyState, /margin:\s*14px auto 0/)
  assert.match(source, /action-label="刷新来源"/)
  assert.match(source, /secondary-action-label="运行诊断"/)
})

test('source health modes expose a dense next-action queue', () => {
  assert.match(source, /class="source-next-actions"/)
  assert.match(source, /v-for="action in sourceHealthActionQueue"/)
  assert.match(source, /class="source-next-action-card"/)
  assert.match(source, /sourceNextActionCardClass\(action\)/)
  assert.match(source, /sourceHealthActionQueue/)
  assert.match(source, /sourceHealthActionQueue[\s\S]*运行诊断/)
  assert.match(source, /sourceHealthActionQueue[\s\S]*恢复来源/)
  assert.match(source, /sourceHealthActionQueue[\s\S]*隔离风险/)
  assert.match(source, /diagnoseQueueRows/)
  assert.match(source, /recoverQueueRows/)
  assert.match(source, /isolateQueueRows/)
  assert.match(source, /sourceHealthMode = action\.mode/)
  assert.match(source, /@click="action\.event \? \$emit\(action\.event\) : sourceHealthMode = action\.mode"/)
  assert.match(source, /action\.count/)
  assert.match(source, /action\.primary/)
  assert.match(source, /当前模式/)

  const actions = cssBlock('.source-next-actions')
  const card = cssBlock('.source-next-action-card')
  const activeCard = cssBlock('.source-next-action-card.active')
  const value = cssBlock('.source-next-action-value')
  const button = cssBlock('.source-next-action-card button')

  assert.match(actions, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assertLayeredBackground(card, '--material-glass-control', 'source health next action card')
  assert.match(card, /min-height:\s*92px/)
  assert.match(activeCard, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(activeCard, '--glass-active-material', 'source health active next action')
  assert.match(value, /font-variant-numeric:\s*tabular-nums/)
  assert.match(button, /justify-self:\s*start/)
})
