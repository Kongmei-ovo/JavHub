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
            :disabled="!editMode && visibleFavoriteCount === 0"
            @click="toggleEditMode"
          >
            {{ editMode ? '完成' : '编辑' }}
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

      <div
        v-if="editMode"
        class="selection-bar"
        role="toolbar"
        aria-label="收藏批量操作"
      >
        <div class="selection-summary">
          <strong>{{ selectedFavoriteCount }}</strong>
          <span>已选择 · 当前视图 {{ visibleFavoriteCount }}</span>
        </div>
        <div class="selection-actions">
          <button class="btn-mini" type="button" :disabled="visibleFavoriteCount === 0 || allVisibleSelected" @click="selectAllVisibleFavorites">全选</button>
          <button class="btn-mini" type="button" :disabled="selectedFavoriteCount === 0" @click="clearFavoriteSelection">清空</button>
          <button class="btn-mini danger" type="button" :disabled="selectedFavoriteCount === 0" @click="removeSelectedFavorites">
            取消收藏 {{ selectedFavoriteCount || '' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <AppleSkeleton
      v-if="videoLoading"
      class="favorites-grid favorites-grid-loading"
      variant="gallery"
      :items="8"
      columns="repeat(auto-fill, minmax(180px, 1fr))"
      label="收藏影片加载中"
    />

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

      <div v-if="(activeTab === 'video' || activeTab === 'all') && videoHasMore" class="load-more-row">
        <button class="btn-mini" type="button" :disabled="videoLoadingMore" @click="loadMoreVideos">
          {{ videoLoadingMore ? '加载中...' : '继续加载影片' }}
          <span>{{ videoItems.length }} / {{ videoTotal }}</span>
        </button>
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
      <AppleEmptyState
        v-if="displayVideoItems.length === 0 && actorFavoriteItems.length === 0 && otherEntityItems.length === 0"
        :title="emptyTitle"
        :description="emptyDescription"
        :next-step="emptyNextStep"
        :action-label="emptyActionLabel"
        :secondary-action-label="emptySecondaryActionLabel"
        @action="handleEmptyAction"
        @secondary-action="handleEmptySecondaryAction"
      >
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
        </template>
      </AppleEmptyState>
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
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import { movieCardVariantProps, variantGroupKey, visibleVariantItems } from '../utils/videoVariantPresentation.js'

const TYPE_LABELS = {
  video: '影片',
  actress: '演员',
  category: '题材',
  series: '系列',
  maker: '工作室',
}
const FAVORITE_VIDEO_PAGE_SIZE = 48

export default {
  name: 'Favorites',
  components: { MovieCard, ActorPortraitCard, VariantGroupDisclosure, AppleSkeleton, AppleEmptyState },
  setup() {
    const router = useRouter()
    const activeTab = ref('all')
    const videoLoading = ref(false)
    const videoLoadingMore = ref(false)
    const videoItems = ref([])
    const videoTotal = ref(0)
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
      counts.video = videoTotal.value || videoItems.value.length || counts.video || 0
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

    // 分页加载完整影片数据，避免收藏多时一次性 fanout 所有详情请求
    const mapFavoriteVideo = (v) => ({
      entity_type: 'video',
      entity_id: v._favorite_entity_id || (v.service_code ? `${v.content_id || v.dvd_id}::${v.service_code}` : (v.content_id || v.dvd_id)),
      metadata: v,
      created_at: v._created_at
    })
    const loadVideos = async ({ reset = true } = {}) => {
      const loadingRef = reset ? videoLoading : videoLoadingMore
      loadingRef.value = true
      try {
        const offset = reset ? 0 : videoItems.value.length
        const resp = await api.getFavoriteVideosPage({ limit: FAVORITE_VIDEO_PAGE_SIZE, offset })
        const payload = resp.data || {}
        const rows = Array.isArray(payload) ? payload : (payload.data || [])
        const mapped = rows.map(mapFavoriteVideo)
        videoTotal.value = Number(payload.total ?? (reset ? mapped.length : videoItems.value.length + mapped.length))
        if (reset) {
          videoItems.value = mapped
        } else {
          const byId = new Map(videoItems.value.map(item => [String(item.entity_id), item]))
          mapped.forEach(item => { byId.set(String(item.entity_id), item) })
          videoItems.value = [...byId.values()]
        }
      } catch (e) {
        console.error('Failed to load favorite videos:', e)
      } finally {
        loadingRef.value = false
      }
    }
    const loadMoreVideos = () => loadVideos({ reset: false })
    const videoHasMore = computed(() => videoTotal.value > videoItems.value.length)

    const loadNonVideoFavoriteMetadata = async () => {
      try {
        await favoriteState.init()
        const types = [...new Set(state.items.map(item => item.entity_type).filter(type => type && type !== 'video'))]
        await favoriteState.loadMetadataForTypes(types)
      } catch (err) {
        console.error('Failed to load favorite metadata:', err)
      }
    }

    onMounted(() => {
      loadNonVideoFavoriteMetadata()
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
    const favoriteActorFromItem = (item) => {
      const metadata = item.metadata || {}
      return {
        id: item.entity_id,
        actress_id: item.entity_id,
        ...metadata,
        name: metadata.name || entityDisplayName(item) || String(item.entity_id),
      }
    }
    const actorFavoriteItems = computed(() => {
      if (activeTab.value !== 'all' && activeTab.value !== 'actress') return []
      return actorSourceItems.value.map(item => ({ ...item, actor: favoriteActorFromItem(item) }))
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
    const emptyNextStep = computed(() => (
      activeTab.value === 'all'
        ? '先浏览题材添加影片，或订阅演员让系统持续发现缺失作品。'
        : '切回全部收藏确认是否有其他类型，或去发现页添加当前分类内容。'
    ))
    const emptyActionLabel = computed(() => activeTab.value === 'all' ? '浏览题材' : '查看全部')
    const emptySecondaryActionLabel = computed(() => activeTab.value === 'all' ? '订阅演员' : '浏览题材')

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
    const handleEmptyAction = () => {
      if (activeTab.value === 'all') router.push('/entities')
      else setActiveTab('all')
    }
    const handleEmptySecondaryAction = () => {
      if (activeTab.value === 'all') router.push('/subscription')
      else router.push('/entities')
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
    const trimSelectionToVisibleFavorites = (items) => {
      if (selectedFavoriteKeys.value.size === 0) return
      const visibleKeys = new Set(items.map(favoriteKey))
      selectedFavoriteKeys.value = new Set([...selectedFavoriteKeys.value].filter(key => visibleKeys.has(key)))
    }
    watch(allVisibleFavoriteItems, trimSelectionToVisibleFavorites)
    const selectedFavoriteCount = computed(() => selectedFavoriteKeys.value.size)
    const visibleFavoriteCount = computed(() => allVisibleFavoriteItems.value.length)
    const allVisibleSelected = computed(() => (
      visibleFavoriteCount.value > 0 && allVisibleFavoriteItems.value.every(item => isSelected(item))
    ))
    const selectAllVisibleFavorites = () => {
      selectedFavoriteKeys.value = new Set(allVisibleFavoriteItems.value.map(favoriteKey))
    }
    const clearFavoriteSelection = () => {
      selectedFavoriteKeys.value = new Set()
    }
    const removeSelectedFavorites = async () => {
      const selectedItems = allVisibleFavoriteItems.value.filter(item => isSelected(item))
      for (const item of selectedItems) {
        await favoriteState.toggle(item.entity_type, item.entity_id)
      }
      selectedFavoriteKeys.value = new Set()
      await loadNonVideoFavoriteMetadata()
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

    return {
      state,
      count: favoriteState.count,
      activeTab,
      editMode,
      selectedFavoriteKeys,
      selectedFavoriteCount,
      visibleFavoriteCount,
      allVisibleSelected,
      tabs,
      videoLoading,
      videoLoadingMore,
      videoItems,
      videoTotal,
      videoHasMore,
      displayVideoItems,
      nonVideoItems,
      actorFavoriteItems,
      otherEntityItems,
      sectionLabel,
      instanceNote,
      emptyTitle,
      emptyDescription,
      emptyNextStep,
      emptyActionLabel,
      emptySecondaryActionLabel,
      typeLabel,
      entityDisplayName,
      navigateToEntity,
      navigateToActor,
      openVideo,
      openVideoModalFromMetadata,
      favoriteKey,
      isSelected,
      toggleFavoriteSelection,
      selectAllVisibleFavorites,
      clearFavoriteSelection,
      toggleEditMode,
      setActiveTab,
      handleEmptyAction,
      handleEmptySecondaryAction,
      handleFavoriteItemClick,
      removeSelectedFavorites,
      loadMoreVideos,
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
    }
  }
}
</script>

<style scoped src="../features/favorites/favorites.css"></style>
