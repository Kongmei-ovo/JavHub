<template>
  <section class="actor-picker-view">
    <section class="actor-search-panel apple-surface">
      <div class="actor-search-head">
        <div>
          <h2>{{ searched ? '搜索结果' : '最近补全' }}</h2>
        </div>
        <span class="soft-count">{{ actors.length }} 位</span>
      </div>

      <div class="search-row">
        <label class="search-shell">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <circle cx="11" cy="11" r="7"></circle>
            <path d="M16.5 16.5 21 21"></path>
          </svg>
          <input
            :value="keyword"
            placeholder="演员名 / 罗马音"
            @input="$emit('update:keyword', $event.target.value)"
            @keyup.enter="$emit('search')"
          />
        </label>
        <button
          class="btn btn-primary btn-sm search-action"
          type="button"
          :disabled="searching || !keyword.trim()"
          @click="$emit('search')"
        >{{ searching ? '筛选中...' : '筛选' }}</button>
        <button
          v-if="searched"
          class="btn btn-ghost btn-sm search-action"
          type="button"
          @click="$emit('clear-search')"
        >清除</button>
      </div>
    </section>

    <section class="actor-results">
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
            <span>编号 {{ actor.id }}</span>
            <small>{{ actorChoiceStatus(actor) }}</small>
          </span>
          <span class="actor-card-action">选择</span>
        </button>
      </div>
      <div v-else-if="searched && !searching" class="empty-panel apple-surface">
        <h3>没有匹配演员</h3>
        <p>换一个日文名、罗马音再试。</p>
      </div>
      <div v-else class="empty-panel apple-surface">
        <h3>{{ error ? '补全队列不可用' : '暂无可选演员' }}</h3>
        <p>{{ error ? '补全接口暂时无法连接，可稍后重试。' : '搜索后会显示可补全的演员。' }}</p>
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

<style scoped>
.actor-picker-view {
  --actor-control-radius: 16px;
  display: grid;
  gap: 16px;
}

.actor-picker-view h2,
.actor-picker-view h3,
.actor-picker-view p {
  margin: 0;
}

.actor-search-panel {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 22px;
}

.actor-search-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.actor-search-head h2 {
  color: var(--text-primary);
  font-size: 20px;
}

.soft-count {
  color: var(--text-muted);
  font-size: 13px;
}

.search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
}

.search-shell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 42px;
  padding: 0 13px;
  border: 1px solid var(--border);
  border-radius: var(--actor-control-radius);
  background: rgba(255, 255, 255, 0.045);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.04);
}

.search-shell svg {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-shell input {
  width: 100%;
  min-width: 0;
  min-height: 40px;
  padding: 0;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  border-radius: 999px;
  outline: none;
  font-size: 15px;
}

.search-action {
  min-width: 76px;
  min-height: 42px;
  border-radius: var(--actor-control-radius);
  justify-content: center;
  white-space: nowrap;
}

.actor-choice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.actor-choice-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  min-height: 214px;
  padding: 20px 16px;
  color: var(--text-primary);
  border: 1px solid var(--border);
  cursor: pointer;
  text-align: center;
  transition:
    transform var(--motion-standard),
    border-color var(--motion-standard),
    background var(--motion-standard),
    box-shadow var(--motion-standard);
}

.actor-choice-card:hover {
  transform: translateY(-5px);
  border-color: var(--border-light);
  background: var(--surface-card-hover);
  box-shadow: var(--shadow-floating);
}

.select-orb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 92px;
  height: 92px;
  overflow: hidden;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 50%;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.12), 0 18px 36px rgba(0, 0, 0, 0.42);
  flex-shrink: 0;
  font-weight: 800;
}

.select-orb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
}

.actor-card-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.actor-card-copy strong {
  color: var(--text-primary);
  font-size: 14px;
}

.actor-card-copy span,
.actor-card-copy small {
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actor-card-copy small {
  max-width: 190px;
  margin: 0 auto;
}

.actor-card-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 16px;
  margin-top: 2px;
  border-radius: 999px;
  background: var(--accent);
  color: var(--text-on-accent);
  font-size: 13px;
  font-weight: 700;
}

.empty-panel {
  padding: 28px;
  text-align: center;
}

.empty-panel h3 {
  color: var(--text-primary);
  font-size: 16px;
}

.empty-panel p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 860px) {
  .actor-picker-view {
    gap: 14px;
  }

  .actor-search-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .actor-search-panel {
    padding: 14px;
    border-radius: 20px;
  }

  .search-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .search-shell,
  .search-action {
    border-radius: var(--actor-control-radius);
  }

  .search-action {
    width: 100%;
  }

  .actor-choice-card {
    min-height: 204px;
  }
}
</style>
