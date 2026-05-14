<template>
  <div class="app-layout">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <!-- 左侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="logo-text">JavHub</span>
        </div>
        <button class="collapse-btn" type="button" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
            <path v-if="sidebarCollapsed" d="M9 18l6-6-6-6"/>
            <path v-else d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <component :is="item.icon" />
          <span v-if="!sidebarCollapsed" class="nav-text">{{ item.label }}</span>
          <span v-if="!sidebarCollapsed && item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="!sidebarCollapsed" class="version">v0.1.0</div>
      </div>
    </aside>

    <!-- 移动端底部导航 -->
    <nav class="bottom-nav">
      <router-link
        v-for="item in bottomNavItems"
        :key="item.path"
        :to="item.path"
        class="bottom-nav-item"
        :class="{ active: $route.path === item.path }"
      >
        <component :is="item.icon" />
        <span>{{ item.label }}</span>
      </router-link>
      <button
        class="bottom-nav-item bottom-nav-more"
        type="button"
        :class="{ active: mobileMoreOpen || isMoreRoute }"
        aria-haspopup="dialog"
        :aria-expanded="mobileMoreOpen"
        @click="mobileMoreOpen = !mobileMoreOpen"
      >
        <component :is="IconList" />
        <span>更多</span>
      </button>
    </nav>

    <transition name="mobile-more">
      <div v-if="mobileMoreOpen" class="mobile-more-overlay" @click.self="mobileMoreOpen = false">
        <div class="mobile-more-sheet" role="dialog" aria-label="更多功能">
          <div class="mobile-more-grabber"></div>
          <div class="mobile-more-grid">
            <router-link
              v-for="item in mobileMoreItems"
              :key="item.path"
              :to="item.path"
              class="mobile-more-item"
              :class="{ active: $route.path === item.path }"
              @click="mobileMoreOpen = false"
            >
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </router-link>
          </div>
        </div>
      </div>
    </transition>

    <!-- 主内容区 -->
    <main id="main-content" class="main-content" tabindex="-1">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <keep-alive :include="['Search', 'Genres', 'Favorites', 'Subscriptions', 'DiscoveryDetail', 'InventoryActor', 'SupplementManagement']">
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>

    <!-- 全局影片详情弹窗 -->
    <VideoModal
      v-if="modalState.selectedVideo"
      :visible="modalState.visible"
      :video="modalState.selectedVideo"
      @close="closeVideoModal"
      @download="handleDownload"
      @navigate="handleNavigate"
    />

    <!-- 全局 Toast 提示 -->
    <ToastCapsule
      :visible="toast.visible"
      :message="toast.message"
      :show-organize="toast.showOrganize"
      @close="toast.visible = false"
      @organize="handleOrganize"
    />

    <ConfirmDialog />
  </div>
</template>

<script>
import { h, ref, defineComponent, watch, onMounted, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VideoModal from './components/VideoModal.vue'
import ToastCapsule from './components/ToastCapsule.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import { modalState, closeVideoModal, openVideoModal, interruptModal, resumeModal } from './utils/modalState'
import { favoriteState } from './utils/favoriteState'
import api from './api'
import { ElMessage } from 'element-plus'

// Icon components (inline SVG)
const IconHome = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z' }), h('polyline', { points: '9 22 9 12 15 12 15 22' })]) })
const IconSearch = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('circle', { cx: '11', cy: '11', r: '8' }), h('path', { d: 'm21 21-4.35-4.35' })]) })
const IconGenres = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M4 19.5A2.5 2.5 0 016.5 17H20' }), h('path', { d: 'M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z' })]) })
const IconDownload = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }), h('polyline', { points: '7 10 12 15 17 10' }), h('line', { x1: '12', y1: '15', x2: '12', y2: '3' })]) })
const IconList = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('line', { x1: '8', y1: '6', x2: '21', y2: '6' }), h('line', { x1: '8', y1: '12', x2: '21', y2: '12' }), h('line', { x1: '8', y1: '18', x2: '21', y2: '18' }), h('line', { x1: '3', y1: '6', x2: '3.01', y2: '6' }), h('line', { x1: '3', y1: '12', x2: '3.01', y2: '12' }), h('line', { x1: '3', y1: '18', x2: '3.01', y2: '18' })]) })
const IconParse = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z' }), h('polyline', { points: '14 2 14 8 20 8' }), h('line', { x1: '16', y1: '13', x2: '8', y2: '13' }), h('line', { x1: '16', y1: '17', x2: '8', y2: '17' }), h('polyline', { points: '10 9 9 9 8 9' })]) })
const IconStar = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2' }), h('circle', { cx: '9', cy: '7', r: '4' }), h('path', { d: 'M23 21v-2a4 4 0 00-3-3.87' }), h('path', { d: 'M16 3.13a4 4 0 010 7.75' })]) })
const IconHeart = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z' })]) })
const IconSettings = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('circle', { cx: '12', cy: '12', r: '3' }), h('path', { d: 'M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z' })]) })
const IconInventory = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5' })]) })
const IconNormalize = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z' })]) })
const IconTranslate = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M5 8l6 6' }), h('path', { d: 'M4 14l6-6 2-2' }), h('path', { d: 'M2 5h12' }), h('path', { d: 'M7 2v3' }), h('path', { d: 'M22 22l-5-10-5 10' }), h('path', { d: 'M14 18h6' })]) })
const IconSupplement = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' }), h('circle', { cx: '12', cy: '12', r: '3' })]) })
const IconOperations = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [h('path', { d: 'M3 3v18h18' }), h('path', { d: 'M7 15l3-3 3 2 5-7' }), h('path', { d: 'M18 7h-4' }), h('path', { d: 'M18 7v4' })]) })

export default {
  name: 'App',
  components: { VideoModal, ToastCapsule, ConfirmDialog },
  setup() {
    const sidebarCollapsed = ref(false)
    const mobileMoreOpen = ref(false)
    const route = useRoute()
    const router = useRouter()

    // Toast state
    const toast = reactive({
      visible: false,
      message: '',
      showOrganize: false,
      timer: null
    })

    const showToast = (message, showOrganize = false) => {
      if (toast.timer) clearTimeout(toast.timer)
      toast.message = message
      toast.showOrganize = showOrganize
      toast.visible = true
      toast.timer = setTimeout(() => {
        toast.visible = false
      }, 4000)
    }

    const handleOrganize = () => {
      toast.visible = false
      router.push('/favorites')
    }

    // 监听收藏状态变化
    favoriteState.subscribe(({ is_favorited }) => {
      if (is_favorited) {
        showToast('已加入收藏', true)
      }
    })

    onMounted(() => {
      favoriteState.init()
    })

    // 监听路由变化，处理弹窗恢复
    watch(() => route.path, (newPath) => {
      mobileMoreOpen.value = false
      if (newPath === modalState.openedOnRoute && modalState.interrupted) {
        resumeModal()
      }
    })

    const navItems = computed(() => [
      { path: '/operations', label: '运营总览', icon: IconOperations },
      { path: '/genres', label: '个性推荐', icon: IconGenres },
      { path: '/search', label: '影片检索', icon: IconSearch },
      { path: '/parse', label: '磁链解析', icon: IconParse },
      { path: '/favorites', label: '我的收藏', icon: IconHeart },
      { path: '/subscription', label: '订阅演员', icon: IconStar },
      { path: '/inventory', label: '库存对比', icon: IconInventory },
      { path: '/normalize', label: '演员映射', icon: IconNormalize },
      { path: '/translations', label: '翻译作业', icon: IconTranslate },
      { path: '/supplement', label: '补全管理', icon: IconSupplement },
      { path: '/downloads', label: '下载管理', icon: IconHome },
      { path: '/settings', label: '设置', icon: IconSettings },
    ])

    const bottomNavItems = computed(() => [
      { path: '/operations', label: '总览', icon: IconOperations },
      { path: '/genres', label: '推荐', icon: IconGenres },
      { path: '/search', label: '检索', icon: IconSearch },
      { path: '/downloads', label: '下载', icon: IconHome },
    ])

    const mobileMoreItems = computed(() => [
      { path: '/favorites', label: '我的收藏', icon: IconHeart },
      { path: '/parse', label: '磁链解析', icon: IconParse },
      { path: '/subscription', label: '订阅演员', icon: IconStar },
      { path: '/inventory', label: '库存对比', icon: IconInventory },
      { path: '/normalize', label: '演员映射', icon: IconNormalize },
      { path: '/translations', label: '翻译作业', icon: IconTranslate },
      { path: '/supplement', label: '补全管理', icon: IconSupplement },
      { path: '/settings', label: '设置', icon: IconSettings },
    ])

    const isMoreRoute = computed(() => mobileMoreItems.value.some(item => route.path === item.path))

    const handleDownload = async (magnet) => {
      try {
        await api.createDownload({
          content_id: modalState.selectedVideo.content_id || modalState.selectedVideo.dvd_id,
          title: modalState.selectedVideo.title_en,
          magnet: magnet.magnet || magnet
        })
        ElMessage.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
      }
    }

    const handleNavigate = async ({ type, item }) => {
      // 在跳转前，暂时隐藏（中断）弹窗
      interruptModal()

      if (type === 'category') {
        // 题材跳转
        try {
          const resp = await api.listCategories()
          const categories = Array.isArray(resp.data) ? resp.data : (resp.data.data || [])
          const cat = categories.find(c => (c.name_en || c.name_ja || c.name) === (item.name_en || item.name_ja || item.name))
          if (cat) {
            router.push({
              name: 'DiscoveryDetail',
              params: { type: 'category', value: cat.id },
              query: { returnTo: 'video' }
            })
          }
        } catch (e) { console.error(e) }
      } else if (type === 'actress') {
        const name = item.name_kanji || item.name_romaji || item.name_en || ''
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'actress', value: name },
          query: { returnTo: 'video' }
        })
      } else if (type === 'maker') {
        const name = item.name_en || item.name_ja || ''
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'maker', value: name },
          query: { returnTo: 'video' }
        })
      } else if (type === 'series') {
        const name = item.name_en || item.name_ja || ''
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'series', value: name },
          query: { returnTo: 'video' }
        })
      }
    }

    return {
      sidebarCollapsed,
      mobileMoreOpen,
      IconList,
      navItems,
      bottomNavItems,
      mobileMoreItems,
      isMoreRoute,
      toast,
      modalState,
      closeVideoModal,
      handleDownload,
      handleNavigate,
      handleOrganize
    }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--bg-primary);
}

/* ===== Sidebar ===== */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--surface-nav);
  backdrop-filter: blur(26px) saturate(150%);
  -webkit-backdrop-filter: blur(26px) saturate(150%);
  border-right: 1px solid var(--surface-nav-border);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, min-width 0.3s ease, background 0.3s ease;
  z-index: var(--z-nav);
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px;
  border-bottom: 1px solid var(--surface-nav-border);
  min-height: 72px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
  color: var(--text-primary);
}

.logo-text {
  font-size: 17px;
  font-weight: 650;
  color: var(--text-primary);
  white-space: nowrap;
  letter-spacing: -0.02em;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  transition: var(--transition);
  flex-shrink: 0;
}
.collapse-btn:hover { color: var(--text-primary); background: var(--surface-control-hover); }
.collapse-btn:focus-visible { outline: 3px solid rgba(var(--accent-rgb), 0.18); outline-offset: 2px; }

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: var(--radius-control);
  color: var(--text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}
.nav-item:hover {
  background: var(--surface-control-hover);
  color: var(--text-primary);
}
.nav-item.active {
  background: var(--nav-active-bg);
  color: var(--text-primary);
  border: 1px solid var(--active-border);
}
.nav-item.active::before {
  display: none;
}
.nav-item svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}
.nav-item.active svg { filter: none; }
.nav-item:focus-visible {
  outline: 3px solid rgba(var(--accent-rgb), 0.18);
  outline-offset: 2px;
}

.nav-badge {
  margin-left: auto;
  background: var(--surface-control-hover);
  color: var(--text-primary);
  border: 1px solid var(--border-light);
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--surface-nav-border);
}
.version { font-size: 11px; color: var(--text-muted); text-align: center; }

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-width: 0;
  background: var(--bg-primary);
}

.main-content:focus {
  outline: none;
}

/* ===== Bottom Nav (Mobile) ===== */
.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--surface-nav);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-top: 1px solid var(--border-light);
  z-index: var(--z-nav);
  padding: 8px 0 env(safe-area-inset-bottom, 8px);
}

.bottom-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 10px;
  font-weight: 500;
  padding: 6px 0;
  min-height: 52px;
  transition: all 0.25s ease;
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}
.bottom-nav-item svg { width: 22px; height: 22px; transition: transform 0.2s ease; }
.bottom-nav-item:hover { color: var(--text-primary); }
.bottom-nav-item:hover svg { transform: translateY(-1px); }
.bottom-nav-item.active { color: var(--text-primary); }
.bottom-nav-item.active svg { filter: none; }

.mobile-more-overlay {
  display: none;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .bottom-nav { display: flex; }
  .mobile-more-overlay {
    position: fixed;
    inset: 0;
    z-index: var(--z-sheet);
    display: flex;
    align-items: flex-end;
    background: var(--surface-scrim);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    padding: 0 12px calc(74px + env(safe-area-inset-bottom, 0px));
  }
  .mobile-more-sheet {
    width: 100%;
    padding: 10px 10px 14px;
    border: 1px solid var(--border-light);
    border-radius: 22px;
    background: var(--material-glass-sheet);
    box-shadow: var(--shadow-sheet);
  }
  .mobile-more-grabber {
    width: 38px;
    height: 4px;
    margin: 0 auto 12px;
    border-radius: 999px;
    background: var(--border-light);
  }
  .mobile-more-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .mobile-more-item {
    display: flex;
    min-width: 0;
    min-height: 72px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: var(--material-glass-subtle);
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
  }
  .mobile-more-item svg {
    width: 22px;
    height: 22px;
  }
  .mobile-more-item.active {
    color: var(--text-primary);
    border-color: var(--border-light);
    background: var(--material-glass-elevated);
  }
  .mobile-more-enter-active,
  .mobile-more-leave-active {
    transition: opacity 180ms var(--ease-pro);
  }
  .mobile-more-enter-active .mobile-more-sheet,
  .mobile-more-leave-active .mobile-more-sheet {
    transition: transform 220ms var(--ease-pro);
  }
  .mobile-more-enter-from,
  .mobile-more-leave-to {
    opacity: 0;
  }
  .mobile-more-enter-from .mobile-more-sheet,
  .mobile-more-leave-to .mobile-more-sheet {
    transform: translateY(16px);
  }
}
</style>
