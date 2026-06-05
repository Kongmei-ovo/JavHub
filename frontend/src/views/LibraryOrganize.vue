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
              <span class="priority-mark">{{ missingTotal }}</span>
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
              <span class="priority-mark danger">{{ duplicateTotal }}</span>
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
              <img v-if="video.jacket_thumb_url" :src="video.jacket_thumb_url" :alt="video.title || video.content_id" loading="lazy" decoding="async" />
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
              <img v-if="actor.avatar_url" :src="actor.avatar_url" :alt="actor.emby_actor_name" loading="lazy" decoding="async" />
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
            <img v-if="candidate.jacket_thumb_url" :src="candidate.jacket_thumb_url" :alt="candidate.title || candidate.content_id" loading="lazy" decoding="async" />
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
          <button class="btn btn-ghost btn-sm" type="button" :disabled="loadingDuplicates" @click="loadDuplicates">
            {{ loadingDuplicates ? '扫描中...' : '重新扫描' }}
          </button>
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
        <div v-else-if="loadingDuplicates" class="empty-inline">扫描重复条目中...</div>
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
import { candidateKey, candidateName, confidenceText, initials } from '../utils/inventoryPresentation.js'

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
const AUTO_MATCH_BATCH_LIMIT = 500
const lastAutoMatch = ref(null)
const missingVideos = ref([])
const missingTotal = ref(0)
const inventoryCandidates = ref([])
const inventoryCandidateStats = ref({})
const candidateSearch = ref('')
const candidateStatus = ref('candidate')
const candidateNeedsMagnet = ref(null)
const mutatingCandidateId = ref(null)
const duplicates = ref([])
const duplicateTotal = ref(0)
const duplicatesDeferred = ref(false)
const loadingDuplicates = ref(false)
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
  { value: 'inventory', label: '库存对比', count: missingTotal.value },
  { value: 'check', label: '单片检测', count: null },
  { value: 'mapping', label: '演员映射', count: mappingSummary.value.unmapped || 0 },
  { value: 'candidates', label: '库存候选', count: inventoryCandidateStats.value.candidate || 0 },
  { value: 'duplicates', label: '重复清理', count: duplicateTotal.value },
  { value: 'jobs', label: '作业历史', count: jobs.value.length },
])

const queueCount = computed(() => (
  Number(mappingSummary.value.unmapped || 0)
  + Number(missingTotal.value || 0)
  + Number(inventoryCandidateStats.value.candidate || 0)
  + Number(duplicateTotal.value || 0)
))

const isJobRunning = computed(() => collecting.value || comparing.value)
const headerSummary = computed(() => snapshotKey.value
  ? `当前快照 ${snapshotKey.value}，待处理 ${queueCount.value} 项`
  : '采集快照后统一处理库存、映射、候选和重复项')
const queueSummary = computed(() => queueCount.value ? `当前有 ${queueCount.value} 个整理项需要处理。` : '片库状态干净，暂无集中待处理项。')

const statusMetrics = computed(() => [
  { key: 'inventory', label: '演员', value: inventoryActors.value.length, hint: snapshotKey.value ? '来自最新快照' : '等待采集', urgent: false },
  { key: 'mapping', label: '待映射', value: mappingSummary.value.unmapped || 0, hint: `覆盖率 ${coverageText.value}`, urgent: Number(mappingSummary.value.unmapped || 0) > 0 },
  { key: 'inventory', label: '缺失影片', value: missingTotal.value, hint: '库存对比产出', urgent: missingTotal.value > 0 },
  { key: 'candidates', label: '库存候选', value: inventoryCandidateStats.value.candidate || 0, hint: `${inventoryCandidateStats.value.needs_magnet || 0} 个待补磁力`, urgent: Number(inventoryCandidateStats.value.candidate || 0) > 0 },
  { key: 'duplicates', label: '重复条目', value: duplicateTotal.value, hint: '待人工清理', urgent: duplicateTotal.value > 0 },
  { key: 'jobs', label: '最近作业', value: jobs.value.length, hint: jobs.value[0]?.status || '暂无记录', urgent: jobs.value[0]?.status === 'failed' },
])

const flowSteps = computed(() => [
  { index: '1', key: 'inventory', title: '采集快照', hint: snapshotKey.value ? '快照已就绪' : '先采集 Emby' },
  { index: '2', key: 'mapping', title: '确认映射', hint: `${mappingSummary.value.unmapped || 0} 位待处理` },
  { index: '3', key: 'inventory', title: '全量对比', hint: `${missingTotal.value} 个缺口` },
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
    await loadOverview()
  } catch (err) {
    error.value = err?.message || '加载失败'
  } finally {
    loadingInitial.value = false
  }
}

function overviewParams() {
  const params = {
    actor_sort: actorSort.value,
    candidate_status: candidateStatus.value || undefined,
  }
  if (actorSearch.value) params.actor_search = actorSearch.value
  if (mappingSearch.value) params.mapping_search = mappingSearch.value
  if (candidateSearch.value) params.candidate_search = candidateSearch.value
  if (candidateNeedsMagnet.value !== null) params.candidate_needs_magnet = candidateNeedsMagnet.value
  return params
}

function applyOverview(data) {
  snapshotKey.value = data?.snapshot?.snapshot_key || ''
  inventoryActors.value = data?.actors?.data || []
  mappingSummary.value = data?.mapping?.summary || {}
  unmappedActors.value = data?.mapping?.unmapped?.data || []
  missingVideos.value = data?.missing?.data || []
  missingTotal.value = Number(data?.missing?.total || missingVideos.value.length || 0)
  inventoryCandidates.value = data?.candidates?.data || []
  const stats = data?.candidates?.stats || {}
  inventoryCandidateStats.value = {
    ...stats,
    candidate: stats.candidate_by_source?.inventory ?? stats.by_source?.inventory ?? inventoryCandidates.value.filter(item => item.status === 'candidate').length,
  }
  duplicates.value = data?.duplicates?.data || []
  duplicatesDeferred.value = Boolean(data?.duplicates?.deferred)
  duplicateTotal.value = Number(data?.duplicates?.total || duplicates.value.length || 0)
  jobs.value = data?.jobs?.data || []
  ensureDuplicateTabLoaded()
}

async function loadOverview() {
  loadingActors.value = true
  loadingMappings.value = true
  try {
    const resp = await api.getLibraryOrganizeOverview(overviewParams())
    applyOverview(resp.data || {})
  } finally {
    loadingActors.value = false
    loadingMappings.value = false
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
  const resp = await api.listInventoryMissing({ page: 1, page_size: 80 })
  missingVideos.value = resp.data?.data || []
  missingTotal.value = Number(resp.data?.total || missingVideos.value.length || 0)
}

async function loadInventoryCandidates() {
  const params = {
    source: 'inventory',
    page: 1,
    page_size: 80,
    include_stats: false,
  }
  if (candidateStatus.value) params.status = candidateStatus.value
  if (candidateSearch.value) params.q = candidateSearch.value
  if (candidateNeedsMagnet.value !== null) params.needs_magnet = candidateNeedsMagnet.value
  const resp = await api.listDownloadCandidates(params)
  inventoryCandidates.value = resp.data?.data || []
  const summaryResp = await api.getDownloadCandidateSummary({ status: 'candidate', source: 'inventory' })
  const stats = summaryResp.data || {}
  inventoryCandidateStats.value = {
    ...stats,
    candidate: stats.candidate ?? inventoryCandidates.value.filter(item => item.status === 'candidate').length,
  }
}

async function loadDuplicates() {
  if (loadingDuplicates.value) return
  loadingDuplicates.value = true
  try {
    const resp = await api.getDuplicates()
    duplicates.value = resp.data?.data || []
    duplicateTotal.value = Number(resp.data?.total || duplicates.value.length || 0)
    duplicatesDeferred.value = false
  } finally {
    loadingDuplicates.value = false
  }
}

function ensureDuplicateTabLoaded() {
  if (activeTab.value === 'duplicates' && duplicatesDeferred.value && !loadingDuplicates.value) {
    loadDuplicates().catch(err => {
      error.value = err?.message || '重复扫描加载失败'
    })
  }
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
  missingTotal.value = Math.max(0, missingTotal.value - 1)
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
    details: [`影响范围：本批最多 ${AUTO_MATCH_BATCH_LIMIT} 个待映射演员`, '可先使用“自动匹配预演”查看预计结果'],
    tone: 'warning',
    confirmText: '执行自动匹配',
  })
  if (!confirmed) return
  await runAutoMatchRequest(false)
}

async function runAutoMatchRequest(dryRun) {
  autoMatching.value = true
  try {
    const resp = await api.autoMatchActorMappings({ dry_run: dryRun, limit: AUTO_MATCH_BATCH_LIMIT })
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
  let removedGroup = false
  duplicates.value = duplicates.value
    .map(group => {
      const items = duplicateItems(group).filter(item => item.emby_item_id !== embyItemId)
      if (!group.items) {
        if (group.emby_item_id === embyItemId) {
          removedGroup = true
          return null
        }
        return group
      }
      if (items.length < 2) {
        removedGroup = true
        return null
      }
      return { ...group, emby_item_id: items[0].emby_item_id, emby_name: items[0].emby_name, duplicate_count: items.length, items }
    })
    .filter(Boolean)
  if (removedGroup) duplicateTotal.value = Math.max(0, duplicateTotal.value - 1)
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

function candidateStatusLabel(status) {
  const labels = { candidate: '待确认', sent: '已下发', failed: '失败', rejected: '已拒绝', approved: '已批准' }
  return labels[status] || status || '未知'
}

function jobTypeLabel(type) {
  const labels = { collect: '采集 Emby', full: '全量对比', actor: '演员对比' }
  return labels[type] || type
}

watch(() => route.query, syncTabFromRoute, { deep: true })
watch(activeTab, ensureDuplicateTabLoaded)

onMounted(async () => {
  syncTabFromRoute()
  await reloadAll()
})
</script>

<style scoped src="../features/library/libraryOrganize.css"></style>
