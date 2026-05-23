<template>
  <div class="library-organize-page page-shell page-shell--workspace">
    <header class="organize-header apple-surface">
      <div class="organize-header__copy">
        <h1>片库整理</h1>
        <p>{{ headerSummary }}</p>
      </div>
      <div class="header-actions">
        <div v-if="isJobRunning" class="job-progress" aria-label="库存作业进度">
          <span>{{ currentProgress }}%</span>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="collecting || comparing" @click="triggerCollect">
          {{ collecting ? '采集中...' : '采集 Emby' }}
        </button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="collecting || comparing || !snapshotKey" @click="triggerFullCompare">
          {{ comparing ? '对比中...' : '全量对比' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" @click="reloadAll">刷新</button>
      </div>
    </header>

    <section class="status-strip organize-status apple-surface" aria-label="片库整理状态">
      <button
        v-for="metric in statusMetrics"
        :key="metric.key"
        class="status-cell"
        :class="{ urgent: metric.urgent }"
        type="button"
        @click="openMetric(metric.key)"
      >
        <span class="status-value">{{ metric.value }}</span>
        <span class="status-label">{{ metric.label }}</span>
        <small>{{ metric.hint }}</small>
      </button>
    </section>

    <section v-if="!snapshotKey" class="setup-banner apple-surface">
      <div>
        <strong>还没有 Emby 快照</strong>
        <span>先采集媒体库，后续映射、库存对比和重复清理才有可靠基准。</span>
      </div>
      <button class="btn btn-primary btn-sm" type="button" :disabled="collecting" @click="triggerCollect">
        {{ collecting ? '采集中...' : '开始采集' }}
      </button>
    </section>

    <nav class="organize-tabs apple-surface" aria-label="片库整理视图">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="tab-btn"
        type="button"
        :class="{ active: activeTab === tab.value }"
        @click="setTab(tab.value)"
      >
        <span>{{ tab.label }}</span>
        <small v-if="tab.count !== null">{{ tab.count }}</small>
      </button>
    </nav>

    <div v-if="loadingInitial" class="loading-panel">加载中...</div>
    <div v-else-if="error" class="empty-panel">
      <h2>片库整理加载失败</h2>
      <p>{{ error }}</p>
      <button class="btn btn-primary" type="button" @click="reloadAll">重试</button>
    </div>

    <template v-else>
      <section v-if="activeTab === 'queue'" class="organize-workbench">
        <article class="workbench-panel queue-panel">
          <div class="panel-head">
            <div>
              <h2>待处理</h2>
              <p>{{ queueSummary }}</p>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="reloadAll">刷新队列</button>
          </div>

          <div class="priority-list">
            <button class="priority-row" type="button" @click="setTab('mapping')">
              <span class="priority-mark warning">{{ mappingSummary.unmapped || 0 }}</span>
              <div>
                <strong>确认演员映射</strong>
                <small>未映射演员会让库存对比跳过对应作品。</small>
              </div>
              <span>去处理</span>
            </button>
            <button class="priority-row" type="button" @click="setTab('inventory')">
              <span class="priority-mark">{{ missingVideos.length }}</span>
              <div>
                <strong>处理缺失影片</strong>
                <small>把库存缺口转成库存来源下载候选。</small>
              </div>
              <span>查看</span>
            </button>
            <button class="priority-row" type="button" @click="setTab('candidates')">
              <span class="priority-mark">{{ inventoryCandidateStats.candidate || 0 }}</span>
              <div>
                <strong>审核库存候选</strong>
                <small>只显示库存发现的候选，不混入订阅和补全来源。</small>
              </div>
              <span>审核</span>
            </button>
            <button class="priority-row" type="button" @click="setTab('duplicates')">
              <span class="priority-mark danger">{{ duplicates.length }}</span>
              <div>
                <strong>清理重复条目</strong>
                <small>逐条删除或忽略可疑重复，保留人工判断。</small>
              </div>
              <span>清理</span>
            </button>
          </div>
        </article>

        <aside class="side-stack">
          <article class="workbench-panel">
            <div class="panel-head">
              <div>
                <h2>整理流程</h2>
                <p>从快照到候选，按阻塞关系顺着走。</p>
              </div>
            </div>
            <div class="flow-steps">
              <button v-for="step in flowSteps" :key="step.key" type="button" @click="openMetric(step.key)">
                <span>{{ step.index }}</span>
                <strong>{{ step.title }}</strong>
                <small>{{ step.hint }}</small>
              </button>
            </div>
          </article>

          <article class="workbench-panel compact-check">
            <div class="panel-head">
              <div>
                <h2>单片检测</h2>
                <p>临时核对一个番号是否已经在 Emby。</p>
              </div>
            </div>
            <div class="mini-check-form">
              <input v-model.trim="checkCode" placeholder="例如 ABC-123" @keyup.enter="checkOneVideo" />
              <button class="btn btn-primary btn-sm" type="button" :disabled="checkingVideo || !checkCode" @click="checkOneVideo">
                {{ checkingVideo ? '检测中...' : '检测' }}
              </button>
            </div>
            <div v-if="checkResult" class="mini-check-result" :class="{ exists: checkResult.exists }">
              <strong>{{ checkResult.exists ? '已存在' : '不在库中' }}</strong>
              <span v-if="checkResult.exists">{{ (checkResult.items || []).length }} 个 Emby 条目</span>
              <button v-else class="inline-link" type="button" @click="createManualInventoryCandidate">转为候选</button>
            </div>
          </article>
        </aside>
      </section>

      <section v-else-if="activeTab === 'inventory'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>库存对比</h2>
            <p>按演员查看 Emby 存量和缺失数量，缺口可转入库存候选。</p>
          </div>
          <div class="panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" :disabled="collecting || comparing" @click="triggerCollect">采集 Emby</button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="collecting || comparing || !snapshotKey" @click="triggerFullCompare">全量对比</button>
          </div>
        </div>

        <div class="organize-filters">
          <input v-model.trim="actorSearch" placeholder="搜索演员" @keyup.enter="loadInventoryActors" />
          <GlassSelect v-model="actorSort" :options="actorSortOptions" size="regular" @change="loadInventoryActors" />
          <button class="btn btn-ghost btn-sm" type="button" @click="loadInventoryActors">搜索</button>
        </div>

        <div v-if="selectedActor" class="actor-detail-panel">
          <div class="actor-detail-head">
            <button class="btn btn-ghost btn-sm" type="button" @click="clearActorDetail">返回演员列表</button>
            <div>
              <strong>{{ selectedActor.display_name || selectedActor.actress_name }}</strong>
              <span>Emby {{ selectedActor.total_videos || 0 }} 部 · 缺失 {{ actorMissingVideos.length }} 部</span>
            </div>
            <button v-if="selectedActor.mapping_status !== 'confirmed'" class="btn btn-primary btn-sm" type="button" @click="setTab('mapping')">处理映射</button>
          </div>
          <div class="missing-grid">
            <article v-for="video in actorMissingVideos" :key="video.content_id" class="missing-video">
              <img v-if="video.jacket_thumb_url" :src="video.jacket_thumb_url" :alt="video.title || video.content_id" />
              <div v-else class="poster-fallback">{{ video.content_id }}</div>
              <div>
                <strong>{{ video.content_id }}</strong>
                <span>{{ video.title || '未命名影片' }}</span>
                <small>{{ video.release_date || '日期未知' }}</small>
              </div>
              <button class="btn btn-ghost btn-sm" type="button" @click="fillVideo(video)">转为候选</button>
            </article>
          </div>
          <div v-if="actorMissingVideos.length === 0" class="empty-inline">这个演员暂无缺失影片。</div>
        </div>

        <template v-else>
          <div v-if="loadingActors" class="empty-inline">加载演员中...</div>
          <div v-else-if="inventoryActors.length === 0" class="empty-inline">暂无可对比演员。</div>
          <div v-else class="actor-grid">
            <ActorPortraitCard
              v-for="actor in inventoryActors"
              :key="actor.actress_id"
              :actor="inventoryActorCardActor(actor)"
              :name="inventoryActorName(actor)"
              :subtitle="inventoryActorSubtitle(actor)"
              :avatar-url="inventoryActorAvatar(actor)"
              :meta="inventoryActorMeta(actor)"
              density="standard"
              @open="goActorDetail(actor.actress_id)"
            />
          </div>
        </template>
      </section>

      <section v-else-if="activeTab === 'check'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>单片检测</h2>
            <p>输入番号，检查 JavInfo 与 Emby 库中是否已有条目。</p>
          </div>
        </div>
        <div class="check-form">
          <input v-model.trim="checkCode" placeholder="输入影片番号，如 ABC-123" @keyup.enter="checkOneVideo" />
          <button class="btn btn-primary" type="button" :disabled="checkingVideo || !checkCode" @click="checkOneVideo">
            {{ checkingVideo ? '检测中...' : '检测' }}
          </button>
        </div>
        <div v-if="checkResult" class="check-result" :class="{ exists: checkResult.exists }">
          <strong>{{ checkResult.exists ? '影片存在于 Emby 库中' : '影片不在 Emby 库中' }}</strong>
          <div v-if="checkResult.exists" class="check-items">
            <div v-for="item in checkResult.items" :key="item.id || item.path" class="check-item">
              <span>{{ item.name }}</span>
              <small>{{ item.path }}</small>
            </div>
          </div>
          <button v-else class="btn btn-ghost btn-sm" type="button" @click="createManualInventoryCandidate">转为库存候选</button>
        </div>
      </section>

      <section v-else-if="activeTab === 'mapping'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>演员映射</h2>
            <p>确认 Emby 演员到 JavInfo 演员的关系，优先处理会阻塞库存对比的未映射项。</p>
          </div>
          <div class="panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" :disabled="autoMatching" @click="previewAutoMatch">
              {{ autoMatching ? '预演中...' : '自动匹配预演' }}
            </button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="autoMatching" @click="runAutoMatch">执行自动匹配</button>
          </div>
        </div>

        <div class="organize-filters">
          <input v-model.trim="mappingSearch" placeholder="搜索 Emby 演员" @keyup.enter="loadUnmappedActors" />
          <button class="btn btn-ghost btn-sm" type="button" @click="loadUnmappedActors">搜索</button>
          <button class="btn btn-primary btn-sm" type="button" :disabled="generatingCandidates" @click="generateMappingCandidates">
            {{ generatingCandidates ? '生成中...' : '生成建议' }}
          </button>
        </div>

        <div v-if="lastAutoMatch" class="auto-match-panel">
          <strong>{{ lastAutoMatch.dry_run ? '自动匹配预演' : '自动匹配结果' }}</strong>
          <span>检查 {{ lastAutoMatch.checked || 0 }} · 自动确认 {{ lastAutoMatch.auto_confirmed || 0 }} · 待审 {{ lastAutoMatch.candidates_created || 0 }} · 歧义 {{ lastAutoMatch.ambiguous || 0 }}</span>
        </div>

        <div v-if="loadingMappings" class="empty-inline">加载映射中...</div>
        <div v-else-if="unmappedActors.length === 0" class="empty-inline">暂无待映射演员。</div>
        <div v-else class="mapping-list">
          <article v-for="actor in unmappedActors" :key="actor.emby_actor_id" class="mapping-item">
            <div class="actor-avatar small">
              <img v-if="actor.avatar_url" :src="actor.avatar_url" :alt="actor.emby_actor_name" />
              <span v-else>{{ initials(actor.emby_actor_name) }}</span>
            </div>
            <div class="mapping-copy">
              <strong>{{ actor.emby_actor_name }}</strong>
              <small>Emby 编号 {{ actor.emby_actor_id }} · {{ actor.total_videos || 0 }} 部</small>
              <div v-if="actor.candidates?.length" class="candidate-pills">
                <button v-for="candidate in actor.candidates" :key="candidateKey(candidate)" type="button" @click="confirmMapping(actor, candidate)">
                  {{ candidateName(candidate) }} · {{ confidenceText(candidate.confidence) }}
                </button>
              </div>
              <span v-else class="muted">暂无候选，先生成建议或进入原审核流。</span>
            </div>
            <button class="btn btn-ghost btn-sm" type="button" @click="ignoreActor(actor)">忽略</button>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'candidates'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>库存候选</h2>
            <p>这里只处理库存发现的下载候选，其他来源仍留在下载任务页。</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="$router.push({ path: '/downloads', query: { tab: 'candidates', source: 'inventory' } })">打开下载任务页</button>
        </div>
        <div class="organize-filters">
          <input v-model.trim="candidateSearch" placeholder="搜索番号、标题、演员" @keyup.enter="loadInventoryCandidates" />
          <button class="chip" type="button" :class="{ active: candidateStatus === 'candidate' }" @click="setCandidateStatus('candidate')">待确认</button>
          <button class="chip" type="button" :class="{ active: candidateNeedsMagnet === true }" @click="setCandidateNeedsMagnet(true)">待补磁力</button>
          <button class="chip" type="button" :class="{ active: candidateNeedsMagnet === false }" @click="setCandidateNeedsMagnet(false)">可批准</button>
          <button class="chip" type="button" :class="{ active: !candidateStatus && candidateNeedsMagnet === null }" @click="setCandidateStatus('')">全部</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="loadInventoryCandidates">搜索</button>
        </div>
        <div v-if="inventoryCandidates.length" class="candidate-grid">
          <article v-for="candidate in inventoryCandidates" :key="candidate.id" class="inventory-candidate">
            <img v-if="candidate.jacket_thumb_url" :src="candidate.jacket_thumb_url" :alt="candidate.title || candidate.content_id" />
            <div v-else class="poster-fallback">{{ candidate.dvd_id || candidate.content_id }}</div>
            <div>
              <strong>{{ candidate.dvd_id || candidate.content_id }}</strong>
              <span>{{ candidate.title || candidate.content_id }}</span>
              <small>{{ candidate.actress_name || '未知演员' }} · {{ candidateStatusLabel(candidate.status) }} · {{ candidate.magnet ? '已有磁力' : '待补磁力' }}</small>
            </div>
            <div class="candidate-actions">
              <button class="btn btn-ghost btn-sm" type="button" :disabled="mutatingCandidateId === candidate.id" @click="enrichCandidate(candidate)">补磁力</button>
              <button class="btn btn-primary btn-sm" type="button" :disabled="mutatingCandidateId === candidate.id || !candidate.magnet" @click="approveCandidate(candidate)">批准</button>
              <button class="btn btn-ghost btn-sm" type="button" :disabled="mutatingCandidateId === candidate.id" @click="rejectCandidate(candidate)">拒绝</button>
            </div>
          </article>
        </div>
        <div v-else class="empty-inline">暂无库存来源下载候选。</div>
      </section>

      <section v-else-if="activeTab === 'duplicates'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>重复清理</h2>
            <p>来自最新 Emby 快照或实时检测的可疑重复条目。</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="loadDuplicates">重新扫描</button>
        </div>
        <div v-if="duplicates.length" class="duplicate-list">
          <article v-for="item in duplicates" :key="item.emby_item_id" class="duplicate-group">
            <div class="duplicate-head">
              <strong>{{ item.content_id }}</strong>
              <span>{{ item.duplicate_count ? `${item.duplicate_count} 个条目` : `相似度 ${confidenceText(item.similarity)}` }}</span>
            </div>
            <small>{{ item.reason }}</small>
            <div class="duplicate-entries">
              <div v-for="duplicate in duplicateItems(item)" :key="duplicate.emby_item_id" class="duplicate-entry">
                <div>
                  <strong>{{ duplicate.emby_name }}</strong>
                  <small>{{ duplicate.filename || duplicate.emby_item_id }}</small>
                </div>
                <div class="duplicate-actions">
                  <button class="btn btn-ghost btn-sm" type="button" @click="ignoreDuplicate(duplicate)">忽略</button>
                  <button class="btn btn-primary btn-sm danger" type="button" @click="deleteDuplicate(duplicate)">删除</button>
                </div>
              </div>
            </div>
          </article>
        </div>
        <div v-else class="empty-inline">暂无可疑重复。</div>
      </section>

      <section v-else-if="activeTab === 'jobs'" class="workbench-panel apple-reveal">
        <div class="panel-head">
          <div>
            <h2>作业历史</h2>
            <p>采集、全量对比和单演员对比的最近记录。</p>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新</button>
        </div>
        <div v-if="jobs.length" class="job-list">
          <article v-for="job in jobs" :key="job.id" class="job-row">
            <div>
              <strong>{{ jobTypeLabel(job.job_type) }}</strong>
              <small>{{ job.created_at }} · {{ job.snapshot_key || '无快照' }}</small>
            </div>
            <span class="status-pill">{{ job.status }}</span>
            <span>{{ job.progress || 0 }}%</span>
          </article>
        </div>
        <div v-else class="empty-inline">暂无作业记录。</div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import ActorPortraitCard from '../components/ActorPortraitCard.vue'
import GlassSelect from '../components/GlassSelect.vue'
import { ElMessage } from '../utils/message.js'
import { requestConfirm } from '../utils/confirmDialog'

const route = useRoute()
const router = useRouter()

const activeTab = ref('queue')
const loadingInitial = ref(true)
const error = ref('')
const snapshotKey = ref('')
const inventoryActors = ref([])
const loadingActors = ref(false)
const actorSearch = ref('')
const actorSort = ref('missing_count')
const selectedActor = ref(null)
const actorMissingVideos = ref([])
const mappingSummary = ref({})
const unmappedActors = ref([])
const loadingMappings = ref(false)
const mappingSearch = ref('')
const generatingCandidates = ref(false)
const autoMatching = ref(false)
const lastAutoMatch = ref(null)
const missingVideos = ref([])
const inventoryCandidates = ref([])
const inventoryCandidateStats = ref({})
const candidateSearch = ref('')
const candidateStatus = ref('candidate')
const candidateNeedsMagnet = ref(null)
const mutatingCandidateId = ref(null)
const duplicates = ref([])
const jobs = ref([])
const collecting = ref(false)
const comparing = ref(false)
const currentProgress = ref(0)
const checkCode = ref('')
const checkingVideo = ref(false)
const checkResult = ref(null)

let pollTimer = null

const actorSortOptions = [
  { value: 'missing_count', label: '缺失 多→少' },
  { value: 'total_videos', label: '影片数 多→少' },
  { value: 'actress_name', label: '名称 A→Z' },
]

const tabs = computed(() => [
  { value: 'queue', label: '待处理', count: queueCount.value },
  { value: 'inventory', label: '库存对比', count: missingVideos.value.length },
  { value: 'check', label: '单片检测', count: null },
  { value: 'mapping', label: '演员映射', count: mappingSummary.value.unmapped || 0 },
  { value: 'candidates', label: '库存候选', count: inventoryCandidateStats.value.candidate || 0 },
  { value: 'duplicates', label: '重复清理', count: duplicates.value.length },
  { value: 'jobs', label: '作业历史', count: jobs.value.length },
])

const queueCount = computed(() => (
  Number(mappingSummary.value.unmapped || 0)
  + Number(missingVideos.value.length || 0)
  + Number(inventoryCandidateStats.value.candidate || 0)
  + Number(duplicates.value.length || 0)
))

const isJobRunning = computed(() => collecting.value || comparing.value)
const headerSummary = computed(() => snapshotKey.value
  ? `当前快照 ${snapshotKey.value}，待处理 ${queueCount.value} 项`
  : '采集快照后统一处理库存、映射、候选和重复项')
const queueSummary = computed(() => queueCount.value ? `当前有 ${queueCount.value} 个整理项需要处理。` : '片库状态干净，暂无集中待处理项。')

const statusMetrics = computed(() => [
  { key: 'inventory', label: '演员', value: inventoryActors.value.length, hint: snapshotKey.value ? '来自最新快照' : '等待采集', urgent: false },
  { key: 'mapping', label: '待映射', value: mappingSummary.value.unmapped || 0, hint: `覆盖率 ${coverageText.value}`, urgent: Number(mappingSummary.value.unmapped || 0) > 0 },
  { key: 'inventory', label: '缺失影片', value: missingVideos.value.length, hint: '库存对比产出', urgent: missingVideos.value.length > 0 },
  { key: 'candidates', label: '库存候选', value: inventoryCandidateStats.value.candidate || 0, hint: `${inventoryCandidateStats.value.needs_magnet || 0} 个待补磁力`, urgent: Number(inventoryCandidateStats.value.candidate || 0) > 0 },
  { key: 'duplicates', label: '重复条目', value: duplicates.value.length, hint: '待人工清理', urgent: duplicates.value.length > 0 },
  { key: 'jobs', label: '最近作业', value: jobs.value.length, hint: jobs.value[0]?.status || '暂无记录', urgent: jobs.value[0]?.status === 'failed' },
])

const flowSteps = computed(() => [
  { index: '1', key: 'inventory', title: '采集快照', hint: snapshotKey.value ? '快照已就绪' : '先采集 Emby' },
  { index: '2', key: 'mapping', title: '确认映射', hint: `${mappingSummary.value.unmapped || 0} 位待处理` },
  { index: '3', key: 'inventory', title: '全量对比', hint: `${missingVideos.value.length} 个缺口` },
  { index: '4', key: 'candidates', title: '处理候选', hint: `${inventoryCandidateStats.value.candidate || 0} 个库存候选` },
])

const coverageText = computed(() => `${Math.round((Number(mappingSummary.value.coverage || 0)) * 100)}%`)

function setTab(tab) {
  activeTab.value = tab || 'queue'
  const query = { ...route.query, tab: activeTab.value }
  delete query.actor_id
  router.replace({ path: '/library-organize', query })
}

function openMetric(key) {
  setTab(key || 'queue')
}

function syncTabFromRoute() {
  const tab = String(route.query.tab || 'queue')
  activeTab.value = tabs.value.some(item => item.value === tab) ? tab : 'queue'
  if (route.query.actor_id) {
    activeTab.value = 'inventory'
    goActorDetail(route.query.actor_id, { syncRoute: false })
  }
}

async function reloadAll() {
  error.value = ''
  try {
    await Promise.all([
      loadSnapshot(),
      loadInventoryActors(),
      loadMappingSummary(),
      loadUnmappedActors(),
      loadMissingVideos(),
      loadInventoryCandidates(),
      loadDuplicates(),
      loadJobs(),
    ])
  } catch (err) {
    error.value = err?.message || '加载失败'
  } finally {
    loadingInitial.value = false
  }
}

async function loadSnapshot() {
  const resp = await api.getInventorySnapshotLatest()
  snapshotKey.value = resp.data?.snapshot_key || ''
}

async function loadInventoryActors() {
  loadingActors.value = true
  try {
    const params = { page: 1, page_size: 60 }
    if (actorSearch.value) params.search = actorSearch.value
    if (actorSort.value === 'missing_count') {
      params.sort_by = 'missing_count'
      params.sort_order = 'desc'
    } else if (actorSort.value === 'total_videos') {
      params.sort_by = 'total_videos'
      params.sort_order = 'desc'
    } else {
      params.sort_by = 'actress_name'
      params.sort_order = 'asc'
    }
    const resp = await api.listInventoryActors(params)
    inventoryActors.value = resp.data?.data || []
  } finally {
    loadingActors.value = false
  }
}

async function loadMappingSummary() {
  const resp = await api.getActorMappingSummary()
  mappingSummary.value = resp.data || {}
}

async function loadUnmappedActors() {
  loadingMappings.value = true
  try {
    const resp = await api.listUnmappedActors({ search: mappingSearch.value || undefined, limit: 80 })
    unmappedActors.value = resp.data?.data || []
  } finally {
    loadingMappings.value = false
  }
}

async function loadMissingVideos() {
  const resp = await api.listInventoryMissing()
  missingVideos.value = resp.data?.data || []
}

async function loadInventoryCandidates() {
  const params = {
    source: 'inventory',
    page: 1,
    page_size: 80,
  }
  if (candidateStatus.value) params.status = candidateStatus.value
  if (candidateSearch.value) params.q = candidateSearch.value
  if (candidateNeedsMagnet.value !== null) params.needs_magnet = candidateNeedsMagnet.value
  const resp = await api.listDownloadCandidates(params)
  inventoryCandidates.value = resp.data?.data || []
  const stats = resp.data?.stats || {}
  inventoryCandidateStats.value = {
    ...stats,
    candidate: stats.candidate_by_source?.inventory ?? stats.by_source?.inventory ?? inventoryCandidates.value.filter(item => item.status === 'candidate').length,
  }
}

async function loadDuplicates() {
  const resp = await api.getDuplicates()
  duplicates.value = resp.data?.data || []
}

async function loadJobs() {
  const resp = await api.listInventoryJobs()
  jobs.value = resp.data?.data || []
}

async function triggerCollect() {
  const confirmed = await requestConfirm({
    title: '采集 Emby 数据',
    message: '确定要采集 Emby 数据吗？',
    details: '这会拉取全量媒体库信息，库存整理会用它作为快照基准。',
    confirmText: '开始采集',
  })
  if (!confirmed) return
  collecting.value = true
  currentProgress.value = 0
  await api.triggerInventoryJob({ job_type: 'collect' })
  pollJobStatus()
}

async function triggerFullCompare() {
  if (!snapshotKey.value) {
    ElMessage.warning('请先采集 Emby 数据')
    return
  }
  const confirmed = await requestConfirm({
    title: '全量库存对比',
    message: '确认开始全量库存对比？',
    details: '会读取最近一次 Emby 快照，刷新缺失影片和库存候选。',
    confirmText: '开始对比',
  })
  if (!confirmed) return
  comparing.value = true
  currentProgress.value = 0
  await api.triggerInventoryJob({ job_type: 'full', snapshot_key: snapshotKey.value })
  pollJobStatus()
}

function pollJobStatus() {
  clearTimeout(pollTimer)
  pollTimer = setTimeout(async () => {
    try {
      await loadJobs()
      const latest = jobs.value[0]
      currentProgress.value = latest?.progress || 0
      if (latest?.status === 'running' || latest?.status === 'pending') {
        pollJobStatus()
        return
      }
      collecting.value = false
      comparing.value = false
      currentProgress.value = latest?.status === 'completed' ? 100 : 0
      await reloadAll()
    } catch {
      collecting.value = false
      comparing.value = false
      currentProgress.value = 0
    }
  }, 1500)
}

async function goActorDetail(actorId, options = {}) {
  const resp = await api.getInventoryActor(actorId)
  selectedActor.value = resp.data || null
  actorMissingVideos.value = resp.data?.missing_videos || []
  if (options.syncRoute !== false) {
    router.replace({ path: '/library-organize', query: { ...route.query, tab: 'inventory', actor_id: actorId } })
  }
}

function clearActorDetail() {
  selectedActor.value = null
  actorMissingVideos.value = []
  const query = { ...route.query, tab: 'inventory' }
  delete query.actor_id
  router.replace({ path: '/library-organize', query })
}

async function fillVideo(video) {
  await api.fillInventoryVideo(video.content_id)
  ElMessage.success('已加入库存候选')
  await Promise.all([loadInventoryCandidates(), loadMissingVideos()])
}

async function checkOneVideo() {
  if (!checkCode.value) return
  checkingVideo.value = true
  checkResult.value = null
  try {
    const resp = await api.checkLibrary(checkCode.value)
    checkResult.value = resp.data
  } finally {
    checkingVideo.value = false
  }
}

async function createManualInventoryCandidate() {
  if (!checkCode.value) return
  await api.createDownloadCandidate({
    content_id: checkCode.value,
    dvd_id: checkCode.value,
    title: checkCode.value,
    source: 'inventory',
    reason: 'library_organize_manual_check',
  })
  ElMessage.success('已加入库存候选')
  await loadInventoryCandidates()
}

async function previewAutoMatch() {
  await runAutoMatchRequest(true)
}

async function runAutoMatch() {
  const confirmed = await requestConfirm({
    title: '执行自动匹配?',
    message: '系统会自动确认高置信演员映射，并生成需要人工审核的候选。',
    details: ['影响范围：全部待映射演员', '可先使用“自动匹配预演”查看预计结果'],
    tone: 'warning',
    confirmText: '执行自动匹配',
  })
  if (!confirmed) return
  await runAutoMatchRequest(false)
}

async function runAutoMatchRequest(dryRun) {
  autoMatching.value = true
  try {
    const resp = await api.autoMatchActorMappings({ dry_run: dryRun, limit: 100000 })
    lastAutoMatch.value = resp.data || {}
    if (!dryRun) await Promise.all([loadMappingSummary(), loadUnmappedActors(), loadInventoryActors()])
  } finally {
    autoMatching.value = false
  }
}

async function generateMappingCandidates() {
  generatingCandidates.value = true
  try {
    await api.generateActorMappingCandidates({ search: mappingSearch.value || undefined, limit: 50, per_actor: 3, min_confidence: 0.55 })
    await loadUnmappedActors()
  } finally {
    generatingCandidates.value = false
  }
}

async function confirmMapping(actor, candidate) {
  await api.confirmActorMapping({
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    javinfo_actress_id: candidate.id || candidate.javinfo_actress_id,
    javinfo_actress_name: candidateName(candidate),
    confidence: candidate.confidence || 1,
    source: 'manual',
    javinfo_avatar_url: candidate.javinfo_avatar_url || candidate.image_url || candidate.avatar_url || '',
    movie_count: candidate.movie_count || 0,
    confidence_breakdown: candidate.confidence_breakdown || {},
    confidence_label: candidate.confidence_label || '',
    risk_flags: candidate.risk_flags || [],
  })
  await Promise.all([loadMappingSummary(), loadUnmappedActors(), loadInventoryActors()])
}

async function ignoreActor(actor) {
  await api.ignoreActorMapping({
    emby_actor_id: actor.emby_actor_id,
    emby_actor_name: actor.emby_actor_name,
    source: 'manual',
  })
  await Promise.all([loadMappingSummary(), loadUnmappedActors()])
}

function setCandidateStatus(status) {
  candidateStatus.value = status
  candidateNeedsMagnet.value = null
  loadInventoryCandidates()
}

function setCandidateNeedsMagnet(value) {
  candidateStatus.value = 'candidate'
  candidateNeedsMagnet.value = candidateNeedsMagnet.value === value ? null : value
  loadInventoryCandidates()
}

async function enrichCandidate(candidate) {
  mutatingCandidateId.value = candidate.id
  try {
    await api.enrichDownloadCandidateMagnet(candidate.id)
    await loadInventoryCandidates()
  } finally {
    mutatingCandidateId.value = null
  }
}

async function approveCandidate(candidate) {
  mutatingCandidateId.value = candidate.id
  try {
    await api.approveDownloadCandidate(candidate.id)
    await loadInventoryCandidates()
  } finally {
    mutatingCandidateId.value = null
  }
}

async function rejectCandidate(candidate) {
  mutatingCandidateId.value = candidate.id
  try {
    await api.rejectDownloadCandidate(candidate.id)
    await loadInventoryCandidates()
  } finally {
    mutatingCandidateId.value = null
  }
}

const duplicateItems = item => item.items?.length ? item.items : [item]

function removeDuplicateItem(embyItemId) {
  duplicates.value = duplicates.value
    .map(group => {
      const items = duplicateItems(group).filter(item => item.emby_item_id !== embyItemId)
      if (!group.items) return group.emby_item_id === embyItemId ? null : group
      if (items.length < 2) return null
      return { ...group, emby_item_id: items[0].emby_item_id, emby_name: items[0].emby_name, duplicate_count: items.length, items }
    })
    .filter(Boolean)
}

async function deleteDuplicate(item) {
  const confirmed = await requestConfirm({
    title: '删除 Emby 条目',
    message: '确定要删除 Emby 中的这个条目吗？',
    details: item.emby_name || item.content_id || '',
    confirmText: '删除',
    tone: 'danger',
  })
  if (!confirmed) return
  await api.deleteDuplicate(item.emby_item_id)
  removeDuplicateItem(item.emby_item_id)
}

async function ignoreDuplicate(item) {
  await api.ignoreDuplicate(item.emby_item_id)
  removeDuplicateItem(item.emby_item_id)
}

function candidateName(candidate) {
  return candidate.javinfo_actress_name || candidate.name_kanji || candidate.name_romaji || candidate.name_ja || candidate.name_en || candidate.name || String(candidate.id || '')
}

function candidateKey(candidate) {
  return String(candidate.id || candidate.javinfo_actress_id || candidateName(candidate))
}

function confidenceText(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

function inventoryActorName(actor) {
  return actor?.display_name || actor?.actress_name || `演员 ${actor?.actress_id || ''}`.trim()
}

function inventoryActorSubtitle(actor) {
  const rawName = actor?.actress_name || ''
  return rawName && rawName !== inventoryActorName(actor) ? rawName : ''
}

function inventoryActorAvatar(actor) {
  return actor?.avatar_url || actor?.javinfo_avatar_url || ''
}

function inventoryActorMissingText(actor) {
  const missing = Number(actor?.missing_count ?? 0)
  return missing < 0 ? '待对比' : `缺失 ${missing.toLocaleString()}`
}

function inventoryActorMeta(actor) {
  return `Emby ${Number(actor?.total_videos || 0).toLocaleString()} 部 · ${inventoryActorMissingText(actor)}`
}

function inventoryActorCardActor(actor) {
  return {
    id: actor?.actress_id,
    actress_id: actor?.actress_id,
    name: inventoryActorName(actor),
    name_kanji: inventoryActorName(actor),
    image_url: inventoryActorAvatar(actor),
  }
}

function initials(name) {
  return String(name || '?').slice(0, 1).toUpperCase()
}

function candidateStatusLabel(status) {
  const labels = { candidate: '待确认', sent: '已下发', failed: '失败', rejected: '已拒绝', approved: '已批准' }
  return labels[status] || status || '未知'
}

function jobTypeLabel(type) {
  const labels = { collect: '采集 Emby', full: '全量对比', actor: '演员对比' }
  return labels[type] || type
}

watch(() => route.query, syncTabFromRoute, { deep: true })

onMounted(async () => {
  syncTabFromRoute()
  await reloadAll()
})
</script>

<style scoped>
.library-organize-page {
  color: var(--text-primary);
  padding-top: clamp(18px, 3vw, 34px);
}

.organize-header {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  min-height: 148px;
  margin-bottom: 14px;
  padding: clamp(22px, 3vw, 34px);
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 8%, rgba(255,255,255,0.98), transparent 32%),
    radial-gradient(circle at 82% 2%, rgba(180, 192, 211, 0.22), transparent 31%),
    linear-gradient(145deg, rgba(255,255,255,0.82), rgba(246,246,248,0.58));
}

.organize-header::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.52;
  background-image:
    linear-gradient(rgba(29,29,31,0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(29,29,31,0.024) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(90deg, rgba(0,0,0,0.78), transparent 74%);
}

.organize-header__copy,
.header-actions {
  position: relative;
  z-index: 1;
}

.organize-header h1 {
  margin: 0;
  font-size: clamp(34px, 5vw, 56px);
  line-height: 0.96;
  font-weight: 700;
  letter-spacing: 0;
}

.organize-header p,
.panel-head p,
.setup-banner span {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.35;
}

.header-actions,
.panel-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 9px;
  flex-wrap: wrap;
}

.btn-sm {
  min-height: 36px;
  padding: 7px 12px;
  font-size: 12px;
}

.job-progress {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  background: var(--glass-active-material);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  box-shadow: var(--glass-active-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.organize-status {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 1px;
  margin-bottom: 14px;
  padding: 1px;
  overflow: hidden;
  border-color: var(--glass-edge);
  background: var(--material-glass-sheet);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.status-cell {
  min-width: 0;
  min-height: 70px;
  padding: 12px;
  border: 0;
  border-radius: calc(var(--radius-card) - 7px);
  background: var(--material-glass-control);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--glass-inner-shadow);
  transition: background var(--motion-fast), color var(--motion-fast), transform var(--motion-fast), box-shadow var(--motion-fast);
}

.status-cell:hover {
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.status-cell:active {
  transform: scale(0.985);
}

.status-cell.urgent .status-value {
  color: #b45309;
}

.status-value {
  display: block;
  margin-bottom: 5px;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}

.status-label {
  display: block;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-cell small {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: var(--type-micro);
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.setup-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-card);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.72), rgba(255,255,255,0.44)),
    var(--surface-card);
}

.setup-banner strong,
.setup-banner span {
  display: block;
}

.organize-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
  padding: 6px;
  overflow-x: auto;
  border-radius: var(--radius-card);
  background: var(--material-glass-sheet);
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 0 13px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: var(--type-control);
  font-weight: 650;
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--motion-fast), color var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}

.tab-btn:hover {
  border-color: var(--glass-control-border);
  background: var(--material-glass-control-hover);
  color: var(--text-primary);
}

.tab-btn.active {
  border-color: var(--glass-active-border);
  background: var(--glass-active-material);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.tab-btn:active {
  transform: scale(0.985);
}

.tab-btn small {
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.organize-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.85fr);
  gap: 14px;
  align-items: start;
}

.workbench-panel,
.loading-panel,
.empty-panel {
  min-width: 0;
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-card);
  background: var(--material-glass-elevated);
  box-shadow: var(--glass-surface-shadow);
  backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-surface)) saturate(var(--glass-saturate-surface));
}

.workbench-panel {
  padding: 14px;
}

.loading-panel,
.empty-panel {
  padding: 38px 16px;
  color: var(--text-secondary);
  text-align: center;
}

.empty-panel h2 {
  margin: 0 0 8px;
  color: var(--text-primary);
  font-size: var(--type-section-title);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-head h2 {
  margin: 0;
  font-size: var(--type-card-title);
  line-height: 1.2;
  font-weight: 650;
  letter-spacing: 0;
}

.side-stack {
  display: grid;
  gap: 14px;
}

.priority-list,
.flow-steps,
.mapping-list,
.duplicate-list,
.job-list,
.duplicate-entries,
.check-items {
  display: grid;
  gap: 9px;
}

.priority-row,
.flow-steps button,
.mapping-item,
.duplicate-group,
.job-row,
.duplicate-entry,
.check-item,
.inventory-candidate,
.missing-video {
  min-width: 0;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--material-glass-control);
  box-shadow: var(--glass-inner-shadow);
  transition:
    background var(--motion-fast),
    border-color var(--motion-fast),
    box-shadow var(--motion-fast),
    transform var(--motion-fast);
}

.priority-row,
.flow-steps button,
.job-row,
.duplicate-entry,
.check-item {
  display: grid;
  align-items: center;
}

.priority-row {
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  width: 100%;
  min-height: 72px;
  padding: 12px;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}

.priority-row:hover,
.flow-steps button:hover {
  background: var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.priority-row:active,
.flow-steps button:active {
  transform: scale(0.992);
}

.priority-row strong,
.priority-row small,
.flow-steps strong,
.flow-steps small,
.inventory-candidate strong,
.inventory-candidate span,
.inventory-candidate small,
.missing-video strong,
.missing-video span,
.missing-video small {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.priority-row small,
.flow-steps small,
.mapping-copy small,
.duplicate-group small,
.job-row small,
.check-item small,
.inventory-candidate small,
.missing-video small,
.muted {
  color: var(--text-secondary);
  font-size: 12px;
}

.priority-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--glass-active-border);
  background: var(--glass-active-material);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 700;
  box-shadow: var(--glass-active-shadow);
}

.priority-mark.warning {
  border: 1px solid var(--badge-warning-border);
  background: var(--badge-warning-bg);
}

.priority-mark.danger {
  border: 1px solid var(--badge-error-border);
  background: var(--badge-error-bg);
}

.flow-steps button {
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 10px;
  padding: 10px;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}

.flow-steps span {
  grid-row: 1 / span 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  background: var(--glass-active-material);
  font-family: var(--font-mono);
  box-shadow: var(--glass-inner-shadow);
}

.mini-check-form,
.organize-filters,
.check-form {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.mini-check-form input,
.organize-filters input,
.check-form input {
  flex: 1;
  min-width: 180px;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--material-glass-control);
  color: var(--text-primary);
  font: inherit;
  outline: none;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast);
}

.mini-check-form input:focus,
.organize-filters input:focus,
.check-form input:focus {
  border-color: var(--accent);
  background: var(--glass-active-material);
  box-shadow: var(--glass-control-shadow), 0 0 0 4px rgba(var(--accent-rgb), 0.12);
}

.mini-check-result,
.check-result {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--badge-warning-border);
  border-radius: var(--radius-md);
  background: var(--badge-warning-bg);
  color: var(--text-primary);
}

.mini-check-result.exists,
.check-result.exists {
  border-color: var(--badge-success-border);
  background: var(--badge-success-bg);
}

.inline-link {
  border: 0;
  background: transparent;
  color: var(--link-text);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: var(--link-underline);
  text-underline-offset: 3px;
}

.actor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 16px;
}

.actor-avatar {
  width: 72px;
  height: 92px;
  overflow: hidden;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-sm);
  background:
    radial-gradient(circle at 45% 18%, rgba(255,255,255,0.84), transparent 26%),
    linear-gradient(145deg, rgba(242,242,247,0.88), rgba(214,216,224,0.82));
  box-shadow: var(--glass-inner-shadow);
}

.actor-avatar.small {
  width: 48px;
  height: 62px;
}

.actor-avatar img,
.actor-avatar span {
  width: 100%;
  height: 100%;
}

.actor-avatar img {
  display: block;
  object-fit: cover;
}

.actor-avatar span {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-weight: 700;
}

.actor-detail-panel {
  display: grid;
  gap: 12px;
}

.actor-detail-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--material-glass-control);
  box-shadow: var(--glass-inner-shadow);
}

.actor-detail-head strong,
.actor-detail-head span {
  display: block;
}

.actor-detail-head span {
  color: var(--text-secondary);
  font-size: 12px;
}

.missing-grid,
.candidate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
}

.missing-video,
.inventory-candidate {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 10px;
  padding: 10px;
}

.missing-video .btn,
.inventory-candidate .candidate-actions {
  grid-column: 1 / -1;
}

.missing-video img,
.inventory-candidate img,
.poster-fallback {
  width: 58px;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-xs);
  object-fit: cover;
  background:
    radial-gradient(circle at 45% 18%, rgba(255,255,255,0.84), transparent 26%),
    linear-gradient(145deg, rgba(242,242,247,0.88), rgba(214,216,224,0.82));
  box-shadow: var(--glass-inner-shadow);
}

.poster-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
}

.empty-inline {
  padding: 28px 12px;
  color: var(--text-secondary);
  text-align: center;
}

.mapping-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
  padding: 10px;
}

.mapping-copy {
  min-width: 0;
}

.mapping-copy strong,
.mapping-copy small {
  display: block;
}

.candidate-pills {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  overflow-x: auto;
}

.candidate-pills button,
.chip,
.status-pill {
  min-height: 32px;
  padding: 5px 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--material-glass-control);
  color: var(--text-primary);
  cursor: pointer;
  white-space: nowrap;
  box-shadow: var(--glass-inner-shadow);
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}

.candidate-pills button:hover,
.chip:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}

.chip.active {
  border-color: var(--glass-active-border);
  background: var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}

.auto-match-panel {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-md);
  background: var(--material-glass-control);
  box-shadow: var(--glass-inner-shadow);
}

.auto-match-panel span {
  color: var(--text-secondary);
  font-size: 12px;
}

.candidate-actions,
.duplicate-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.duplicate-group {
  display: grid;
  gap: 8px;
  padding: 12px;
}

.duplicate-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.duplicate-head span {
  color: var(--text-secondary);
  font-size: 12px;
}

.duplicate-entry {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 10px;
}

.duplicate-entry strong,
.duplicate-entry small {
  display: block;
  min-width: 0;
  overflow-wrap: anywhere;
}

.btn.danger {
  border-color: var(--badge-error-border);
  background: var(--badge-error-bg);
  color: var(--text-primary);
}

.job-row {
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
  padding: 10px;
}

.check-form {
  max-width: 760px;
}

.check-result {
  max-width: 760px;
}

:global(:root[data-theme="dark"] .organize-header) {
  background:
    radial-gradient(circle at 16% 0%, rgba(255,255,255,0.18), transparent 34%),
    radial-gradient(circle at 84% 4%, rgba(255,255,255,0.10), transparent 28%),
    linear-gradient(145deg, rgba(255,255,255,0.115), rgba(14,15,18,0.72) 48%, rgba(255,255,255,0.070));
}

:global(:root[data-theme="dark"] .organize-header::before) {
  opacity: 0.28;
  background-image:
    linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
}

:global(:root[data-theme="dark"] .organize-status),
:global(:root[data-theme="dark"] .organize-tabs),
:global(:root[data-theme="dark"] .workbench-panel),
:global(:root[data-theme="dark"] .loading-panel),
:global(:root[data-theme="dark"] .empty-panel) {
  border-color: rgba(255,255,255,0.16);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.155), rgba(18,19,21,0.54) 50%, rgba(255,255,255,0.085));
  box-shadow: var(--glass-surface-shadow);
}

:global(:root[data-theme="dark"] .status-cell),
:global(:root[data-theme="dark"] .priority-row),
:global(:root[data-theme="dark"] .flow-steps button),
:global(:root[data-theme="dark"] .mapping-item),
:global(:root[data-theme="dark"] .duplicate-group),
:global(:root[data-theme="dark"] .job-row),
:global(:root[data-theme="dark"] .duplicate-entry),
:global(:root[data-theme="dark"] .check-item),
:global(:root[data-theme="dark"] .inventory-candidate),
:global(:root[data-theme="dark"] .missing-video),
:global(:root[data-theme="dark"] .actor-detail-head),
:global(:root[data-theme="dark"] .auto-match-panel),
:global(:root[data-theme="dark"] .candidate-pills button),
:global(:root[data-theme="dark"] .chip),
:global(:root[data-theme="dark"] .status-pill),
:global(:root[data-theme="dark"] .mini-check-form input),
:global(:root[data-theme="dark"] .organize-filters input),
:global(:root[data-theme="dark"] .check-form input) {
  border-color: rgba(255,255,255,0.14);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.135), rgba(18,19,21,0.46) 50%, rgba(255,255,255,0.075));
}

:global(:root[data-theme="dark"] .status-cell:hover),
:global(:root[data-theme="dark"] .priority-row:hover),
:global(:root[data-theme="dark"] .flow-steps button:hover),
:global(:root[data-theme="dark"] .candidate-pills button:hover),
:global(:root[data-theme="dark"] .chip:hover) {
  border-color: rgba(255,255,255,0.24);
  background:
    linear-gradient(145deg, rgba(255,255,255,0.18), rgba(24,25,28,0.54) 50%, rgba(255,255,255,0.10));
}

:global(:root[data-theme="dark"] .mini-check-form input:focus),
:global(:root[data-theme="dark"] .organize-filters input:focus),
:global(:root[data-theme="dark"] .check-form input:focus) {
  border-color: rgba(255,255,255,0.30);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 4px rgba(255,255,255,0.08);
}

@media (max-width: 980px) {
  .organize-header,
  .setup-banner,
  .panel-head,
  .auto-match-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .organize-status {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .organize-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .organize-status {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .priority-row,
  .mapping-item,
  .actor-detail-head,
  .duplicate-entry,
  .job-row {
    grid-template-columns: 1fr;
  }

  .priority-mark {
    width: 100%;
  }

  .mini-check-form,
  .organize-filters,
  .check-form,
  .header-actions,
  .panel-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .mini-check-form input,
  .organize-filters input,
  .check-form input,
  .header-actions .btn,
  .panel-actions .btn {
    width: 100%;
  }
}
</style>
