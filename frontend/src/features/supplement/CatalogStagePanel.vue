<template>
  <section class="stage-panel">
    <AppleEmptyState
      v-if="!films.length"
      class="panel-state"
      :title="emptyTitle"
      :description="emptyDescription"
      :next-step="hasFilter ? '放宽搜索 / 筛选条件，或清除后查看全部。' : '切到其他阶段，或回到影片目录。'"
      density="compact"
    />

    <div v-else class="field-list">
      <CatalogFilmCard
        v-for="film in films" :key="film.canonical_number"
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
    films: { type: Array, default: () => [] },     // already filtered (stage + search) by the parent toolbar
    hasFilter: { type: Boolean, default: false },
    busy: { type: Object, default: () => ({}) },
  },
  emits: ['enrich', 'find', 'download', 'open-sources'],
  computed: {
    emptyTitle() {
      if (this.hasFilter) return '没有符合条件的作品'
      return this.tab === 'fields' ? '字段都补齐了' : '没有待处理的下载'
    },
    emptyDescription() {
      if (this.hasFilter) return '当前搜索 / 筛选条件下没有作品。'
      return this.tab === 'fields' ? '这位演员所有作品的元数据都已补全。' : '当前没有待找源 / 可下载的作品。'
    },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped>
.stage-panel { display: grid; gap: var(--space-4); }
</style>
