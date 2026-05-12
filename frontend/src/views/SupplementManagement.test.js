import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8')

test('supplement management shows and controls actor context when routed from an actor', () => {
  assert.match(source, /v-if="actorContext"/)
  assert.match(source, /class="actor-context-card"/)
  assert.match(source, /api\.getActress\(normalized\)/)
  assert.match(source, /clearActorContext\(\)/)
  assert.match(source, /goActorContext\(\)/)
  assert.match(source, /applyJobActorContext\(job\)/)
})

test('supplement management keeps jobs and movies scoped to actor context', () => {
  assert.match(source, /applyActorContext\(actressId\)/)
  assert.match(source, /this\.jobFilters\.actress_id = normalized/)
  assert.match(source, /this\.movieFilters\.actress_id = normalized/)
  assert.match(source, /jobActorLabel\(job\)/)
})

test('supplement management lets users search and select an actor instead of typing ids', () => {
  assert.match(source, /class="actor-picker-card"/)
  assert.match(source, /v-model="actorSearchKeyword"/)
  assert.match(source, /searchActorContext\(\)/)
  assert.match(source, /selectActorContext\(actor\)/)
  assert.match(source, /api\.searchActors\(keyword\)/)
  assert.match(source, /v-for="actor in actorChoiceCards"/)
  assert.match(source, /actorChoiceCards/)
  assert.match(source, /class="actor-choice-card apple-surface"/)
  assert.match(source, /class="select-orb"/)
  assert.match(source, />选择</)
  assert.doesNotMatch(source, /placeholder="演员 ID"/)
})

test('supplement management defaults to an actor-first selection view', () => {
  assert.match(source, /补全演员/)
  assert.match(source, /v-if="showActorPicker"/)
  assert.match(source, /class="supplement-hero apple-surface"/)
  assert.match(source, /class="actor-filter-bar apple-surface"/)
  assert.match(source, /recentActorJobs/)
})

test('supplement management uses an actor workspace with segmented panels', () => {
  assert.match(source, /class="actor-workspace-hero apple-surface"/)
  assert.match(source, /workspaceSegments/)
  assert.match(source, /activeWorkspaceSegment/)
  assert.match(source, /作品字段/)
  assert.match(source, /任务队列/)
  assert.match(source, /来源诊断/)
  assert.match(source, /来源状态/)
  assert.match(source, /jobAttemptMeta/)
  assert.match(source, /next_run_at/)
  assert.match(source, /getSupplementActressStatus\(normalized\)/)
  assert.match(source, /startSupplementFilmographyJob\(this\.actorContext\.id\)/)
  assert.match(source, /refreshSupplementActressResolved\(this\.actorContext\.id\)/)
  assert.match(source, /生成下载候选/)
  assert.match(source, /createDownloadCandidates/)
  assert.match(source, /api\.createSupplementDownloadCandidates\(params\)/)
  assert.match(source, /path: '\/downloads'/)
  assert.match(source, /source: 'supplement'/)
})

test('supplement management exposes source health and manual correction controls', () => {
  assert.match(source, /api\.listSupplementSourcesHealth\(\)/)
  assert.match(source, /api\.listSupplementSourcesBudgets\(\)/)
  assert.match(source, /sourceHealthRows/)
  assert.match(source, /当前预算/)
  assert.match(source, /api\.pauseSupplementSource/)
  assert.match(source, /api\.resumeSupplementSource/)
  assert.match(source, /已暂停/)
  assert.match(source, /manual-match-bar/)
  assert.match(source, /manualMatchMovie/)
  assert.match(source, /api\.matchSupplementMovie/)
  assert.match(source, /api\.ignoreSupplementMovie/)
  assert.match(source, /api\.unmatchSupplementMovie/)
  assert.match(source, /manual_actions/)
  assert.match(source, /人工校正记录/)
})

test('supplement management exposes provider smoke diagnostics', () => {
  assert.match(source, /运行诊断/)
  assert.match(source, /runProviderSmoke/)
  assert.match(source, /api\.runSupplementProviderSmoke\(payload\)/)
  assert.match(source, /providerSmokeForm/)
  assert.match(source, /source_movie_id/)
  assert.match(source, /自定义样本需要先选择来源/)
  assert.match(source, /最近诊断/)
  assert.match(source, /api\.listSupplementProviderSmokeRuns\(5, this\.providerSmokeForm\.source\)/)
  assert.match(source, /smokeRunLabel/)
  assert.match(source, /providerSmokeReport/)
  assert.match(source, /字段分/)
})

test('supplement management preserves a global queue entry point', () => {
  assert.match(source, /showGlobalQueue/)
  assert.match(source, /openGlobalQueue\(\)/)
  assert.match(source, /全局队列/)
  assert.match(source, /applyJobActorContext\(job\)/)
})
