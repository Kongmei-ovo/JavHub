<template>
  <div class="favorites-page page-shell page-shell--gallery">
    <div class="curate-header">
      <div class="curate-header-main">
        <div class="curate-copy">
          <h1 class="curate-title">私人策展</h1>
          <div class="curate-stats">
            共 {{ count }} 个收藏项
          </div>
          <p class="instance-note">{{ instanceNote }}</p>
        </div>
        <div class="curate-toolbar">
          <button
            class="btn-mini"
            type="button"
            :class="{ active: editMode }"
            @click="toggleEditMode"
          >
            {{ editMode ? '完成' : '编辑' }}
          </button>
          <button
            v-if="editMode"
            class="btn-mini danger"
            type="button"
            :disabled="selectedFavoriteKeys.size === 0"
            @click="removeSelectedFavorites"
          >
            取消收藏 {{ selectedFavoriteKeys.size || '' }}
          </button>
        </div>
      </div>

      <section class="collection-manager" aria-label="收藏集合">
        <div class="collection-manager-head">
          <div>
            <h2>收藏集合</h2>
            <p>{{ collections.length }} 个集合 · 管理本地策展分组</p>
          </div>
          <button class="btn-mini" type="button" @click="resetCollectionForm">新建集合</button>
        </div>
        <form class="collection-form" @submit.prevent="saveCollection">
          <input v-model="collectionForm.name" placeholder="集合名称" />
          <input v-model="collectionForm.description" placeholder="描述，可选" />
          <button class="btn-mini primary" type="submit" :disabled="collectionsLoading || !collectionForm.name.trim()">
            {{ editingCollectionId ? '保存' : '创建' }}
          </button>
          <button v-if="editingCollectionId" class="btn-mini" type="button" @click="resetCollectionForm">取消</button>
        </form>
        <div class="collection-list">
          <article v-for="collection in collections" :key="collection.id" class="collection-row">
            <div>
              <strong>{{ collection.name }}</strong>
              <span>{{ collection.description || '暂无描述' }}</span>
            </div>
            <div class="collection-actions">
              <button class="btn-mini" type="button" @click="editCollection(collection)">重命名</button>
              <button class="btn-mini danger" type="button" @click="removeCollection(collection)">删除</button>
            </div>
          </article>
          <small v-if="!collectionsLoading && collections.length === 0" class="collection-empty">还没有收藏集合</small>
        </div>
      </section>

      <!-- iOS 风格的分段选择器 -->
      <div class="segmented-control">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="segment-item"
          type="button"
          :class="{ active: activeTab === tab.id }"
          @click="setActiveTab(tab.id)"
        >
          {{ tab.label }}
          <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="videoLoading" class="favorites-grid favorites-grid-loading">
      <div v-for="n in 8" :key="n" class="skeleton-card">
        <div class="skeleton-cover"></div>
        <div class="skeleton-info">
          <div class="skeleton-line w-60"></div>
          <div class="skeleton-line w-80"></div>
        </div>
      </div>
    </div>

    <!-- 收藏内容 -->
    <div v-else class="curate-content">
      <!-- 影片网格 -->
      <div v-if="activeTab === 'video' || activeTab === 'all'" v-show="videoItems.length > 0" class="favorites-grid" :class="{ 'is-editing': editMode }">
        <div
          v-for="item in displayVideoItems"
          :key="'v-' + item.entity_id"
          class="favorite-selectable"
          :class="{ selected: isSelected(item) }"
          @click="handleFavoriteItemClick(item)"
        >
          <MovieCard
            v-bind="movieCardVariantProps(item.metadata || {})"
            :coverUrl="cardImageUrl(item.metadata || {})"
            :title="item.metadata?.title_en_translated || item.metadata?.title_ja_translated || item.metadata?.title_en || item.metadata?.title_ja || item.metadata?.title || ''"
            :serviceCode="item.metadata?.service_code || ''"
            :releaseDate="item.metadata?.release_date || ''"
            :runtimeMins="item.metadata?.runtime_mins || item.metadata?.runtime || ''"
            :sampleUrl="item.metadata?.sample_url || ''"
          />
          <VariantGroupDisclosure
            :variantGroupCount="Number(item.metadata?.variant_group_count || 0)"
            :variantGroupItems="visibleVariantItems(item.metadata || {})"
            :expanded="isVariantGroupExpanded(item.metadata || {})"
            :itemKey="variantGroupKey(item.metadata || {})"
            @toggle="toggleVariantGroup"
            @openVariant="openVideoModalFromMetadata"
          />
          <button
            v-if="editMode"
            class="select-check"
            type="button"
            :aria-label="isSelected(item) ? '取消选择' : '选择收藏项'"
            @click.stop="toggleFavoriteSelection(item)"
          >
            <span></span>
          </button>
        </div>
      </div>

      <!-- 演员收藏：肖像卡片 -->
      <div v-if="actorFavoriteItems.length > 0" class="entity-section actor-favorites-section">
        <div v-if="activeTab === 'all'" class="section-label">演员</div>
        <div class="actor-favorites-grid">
          <div
            v-for="item in actorFavoriteItems"
            :key="'a-' + item.entity_id"
            class="favorite-selectable"
            :class="{ selected: isSelected(item) }"
          >
            <ActorPortraitCard
              :actor="item.actor"
              :name="actorCardName(item)"
              :subtitle="actorCardSubtitle(item)"
              :meta="actorCardMeta(item)"
              :avatar-url="actorCardAvatar(item)"
              :badges="actorCardBadges(item)"
              density="standard"
              @open="handleFavoriteItemClick(item)"
            />
            <button
              v-if="editMode"
              class="select-check select-check--actor"
              type="button"
              :aria-label="isSelected(item) ? '取消选择' : '选择收藏项'"
              @click.stop="toggleFavoriteSelection(item)"
            >
              <span></span>
            </button>
          </div>
        </div>
      </div>

      <!-- 非影片收藏：标签云 -->
      <div v-if="otherEntityItems.length > 0" class="entity-section">
        <div v-if="activeTab === 'all'" class="section-label">{{ sectionLabel }}</div>
        <div class="entity-cloud">
          <div
            v-for="item in otherEntityItems"
            :key="item.entity_type + '-' + item.entity_id"
            class="entity-bubble"
            :class="{ selected: isSelected(item) }"
            role="button"
            tabindex="0"
            :aria-label="`查看${typeLabel(item.entity_type)}详情：${entityDisplayName(item)}`"
            @click="handleFavoriteItemClick(item)"
            @keydown.enter.prevent="handleFavoriteItemClick(item)"
            @keydown.space.prevent="handleFavoriteItemClick(item)"
          >
            <span class="entity-name">{{ entityDisplayName(item) }}</span>
            <span class="entity-type-tag">{{ typeLabel(item.entity_type) }}</span>
            <button v-if="!editMode" class="entity-fav-btn" type="button" @click.stop="toggleFavorite(item.entity_type, item.entity_id)">
              <svg viewBox="0 0 24 24" width="12" height="12">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>
              </svg>
            </button>
            <span v-else class="entity-select-dot" aria-hidden="true"></span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="displayVideoItems.length === 0 && actorFavoriteItems.length === 0 && otherEntityItems.length === 0" class="curate-empty">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </div>
        <h3>{{ emptyTitle }}</h3>
        <p>{{ emptyDescription }}</p>
        <button v-if="activeTab === 'all'" class="btn-explore" type="button" @click="$router.push('/genres')">去探索</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { state, favoriteState } from '../utils/favoriteState'
import subscriptionState from '../utils/subscriptionState'
import { openVideoModal } from '../utils/modalState'
import { videoCardCoverUrl } from '../utils/imageUrl.js'
import { actorAvatar, actorName, actorOriginalName } from '../utils/actorDisplay.js'
import api from '../api'
import MovieCard from '../components/MovieCard.vue'
import ActorPortraitCard from '../components/ActorPortraitCard.vue'
import VariantGroupDisclosure from '../components/VariantGroupDisclosure.vue'
import { movieCardVariantProps, variantGroupKey, visibleVariantItems } from '../utils/videoVariantPresentation.js'

const TYPE_LABELS = {
  video: '影片',
  actress: '演员',
  category: '题材',
  series: '系列',
  maker: '工作室',
}

export default {
  name: 'Favorites',
  components: { MovieCard, ActorPortraitCard, VariantGroupDisclosure },
  setup() {
    const router = useRouter()
    const activeTab = ref('all')
    const videoLoading = ref(false)
    const videoItems = ref([])
    const actorMetaMap = ref({})
    const collections = ref([])
    const collectionsLoading = ref(false)
    const editingCollectionId = ref(null)
    const collectionForm = ref({ name: '', description: '' })
    const editMode = ref(false)
    const selectedFavoriteKeys = ref(new Set())
    const expandedVariantGroups = ref({})

    // 动态计算各类型数量
    const typeCounts = computed(() => {
      const counts = {}
      state.items.forEach(item => {
        counts[item.entity_type] = (counts[item.entity_type] || 0) + 1
      })
      counts.video = videoItems.value.length || counts.video || 0
      return counts
    })

    const tabs = computed(() => [
      { id: 'all', label: '全部', count: state.count },
      { id: 'video', label: '影片', count: typeCounts.value.video || 0 },
      { id: 'actress', label: '演员', count: typeCounts.value.actress || 0 },
      { id: 'category', label: '题材', count: typeCounts.value.category || 0 },
      { id: 'series', label: '系列', count: typeCounts.value.series || 0 },
      { id: 'maker', label: '工作室', count: typeCounts.value.maker || 0 },
    ])

    // 从新接口加载完整影片数据
    const loadVideos = async () => {
      videoLoading.value = true
      try {
        const resp = await api.getFavoriteVideos()
        videoItems.value = (resp.data || []).map(v => ({
          entity_type: 'video',
          entity_id: v._favorite_entity_id || (v.service_code ? `${v.content_id || v.dvd_id}::${v.service_code}` : (v.content_id || v.dvd_id)),
          metadata: v,
          created_at: v._created_at
        }))
      } catch (e) {
        console.error('Failed to load favorite videos:', e)
      } finally {
        videoLoading.value = false
      }
    }

    onMounted(() => {
      loadVideos()
      loadCollections()
      subscriptionState.refresh().catch(err => {
        console.error('Failed to initialize subscriptions:', err)
      })
    })

    // 影片展示列表
    const displayVideoItems = computed(() => {
      if (activeTab.value === 'video') return videoItems.value
      if (activeTab.value === 'all') return videoItems.value
      return []
    })

    // 非影片收藏
    const nonVideoItems = computed(() => {
      const items = state.items.filter(i => i.entity_type !== 'video')
      if (activeTab.value === 'all') return items
      return items.filter(i => i.entity_type === activeTab.value)
    })

    const actorSourceItems = computed(() => state.items.filter(i => i.entity_type === 'actress'))
    const actorFavoriteItems = computed(() => {
      if (activeTab.value !== 'all' && activeTab.value !== 'actress') return []
      return actorSourceItems.value.map(item => {
        const cached = actorMetaMap.value[String(item.entity_id)]
        const fallback = {
          id: item.entity_id,
          ...(item.metadata || {}),
        }
        return { ...item, actor: cached || fallback }
      })
    })
    const otherEntityItems = computed(() => nonVideoItems.value.filter(i => i.entity_type !== 'actress'))

    const sectionLabel = computed(() => {
      const types = [...new Set(otherEntityItems.value.map(i => i.entity_type))]
      return types.map(t => TYPE_LABELS[t] || t).join('、')
    })

    const activeTabLabel = computed(() => tabs.value.find(tab => tab.id === activeTab.value)?.label || '当前分类')
    const instanceNote = computed(() => `当前实例收藏 · 影片 ${typeCounts.value.video || 0} · 演员 ${typeCounts.value.actress || 0}`)
    const emptyTitle = computed(() => activeTab.value === 'all' ? '当前实例还没有收藏' : `当前分类暂无收藏`)
    const emptyDescription = computed(() => (
      activeTab.value === 'all'
        ? '这里显示当前 JavHub 实例的本地收藏。'
        : `当前实例暂无${activeTabLabel.value}收藏，可切换到其他分类查看。`
    ))

    const typeLabel = (type) => TYPE_LABELS[type] || type

    const entityDisplayName = (item) => {
      const m = item.metadata || {}
      return m.name_translated || m.name_ja_translated || m.name_en_translated
        || m.name_kanji_translated || m.name_romaji_translated
        || m.name_ja || m.name_en || m.name_kanji || m.name_romaji || m.name
        || m.title || item.entity_id
    }

    const navigateToEntity = (item) => {
      const type = item.entity_type
      const id = item.entity_id
      const name = entityDisplayName(item)
      if (type === 'video') {
        openVideo(item)
      } else {
        router.push({ name: 'DiscoveryDetail', params: { type, value: id }, query: { name } })
      }
    }

    const navigateToActor = (item) => {
      const id = actorCardSubscriptionId(item)
      const name = actorCardName(item)
      router.push({ path: `/actor/${encodeURIComponent(name)}`, query: id ? { name, actress_id: id } : { name } })
    }

    const openVideo = (item) => {
      if (item.entity_type === 'video') {
        openVideoModal(item.metadata || { content_id: item.entity_id }, '/favorites')
      }
    }
    const openVideoModalFromMetadata = (metadata) => {
      openVideoModal(metadata, '/favorites')
    }

    const favoriteKey = (item) => `${item.entity_type}:${item.entity_id}`
    const isSelected = (item) => selectedFavoriteKeys.value.has(favoriteKey(item))
    const toggleFavoriteSelection = (item) => {
      const next = new Set(selectedFavoriteKeys.value)
      const key = favoriteKey(item)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      selectedFavoriteKeys.value = next
    }
    const toggleEditMode = () => {
      editMode.value = !editMode.value
      if (!editMode.value) selectedFavoriteKeys.value = new Set()
    }
    const setActiveTab = (tabId) => {
      activeTab.value = tabId
      selectedFavoriteKeys.value = new Set()
    }
    const handleFavoriteItemClick = (item) => {
      if (editMode.value) {
        toggleFavoriteSelection(item)
        return
      }
      if (item.entity_type === 'video') openVideo(item)
      else if (item.entity_type === 'actress') navigateToActor(item)
      else navigateToEntity(item)
    }
    const allVisibleFavoriteItems = computed(() => [
      ...displayVideoItems.value,
      ...actorFavoriteItems.value,
      ...otherEntityItems.value,
    ])
    const removeSelectedFavorites = async () => {
      const selectedItems = allVisibleFavoriteItems.value.filter(item => isSelected(item))
      for (const item of selectedItems) {
        await favoriteState.toggle(item.entity_type, item.entity_id)
      }
      selectedFavoriteKeys.value = new Set()
      await favoriteState.refresh()
      await loadVideos()
    }

    const isFavorited = (type, id) => {
      return favoriteState.isFavorited(type, id)
    }

    const toggleFavorite = async (type, id) => {
      try {
        await favoriteState.toggle(type, id)
        if (type === 'video') await loadVideos()
      } catch (err) {
        console.error('Failed to toggle favorite:', err)
      }
    }

    const cardImageUrl = (metadata) => videoCardCoverUrl(metadata)
    const isVariantGroupExpanded = (metadata) => {
      const key = variantGroupKey(metadata)
      return Boolean(key && expandedVariantGroups.value[key])
    }
    const toggleVariantGroup = (key) => {
      if (!key) return
      expandedVariantGroups.value = {
        ...expandedVariantGroups.value,
        [key]: !expandedVariantGroups.value[key],
      }
    }

    const actorCardName = (item) => actorName(item.actor, entityDisplayName(item) || String(item.entity_id))
    const actorCardSubtitle = (item) => actorOriginalName(item.actor)
    const actorCardMeta = (item) => {
      const count = item.actor?.movie_count
      return count != null ? `${Number(count).toLocaleString()} 部作品` : ''
    }
    const actorCardAvatar = (item) => actorAvatar(item.actor)
    const actorCardSubscriptionId = (item) => {
      const id = item.actor?.id || item.actor?.actress_id || item.actor?.javinfo_actress_id || item.entity_id
      return /^\d+$/.test(String(id || '')) ? String(id) : ''
    }
    const actorCardSubscribed = (item) => subscriptionState.isSubscribed(actorCardSubscriptionId(item))
    const actorCardBadges = (item) => {
      const badges = [{ label: '收藏', tone: 'favorite' }]
      if (actorCardSubscribed(item)) badges.push({ label: '已订阅', tone: 'subscribed' })
      return badges
    }

    const loadCollections = async () => {
      collectionsLoading.value = true
      try {
        const resp = await api.getCollections()
        collections.value = resp.data || []
      } catch (err) {
        console.error('Failed to load collections:', err)
      } finally {
        collectionsLoading.value = false
      }
    }

    const resetCollectionForm = () => {
      editingCollectionId.value = null
      collectionForm.value = { name: '', description: '' }
    }

    const editCollection = (collection) => {
      editingCollectionId.value = collection.id
      collectionForm.value = {
        name: collection.name || '',
        description: collection.description || '',
      }
    }

    const saveCollection = async () => {
      const payload = {
        name: collectionForm.value.name.trim(),
        description: collectionForm.value.description?.trim() || null,
      }
      if (!payload.name) return
      try {
        if (editingCollectionId.value) {
          await api.updateCollection(editingCollectionId.value, payload)
        } else {
          await api.createCollection(payload)
        }
        resetCollectionForm()
        await loadCollections()
      } catch (err) {
        console.error('Failed to save collection:', err)
      }
    }

    const removeCollection = async (collection) => {
      try {
        await api.deleteCollection(collection.id)
        if (editingCollectionId.value === collection.id) resetCollectionForm()
        await loadCollections()
      } catch (err) {
        console.error('Failed to delete collection:', err)
      }
    }

    const enrichFavoriteActor = async (item) => {
      const id = String(item.entity_id)
      if (!id || actorMetaMap.value[id]) return
      const metadata = item.metadata || {}
      try {
        if (/^\d+$/.test(id)) {
          const resp = await api.getActress(id)
          actorMetaMap.value = { ...actorMetaMap.value, [id]: resp.data || resp }
          return
        }
        const name = entityDisplayName(item)
        if (name) {
          const resp = await api.searchActors(name)
          const results = resp.data?.data || resp.data || []
          const match = results.find(actor => actorName(actor) === name) || results[0]
          if (match) {
            actorMetaMap.value = { ...actorMetaMap.value, [id]: match }
            return
          }
        }
      } catch (err) {
        console.warn('Failed to enrich favorite actor:', err)
      }
      actorMetaMap.value = {
        ...actorMetaMap.value,
        [id]: { id, ...metadata, name: entityDisplayName(item) || id },
      }
    }

    watch(
      actorSourceItems,
      (items) => {
        items.forEach(item => { enrichFavoriteActor(item) })
      },
      { immediate: true }
    )

    return {
      state,
      count: favoriteState.count,
      activeTab,
      editMode,
      selectedFavoriteKeys,
      tabs,
      videoLoading,
      videoItems,
      displayVideoItems,
      nonVideoItems,
      actorFavoriteItems,
      otherEntityItems,
      sectionLabel,
      instanceNote,
      emptyTitle,
      emptyDescription,
      typeLabel,
      entityDisplayName,
      navigateToEntity,
      navigateToActor,
      openVideo,
      openVideoModalFromMetadata,
      favoriteKey,
      isSelected,
      toggleFavoriteSelection,
      toggleEditMode,
      setActiveTab,
      handleFavoriteItemClick,
      removeSelectedFavorites,
      isFavorited,
      toggleFavorite,
      cardImageUrl,
      movieCardVariantProps,
      variantGroupKey,
      visibleVariantItems,
      isVariantGroupExpanded,
      toggleVariantGroup,
      actorCardName,
      actorCardSubtitle,
      actorCardMeta,
      actorCardAvatar,
      actorCardSubscriptionId,
      actorCardSubscribed,
      actorCardBadges,
      collections,
      collectionsLoading,
      editingCollectionId,
      collectionForm,
      loadCollections,
      resetCollectionForm,
      editCollection,
      saveCollection,
      removeCollection,
      enrichFavoriteActor,
    }
  }
}
</script>

<style scoped>
.favorites-page {
  --page-top-space: 38px;
  min-height: 100dvh;
}

.curate-header {
  margin-bottom: 32px;
}

.curate-header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin: 0 0 22px;
  text-align: left;
}

.curate-copy {
  min-width: 0;
}

.curate-title {
  font-size: var(--page-title-size);
  font-weight: var(--page-title-weight);
  line-height: var(--page-title-line);
  letter-spacing: 0;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.curate-stats {
  font-size: var(--type-body);
  color: var(--text-muted);
  margin-bottom: 6px;
}

.instance-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--type-control);
}

.curate-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex: 0 0 auto;
}

.collection-manager {
  margin: 0 0 22px;
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--surface-card);
  text-align: left;
}

.collection-manager-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.collection-manager h2 {
  margin: 0;
  font-size: var(--type-card-title);
  letter-spacing: 0;
}

.collection-manager p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.collection-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr) auto auto;
  gap: 8px;
  margin-bottom: 10px;
}

.collection-form input {
  min-width: 0;
  min-height: 36px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--surface-control);
  color: var(--text-primary);
  font: inherit;
  outline: none;
}

.btn-mini {
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-control);
  background: var(--surface-control);
  color: var(--text-primary);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 650;
}

.btn-mini.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--text-on-accent);
}

.btn-mini.danger {
  color: #ff375f;
}

.btn-mini.active {
  background: var(--text-primary);
  border-color: var(--text-primary);
  color: var(--text-on-accent);
}

.btn-mini:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.collection-list {
  display: grid;
  gap: 6px;
}

.collection-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-control);
  background: var(--surface-control);
}

.collection-row div:first-child {
  min-width: 0;
}

.collection-row strong,
.collection-row span {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collection-row span,
.collection-empty {
  color: var(--text-secondary);
  font-size: 12px;
}

.collection-actions {
  display: flex;
  gap: 6px;
  flex: 0 0 auto;
}

/* Segmented Control - Apple Look */
.segmented-control {
  display: inline-flex;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: 14px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-light);
  flex-wrap: wrap;
  justify-content: center;
}

.segment-item {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  padding: 8px 20px;
  font-size: var(--type-control);
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.segment-item:hover {
  color: var(--text-primary);
}

.segment-item.active {
  background: var(--white-10);
  color: var(--text-primary);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  border: 1px solid var(--border-light);
}

.tab-badge {
  font-size: var(--type-badge);
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 500;
}

.segment-item.active .tab-badge {
  background: rgba(255, 255, 255, 0.15);
}

.curate-content {
  margin-top: 28px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

.favorites-grid-loading {
  opacity: 0.5;
}

.favorite-selectable {
  position: relative;
}

.favorites-grid.is-editing :deep(.apple-video-card),
.favorite-selectable.selected :deep(.actor-portrait-card) {
  outline: 2px solid rgba(var(--accent-rgb), 0.82);
  outline-offset: 3px;
}

.select-check {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(255,255,255,0.68);
  border-radius: 50%;
  background: rgba(20,20,24,0.42);
  box-shadow: 0 10px 22px rgba(0,0,0,0.18);
  cursor: pointer;
}

.select-check--actor {
  top: 12px;
  right: 12px;
}

.select-check span,
.entity-select-dot {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.9);
  border-radius: 50%;
}

.favorite-selectable.selected .select-check span,
.entity-bubble.selected .entity-select-dot {
  border-color: var(--accent);
  background: var(--accent);
  box-shadow: inset 0 0 0 3px #fff;
}

/* ===== 非影片收藏区 ===== */
.entity-section {
  margin-top: 20px;
}

.actor-favorites-section {
  margin-bottom: 34px;
}

.actor-favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 18px;
}

.section-label {
  font-size: var(--type-control);
  color: var(--text-muted);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.entity-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.entity-bubble {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-card);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
  font: inherit;
  text-align: left;
}

.entity-bubble:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-light);
  transform: translateY(-2px);
}

.entity-bubble.selected {
  border-color: var(--accent);
  background: rgba(var(--accent-rgb), 0.12);
}

.entity-name {
  font-size: var(--type-body);
  font-weight: 600;
  color: var(--text-primary);
}

.entity-type-tag {
  font-size: var(--type-badge);
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.entity-fav-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: none;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FF375F;
  cursor: pointer;
  opacity: 0.6;
  transition: all 0.2s;
  padding: 0;
}

.entity-fav-btn:hover {
  opacity: 1;
  transform: scale(1.15);
}

.entity-select-dot {
  display: inline-block;
  flex: 0 0 auto;
}

/* ===== 空状态 ===== */
.curate-empty {
  padding: 120px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: 24px;
  opacity: 0.4;
}

.curate-empty h3 {
  font-size: var(--type-section-title);
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
  letter-spacing: 0;
}

.curate-empty p {
  color: var(--text-muted);
  margin-bottom: 40px;
  font-size: var(--type-card-title);
}

.btn-explore {
  background: var(--text-primary);
  color: var(--text-on-accent);
  border: none;
  padding: 14px 48px;
  border-radius: 24px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s var(--ease-pro);
}

.btn-explore:hover {
  transform: scale(1.05);
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

/* Skeleton loading */
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border);
}

.skeleton-cover {
  width: 100%;
  aspect-ratio: 3/4;
  background: var(--bg-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-info {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  background: var(--bg-secondary);
  animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-line.w-60 { width: 60%; margin: 0 auto; }
.skeleton-line.w-80 { width: 80%; margin: 0 auto; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@media (max-width: 768px) {
  .favorites-page { --page-top-space: 40px; }
  .curate-title { font-size: var(--page-title-size-mobile); }
  .favorites-grid {
    grid-template-columns: repeat(auto-fit, minmax(var(--video-grid-min-mobile), 1fr));
    gap: var(--video-grid-gap-mobile) !important;
  }
  .actor-favorites-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 14px; }
  .segment-item {
    min-height: 44px;
    padding: 8px 14px;
    font-size: var(--type-caption);
  }
  .entity-bubble {
    min-height: 44px;
  }
  .entity-fav-btn {
    width: 44px;
    height: 44px;
  }
  .collection-form,
  .collection-row,
  .collection-manager-head {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }
  .collection-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .curate-header-main {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  .curate-toolbar {
    justify-content: center;
  }
}
</style>
