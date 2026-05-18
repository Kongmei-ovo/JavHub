import { reactive, computed } from 'vue'
import api from '../api/index.js'

/**
 * 全局收藏状态管理
 * 使用 Action-First-Organize-Later 理念
 */
export const state = reactive({
  // 按实体类型存储收藏 ID 集合 (Set)
  registry: new Map(),
  // 存储完整的收藏对象列表
  items: [],
  initialized: false
})

export const favoriteState = {
  /**
   * 初始化：从后端拉取所有收藏
   */
  async init() {
    if (state.initialized) return
    try {
      const resp = await api.getFavorites()
      const items = resp.data || []

      state.items = items
      state.registry = new Map()

      items.forEach(item => {
        const type = String(item.entity_type || '')
        if (!state.registry.has(type)) {
          state.registry.set(type, new Set())
        }
        state.registry.get(type).add(String(item.entity_id))
      })

      state.initialized = true
      console.info(`[FavoriteState] Initialized with ${items.length} items.`)
    } catch (err) {
      console.error('[FavoriteState] Init failed:', err)
    }
  },

  /**
   * 刷新数据
   */
  async refresh() {
    state.initialized = false
    await this.init()
  },

  /**
   * 检查是否已收藏
   */
  isFavorited(type, id) {
    const bucket = state.registry.get(String(type || ''))
    if (!bucket) return false
    return bucket.has(String(id))
  },

  /**
   * 切换收藏状态
   */
  async toggle(type, id) {
    if (!type || !id) return false

    try {
      const resp = await api.toggleFavorite({
        entity_type: type,
        entity_id: String(id),
      })
      
      const is_favorited = resp.data.is_favorited
      
      const normalizedType = String(type)
      if (!state.registry.has(normalizedType)) {
        state.registry.set(normalizedType, new Set())
      }
      const bucket = state.registry.get(normalizedType)
      
      if (is_favorited) {
        bucket.add(String(id))
        const exists = state.items.some(item => item.entity_type === normalizedType && String(item.entity_id) === String(id))
        if (!exists) {
          state.items.unshift({
            entity_type: normalizedType,
            entity_id: String(id),
            metadata: {},
            created_at: new Date().toISOString()
          })
        }
      } else {
        bucket.delete(String(id))
        state.items = state.items.filter(item => !(item.entity_type === normalizedType && String(item.entity_id) === String(id)))
      }

      // Notify listeners (for Toast)
      if (this.listener) {
        this.listener({ type: normalizedType, id, is_favorited })
      }

      return is_favorited
    } catch (err) {
      console.error('[FavoriteState] Toggle failed:', err)
      throw err
    }
  },

  // 简单的监听器机制，用于触发全局 Toast
  listener: null,
  subscribe(callback) {
    this.listener = callback
  },

  /**
   * 统计总数 (Computed)
   */
  count: computed(() => {
    let total = 0
    for (const bucket of state.registry.values()) {
      total += bucket.size
    }
    return total
  }),

  // 暴露原始响应式状态
  state
}

export default favoriteState
