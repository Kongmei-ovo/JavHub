<template>
  <div class="mapping-page">
    <div class="page-header">
      <div>
        <h1>演员映射</h1>
        <p>把 Emby 演员确认到 JavInfo 演员，库存对比只使用已确认映射。</p>
      </div>
      <button class="btn-primary" @click="reloadAll">刷新</button>
    </div>

    <div class="summary-row">
      <div class="summary-card">
        <strong>{{ mappingSummary.confirmed || 0 }}</strong>
        <span>已确认</span>
      </div>
      <div class="summary-card">
        <strong>{{ mappingSummary.unmapped || 0 }}</strong>
        <span>未映射</span>
      </div>
      <div class="summary-card">
        <strong>{{ mappingSummary.candidate || 0 }}</strong>
        <span>建议候选</span>
      </div>
      <div class="summary-card">
        <strong>{{ coverageText }}</strong>
        <span>映射覆盖率</span>
      </div>
    </div>

    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'unmapped' }" @click="activeTab = 'unmapped'">未映射演员</button>
      <button class="tab-btn" :class="{ active: activeTab === 'candidate' }" @click="activeTab = 'candidate'">建议候选</button>
      <button class="tab-btn" :class="{ active: activeTab === 'confirmed' }" @click="activeTab = 'confirmed'">已确认映射</button>
      <button class="tab-btn" :class="{ active: activeTab === 'ignored' }" @click="activeTab = 'ignored'">已忽略</button>
    </div>

    <div v-if="activeTab === 'unmapped'" class="panel">
      <div class="filter-bar">
        <input v-model="search" class="search-input" placeholder="搜索 Emby 演员" @keyup.enter="loadUnmapped" />
        <button class="btn-secondary" @click="loadUnmapped">搜索</button>
        <button class="btn-primary" :disabled="generatingCandidates" @click="generateCandidates">
          {{ generatingCandidates ? '生成中...' : '生成建议' }}
        </button>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="unmappedActors.length === 0" class="empty">暂无未映射演员</div>
      <div v-else class="actor-list">
        <div v-for="actor in unmappedActors" :key="actor.emby_actor_id" class="mapping-card">
          <div class="actor-side">
            <div class="avatar">
              <img v-if="actor.avatar_url" :src="actor.avatar_url" :alt="actor.emby_actor_name" />
            </div>
            <div>
              <div class="actor-name">{{ actor.emby_actor_name }}</div>
              <div class="actor-meta">Emby ID {{ actor.emby_actor_id }} · {{ actor.total_videos || 0 }} 部</div>
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
              <button class="btn-secondary" @click="searchJavInfo(actor)">查找</button>
              <button class="btn-ghost" @click="ignoreActor(actor)">忽略</button>
            </div>
            <div v-if="suggestedMappings(actor).length" class="suggestion-block">
              <div class="suggestion-title">名称匹配建议</div>
              <div
                v-for="candidate in suggestedMappings(actor)"
                :key="candidate.id"
                class="javinfo-row"
              >
                <span>{{ candidate.javinfo_actress_name || candidate.javinfo_actress_id }}</span>
                <small>ID {{ candidate.javinfo_actress_id }} · 置信 {{ confidenceText(candidate.confidence) }}</small>
                <button class="btn-primary" @click="confirmMapping(actor, candidate)">确认</button>
                <button class="btn-ghost" @click="ignoreCandidate(actor, candidate)">忽略</button>
              </div>
            </div>
            <div v-if="candidateResults[actor.emby_actor_id]?.length" class="javinfo-results">
              <div
                v-for="candidate in candidateResults[actor.emby_actor_id]"
                :key="candidate.id"
                class="javinfo-row"
              >
                <span>{{ candidate.name_kanji || candidate.name_romaji || candidate.name || candidate.id }}</span>
                <small>ID {{ candidate.id }} · {{ candidate.movie_count || 0 }} 部</small>
                <button class="btn-primary" @click="confirmMapping(actor, candidate)">确认</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="panel">
      <div v-if="currentMappings.length === 0" class="empty">暂无记录</div>
      <div v-else class="mapping-table">
        <div v-for="mapping in currentMappings" :key="mapping.id" class="mapping-row">
          <div>
            <strong>{{ mapping.emby_actor_name }}</strong>
            <small>Emby ID {{ mapping.emby_actor_id }}</small>
          </div>
          <span class="arrow">→</span>
          <div>
            <strong>{{ mapping.javinfo_actress_name || '已忽略' }}</strong>
            <small v-if="mapping.javinfo_actress_id">JavInfo ID {{ mapping.javinfo_actress_id }}</small>
          </div>
          <span class="status-pill">{{ mapping.status }}</span>
          <button class="btn-ghost" @click="deleteMapping(mapping.id)">解除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const activeTab = ref('unmapped')
const search = ref('')
const loading = ref(false)
const generatingCandidates = ref(false)
const mappingSummary = ref({})
const unmappedActors = ref([])
const mappings = ref([])
const candidateQuery = ref({})
const candidateResults = ref({})

const coverageText = computed(() => `${Math.round((mappingSummary.value.coverage || 0) * 100)}%`)
const currentMappings = computed(() => mappings.value.filter(m => m.status === activeTab.value))
const candidateMappingsByActor = computed(() => {
  const grouped = {}
  for (const mapping of mappings.value.filter(m => m.status === 'candidate')) {
    const key = String(mapping.emby_actor_id)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(mapping)
  }
  return grouped
})

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
  const resp = await api.listActorMappings()
  mappings.value = resp.data.data || []
}

function suggestedMappings(actor) {
  return candidateMappingsByActor.value[String(actor.emby_actor_id)] || []
}

function confidenceText(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

async function searchJavInfo(actor) {
  const q = candidateQuery.value[actor.emby_actor_id] || actor.emby_actor_name
  const resp = await api.searchActors(q)
  candidateResults.value = {
    ...candidateResults.value,
    [actor.emby_actor_id]: resp.data.data || resp.data || []
  }
}

async function confirmMapping(actor, candidate) {
  const javinfoId = candidate.id || candidate.javinfo_actress_id
  const javinfoName = candidate.name_kanji || candidate.name_romaji || candidate.name || candidate.javinfo_actress_name || ''
  await api.confirmActorMapping({
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    javinfo_actress_id: javinfoId,
    javinfo_actress_name: javinfoName,
    confidence: candidate.confidence || 1,
    source: 'manual'
  })
  ElMessage.success('映射已确认')
  await reloadAll()
}

async function ignoreCandidate(actor, candidate) {
  await api.ignoreActorMapping({
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    javinfo_actress_id: candidate.javinfo_actress_id,
    javinfo_actress_name: candidate.javinfo_actress_name,
    source: 'manual'
  })
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

onMounted(reloadAll)
</script>

<style scoped>
.mapping-page { padding: 16px; }
.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.page-header h1 { margin: 0; font-size: 22px; }
.page-header p { margin: 6px 0 0; color: var(--text-secondary); font-size: 13px; }
.summary-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.summary-card {
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
}
.summary-card strong { display: block; font-size: 24px; color: var(--text-primary); }
.summary-card span { color: var(--text-secondary); font-size: 13px; }
.tab-bar { display: flex; gap: 6px; margin-bottom: 16px; border-bottom: 1px solid var(--border); }
.tab-btn {
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  padding: 10px 16px;
  cursor: pointer;
}
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.panel { min-height: 240px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 8px 10px;
}
.actor-list { display: flex; flex-direction: column; gap: 12px; }
.mapping-card {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(260px, 1.2fr);
  gap: 16px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
}
.actor-side { display: flex; align-items: center; gap: 12px; min-width: 0; }
.avatar {
  width: 48px;
  height: 64px;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: 6px;
  background: var(--bg-secondary);
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.actor-name { font-weight: 700; color: var(--text-primary); }
.actor-meta,
.mapping-row small { display: block; margin-top: 4px; color: var(--text-muted); font-size: 12px; }
.candidate-search { display: flex; gap: 8px; }
.javinfo-results { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.javinfo-row,
.mapping-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
}
.mapping-row { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto auto; margin-bottom: 8px; }
.javinfo-row small { color: var(--text-muted); }
.arrow { color: var(--accent); font-weight: 700; }
.status-pill {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--text-secondary);
  font-size: 12px;
}
.btn-primary,
.btn-secondary,
.btn-ghost {
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary { border: 0; background: var(--accent); color: #fff; }
.btn-secondary { border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); }
.btn-ghost { border: 1px solid var(--border); background: transparent; color: var(--text-secondary); }
.empty { padding: 40px 12px; text-align: center; color: var(--text-secondary); }
@media (max-width: 760px) {
  .summary-row,
  .mapping-card { grid-template-columns: 1fr; }
  .candidate-search,
  .filter-bar { flex-direction: column; }
  .mapping-row { grid-template-columns: 1fr; }
}
</style>
