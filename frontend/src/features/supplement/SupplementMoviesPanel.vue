<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>作品字段</h2>
      </div>
      <button class="btn btn-primary btn-sm" type="button" :disabled="batchEnriching" @click="$emit('batch-enrich')">
        {{ batchEnriching ? '批量排队中...' : '批量补详情' }}
      </button>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="candidateImporting" @click="$emit('create-candidates')">
        {{ candidateImporting ? '生成中...' : '生成下载候选' }}
      </button>
    </div>
    <div class="filter-bar">
      <GlassSelect
        v-model="movieFilters.matched"
        :options="matchFilterOptions"
        size="compact"
        aria-label="影片匹配状态"
        @change="$emit('apply-filters')"
      />
      <GlassSelect
        v-model="movieFilters.quality"
        :options="qualityFilterOptions"
        size="compact"
        aria-label="影片质量筛选"
        @change="$emit('apply-filters')"
      />
      <input
        v-model="movieFilters.q"
        placeholder="搜索番号/标题"
        class="filter-input"
        @keyup.enter="$emit('apply-filters')"
      />
      <button class="btn btn-ghost btn-sm" type="button" @click="$emit('apply-filters')">筛选</button>
    </div>
    <div v-if="moviesLoading" class="loading-wrap"><div class="spinner-large"></div></div>
    <div v-else class="ios-list">
      <article v-for="movie in supplementMovies" :key="movie.id" class="ios-row movie-row">
        <img
          v-if="movieCover(movie)"
          :src="movieCover(movie)"
          class="movie-cover"
          loading="lazy"
          decoding="async"
          referrerpolicy="no-referrer"
          alt=""
          @error="applyImageFallback($event)"
        />
        <div v-else class="movie-cover movie-cover-empty">无封面</div>
        <div class="movie-row-main">
          <strong>{{ movie.dvd_id || movie.canonical_number || '—' }}</strong>
          <span>{{ movie.title || movie.dvd_id || movie.canonical_number || '—' }}</span>
          <small>{{ movie.release_date || '未知日期' }}</small>
          <div class="movie-meta">
            <span v-if="movie.runtime_mins">{{ movie.runtime_mins }} 分钟</span>
            <span v-if="movie.maker_name">{{ movie.maker_name }}</span>
            <span v-if="movieCategories(movie)" class="movie-meta-cats">{{ movieCategories(movie) }}</span>
          </div>
        </div>
        <div class="movie-row-actions">
          <span class="status-pill" :class="`match-${movieMatchClass(movie)}`">{{ movieMatchLabel(movie) }}</span>
          <button
            v-if="movie.source_movie_id"
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="enrichingMovies[movie.id]"
            @click="$emit('enrich', movie)"
          >{{ enrichingMovies[movie.id] ? '排队中...' : '补详情' }}</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$emit('open-sources', movie)">诊断</button>
        </div>
      </article>
      <div v-if="!supplementMovies.length" class="empty-inline">暂无补全影片</div>
    </div>
    <div v-if="moviesTotalPages > 1" class="pagination">
      <button class="btn btn-ghost btn-sm" :disabled="moviePage <= 1" @click="$emit('go-page', moviePage - 1)">上一页</button>
      <span>{{ moviePage }} / {{ moviesTotalPages }}</span>
      <button class="btn btn-ghost btn-sm" :disabled="moviePage >= moviesTotalPages" @click="$emit('go-page', moviePage + 1)">下一页</button>
    </div>
  </section>
</template>

<script>
import GlassSelect from '../../components/GlassSelect.vue'

export default {
  name: 'SupplementMoviesPanel',
  components: { GlassSelect },
  props: {
    movieFilters: { type: Object, required: true },
    matchFilterOptions: { type: Array, default: () => [] },
    qualityFilterOptions: { type: Array, default: () => [] },
    moviesLoading: { type: Boolean, default: false },
    supplementMovies: { type: Array, default: () => [] },
    moviesTotalPages: { type: Number, default: 1 },
    moviePage: { type: Number, default: 1 },
    batchEnriching: { type: Boolean, default: false },
    candidateImporting: { type: Boolean, default: false },
    enrichingMovies: { type: Object, default: () => ({}) },
    applyImageFallback: { type: Function, required: true },
    movieCover: { type: Function, required: true },
    movieCategories: { type: Function, required: true },
    movieMatchClass: { type: Function, required: true },
    movieMatchLabel: { type: Function, required: true },
  },
  emits: [
    'apply-filters',
    'batch-enrich',
    'create-candidates',
    'enrich',
    'open-sources',
    'go-page',
  ],
}
</script>

<style scoped src="./supplementMoviesPanel.css"></style>
