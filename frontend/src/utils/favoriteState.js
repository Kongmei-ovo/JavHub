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
  initialized: false,
  detailsLoaded: false,
  metadataTypesLoaded: new Set()
})

function normalizeFavoriteItems(items, includeMetadata) {
  return items.map(item => {
    const normalized = {
      entity_type: String(item.entity_type || ''),
      entity_id: String(item.entity_id ?? ''),
      created_at: item.created_at
    }
    if (includeMetadata) {
      normalized.metadata = item.metadata || {}
    }
    return normalized
  })
}

export const favoriteState = {
  /**
   * 初始化：默认只从后端拉取收藏索引，避免所有页面背完整 metadata。
   */
  async init(options = {}) {
    const includeMetadata = Boolean(options.includeMetadata)
    if (state.initialized && (!includeMetadata || state.detailsLoaded)) return
    try {
      const resp = await api.getFavorites(undefined, { include_metadata: includeMetadata })
      const items = normalizeFavoriteItems(resp.data || [], includeMetadata)

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
      state.detailsLoaded = includeMetadata
      state.metadataTypesLoaded = includeMetadata
        ? new Set(items.map(item => item.entity_type).filter(Boolean))
        : new Set()
      console.info(`[FavoriteState] Initialized with ${items.length} items.`)
    } catch (err) {
      console.error('[FavoriteState] Init failed:', err)
    }
  },

  /**
   * 刷新数据
   */
  async refresh(options = {}) {
    state.initialized = false
    state.detailsLoaded = false
    state.metadataTypesLoaded = new Set()
    await this.init(options)
  },

  async loadMetadataForTypes(types = []) {
    if (!state.initialized) {
      await this.init()
    }
    const requestedTypes = [...new Set(types.map(type => String(type || '').trim()).filter(Boolean))]
    const missingTypes = requestedTypes.filter(type => !state.metadataTypesLoaded.has(type))
    if (missingTypes.length === 0) return

    const responses = await Promise.all(
      missingTypes.map(async type => {
        const resp = await api.getFavorites(type, { include_metadata: true })
        return [type, resp.data || []]
      })
    )
    const detailByKey = new Map()
    responses.forEach(([_type, items]) => {
      items.forEach(item => {
        const type = String(item.entity_type || '')
        const id = String(item.entity_id ?? '')
        if (type && id) {
          detailByKey.set(`${type}:${id}`, {
            entity_type: type,
            entity_id: id,
            metadata: item.metadata || {},
            created_at: item.created_at,
          })
        }
      })
    })

    const existingKeys = new Set()
    state.items = state.items.map(item => {
      const key = `${item.entity_type}:${item.entity_id}`
      existingKeys.add(key)
      const detail = detailByKey.get(key)
      return detail ? { ...item, metadata: detail.metadata, created_at: detail.created_at || item.created_at } : item
    })
    detailByKey.forEach((detail, key) => {
      if (!existingKeys.has(key)) {
        state.items.push(detail)
      }
    })
    state.metadataTypesLoaded = new Set([...state.metadataTypesLoaded, ...missingTypes])
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
  async toggle(type, id, metadata = {}) {
    if (!type || !id) return false

    try {
      const resp = await api.toggleFavorite({
        entity_type: type,
        entity_id: String(id),
        metadata,
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
          const nextItem = {
            entity_type: normalizedType,
            entity_id: String(id),
            created_at: new Date().toISOString()
          }
          if (state.detailsLoaded) {
            nextItem.metadata = metadata
          }
          state.items.unshift(nextItem)
        }
      } else {
        bucket.delete(String(id))
        state.items = state.items.filter(item => !(item.entity_type === normalizedType && String(item.entity_id) === String(id)))
      }

      // Notify listeners (for Toast)
      for (const listener of this.listeners) {
        listener({ type: normalizedType, id, is_favorited })
      }

      return is_favorited
    } catch (err) {
      console.error('[FavoriteState] Toggle failed:', err)
      throw err
    }
  },

  // 简单的监听器机制，用于触发全局 Toast
  listener: null,
  listeners: new Set(),
  subscribe(callback) {
    this.listeners.add(callback)
    return () => {
      this.listeners.delete(callback)
    }
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
