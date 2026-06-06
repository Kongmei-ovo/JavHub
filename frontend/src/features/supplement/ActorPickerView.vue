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
        <ActorPortraitCard
          v-for="actor in actors"
          :key="actor.id"
          :actor="actor"
          :name="actorDisplayName(actor)"
          :subtitle="`编号 ${actor.id}`"
          :avatar-url="actorAvatar(actor)"
          :badges="actorBadges(actor)"
          density="compact"
          action-label="选择"
          @open="$emit('select', actor)"
        />
      </div>
      <AppleEmptyState
        v-else
        class="empty-panel"
        :title="actorEmptyState.title"
        :description="actorEmptyState.description"
        :next-step="actorEmptyState.nextStep"
        :action-label="actorEmptyState.actionLabel"
        :secondary-action-label="actorEmptyState.secondaryActionLabel"
        density="compact"
        @action="handleEmptyAction"
        @secondary-action="handleEmptySecondaryAction"
      />
    </section>
  </section>
</template>

<script>
import ActorPortraitCard from '../../components/ActorPortraitCard.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

export default {
  name: 'ActorPickerView',
  components: { ActorPortraitCard, AppleEmptyState },
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
  computed: {
    actorEmptyState() {
      if (this.error) {
        return {
          title: '补全队列不可用',
          description: '补全接口暂时无法连接。',
          nextStep: '重试会重新读取最近补全演员；也可以清除搜索后稍后再筛选。',
          actionLabel: '重试',
          secondaryActionLabel: this.searched ? '清除搜索' : '',
        }
      }
      if (this.searched && !this.searching) {
        return {
          title: '没有匹配演员',
          description: '当前关键词没有找到可补全的演员。',
          nextStep: '换一个日文名或罗马音继续搜索，或清除搜索回到最近补全列表。',
          actionLabel: this.keyword.trim() ? '重新搜索' : '',
          secondaryActionLabel: '清除搜索',
        }
      }
      return {
        title: '暂无可选演员',
        description: '最近补全列表还没有可选演员。',
        nextStep: '可以输入演员名筛选，或刷新最近补全队列等待新任务写入。',
        actionLabel: this.keyword.trim() ? '筛选演员' : '刷新最近补全',
        secondaryActionLabel: this.keyword.trim() ? '清除搜索' : '',
      }
    },
  },
  methods: {
    handleEmptyAction() {
      if (this.error) {
        this.$emit('retry')
        return
      }
      if (this.keyword.trim()) {
        this.$emit('search')
        return
      }
      this.$emit('retry')
    },
    handleEmptySecondaryAction() {
      this.$emit('clear-search')
    },
    actorBadges(actor) {
      const status = this.actorChoiceStatus(actor)
      if (!status) return []
      const tone = /失败|不可用|failed/i.test(status)
        ? 'warning'
        : (/成功|succeeded|已完成/i.test(status) ? 'success' : 'neutral')
      return [{ label: status, tone }]
    },
  },
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
  border: 1px solid var(--glass-control-border);
  border-radius: var(--actor-control-radius);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

.search-shell:focus-within {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
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
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 16px;
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

  .actor-choice-grid {
    grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
  }
}
</style>
