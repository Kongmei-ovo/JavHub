import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./SourceHealthPanel.vue', import.meta.url), 'utf8')
const styleSource = [
  readFileSync(new URL('./sourceHealthPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('./sourceRepairLane.css', import.meta.url), 'utf8'),
].join('\n')
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
  assert.match(source, /action\.status/)
  assert.match(source, /action\.tone/)
  assert.match(source, /sourceNextActionStatusClass\(action\)/)
  assert.match(source, /当前模式/)
  assert.match(source, /高风险/)
  assert.match(source, /待处理/)
  assert.match(source, /可执行/)

  const actionBlocks = cssBlocks('.source-next-actions')
  const actions = actionBlocks.find(block => /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/.test(block)) || actionBlocks[0]
  const card = cssBlock('.source-next-action-card')
  const activeCard = cssBlock('.source-next-action-card.active')
  const value = cssBlock('.source-next-action-value')
  const status = cssBlock('.source-next-action-status')
  const danger = cssBlock('.source-next-action-card.danger')
  const warning = cssBlock('.source-next-action-card.warning')
  const ready = cssBlock('.source-next-action-card.ready')
  const button = cssBlock('.source-next-action-card button')

  assert.match(actions, /grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.ok(
    actionBlocks.some(block => /grid-template-columns:\s*1fr/.test(block)),
    'source health next actions should collapse to one column on mobile',
  )
  assertLayeredBackground(card, '--material-glass-control', 'source health next action card')
  assert.match(card, /min-height:\s*92px/)
  assert.match(activeCard, /border-color:\s*var\(--glass-active-border\)/)
  assertLayeredBackground(activeCard, '--glass-active-material', 'source health active next action')
  assert.match(value, /font-variant-numeric:\s*tabular-nums/)
  assert.match(status, /border:\s*1px solid var\(--badge-warning-border\)/)
  assert.match(danger, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(warning, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(ready, /border-color:\s*var\(--badge-success-border\)/)
  assert.match(button, /justify-self:\s*start/)
})

test('source health exposes a prioritized source triage shortlist', () => {
  assert.match(source, /class="source-triage-strip"/)
  assert.match(source, /aria-label="来源处置短名单"/)
  assert.match(source, /class="source-triage-summary"/)
  assert.match(source, /class="source-triage-grid"/)
  assert.match(source, /v-for="item in sourceTriageShortlist"/)
  assert.match(source, /class="source-triage-card"/)
  assert.match(source, /sourceTriageCardClass\(item\)/)
  assert.match(source, /sourceTriageShortlist/)
  assert.match(source, /sourceTriagePriority\(source\)/)
  assert.match(source, /sourceTriagePriorityCount/)
  assert.match(source, /sourceTriageNextStep\(source\)/)
  assert.match(source, /sourceTriageStatus\(source\)/)
  assert.match(source, /sourceTriagePriorityCount \? `\$\{sourceTriagePriorityCount\} 个优先处理` : '来源稳定'/)
  assert.match(source, /来源处置/)
  assert.match(source, /优先处理/)
  assert.match(source, /连续失败/)
  assert.match(source, /最近错误/)
  assert.match(source, /下一步/)
  assert.match(source, /slice\(0, 4\)/)
  assert.match(source, /sort\(\(a, b\) => b\.priority - a\.priority\)/)
  assert.match(source, /filter\(item => item\.status !== 'ready'\)\.length/)

  const strip = cssBlock('.source-triage-strip')
  const grid = cssBlock('.source-triage-grid')
  const card = cssBlock('.source-triage-card')
  const danger = cssBlock('.source-triage-card.danger')
  const warning = cssBlock('.source-triage-card.warning')
  const ready = cssBlock('.source-triage-card.ready')
  const responsiveGridBlocks = cssBlocks('.source-triage-grid')

  assertLayeredBackground(strip, '--material-glass-sheet', 'source triage strip')
  assert.match(strip, /grid-template-columns:\s*minmax\(140px,\s*0\.22fr\)\s*minmax\(0,\s*1fr\)/)
  assert.match(grid, /grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/)
  assert.ok(
    responsiveGridBlocks.some(block => /grid-template-columns:\s*1fr/.test(block)),
    'source triage grid should collapse to one column on mobile',
  )
  assertLayeredBackground(card, '--material-glass-control', 'source triage card')
  assert.match(card, /min-width:\s*0/)
  assert.match(card, /overflow-wrap:\s*anywhere/)
  assert.match(danger, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(warning, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(ready, /border-color:\s*var\(--badge-success-border\)/)
})

test('source health cards expose source-level repair lanes with smoke and action state', () => {
  assert.match(source, /class="source-repair-lane"/)
  assert.match(source, /v-for="item in sourceRepairLaneItems\(source\)"/)
  assert.match(source, /class="source-repair-lane-item"/)
  assert.match(source, /sourceRepairLaneItemClass\(item\)/)
  assert.match(source, /sourceRepairLaneItems\(source\)/)
  assert.match(source, /sourceSmokeReportFor\(source\)/)
  assert.match(source, /providerSmokeReport\?\.reports/)
  assert.match(source, /this\.sourceActionLoading === source\.source/)
  assert.doesNotMatch(source, /value:\s*sourceActionLoading === source\.source/)
  assert.match(source, /字段分/)
  assert.match(source, /预算/)
  assert.match(source, /动作/)
  assert.match(source, /运行诊断采样/)
  assert.match(source, /解除冷却后复采/)

  const lane = cssBlock('.source-repair-lane')
  const laneResponsiveBlocks = cssBlocks('.source-repair-lane')
  const item = cssBlock('.source-repair-lane-item')
  const itemValue = cssBlock('.source-repair-lane-item b')
  const danger = cssBlock('.source-repair-lane-item.danger')
  const warning = cssBlock('.source-repair-lane-item.warning')
  const ready = cssBlock('.source-repair-lane-item.ready')

  assert.match(lane, /grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/)
  assert.ok(
    laneResponsiveBlocks.some(block => /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/.test(block)),
    'source repair lane should collapse to two dense columns on mobile',
  )
  assertLayeredBackground(item, '--material-glass-control', 'source repair lane item')
  assert.match(item, /min-width:\s*0/)
  assert.match(item, /overflow:\s*hidden/)
  assert.match(itemValue, /font-variant-numeric:\s*tabular-nums/)
  assert.match(danger, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(warning, /border-color:\s*var\(--badge-warning-border\)/)
  assert.match(ready, /border-color:\s*var\(--badge-success-border\)/)
})
