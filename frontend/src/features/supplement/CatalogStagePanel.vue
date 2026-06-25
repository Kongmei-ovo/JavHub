<template>
  <section class="stage-panel">
    <div v-if="tab === 'sources'" class="stage-filter">
      <button
        v-for="chip in chips" :key="chip.key" type="button" class="chip"
        :class="{ on: activeFilter === chip.key }" @click="activeFilter = chip.key"
      >{{ chip.label }}<span class="n">{{ chip.count }}</span></button>
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
  },
  emits: ['enrich', 'find', 'download', 'open-sources'],
  data() { return { activeFilter: 'all' } },
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
</style>
