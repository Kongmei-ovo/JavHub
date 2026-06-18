<template>
  <section class="workspace-panel actors-tab">
    <div class="panel-header">
      <div>
        <h2>待补全演员</h2>
        <p class="panel-subtitle">订阅演员的补全总览 · 点演员进入其待补全作品</p>
      </div>
      <div class="actors-toolbar">
        <label class="actors-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <circle cx="11" cy="11" r="7"></circle>
            <path d="M16.5 16.5 21 21"></path>
          </svg>
          <input v-model="keyword" placeholder="筛选订阅演员" aria-label="筛选订阅演员" />
        </label>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="loading" @click="reload">
          {{ loading ? '加载中…' : '刷新' }}
        </button>
      </div>
    </div>

    <AppleSkeleton
      v-if="loading && !actors.length"
      class="panel-state"
      variant="gallery"
      :items="6"
      label="订阅演员加载中"
    />

    <template v-else>
      <div v-if="filteredActors.length" class="actor-choice-grid">
        <ActorPortraitCard
          v-for="actor in filteredActors"
          :key="actor.id"
          :actor="actor"
          :name="cardName(actor)"
          :subtitle="cardSubtitle(actor)"
          :avatar-url="cardAvatar(actor)"
          :meta="cardMeta(actor)"
          :badges="cardBadges(actor)"
          density="compact"
          action-label="进入补全"
          @open="$emit('select', actor)"
        />
      </div>

      <AppleEmptyState
        v-else
        class="panel-state empty-inline"
        :title="emptyState.title"
        :description="emptyState.description"
        :next-step="emptyState.nextStep"
        :action-label="emptyState.actionLabel"
        :secondary-action-label="emptyState.secondaryActionLabel"
        density="compact"
        @action="emptyState.onAction"
        @secondary-action="emptyState.onSecondary"
      />
    </template>
  </section>
</template>

<script>
import api from '../../api'
import { actressImgUrl } from '../../utils/imageUrl.js'
import { displayName } from '../../utils/displayLang.js'
import ActorPortraitCard from '../../components/ActorPortraitCard.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

const STATUS_LABELS = { queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', idle: '待开始' }

export default {
  name: 'ActorsTab',
  components: { ActorPortraitCard, AppleSkeleton, AppleEmptyState },
  props: {
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['select', 'summary-change'],
  data() {
    return {
      keyword: '',
      loading: true,
      loadFailed: false,
      actors: [],
      _loadToken: 0,
    }
  },
  computed: {
    filteredActors() {
      const kw = this.keyword.trim().toLowerCase()
      if (!kw) return this.actors
      return this.actors.filter(actor => {
        const hay = [actor.name, actor.name_kanji, actor.name_romaji, actor.name_kanji_translated, String(actor.id)]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        return hay.includes(kw)
      })
    },
    emptyState() {
      if (this.loadFailed) {
        return {
          title: '订阅演员加载失败',
          description: '补全接口暂时无法读取订阅演员。',
          nextStep: '稍后重试，或确认 JavInfoApi 来源是否在线。',
          actionLabel: '重试',
          secondaryActionLabel: '',
          onAction: () => this.reload(),
          onSecondary: () => {},
        }
      }
      if (this.keyword.trim() && this.actors.length) {
        return {
          title: '没有匹配演员',
          description: '当前关键词没有匹配到订阅演员。',
          nextStep: '换一个名字或清除筛选回到全部订阅演员。',
          actionLabel: '清除筛选',
          secondaryActionLabel: '',
          onAction: () => { this.keyword = '' },
          onSecondary: () => {},
        }
      }
      return {
        title: '还没有订阅演员',
        description: '补全工作台围绕订阅演员运转，先订阅演员才能开始补全。',
        nextStep: '去订阅页订阅演员，回来后即可逐位补全其作品字段。',
        actionLabel: '去订阅演员',
        secondaryActionLabel: '刷新',
        onAction: () => this.$router.push('/subscription'),
        onSecondary: () => this.reload(),
      }
    },
  },
  watch: {
    refreshNonce() {
      this.load()
    },
  },
  mounted() {
    this.load()
  },
  methods: {
    statusLabel(status) {
      return STATUS_LABELS[status] || status || '待开始'
    },
    cardName(actor) {
      return actor.name_kanji_translated
        || actor.name_romaji_translated
        || displayName(actor, 'name_kanji', 'name_romaji')
        || actor.name_kanji
        || actor.name_romaji
        || actor.name
        || '未知演员'
    },
    cardSubtitle(actor) {
      const name = this.cardName(actor)
      const original = actor.name_kanji || actor.name_romaji || ''
      return original && original !== name ? original : ''
    },
    cardAvatar(actor) {
      return actor.image_url ? (actressImgUrl(actor.image_url) || '') : ''
    },
    cardMeta(actor) {
      const parts = []
      if (Number.isInteger(actor._pending)) parts.push(`${actor._pending} 部待补`)
      else if (actor._pendingLoading) parts.push('待补统计中…')
      if (Number.isInteger(actor.movie_count)) parts.push(`共 ${actor.movie_count} 部`)
      return parts.join(' · ')
    },
    cardBadges(actor) {
      const badges = []
      if (actor._job?.status) {
        const status = actor._job.status
        const tone = status === 'failed'
          ? 'warning'
          : (status === 'succeeded' ? 'success' : 'neutral')
        badges.push({ label: this.statusLabel(status), tone })
      }
      badges.push({ label: '已订阅', tone: 'success' })
      return badges
    },
    patchActor(id, patch) {
      const index = this.actors.findIndex(actor => Number(actor.id) === Number(id))
      if (index >= 0) this.actors[index] = { ...this.actors[index], ...patch }
    },
    async pool(items, size, worker) {
      const queue = [...items]
      const runners = Array.from({ length: Math.min(size, queue.length) }, async () => {
        while (queue.length) {
          const item = queue.shift()
          await worker(item)
        }
      })
      await Promise.all(runners)
    },
    reload() {
      this.load()
    },
    async load() {
      const token = ++this._loadToken
      this.loading = true
      this.loadFailed = false
      let subscriptions = []
      try {
        const resp = await api.getSubscriptions()
        subscriptions = resp.data?.data || resp.data || []
      } catch (e) {
        if (token !== this._loadToken) return
        console.error('Load supplement actors failed:', e)
        this.loadFailed = true
        this.actors = []
        this.loading = false
        this.$emit('summary-change', { actorsTotal: 0 })
        return
      }
      if (token !== this._loadToken) return
      const actressSubs = subscriptions.filter(sub => {
        const scope = String(sub.scope || 'actress').toLowerCase()
        return sub.enabled && scope === 'actress' && (sub.actress_id || sub.target_id)
      })
      // Render base cards immediately from the subscription row, then enrich.
      this.actors = actressSubs.map(sub => ({
        id: sub.actress_id || sub.target_id,
        name: sub.actress_name || sub.target_label || '',
        _subscribed: true,
        _pending: null,
        _pendingLoading: false,
        _job: null,
      }))
      this.loading = false
      this.$emit('summary-change', { actorsTotal: this.actors.length })
      if (!this.actors.length) return
      // Stage 2-4 run independently; cards fill in as data arrives.
      this.enrichActors(token)
      this.loadJobStatuses(token)
      this.loadPendingCounts(token)
    },
    async enrichActors(token) {
      await this.pool(this.actors.map(actor => actor.id), 6, async (id) => {
        if (token !== this._loadToken) return
        try {
          const resp = await api.getActress(id)
          const info = resp.data || resp
          if (token !== this._loadToken) return
          this.patchActor(id, {
            name_kanji: info.name_kanji,
            name_romaji: info.name_romaji,
            name_kana: info.name_kana,
            name_kanji_translated: info.name_kanji_translated,
            name_romaji_translated: info.name_romaji_translated,
            image_url: info.image_url,
            movie_count: info.movie_count,
          })
        } catch (e) {
          /* keep the subscription-name fallback */
        }
      })
    },
    async loadJobStatuses(token) {
      try {
        const resp = await api.listSupplementJobs({ page: 1, page_size: 50 })
        if (token !== this._loadToken) return
        const jobs = resp.data?.data || []
        const latest = new Map()
        for (const job of jobs) {
          if (job.job_type !== 'actress_filmography' || !job.local_actress_id) continue
          const key = Number(job.local_actress_id)
          if (!latest.has(key)) latest.set(key, job) // jobs are ordered newest-first
        }
        for (const actor of this.actors) {
          const job = latest.get(Number(actor.id))
          if (job) this.patchActor(actor.id, { _job: job })
        }
      } catch (e) {
        /* status badges are best-effort */
      }
    },
    async loadPendingCounts(token) {
      await this.pool(this.actors.map(actor => actor.id), 4, async (id) => {
        if (token !== this._loadToken) return
        this.patchActor(id, { _pendingLoading: true })
        try {
          const resp = await api.listSupplementMovies({ actress_id: id, matched: false, page: 1, page_size: 1 })
          if (token !== this._loadToken) return
          const total = Number(resp.data?.total_count)
          this.patchActor(id, { _pending: Number.isFinite(total) ? total : null, _pendingLoading: false })
        } catch (e) {
          this.patchActor(id, { _pending: null, _pendingLoading: false })
        }
      })
    },
  },
}
</script>

<style scoped src="./supplementPanel.css"></style>
<style scoped>
.actors-tab {
  display: grid;
  gap: 16px;
}

.actors-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.actors-search {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 16px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.actors-search:focus-within {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}

.actors-search svg {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.actors-search input {
  width: 168px;
  max-width: 100%;
  min-width: 0;
  min-height: 36px;
  padding: 0;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: none;
  font-size: var(--type-control);
}

.actor-choice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
}

.panel-state {
  margin-top: 4px;
}

.empty-inline {
  padding: 32px 20px;
}

@media (max-width: 860px) {
  .actors-toolbar {
    width: 100%;
  }

  .actors-search {
    flex: 1;
  }

  .actors-search input {
    width: 100%;
  }

  .actor-choice-grid {
    grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
  }
}
</style>
