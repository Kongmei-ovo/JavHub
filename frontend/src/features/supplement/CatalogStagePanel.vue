<template>
  <section class="stage-panel">
    <div v-if="tab === 'sources'" class="stage-filter">
      <button
        v-for="chip in chips" :key="chip.key" type="button" class="chip"
        :class="{ on: activeFilter === chip.key }" @click="activeFilter = chip.key"
      >{{ chip.label }}<span class="n">{{ chip.count }}</span></button>
    </div>

    <!-- 字段阶段：一键把所有缺字段的作品加入补全队列，免去逐部点「补字段」。 -->
    <div v-if="tab === 'fields' && films.length" class="stage-actions">
      <span class="stage-actions-hint">{{ films.length }} 部缺字段</span>
      <button class="btn btn-primary btn-sm" type="button" :disabled="batchBusy" @click="$emit('enrich-all')">
        <span v-if="batchBusy" class="spin-ring" aria-hidden="true"></span>
        {{ batchBusy ? '补全中…' : '一键补全' }}
      </button>
    </div>

    <AppleEmptyState
      v-if="!filtered.length"
      class="panel-state"
      :title="tab === 'fields' ? '字段都补齐了' : '没有待处理的下载'"
      :description="tab === 'fields' ? '这位演员所有作品的元数据都已补全。' : '当前筛选下没有待找源/可下载的作品。'"
      next-step="切到其他阶段，或回到影片目录。"
      density="compact"
    />

    <div v-else class="field-list">
      <CatalogFilmCard
        v-for="film in filtered" :key="film.canonical_number"
        :film="film" :tab="tab" :busy="!!busy[film.canonical_number]"
        @enrich="$emit('enrich', $event)" @find="$emit('find', $event)"
        @download="$emit('download', $event)" @open-sources="$emit('open-sources', $event)"
      />
    </div>
  </section>
</template>

<script>
import CatalogFilmCard from './CatalogFilmCard.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

export default {
  name: 'CatalogStagePanel',
  components: { CatalogFilmCard, AppleEmptyState },
  props: {
    tab: { type: String, required: true },        // 'fields' | 'sources'
    films: { type: Array, default: () => [] },     // already pre-filtered to this tab
    busy: { type: Object, default: () => ({}) },
    batchBusy: { type: Boolean, default: false },  // 字段阶段「一键补全」运行中
  },
  emits: ['enrich', 'enrich-all', 'find', 'download', 'open-sources'],
  data() { return { activeFilter: 'all' } },
  watch: {
    // Reset the sub-filter when switching stage (②↔③), so returning to 下载源
    // never lands on a stale chip that hides the films that actually need work.
    tab() { this.activeFilter = 'all' },
  },
  computed: {
    chips() {
      const by = s => this.films.filter(f => f.stage === s).length
      return [
        { key: 'all', label: '全部', count: this.films.length },
        { key: 'find_source', label: '待找源', count: by('find_source') },
        { key: 'downloadable', label: '可下载', count: by('downloadable') },
        { key: 'fetching', label: '获取中', count: by('fetching') },
      ]
    },
    filtered() {
      if (this.tab !== 'sources' || this.activeFilter === 'all') return this.films
      return this.films.filter(f => f.stage === this.activeFilter)
    },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped>
.stage-panel { display: grid; gap: var(--space-4); }
.stage-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
}
.stage-actions-hint { font-size: var(--type-caption); color: var(--text-muted); margin-right: auto; }
.stage-actions .btn { border-radius: 999px; }
</style>
