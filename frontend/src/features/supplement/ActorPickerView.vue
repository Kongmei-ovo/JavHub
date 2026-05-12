<template>
  <section class="actor-picker-view">
    <div class="supplement-hero apple-surface">
      <div class="hero-copy">
        <p class="eyebrow">Actor First</p>
        <h2>选择一位演员开始补全</h2>
        <p>选择演员后处理作品字段、任务队列和来源诊断。</p>
      </div>
    </div>

    <section class="section-block">
      <div class="section-title-row">
        <div>
          <p class="eyebrow">{{ searched ? 'Filtered' : 'Recent' }}</p>
          <h2>选择补全演员</h2>
        </div>
        <span class="soft-count">{{ actors.length }} 位演员</span>
      </div>

      <div class="actor-picker-card">
        <div class="actor-filter-bar apple-surface">
          <div class="search-shell compact-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <circle cx="11" cy="11" r="7"></circle>
              <path d="M16.5 16.5 21 21"></path>
            </svg>
            <input
              :value="keyword"
              placeholder="输入演员名筛选卡片"
              @input="$emit('update:keyword', $event.target.value)"
              @keyup.enter="$emit('search')"
            />
            <button
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="searching || !keyword.trim()"
              @click="$emit('search')"
            >{{ searching ? '筛选中...' : '筛选' }}</button>
            <button
              v-if="searched"
              class="btn btn-ghost btn-sm"
              type="button"
              @click="$emit('clear-search')"
            >清除</button>
          </div>
        </div>
      </div>

      <div v-if="actors.length" class="actor-choice-grid">
        <button
          v-for="actor in actors"
          :key="actor.id"
          class="actor-choice-card apple-surface"
          type="button"
          @click="$emit('select', actor)"
        >
          <span class="select-orb" aria-hidden="true">
            <img
              v-if="actorAvatar(actor)"
              :src="actorAvatar(actor)"
              :alt="actorDisplayName(actor)"
              @error="$event.target.style.display = 'none'"
            />
            <span v-else>{{ actorDisplayName(actor).slice(0, 1) || '?' }}</span>
          </span>
          <span class="actor-card-copy">
            <strong>{{ actorDisplayName(actor) }}</strong>
            <span>ID {{ actor.id }}</span>
            <small>{{ actorChoiceStatus(actor) }}</small>
          </span>
          <span class="actor-card-action">选择</span>
        </button>
      </div>
      <div v-else-if="searched && !searching" class="empty-panel apple-surface">
        <h3>没有匹配演员</h3>
        <p>换一个日文名、罗马音或关键词再试。</p>
      </div>
      <div v-else class="empty-panel apple-surface">
        <h3>{{ error ? '补全队列不可用' : '暂无可选演员' }}</h3>
        <p>{{ error ? 'JavInfoApi 暂时无法连接，可稍后重试。' : '搜索演员后会出现可选择的演员卡片。' }}</p>
        <button
          v-if="error"
          class="btn btn-ghost btn-sm"
          type="button"
          @click="$emit('retry')"
        >重试</button>
      </div>
    </section>
  </section>
</template>

<script>
export default {
  name: 'ActorPickerView',
  props: {
    actors: { type: Array, default: () => [] },
    keyword: { type: String, default: '' },
    searched: { type: Boolean, default: false },
    searching: { type: Boolean, default: false },
    error: { type: Boolean, default: false },
    actorAvatar: { type: Function, required: true },
    actorDisplayName: { type: Function, required: true },
    actorChoiceStatus: { type: Function, required: true },
  },
  emits: ['update:keyword', 'search', 'clear-search', 'select', 'retry'],
}
</script>
