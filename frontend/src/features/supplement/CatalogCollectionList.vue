<template>
  <section class="collection-list">
    <div class="collection-head">
      <div class="ch-id">
        <span class="ch-meter">收藏 <b>{{ ownedCount }}</b> / {{ totalCount }} 部</span>
        <div class="ch-bar"><i :style="{ width: ownedPct }"></i></div>
      </div>
      <button class="btn btn-primary" type="button" :disabled="recomputing" @click="$emit('recompute')">
        <span v-if="recomputing" class="spin-ring" aria-hidden="true"></span>
        {{ recomputing ? '补全中…' : '重新拉片单' }}
      </button>
    </div>

    <AppleSkeleton v-if="loading && !yearGroups.length" class="panel-state" variant="list" :items="8" label="影片目录加载中" />

    <AppleEmptyState
      v-else-if="!yearGroups.length"
      class="panel-state"
      title="还没有作品目录"
      description="这位演员的片单还没有结果。"
      next-step="点「重新拉片单」拉取她的完整作品集。"
      action-label="重新拉片单"
      density="compact"
      @action="$emit('recompute')"
    />

    <template v-else>
      <div v-for="group in yearGroups" :key="group.year" class="year-group">
        <div class="year-header">
          <span class="year-label">{{ group.year }}</span>
          <span class="year-count">{{ group.films.length }} 部</span>
        </div>
        <div class="movie-list">
          <div class="movie-list-head">
            <span class="ml-col ml-code">番号</span>
            <span class="ml-col ml-title">片名</span>
            <span class="ml-col ml-date">出演时间</span>
            <span class="ml-col ml-origin">来源</span>
            <span class="ml-col ml-owned">115</span>
          </div>
          <div v-for="film in group.films" :key="film.canonical_number" class="movie-list-row">
            <span class="ml-col ml-code">{{ film.display_code || film.canonical_number }}</span>
            <span class="ml-col ml-title">{{ film.title || '—' }}</span>
            <span class="ml-col ml-date">{{ film.release_date || '—' }}</span>
            <span class="ml-col ml-origin">{{ film.origin === 'supplement' ? '私拍' : '正片' }}</span>
            <span class="ml-col ml-owned">
              <span class="owned-badge" :class="isOwned(film) ? 'is-owned' : 'not-owned'">{{ isOwned(film) ? '已入库' : '未入库' }}</span>
            </span>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script>
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

export default {
  name: 'CatalogCollectionList',
  components: { AppleSkeleton, AppleEmptyState },
  props: {
    yearGroups: { type: Array, default: () => [] },
    ownedCount: { type: Number, default: 0 },
    totalCount: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    recomputing: { type: Boolean, default: false },
  },
  emits: ['recompute'],
  computed: {
    ownedPct() {
      if (!this.totalCount) return '0%'
      return `${Math.min(100, Math.round((this.ownedCount / this.totalCount) * 100))}%`
    },
  },
  methods: {
    isOwned(film) { return film.funnel_stage === 'complete' || film.status === 'owned' || film.stage === 'complete' },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped>
.collection-list { display: grid; gap: var(--space-4); }
.collection-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; }
.ch-id { display: grid; gap: 6px; min-width: 220px; }
.ch-meter { font-size: var(--type-caption); color: var(--text-secondary); }
.ch-meter b { color: var(--text-primary); }
.ch-bar { height: 6px; border-radius: 3px; background: var(--hairline-strong); overflow: hidden; }
.ch-bar i { display: block; height: 100%; background: var(--accent); }
.movie-list { display: grid; gap: 2px; background: var(--card); border: 1px solid var(--hairline); border-radius: var(--radius-card); padding: 6px 8px; }
.movie-list-head, .movie-list-row { display: grid; grid-template-columns: 130px 1fr 110px 64px 96px; gap: 12px; align-items: center; padding: 8px 10px; }
.movie-list-head { font-size: var(--type-caption-1); color: var(--text-muted); border-bottom: 1px solid var(--hairline); }
.movie-list-row { border-radius: 8px; }
.movie-list-row:hover { background: var(--card-hover); }
.ml-col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--type-callout); }
.ml-title { color: var(--text-secondary); }
.ml-origin { color: var(--text-muted); }
.owned-badge { font-size: var(--type-caption-1); padding: 2px 8px; border-radius: 999px; }
.owned-badge.is-owned { background: rgba(var(--ok-rgb), 0.16); color: var(--ok); }
.owned-badge.not-owned { background: var(--card-2); color: var(--text-muted); }
.year-header { display: flex; align-items: baseline; gap: 10px; margin: 14px 2px 6px; }
.year-label { font-size: var(--type-section-title); font-weight: 600; color: var(--text-primary); }
.year-count { font-size: var(--type-caption-1); color: var(--text-muted); }
</style>
