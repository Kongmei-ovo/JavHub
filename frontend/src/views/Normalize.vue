<template>
  <div class="mapping-page page-shell page-shell--workspace">
    <div class="page-header">
      <div>
        <h1>演员映射</h1>
      </div>
      <div class="header-actions">
        <button type="button" class="btn btn-ghost" :disabled="autoMatching" @click="previewAutoMatch">
          {{ autoMatching ? '预演中...' : '自动匹配预演' }}
        </button>
        <button type="button" class="btn btn-primary" :disabled="autoMatching" @click="runAutoMatch">
          {{ autoMatching ? '执行中...' : '执行自动匹配' }}
        </button>
        <button type="button" class="btn btn-ghost" @click="reloadAll">刷新</button>
      </div>
    </div>

    <div class="summary-row">
      <div class="summary-card">
        <strong>{{ mappingSummary.confirmed || 0 }}</strong>
        <span>已确认</span>
      </div>
      <div class="summary-card">
        <strong>{{ mappingSummary.unmapped || 0 }}</strong>
        <span>待映射</span>
      </div>
      <div class="summary-card">
        <strong>{{ mappingSummary.candidate || 0 }}</strong>
        <span>待审候选</span>
      </div>
      <div class="summary-card">
        <strong>{{ coverageText }}</strong>
        <span>映射覆盖率</span>
      </div>
      <div class="summary-card">
        <strong>{{ lastAutoMatch?.auto_confirmed || 0 }}</strong>
        <span>本次自动确认</span>
      </div>
      <div class="summary-card">
        <strong>{{ lastAutoMatch?.ambiguous || 0 }}</strong>
        <span>本次歧义</span>
      </div>
    </div>

    <div v-if="lastAutoMatch" class="auto-match-panel">
      <div>
        <strong>{{ lastAutoMatch.dry_run ? '自动匹配预演' : '自动匹配结果' }}</strong>
        <span>
          检查 {{ lastAutoMatch.checked || 0 }} · 自动确认 {{ lastAutoMatch.auto_confirmed || 0 }}
          · 待审候选 {{ lastAutoMatch.candidates_created || 0 }} · 歧义 {{ lastAutoMatch.ambiguous || 0 }}
          · 跳过 {{ lastAutoMatch.skipped || 0 }}
        </span>
      </div>
      <small v-if="(lastAutoMatch.errors || []).length">错误 {{ lastAutoMatch.errors.length }} 个，已保留人工处理</small>
    </div>

    <div class="tab-bar">
      <button type="button" class="tab-btn" :class="{ active: activeTab === 'review' }" @click="activeTab = 'review'">待映射审核</button>
      <button type="button" class="tab-btn" :class="{ active: activeTab === 'confirmed' }" @click="activeTab = 'confirmed'">已确认映射</button>
      <button type="button" class="tab-btn" :class="{ active: activeTab === 'ignored' }" @click="activeTab = 'ignored'">已忽略</button>
    </div>

    <div v-if="activeTab === 'review'" class="panel">
      <div class="filter-bar">
        <input v-model="search" class="search-input" placeholder="搜索 Emby 演员" @keyup.enter="loadUnmapped" />
        <button type="button" class="btn btn-ghost" @click="loadUnmapped">搜索</button>
        <button type="button" class="btn btn-primary" :disabled="generatingCandidates" @click="generateCandidates">
          {{ generatingCandidates ? '生成中...' : '生成建议' }}
        </button>
      </div>

      <div class="review-filter">
        <button
          v-for="option in reviewFilterOptions"
          :key="option.value"
          type="button"
          class="filter-chip"
          :class="{ active: reviewFilter === option.value }"
          @click="reviewFilter = option.value"
        >
          {{ option.label }}
          <span>{{ reviewFilterCount(option.value) }}</span>
        </button>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="filteredUnmappedActors.length === 0" class="empty">{{ reviewEmptyText }}</div>
      <div v-else class="actor-list">
        <div v-for="actor in filteredUnmappedActors" :key="actor.emby_actor_id" class="mapping-card">
          <div class="actor-side">
            <div class="avatar emby-avatar">
              <img v-if="actor.avatar_url" :src="actor.avatar_url" :alt="actor.emby_actor_name" />
              <span v-else>{{ initials(actor.emby_actor_name) }}</span>
            </div>
            <div class="actor-copy">
              <div class="side-label">Emby 库</div>
              <div class="actor-name">{{ actor.emby_actor_name }}</div>
              <div class="actor-meta">Emby 编号 {{ actor.emby_actor_id }} · {{ actor.total_videos || 0 }} 部</div>
              <button type="button" class="btn btn-ghost compact" @click="ignoreActor(actor)">忽略演员</button>
            </div>
          </div>

          <div class="candidate-side">
            <div class="candidate-search">
              <input
                v-model="candidateQuery[actor.emby_actor_id]"
                class="search-input"
                :placeholder="`搜索 JavInfo：${actor.emby_actor_name}`"
                @keyup.enter="searchJavInfo(actor)"
              />
              <button type="button" class="btn btn-ghost" :disabled="searchingActor[actor.emby_actor_id]" @click="searchJavInfo(actor)">
                {{ searchingActor[actor.emby_actor_id] ? '查找中...' : '查找' }}
              </button>
            </div>
            <div v-if="searchErrors[actor.emby_actor_id]" class="inline-error">{{ searchErrors[actor.emby_actor_id] }}</div>

            <div v-if="actorCandidates(actor).length" class="candidate-list">
              <div
                v-for="candidate in actorCandidates(actor)"
                :key="candidateKey(candidate)"
                class="candidate-card"
                :class="candidateConfidenceClass(candidate)"
              >
                <div class="candidate-compare">
                  <div class="compare-person">
                    <div class="avatar compare-avatar">
                      <img v-if="actor.avatar_url" :src="actor.avatar_url" :alt="actor.emby_actor_name" />
                      <span v-else>{{ initials(actor.emby_actor_name) }}</span>
                    </div>
                    <div class="side-label">Emby 库</div>
                    <strong>{{ actor.emby_actor_name }}</strong>
                  </div>

                  <div class="compare-score">
                    <span class="confidence-badge">{{ candidate.confidence_label || aiConfidenceLabel(candidate) }}</span>
                    <strong>{{ confidenceText(candidate.confidence) }}</strong>
                    <small>{{ aiDecisionLabel(candidate) }}</small>
                  </div>

                  <div class="compare-person">
                    <div class="avatar compare-avatar">
                      <img v-if="candidateAvatar(candidate)" :src="candidateAvatar(candidate)" :alt="candidateName(candidate)" />
                      <span v-else>{{ initials(candidateName(candidate)) }}</span>
                    </div>
                    <div class="side-label">JavInfo 库</div>
                    <strong>{{ candidateName(candidate) }}</strong>
                  </div>
                </div>

                <div class="candidate-main">
                  <div class="candidate-meta">
                    编号 {{ candidate.javinfo_actress_id || candidate.id }} · {{ candidate.movie_count || 0 }} 部 · 置信 {{ confidenceText(candidate.confidence) }}
                    <span class="reason-pill">{{ mappingReasonLabel(candidate) }}</span>
                  </div>
                  <div class="ai-judgement">{{ aiJudgement(candidate) }}</div>
                  <div v-if="candidate.ai_reason" class="ai-result">
                    <strong>{{ aiDecisionLabel(candidate) }}</strong>
                    <span>{{ confidenceText(candidate.ai_confidence) }} · {{ candidate.ai_reason }}</span>
                  </div>
                  <div v-if="candidateRiskFlags(candidate).length" class="risk-row">
                    <span v-for="risk in candidateRiskFlags(candidate)" :key="risk">{{ risk }}</span>
                  </div>
                  <div class="candidate-actions">
                    <button type="button" class="btn btn-primary" @click="confirmMapping(actor, candidate)">确认</button>
                    <button type="button" class="btn btn-ghost" :disabled="reviewingCandidate[candidateKey(candidate)]" @click="reviewCandidateWithAi(actor, candidate)">
                      {{ reviewingCandidate[candidateKey(candidate)] ? '智能判断中...' : '智能判断' }}
                    </button>
                    <button type="button" class="btn btn-ghost" @click="ignoreCandidate(actor, candidate)">忽略</button>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="no-candidates">暂无候选，可搜索或生成建议。</div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="panel">
      <div v-if="loadingMappings" class="empty">加载中...</div>
      <div v-else-if="currentMappings.length === 0" class="empty">{{ emptyText }}</div>
      <div v-else class="mapping-table">
        <div v-for="mapping in currentMappings" :key="mapping.id" class="mapping-row">
          <div>
            <strong>{{ mapping.emby_actor_name }}</strong>
            <small>Emby 编号 {{ mapping.emby_actor_id }}</small>
          </div>
          <span class="arrow">→</span>
          <div class="mapping-target">
            <div class="avatar table-avatar">
              <img v-if="candidateAvatar(mapping)" :src="candidateAvatar(mapping)" :alt="mapping.javinfo_actress_name || '已忽略'" />
              <span v-else>{{ initials(mapping.javinfo_actress_name || '忽') }}</span>
            </div>
            <div>
              <strong>{{ mapping.javinfo_actress_name || '已忽略' }}</strong>
              <small v-if="mapping.javinfo_actress_id">JavInfo 编号 {{ mapping.javinfo_actress_id }} · {{ mapping.movie_count || 0 }} 部</small>
              <small v-if="mapping.status === 'candidate'">
                置信 {{ confidenceText(mapping.confidence) }}
                <span class="reason-pill">{{ mappingReasonLabel(mapping) }}</span>
              </small>
              <small v-else-if="mapping.source">来源 {{ mapping.source }}</small>
            </div>
          </div>
          <span class="status-pill">{{ mapping.status }}</span>
          <button type="button" class="btn btn-ghost" @click="deleteMapping(mapping.id)">解除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { actressImgUrl } from '../utils/imageUrl.js'
import { requestConfirm } from '../utils/confirmDialog'
import { candidateKey, candidateName, confidenceText, initials } from '../utils/inventoryPresentation.js'

const activeTab = ref('review')
const search = ref('')
const reviewFilter = ref('all')
const loading = ref(false)
const loadingMappings = ref(false)
const generatingCandidates = ref(false)
const autoMatching = ref(false)
const AUTO_MATCH_BATCH_LIMIT = 500
const MAPPING_LIST_LIMIT = 500
const mappingSummary = ref({})
const unmappedActors = ref([])
const mappings = ref([])
const candidateQuery = ref({})
const candidateResults = ref({})
const searchingActor = ref({})
const searchErrors = ref({})
const reviewingCandidate = ref({})
const lastAutoMatch = ref(null)

const reviewFilterOptions = [
  { value: 'all', label: '全部' },
  { value: 'withCandidates', label: '已有候选' },
  { value: 'withoutCandidates', label: '暂无候选' },
  { value: 'highConfidence', label: '高置信' },
  { value: 'risky', label: '低置信/歧义' },
]

const coverageText = computed(() => `${Math.round((mappingSummary.value.coverage || 0) * 100)}%`)
const currentMappings = computed(() => mappings.value.filter(m => m.status === activeTab.value))
const emptyText = computed(() => {
  const labels = {
    confirmed: '暂无已确认映射',
    ignored: '暂无已忽略记录',
  }
  return labels[activeTab.value] || '暂无记录'
})
const filteredUnmappedActors = computed(() => unmappedActors.value.filter(actor => actorMatchesReviewFilter(actor, reviewFilter.value)))
const reviewEmptyText = computed(() => search.value ? '没有匹配当前条件的待映射演员' : '暂无待映射演员')

async function loadSummary() {
  const resp = await api.getActorMappingSummary()
  mappingSummary.value = resp.data || {}
}

async function loadUnmapped() {
  loading.value = true
  try {
    const resp = await api.listUnmappedActors({ search: search.value })
    unmappedActors.value = resp.data.data || []
    for (const actor of unmappedActors.value) {
      if (!candidateQuery.value[actor.emby_actor_id]) {
        candidateQuery.value[actor.emby_actor_id] = actor.emby_actor_name
      }
    }
  } finally {
    loading.value = false
  }
}

async function loadMappings() {
  loadingMappings.value = true
  try {
    const statuses = ['confirmed', 'ignored']
    const responses = await Promise.all(
      statuses.map(status => api.listActorMappings({ status, limit: MAPPING_LIST_LIMIT }))
    )
    mappings.value = responses.flatMap(resp => resp.data.data || [])
  } finally {
    loadingMappings.value = false
  }
}

function actorCandidates(actor) {
  const actorId = actor.emby_actor_id
  const searched = candidateResults.value[actorId] || []
  const persisted = actor.candidates || []
  return [
    ...persisted,
    ...searched.map(candidate => ({
      ...candidate,
      javinfo_actress_id: candidate.javinfo_actress_id || candidate.id,
      javinfo_actress_name: candidateName(candidate),
      javinfo_avatar_url: candidate.javinfo_avatar_url || candidate.image_url || candidate.avatar_url || '',
      confidence: candidate.confidence ?? 0,
      confidence_label: candidate.confidence_label || '人工搜索',
      reason: candidate.reason || 'manual_search',
      risk_flags: candidate.risk_flags || [],
      confidence_breakdown: candidate.confidence_breakdown || {},
    })),
  ]
}

function actorMatchesReviewFilter(actor, filter) {
  const candidates = actorCandidates(actor)
  if (filter === 'withCandidates') return candidates.length > 0
  if (filter === 'withoutCandidates') return candidates.length === 0
  if (filter === 'highConfidence') return candidates.some(isHighConfidence)
  if (filter === 'risky') return candidates.some(isRiskyCandidate)
  return true
}

function reviewFilterCount(filter) {
  return unmappedActors.value.filter(actor => actorMatchesReviewFilter(actor, filter)).length
}

function isHighConfidence(candidate) {
  return Number(candidate.confidence || 0) >= 0.9 && candidateRiskFlags(candidate).length === 0
}

function isRiskyCandidate(candidate) {
  const confidence = Number(candidate.confidence || 0)
  return confidence < 0.75 || candidateRiskFlags(candidate).length > 0 || ['exact_ambiguous', 'similar_match'].includes(candidate.reason || candidate.source)
}

function candidateConfidenceClass(candidate) {
  return {
    high: isHighConfidence(candidate),
    risky: isRiskyCandidate(candidate),
  }
}

function aiConfidenceLabel(candidate) {
  const confidence = Number(candidate.confidence || 0)
  if (confidence >= 0.9) return '高置信'
  if (confidence >= 0.75) return '中置信'
  return '低置信'
}

function candidateRiskFlags(candidate) {
  return Array.isArray(candidate.risk_flags) ? candidate.risk_flags : []
}

function aiJudgement(candidate) {
  if (candidate.ai_reason) {
    return `智能判断：${aiDecisionLabel(candidate)}，${candidate.ai_reason}`
  }
  const breakdown = candidate.confidence_breakdown || {}
  const signals = Array.isArray(breakdown.signals) ? breakdown.signals : []
  const label = candidate.confidence_label || aiConfidenceLabel(candidate)
  if (signals.length) return `智能判断：${label}，${signals.join('，')}`
  return `智能判断：${label}，建议人工核对头像和名称。`
}

function aiDecisionLabel(candidate) {
  const labels = {
    same_person: '同一人',
    different_person: '不是同一人',
    uncertain: '不确定',
  }
  return labels[candidate.ai_decision] || '待智能判断'
}

function mappingReasonLabel(mapping) {
  const source = mapping.reason || mapping.source || mapping.match_type || ''
  const labels = {
    auto_confirmed_exact_unique: '精确唯一',
    exact_ambiguous: '精确但歧义',
    exact_review: '精确待审',
    contains_match: '包含匹配',
    similar_match: '相似匹配',
    name_match: '名称匹配',
    auto_match: '自动确认',
    manual_search: '人工搜索',
    manual: '人工',
  }
  return labels[source] || source || '待审核'
}

function candidateAvatar(candidate) {
  return actressImgUrl(candidate.javinfo_avatar_url || candidate.image_url || candidate.avatar_url) || ''
}

async function searchJavInfo(actor) {
  const q = candidateQuery.value[actor.emby_actor_id] || actor.emby_actor_name
  const actorId = actor.emby_actor_id
  searchingActor.value = { ...searchingActor.value, [actorId]: true }
  searchErrors.value = { ...searchErrors.value, [actorId]: '' }
  try {
    const resp = await api.searchActorMappingCandidates({
      emby_actor_id: actor.emby_actor_id,
      emby_actor_name: actor.emby_actor_name,
      q,
      limit: 10,
    })
    candidateResults.value = {
      ...candidateResults.value,
      [actorId]: resp.data.data || []
    }
    if ((resp.data.data || []).length === 0) {
      searchErrors.value = { ...searchErrors.value, [actorId]: '未找到可用候选' }
    }
  } catch (error) {
    searchErrors.value = {
      ...searchErrors.value,
      [actorId]: error.response?.data?.detail || error.message || '查找失败'
    }
  } finally {
    searchingActor.value = { ...searchingActor.value, [actorId]: false }
  }
}

async function reviewCandidateWithAi(actor, candidate) {
  const key = candidateKey(candidate)
  reviewingCandidate.value = { ...reviewingCandidate.value, [key]: true }
  try {
    const payload = mappingPayload(actor, candidate)
    const resp = await api.reviewActorMappingWithAi(payload)
    mergeCandidateReview(actor.emby_actor_id, candidate, resp.data || {})
    ElMessage.success('智能判断完成')
  } finally {
    reviewingCandidate.value = { ...reviewingCandidate.value, [key]: false }
  }
}

function mergeCandidateReview(actorId, candidate, review) {
  const targetId = candidate.id || candidate.javinfo_actress_id
  const patch = {
    ai_decision: review.ai_decision,
    ai_confidence: review.ai_confidence,
    ai_reason: review.ai_reason,
    ai_model: review.ai_model,
  }
  const update = item => {
    const itemId = item.id || item.javinfo_actress_id
    return String(itemId) === String(targetId) ? { ...item, ...patch } : item
  }
  candidateResults.value = {
    ...candidateResults.value,
    [actorId]: (candidateResults.value[actorId] || []).map(update),
  }
  unmappedActors.value = unmappedActors.value.map(actor => {
    if (String(actor.emby_actor_id) !== String(actorId)) return actor
    return {
      ...actor,
      candidates: (actor.candidates || []).map(update),
    }
  })
}

function mappingPayload(actor, candidate) {
  return {
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    javinfo_actress_id: candidate.id || candidate.javinfo_actress_id,
    javinfo_actress_name: candidateName(candidate),
    confidence: candidate.confidence || 1,
    source: candidate.reason || candidate.source || 'manual_search',
    javinfo_avatar_url: candidate.javinfo_avatar_url || candidate.image_url || candidate.avatar_url || '',
    movie_count: candidate.movie_count || 0,
    confidence_breakdown: candidate.confidence_breakdown || {},
    confidence_label: candidate.confidence_label || aiConfidenceLabel(candidate),
    risk_flags: candidateRiskFlags(candidate),
  }
}

async function confirmMapping(actor, candidate) {
  await api.confirmActorMapping({ ...mappingPayload(actor, candidate), source: 'manual' })
  ElMessage.success('映射已确认')
  await reloadAll()
}

async function ignoreCandidate(actor, candidate) {
  await api.ignoreActorMapping({ ...mappingPayload(actor, candidate), source: 'manual' })
  ElMessage.success('候选已忽略')
  await reloadAll()
}

async function ignoreActor(actor) {
  await api.ignoreActorMapping({
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    source: 'manual'
  })
  ElMessage.success('已忽略')
  await reloadAll()
}

async function deleteMapping(id) {
  await api.deleteActorMapping(id)
  ElMessage.success('映射已解除')
  await reloadAll()
}

async function reloadAll() {
  await Promise.all([loadSummary(), loadUnmapped(), loadMappings()])
}

async function generateCandidates() {
  generatingCandidates.value = true
  try {
    const resp = await api.generateActorMappingCandidates({
      search: search.value || undefined,
      limit: 50,
      per_actor: 3,
      min_confidence: 0.55
    })
    ElMessage.success(`已检查 ${resp.data.checked || 0} 个演员，生成 ${resp.data.created || 0} 个建议`)
    await reloadAll()
  } finally {
    generatingCandidates.value = false
  }
}

async function runAutoMatchRequest(dryRun) {
  autoMatching.value = true
  try {
    const resp = await api.autoMatchActorMappings({
      dry_run: dryRun,
      limit: AUTO_MATCH_BATCH_LIMIT,
    })
    lastAutoMatch.value = resp.data || {}
    const action = dryRun ? '预演完成' : '自动匹配完成'
    ElMessage.success(`${action}：确认 ${lastAutoMatch.value.auto_confirmed || 0}，待审 ${lastAutoMatch.value.candidates_created || 0}`)
    if (!dryRun) await reloadAll()
  } finally {
    autoMatching.value = false
  }
}

async function previewAutoMatch() {
  await runAutoMatchRequest(true)
}

async function runAutoMatch() {
  const confirmed = await requestConfirm({
    title: '执行自动匹配?',
    message: '系统会根据当前规则自动确认高置信演员映射，并生成需要人工审核的候选。',
    details: [`影响范围：本批最多 ${AUTO_MATCH_BATCH_LIMIT} 个待映射演员`, '可先使用“自动匹配预演”查看预计结果'],
    tone: 'warning',
    confirmText: '执行自动匹配'
  })
  if (!confirmed) return
  await runAutoMatchRequest(false)
}

onMounted(reloadAll)
</script>

<style scoped>
.mapping-page {}
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.page-header h1 { margin: 0; font-size: var(--type-page-title); line-height: 1.1; letter-spacing: 0; }
.header-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.summary-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.summary-card {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}
.summary-card strong { display: block; font-size: var(--type-workbench-title); color: var(--text-primary); }
.summary-card span { color: var(--text-secondary); font-size: var(--type-control); }
.auto-match-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}
.auto-match-panel strong,
.auto-match-panel span {
  display: block;
}
.auto-match-panel span,
.auto-match-panel small {
  color: var(--text-secondary);
  font-size: 12px;
}
.tab-bar { display: flex; gap: 6px; margin-bottom: 16px; border-bottom: 1px solid var(--border); overflow-x: auto; }
.tab-btn {
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  padding: 10px 16px;
  cursor: pointer;
}
.tab-btn.active { color: var(--text-primary); border-bottom-color: var(--active-indicator); }
.panel { min-height: 240px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.review-filter {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  overflow-x: auto;
}
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--bg-card);
  color: var(--text-secondary);
  padding: 7px 11px;
  cursor: pointer;
  white-space: nowrap;
}
.filter-chip.active {
  border-color: var(--active-border);
  background: var(--active-bg);
  color: var(--text-primary);
}
.filter-chip span {
  color: var(--text-muted);
  font-size: 12px;
}
.search-input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 8px 10px;
}
.actor-list { display: flex; flex-direction: column; gap: 12px; }
.mapping-card {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) minmax(360px, 1.3fr);
  gap: 16px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}
.actor-side { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.actor-copy { min-width: 0; }
.side-label {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.2;
}
.avatar {
  flex-shrink: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
}
.avatar img,
.avatar span {
  width: 100%;
  height: 100%;
}
.avatar img {
  display: block;
  object-fit: cover;
}
.avatar span {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-weight: 700;
}
.emby-avatar {
  width: 64px;
  height: 84px;
}
.javinfo-avatar {
  width: 68px;
  height: 88px;
}
.table-avatar {
  width: 40px;
  height: 52px;
}
.actor-name { font-weight: 700; color: var(--text-primary); }
.actor-meta,
.mapping-row small { display: block; margin-top: 4px; color: var(--text-muted); font-size: 12px; }
.candidate-search { display: flex; gap: 8px; margin-bottom: 10px; }
.inline-error {
  margin-bottom: 10px;
  color: #ffb340;
  font-size: 12px;
}
.candidate-list { display: flex; flex-direction: column; gap: 8px; }
.candidate-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
}
.candidate-card.high { border-color: rgba(52, 199, 89, 0.55); }
.candidate-card.risky { border-color: rgba(255, 159, 10, 0.55); }
.candidate-compare {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}
.compare-person {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 0;
  text-align: center;
}
.compare-person strong {
  max-width: 100%;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compare-avatar {
  width: 76px;
  height: 98px;
}
.compare-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  min-width: 92px;
  color: var(--text-secondary);
  text-align: center;
}
.compare-score strong {
  color: var(--text-primary);
  font-size: 20px;
}
.compare-score small {
  color: var(--text-muted);
  font-size: 12px;
}
.candidate-main { min-width: 0; }
.candidate-title-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}
.candidate-title-row strong {
  color: var(--text-primary);
}
.candidate-meta,
.ai-judgement,
.no-candidates {
  color: var(--text-muted);
  font-size: 12px;
}
.ai-judgement {
  margin-top: 6px;
  color: var(--text-secondary);
}
.ai-result {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.ai-result strong {
  color: var(--text-primary);
}
.confidence-badge {
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-primary);
  font-size: 12px;
  padding: 3px 8px;
  white-space: nowrap;
}
.risk-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.risk-row span {
  border: 1px solid rgba(255, 159, 10, 0.45);
  border-radius: 999px;
  color: #ffb340;
  font-size: 11px;
  padding: 2px 7px;
}
.candidate-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
}
.mapping-target {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.arrow { color: var(--text-muted); font-weight: 700; }
.status-pill {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.reason-pill {
  display: inline-flex;
  align-items: center;
  margin-left: 6px;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 1px 6px;
  color: var(--text-secondary);
  font-size: 11px;
}
.btn {
  padding: 8px 12px;
  white-space: nowrap;
  min-height: 44px;
}
.btn.compact {
  min-height: 34px;
  margin-top: 10px;
  padding: 6px 10px;
}
.empty { padding: 40px 12px; text-align: center; color: var(--text-secondary); }
@media (max-width: 760px) {
  .page-header,
  .auto-match-panel {
    flex-direction: column;
    align-items: stretch;
  }
  .summary-row,
  .mapping-card,
  .candidate-compare { grid-template-columns: 1fr; }
  .header-actions {
    justify-content: flex-start;
  }
  .candidate-search,
  .filter-bar { flex-direction: column; }
  .mapping-row { grid-template-columns: 1fr; }
  .tab-btn,
  .search-input {
    min-height: 44px;
  }
}
</style>
