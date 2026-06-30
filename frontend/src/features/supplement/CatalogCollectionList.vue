<template>
  <section class="collection-list">
    <AppleSkeleton v-if="loading && !yearGroups.length && !hasFilter" class="panel-state" variant="list" :items="8" label="影片目录加载中" />

    <AppleEmptyState
      v-else-if="!totalCount"
      class="panel-state"
      title="还没有作品目录"
      description="这位演员的片单还没有结果。"
      next-step="点「重新拉片单」拉取她的完整作品集。"
      action-label="重新拉片单"
      density="compact"
      @action="$emit('recompute')"
    />

    <AppleEmptyState
      v-else-if="!yearGroups.length"
      class="panel-state"
      title="没有符合条件的作品"
      description="当前的搜索 / 来源 / 入库 / 出演时间条件下没有作品。"
      next-step="放宽条件，或清除筛选查看全部。"
      action-label="清除筛选"
      density="compact"
      @action="$emit('clear-filters')"
    />

    <div v-for="group in yearGroups" v-else :key="group.year" class="year-group">
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
          <span class="ml-col ml-origin">{{ isSupplement(film) ? '私拍' : '正片' }}</span>
          <span class="ml-col ml-owned">
            <span class="owned-badge" :class="isOwned(film) ? 'is-owned' : 'not-owned'">{{ isOwned(film) ? '已入库' : '未入库' }}</span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

export default {
  name: 'CatalogCollectionList',
  components: { AppleSkeleton, AppleEmptyState },
  props: {
    // Already filtered (search / 来源 / 入库 / 年份) by the parent toolbar.
    yearGroups: { type: Array, default: () => [] },
    totalCount: { type: Number, default: 0 },     // unfiltered total — distinguishes 空目录 vs 筛选无果
    hasFilter: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
  },
  emits: ['recompute', 'clear-filters'],
  methods: {
    isOwned(film) { return film.funnel_stage === 'complete' || film.status === 'owned' || film.stage === 'complete' },
    isSupplement(film) { return film.origin === 'supplement' },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped>
.collection-list { display: grid; gap: var(--space-4); }

/* ---- year list ----------------------------------------------------------- */
/* 同心圆角:容器 16(radius-lg) − 内边距 8 = 8,与行 .movie-list-row 的 8px 平行 */
.movie-list { display: grid; gap: 2px; background: var(--card); border: 1px solid var(--hairline); border-radius: var(--radius-lg); padding: 6px 8px; }
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
