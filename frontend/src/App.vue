<template>
  <div class="app-layout" :class="{ 'mobile-more-active': mobileMoreActive }">
    <a class="skip-link" href="#main-content" :inert="mobileMoreActive ? '' : undefined" :aria-hidden="mobileMoreActive ? 'true' : undefined" @click.prevent="focusMainContent">跳到主要内容</a>
    <aside class="sidebar material-L2" :class="{ collapsed: sidebarCollapsed }" :inert="mobileMoreActive ? '' : undefined" :aria-hidden="mobileMoreActive ? 'true' : undefined">
      <div class="sidebar-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="logo-text sidebar-copy" :aria-hidden="sidebarCollapsed ? 'true' : undefined">JavHub</span>
        </div>
        <div class="sidebar-header-actions">
          <button class="theme-toggle" type="button" :aria-label="isDarkMode ? '开灯' : '关灯'" :aria-pressed="isDarkMode" :title="isDarkMode ? '开灯' : '关灯'" @click="toggleAppTheme">
            <span class="theme-toggle__orb" :class="{ dark: isDarkMode }">
              <svg v-if="isDarkMode" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="15" height="15">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="15" height="15">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
              </svg>
            </span>
          </button>
          <button
            class="activity-toggle"
            type="button"
            aria-controls="activity-center-panel"
            :aria-pressed="activityCenterExpanded"
            :aria-label="activityCenterExpanded ? '收起活动中心' : '展开活动中心'"
            :title="activityCenterExpanded ? '收起活动中心' : '展开活动中心'"
            @click="toggleActivityCenter"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18">
              <path d="M4 14h4l2-8 4 14 2-6h4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <button
            class="collapse-btn"
            type="button"
            aria-controls="primary-navigation"
            aria-keyshortcuts="Meta+B Control+B"
            :aria-expanded="!sidebarCollapsed"
            :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            @click="sidebarCollapsed = !sidebarCollapsed"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
              <path v-if="sidebarCollapsed" d="M9 18l6-6-6-6"/>
              <path v-else d="M15 18l-6-6 6-6"/>
            </svg>
          </button>
        </div>
      </div>
      <nav class="sidebar-nav" aria-label="主导航" id="primary-navigation">
        <div v-for="group in navGroups" :key="group.label" class="nav-group">
          <div class="nav-group-label sidebar-copy" :aria-hidden="sidebarCollapsed ? 'true' : undefined">{{ group.label }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isNavItemActive(item.path) }"
            :aria-current="isNavItemActive(item.path) ? 'page' : undefined"
            :aria-label="sidebarCollapsed ? item.label : undefined"
            :title="sidebarCollapsed ? item.label : undefined"
            @click="focusMainContentFromNavigation"
          >
            <component :is="item.icon" />
            <span class="nav-text sidebar-copy" :aria-hidden="sidebarCollapsed ? 'true' : undefined">{{ item.label }}</span>
            <span v-if="item.badge" class="nav-badge sidebar-copy" :aria-hidden="sidebarCollapsed ? 'true' : undefined">{{ item.badge }}</span>
          </router-link>
        </div>
      </nav>
      <div class="sidebar-footer">
        <div class="version sidebar-copy" :aria-hidden="sidebarCollapsed ? 'true' : undefined">v{{ appVersion }}</div>
      </div>
    </aside>
    <nav class="bottom-nav" aria-label="移动端主导航" :inert="mobileMoreActive ? '' : undefined" :aria-hidden="mobileMoreActive ? 'true' : undefined">
      <router-link
        v-for="item in bottomNavItems"
        :key="item.path"
        :to="item.path"
        class="bottom-nav-item"
        :class="{ active: isNavItemActive(item.path) }"
        :aria-current="isNavItemActive(item.path) ? 'page' : undefined"
        @click="focusMainContentFromNavigation"
      >
        <component :is="item.icon" />
        <span>{{ item.label }}</span>
      </router-link>
      <button
        class="bottom-nav-item bottom-nav-activity"
        type="button"
        aria-controls="activity-center-panel"
        :aria-pressed="activityCenterExpanded"
        :aria-label="activityCenterExpanded ? '收起活动中心' : '展开活动中心'"
        @click="toggleActivityCenter"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M4 14h4l2-8 4 14 2-6h4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>活动</span>
      </button>
      <button
        ref="mobileMoreButtonRef"
        class="bottom-nav-item bottom-nav-more"
        type="button"
        :class="{ active: isMoreRoute, open: mobileMoreActive }"
        aria-haspopup="dialog"
        aria-controls="mobile-more-dialog"
        aria-keyshortcuts="Escape"
        :aria-expanded="mobileMoreActive"
        :aria-label="mobileMoreActive ? '关闭更多功能' : '打开更多功能'"
        :aria-current="isMoreRoute ? 'page' : undefined"
        @click="toggleMobileMore"
      >
        <component :is="IconList" />
        <span>更多</span>
      </button>
    </nav>
    <transition name="mobile-more" @after-leave="finishMobileMoreClose">
      <div v-if="mobileMoreOpen" class="mobile-more-overlay" @click.self="closeMobileMore({ restoreFocus: true })">
        <div
          ref="mobileMoreSheetRef"
          class="mobile-more-sheet"
          id="mobile-more-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-more-title"
          tabindex="-1"
          @keydown.esc.stop.prevent="closeMobileMore({ restoreFocus: true })"
          @keydown.tab="trapMobileMoreFocus"
        >
          <div class="mobile-more-grabber"></div>
          <div class="mobile-more-head">
            <h2 id="mobile-more-title">更多功能</h2>
            <button class="mobile-more-close" type="button" aria-keyshortcuts="Escape" aria-label="关闭更多面板" @click="closeMobileMore({ restoreFocus: true })"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M18 6L6 18M6 6l12 12" stroke-linecap="round"/></svg></button>
          </div>
          <button class="mobile-theme-toggle" type="button" :aria-pressed="isDarkMode" @click="toggleAppTheme">
            <span>{{ isDarkMode ? '开灯' : '关灯' }}</span>
            <span>{{ isDarkMode ? 'Light' : 'Dark' }}</span>
          </button>
          <nav class="mobile-more-grid" aria-label="更多功能导航">
            <router-link
              v-for="item in mobileMoreItems"
              :key="item.path"
              :to="item.path"
              class="mobile-more-item"
              :class="{ active: isNavItemActive(item.path) }"
              :aria-current="isNavItemActive(item.path) ? 'page' : undefined"
              @click="closeMobileMore({ focusMain: true })"
            >
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </router-link>
          </nav>
        </div>
      </div>
    </transition>
    <main id="main-content" class="main-content" tabindex="-1" aria-label="应用内容" :inert="mobileMoreActive ? '' : undefined" :aria-hidden="mobileMoreActive ? 'true' : undefined">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <keep-alive :include="['Search', 'Genres', 'Favorites', 'Subscription', 'DiscoveryDetail', 'Actor', 'InventoryActor', 'SupplementManagement']">
            <component :is="Component" />
          </keep-alive>
        </transition>
      </router-view>
    </main>
    <ActivityCenter
      v-model:expanded="activityCenterExpanded"
      :inert="mobileMoreActive ? '' : undefined"
      :aria-hidden="mobileMoreActive ? 'true' : undefined"
    />
    <VideoModal
      v-if="modalState.selectedVideo"
      :visible="modalState.visible"
      :video="modalState.selectedVideo"
      @close="closeVideoModal"
      @download="handleDownload"
      @navigate="handleNavigate"
    />
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
import { ref, nextTick, defineAsyncComponent, watch, onMounted, onUnmounted, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToastCapsule from './components/ToastCapsule.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import ActivityCenter from './features/activity/ActivityCenter.vue'
import { modalState, closeVideoModal, interruptModal, resumeModal } from './utils/modalState'
import { favoriteState } from './utils/favoriteState'
import api from './api'
import { ElMessage, MESSAGE_EVENT } from './utils/message.js'
import { isDarkTheme, restoreTheme, toggleTheme } from './assets/themes.js'
import { IconList, bottomNavItems, mobileMoreItems, navActivePaths, navGroups } from './appNavigation.js'
const VideoModal = defineAsyncComponent(() => import('./components/VideoModal.vue'))
const appVersion = import.meta.env.VITE_APP_VERSION || 'dev'
const mobileMoreFocusableSelector = [
  'a[href]',
  'button:not(:disabled)',
].join(',')
export default {
  name: 'App',
  components: { VideoModal, ToastCapsule, ConfirmDialog, ActivityCenter },
  setup() {
    const sidebarCollapsed = ref(false)
    const mobileMoreOpen = ref(false)
    const mobileMoreClosing = ref(false)
    const activityCenterExpanded = ref(false)
    const mobileMoreActive = computed(() => mobileMoreOpen.value || mobileMoreClosing.value)
    const mobileMoreButtonRef = ref(null)
    const mobileMoreSheetRef = ref(null)
    let mobileMoreAfterCloseFocus = null
    const mobileShellBreakpoint = typeof window === 'undefined' ? null : window.matchMedia?.('(max-width: 768px)')
    const currentTheme = ref(restoreTheme())
    const route = useRoute()
    const router = useRouter()
    const normalizedRoutePath = computed(() => route.path.replace(/\/+$/, '') || '/')
    const isDarkMode = computed(() => isDarkTheme(currentTheme.value))
    const toggleAppTheme = () => { currentTheme.value = toggleTheme(currentTheme.value) }
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
      toast.timer = setTimeout(() => { toast.visible = false }, 4000)
    }
    const handleOrganize = () => {
      toast.visible = false
      router.push('/favorites')
    }
    const unsubscribeFavoriteState = favoriteState.subscribe(({ is_favorited }) => {
      if (is_favorited) {
        showToast('已加入收藏', true)
      }
    })
    const handleAppMessage = (event) => {
      const detail = event?.detail || {}
      showToast(detail.message || '', false)
    }
    const toggleSidebarFromKeyboard = (event) => { if (mobileMoreActive.value || event.repeat || event.altKey || event.shiftKey || event.key.toLowerCase() !== 'b' || !(event.metaKey || event.ctrlKey) || event.target?.closest?.('input, textarea, select, [contenteditable="true"]')) return; event.preventDefault(); sidebarCollapsed.value = !sidebarCollapsed.value }
    onMounted(() => {
      favoriteState.init()
      syncActiveNavigationIntoView()
      window.addEventListener(MESSAGE_EVENT, handleAppMessage); window.addEventListener('keydown', toggleSidebarFromKeyboard)
      mobileShellBreakpoint?.addEventListener?.('change', closeMobileMoreOutsideMobile)
    })
    onUnmounted(() => {
      unsubscribeFavoriteState()
      window.removeEventListener(MESSAGE_EVENT, handleAppMessage)
      window.removeEventListener('keydown', toggleSidebarFromKeyboard)
      mobileShellBreakpoint?.removeEventListener?.('change', closeMobileMoreOutsideMobile)
    })
    watch(() => route.fullPath, (newPath) => {
      syncActiveNavigationIntoView()
      if (mobileMoreOpen.value) closeMobileMore({ focusMain: true })
      if (newPath === modalState.openedOnRoute && modalState.interrupted) {
        resumeModal()
      }
    })
    const isNavItemActive = (path) => {
      const currentPath = normalizedRoutePath.value
      const activePaths = navActivePaths[path] || [path]
      return activePaths.some(activePath => currentPath === activePath || currentPath.startsWith(`${activePath}/`))
    }
    const isMoreRoute = computed(() => mobileMoreItems.some(item => isNavItemActive(item.path)))
    const toggleMobileMore = () => {
      if (mobileMoreOpen.value) {
        closeMobileMore({ restoreFocus: true })
        return
      }
      mobileMoreClosing.value = false
      mobileMoreOpen.value = true
    }
    const toggleActivityCenter = () => { activityCenterExpanded.value = !activityCenterExpanded.value }
    const focusMainContent = ({ resetScroll = false } = {}) => nextTick(() => requestAnimationFrame(() => { const main = document.getElementById('main-content'); if (resetScroll) main?.scrollTo?.({ top: 0, left: 0 }); main?.focus({ preventScroll: true }) }))
    const focusMainContentFromNavigation = (event) => { if (event.detail !== 0) return; focusMainContent({ resetScroll: true }) }
    const closeMobileMore = ({ restoreFocus = false, focusMain = false } = {}) => {
      if (!mobileMoreOpen.value) return
      mobileMoreAfterCloseFocus = restoreFocus ? 'trigger' : focusMain ? 'main' : null
      mobileMoreClosing.value = true
      mobileMoreOpen.value = false
    }
    const finishMobileMoreClose = () => {
      mobileMoreClosing.value = false
      if (mobileMoreAfterCloseFocus === 'trigger') nextTick(() => mobileMoreButtonRef.value?.focus({ preventScroll: true }))
      if (mobileMoreAfterCloseFocus === 'main') focusMainContent()
      mobileMoreAfterCloseFocus = null
    }
    const closeMobileMoreOutsideMobile = ({ matches }) => { if (!matches) closeMobileMore({ focusMain: true }) }
    const mobileMoreFocusableElements = () => {
      return Array.from(mobileMoreSheetRef.value?.querySelectorAll(mobileMoreFocusableSelector) || [])
        .filter(element => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true')
    }
    const syncActiveNavigationIntoView = () => nextTick(() => requestAnimationFrame(() => document.querySelectorAll('.sidebar-nav .nav-item.active, .mobile-more-grid .mobile-more-item.active').forEach(element => element.scrollIntoView?.({ block: 'nearest', inline: 'nearest' }))))
    const focusMobileMoreControl = (element) => { element?.focus?.({ preventScroll: true }); element?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' }) }
    const trapMobileMoreFocus = (event) => {
      if (!mobileMoreOpen.value) return
      const focusable = mobileMoreFocusableElements()
      if (!focusable.length) {
        event.preventDefault()
        mobileMoreSheetRef.value?.focus({ preventScroll: true })
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const activeIndex = focusable.indexOf(document.activeElement)
      if (activeIndex === -1) {
        event.preventDefault()
        focusMobileMoreControl(event.shiftKey ? last : first)
        return
      }
      if (event.shiftKey && activeIndex === 0) {
        event.preventDefault()
        focusMobileMoreControl(last)
      } else if (!event.shiftKey && activeIndex === focusable.length - 1) {
        event.preventDefault()
        focusMobileMoreControl(first)
      }
    }
    watch(mobileMoreOpen, async (isOpen) => {
      if (!isOpen) return
      await nextTick()
      mobileMoreSheetRef.value?.focus({ preventScroll: true })
      syncActiveNavigationIntoView()
    })
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
        const name = item.name_ja || item.name_en || item.name || ''
        const value = item.id || name
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'category', value: String(value) },
          query: { returnTo: 'video', ...(name ? { name } : {}) }
        })
      } else if (type === 'actress') {
        const name = item.name_kanji || item.name_romaji || item.name_en || ''
        const value = item.id || item.actress_id || name
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'actress', value: String(value) },
          query: { returnTo: 'video', ...(name ? { name } : {}) }
        })
      } else if (type === 'maker') {
        const name = item.name_ja || item.name_en || item.name || ''
        const value = item.id || name
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'maker', value: String(value) },
          query: { returnTo: 'video', ...(name ? { name } : {}) }
        })
      } else if (type === 'label') {
        const name = item.name_ja || item.name_en || item.name || ''
        const value = item.id || name
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'label', value: String(value) },
          query: { returnTo: 'video', ...(name ? { name } : {}) }
        })
      } else if (type === 'series') {
        const name = item.name_ja || item.name_en || item.name || ''
        const value = item.id || name
        router.push({
          name: 'DiscoveryDetail',
          params: { type: 'series', value: String(value) },
          query: { returnTo: 'video', ...(name ? { name } : {}) }
        })
      }
    }
    return {
      sidebarCollapsed,
      mobileMoreOpen,
      mobileMoreClosing,
      mobileMoreActive,
      activityCenterExpanded,
      mobileMoreButtonRef,
      mobileMoreSheetRef,
      IconList,
      navGroups,
      bottomNavItems,
      mobileMoreItems,
      isMoreRoute,
      isNavItemActive,
      focusMainContent,
      focusMainContentFromNavigation,
      toggleMobileMore,
      toggleActivityCenter,
      closeMobileMore,
      finishMobileMoreClose,
      trapMobileMoreFocus,
      appVersion,
      currentTheme,
      isDarkMode,
      toggleAppTheme,
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
  --mobile-bottom-nav-height: 70px;
  --mobile-bottom-nav-offset: max(10px, env(safe-area-inset-bottom, 0px));
  --mobile-bottom-nav-reserve: calc(var(--mobile-bottom-nav-height) + var(--mobile-bottom-nav-offset) + 12px);
  display: flex;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--bg-primary);
  position: relative;
  isolation: isolate;
}
.app-layout::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--app-backdrop-texture);
  pointer-events: none;
  z-index: var(--z-base);
}
.skip-link:focus-visible {
  outline: none;
  color: var(--text-primary);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  border: 1px solid var(--glass-active-border);
  box-shadow: var(--glass-active-shadow), var(--focus-ring);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transform: translateY(0);
}
/* ===== Sidebar ===== */
.sidebar {
  --c1-sidebar-width: var(--sidebar-width, 224px);
  --c1-sidebar-collapsed-width: calc(var(--space-10, 44px) + var(--space-5, 20px));
  --c1-sidebar-gutter: var(--space-3, 12px);
  --c1-sidebar-copy-offset: calc(var(--space-1, 4px) * -1);
  --c1-sidebar-material-blur: var(--material-L2-blur, blur(34px));
  --c1-sidebar-material-vibrancy: var(--material-L2-vibrancy, saturate(1.14));
  --c1-sidebar-spring: var(--motion-spring, 280ms var(--ease-spring-soft, cubic-bezier(0.34, 1.56, 0.64, 1)));
  --c1-sidebar-fast: var(--motion-fast, 140ms var(--ease-pro, cubic-bezier(0.16, 1, 0.3, 1)));
  --c1-sidebar-standard: var(--motion-standard, 260ms var(--ease-pro, cubic-bezier(0.16, 1, 0.3, 1)));
  --c1-sidebar-hairline: var(--surface-specular-edge, var(--glass-specular-edge));
  width: var(--c1-sidebar-width);
  min-width: var(--c1-sidebar-width);
  height: calc(100dvh - (var(--app-chrome-inset) * 2));
  margin: var(--app-chrome-inset) 0 var(--app-chrome-inset) var(--app-chrome-inset);
  background: var(--surface-nav);
  backdrop-filter: var(--c1-sidebar-material-blur) var(--c1-sidebar-material-vibrancy);
  -webkit-backdrop-filter: var(--c1-sidebar-material-blur) var(--c1-sidebar-material-vibrancy);
  border: 1px solid var(--surface-nav-border);
  border-radius: var(--radius-sheet);
  box-shadow: var(--chrome-floating-shadow);
  display: flex;
  flex-direction: column;
  transition: transform var(--c1-sidebar-spring), opacity var(--c1-sidebar-fast);
  z-index: var(--z-nav);
  flex-shrink: 0;
  overflow: hidden;
  position: relative;
  isolation: isolate;
}
.sidebar::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background:
    var(--surface-specular-edge),
    var(--surface-noise);
  opacity: var(--surface-overlay-opacity);
  pointer-events: none;
  z-index: 0;
}
.sidebar::before {
  content: "";
  position: absolute;
  inset: 0 0 auto;
  height: 34px;
  border-radius: inherit;
  background: linear-gradient(to bottom, var(--bg-primary), transparent);
  opacity: 0.16;
  pointer-events: none;
  z-index: 1;
}
.sidebar.collapsed {
  width: var(--c1-sidebar-collapsed-width);
  min-width: var(--c1-sidebar-collapsed-width);
  transform: translateX(0) scaleX(0.995);
}
.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding-inline: var(--c1-sidebar-gutter);
}
.sidebar.collapsed .logo,
.sidebar.collapsed .theme-toggle,
.sidebar.collapsed .activity-toggle {
  inline-size: 0;
  width: 0;
  min-width: 0;
  padding-inline: 0;
  border: 0;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}
.sidebar.collapsed .sidebar-header-actions { gap: 0; }
.sidebar.collapsed :is(.sidebar-header-actions, .collapse-btn) { justify-content: center; }
.sidebar.collapsed .collapse-btn { width: 38px; height: 38px; }
.sidebar.collapsed .sidebar-nav { padding: 12px 8px; mask-image: linear-gradient(to bottom, transparent, currentColor 10px, currentColor calc(100% - 14px), transparent); }
.sidebar.collapsed .nav-group { gap: 6px; }
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 11px 0;
  gap: 0;
}
.sidebar.collapsed .nav-item.active::after {
  content: "";
  position: absolute;
  left: auto;
  right: 5px;
  width: 3px;
  height: 18px;
  border-radius: 999px;
  background: var(--active-indicator);
  opacity: 0.74;
  box-shadow: var(--glass-inner-shadow);
}
.sidebar.collapsed .nav-item.active:focus-visible { box-shadow: var(--glass-active-shadow), var(--focus-ring); }
.sidebar.collapsed .nav-item.active:focus-visible::after { opacity: 0.34; transform: scaleY(0.74); }
.sidebar-copy {
  opacity: 1;
  transform: translateX(0);
  transform-origin: left center;
  transition: transform var(--c1-sidebar-spring), opacity var(--c1-sidebar-fast);
  transition-delay: 60ms;
  will-change: transform, opacity;
}
.sidebar.collapsed .sidebar-copy {
  opacity: 0;
  transform: translateX(var(--c1-sidebar-copy-offset));
  transition-delay: 0ms;
  pointer-events: none;
}
.sidebar-header {
  position: relative;
  z-index: 1;
  display: flex; align-items: center;
  justify-content: space-between;
  padding: 20px 16px;
  min-height: 72px;
  overflow: hidden;
}
.sidebar-header::after {
  content: "";
  position: absolute;
  left: var(--c1-sidebar-gutter);
  right: var(--c1-sidebar-gutter);
  bottom: 0;
  height: 1px;
  background: var(--c1-sidebar-hairline);
  pointer-events: none;
}
.logo { display: flex; align-items: center; gap: 10px; overflow: hidden; color: var(--text-primary); transition: opacity var(--c1-sidebar-fast); }
.logo-text { font-size: 17px; font-weight: 650; color: var(--text-primary); white-space: nowrap; letter-spacing: 0; }
.sidebar-header-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 28px;
  padding: 3px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  color: var(--text-primary);
  cursor: pointer;
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--c1-sidebar-standard), opacity var(--c1-sidebar-fast);
}
.theme-toggle:hover {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}
.theme-toggle:focus-visible {
  outline: none;
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.theme-toggle:active {
  transform: translateY(0) scale(0.98);
}
.theme-toggle__orb {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  border: 1px solid var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
  transform: translateX(-4px);
  transition: transform var(--c1-sidebar-standard);
}
.theme-toggle__orb.dark { transform: translateX(4px); }
.activity-toggle,
.collapse-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  transition: transform var(--c1-sidebar-standard), opacity var(--c1-sidebar-fast);
  flex-shrink: 0;
}
.activity-toggle {
  width: 32px;
  height: 32px;
  justify-content: center;
}
.activity-toggle[aria-pressed="true"] {
  color: var(--text-primary);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  border: 1px solid var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
}
.activity-toggle:hover,
.collapse-btn:hover {
  color: var(--text-primary);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.activity-toggle:focus-visible,
.collapse-btn:focus-visible {
  outline: none;
  color: var(--text-primary);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.activity-toggle:active,
.collapse-btn:active {
  transform: scale(0.96);
}
.sidebar-nav {
  position: relative;
  z-index: 1;
  flex: 1; padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  -webkit-overflow-scrolling: touch;
  scroll-padding-block: 12px 16px;
  mask-image: linear-gradient(to bottom, transparent, currentColor 12px, currentColor calc(100% - 16px), transparent);
}
.nav-group { display: flex; flex-direction: column; gap: 4px; }
.nav-group-label { padding: 8px 14px 4px; color: var(--text-muted); font-size: 11px; font-weight: 700; letter-spacing: 0; }
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
  transition: transform var(--c1-sidebar-standard);
  white-space: nowrap;
  overflow: hidden;
  position: relative;
  border: 1px solid transparent;
  scroll-margin-block: 12px 16px;
}
.nav-item:hover {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.nav-item:active {
  transform: translateY(0) scale(0.985);
}
.nav-item.active {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  color: var(--text-primary);
  border: 1px solid var(--active-border);
  box-shadow: var(--glass-active-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  padding-left: 22px;
}
.nav-item.active:active {
  box-shadow: var(--glass-active-shadow);
}
.nav-item.active::before {
  display: none;
}
.nav-item.active::after { content: ""; position: absolute; left: 7px; width: 3px; height: 18px; border-radius: 999px; background: var(--active-indicator); opacity: 0.52; box-shadow: var(--glass-inner-shadow); pointer-events: none; transition: opacity var(--c1-sidebar-fast), transform var(--c1-sidebar-standard); }
.nav-item svg { width: 22px; height: 22px; flex-shrink: 0; transition: transform var(--c1-sidebar-standard); }
.nav-item.active svg { filter: none; }
.nav-item:focus-visible {
  outline: none;
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
  transform: translateY(-1px);
}
.nav-item.active:focus-visible {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  border-color: var(--active-border);
  box-shadow: var(--glass-active-shadow), var(--focus-ring);
}
.nav-item.active:focus-visible::after { opacity: 0.28; transform: scaleY(0.74); }
.nav-badge {
  margin-left: auto;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  color: var(--text-primary);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}
.sidebar-footer { position: relative; z-index: 1; padding: 16px; overflow: hidden; }
.sidebar-footer::before {
  content: "";
  position: absolute;
  left: var(--c1-sidebar-gutter);
  right: var(--c1-sidebar-gutter);
  top: 0;
  height: 1px;
  background: var(--c1-sidebar-hairline);
  pointer-events: none;
}
.version { font-size: 11px; color: var(--text-muted); text-align: center; }
/* ===== Main Content ===== */
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  -webkit-overflow-scrolling: touch;
  scroll-padding-block: 30px var(--app-chrome-inset);
  min-width: 0;
  margin: var(--app-chrome-inset);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--content-material);
  border: 1px solid var(--content-material-border);
  border-radius: var(--radius-sheet);
  box-shadow: var(--glass-surface-shadow);
  position: relative;
  z-index: var(--z-raised);
}
.main-content::before {
  content: "";
  position: sticky;
  top: 0;
  display: block;
  height: 30px;
  margin-bottom: -30px;
  background: linear-gradient(to bottom, var(--bg-primary), transparent);
  opacity: 0.10;
  pointer-events: none;
  z-index: 2;
}
.main-content::after {
  content: "";
  position: sticky;
  bottom: 0;
  display: block;
  height: 26px;
  margin-top: -26px;
  background: linear-gradient(to top, var(--bg-primary), transparent);
  opacity: 0.08;
  pointer-events: none;
  z-index: 2;
}
.main-content:focus { outline: none; }
.main-content:focus-visible {
  outline: none;
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-surface-shadow), var(--focus-ring);
}
.app-layout.mobile-more-active { overscroll-behavior: none; } .app-layout.mobile-more-active .main-content { overflow: hidden; }
/* ===== Bottom Nav (Mobile) ===== */
.bottom-nav {
  display: none;
  position: fixed;
  bottom: var(--mobile-bottom-nav-offset);
  left: max(12px, env(safe-area-inset-left, 0px));
  right: max(12px, env(safe-area-inset-right, 0px));
  min-height: var(--mobile-bottom-nav-height);
  background: var(--surface-nav);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  border: 1px solid var(--surface-nav-border);
  border-radius: var(--radius-sheet);
  box-shadow: var(--chrome-floating-shadow);
  z-index: var(--z-nav);
  padding: 6px;
  overflow: hidden;
  isolation: isolate;
  contain: layout paint;
}
.bottom-nav::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background:
    var(--surface-specular-edge),
    var(--surface-noise);
  opacity: var(--surface-overlay-opacity);
  pointer-events: none;
  z-index: 0;
}
.bottom-nav-item {
  position: relative;
  z-index: 1;
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
  min-height: 50px;
  border-radius: 22px;
  transition: transform var(--motion-standard);
  border: 1px solid transparent;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}
.bottom-nav-item svg { width: 22px; height: 22px; transition: transform var(--motion-standard); }
.bottom-nav-item:hover { color: var(--text-primary); }
.bottom-nav-item:hover svg { transform: translateY(-1px); }
.bottom-nav-item.active:hover { box-shadow: var(--glass-active-shadow); }
.bottom-nav-item:active {
  transform: scale(0.97);
}
.bottom-nav-item:focus-visible {
  outline: none;
  color: var(--text-primary);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.bottom-nav-item.active {
  color: var(--text-primary);
  border-color: var(--active-border);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.bottom-nav-item.active::before {
  content: "";
  position: absolute;
  left: 50%;
  bottom: 6px;
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: var(--active-indicator);
  box-shadow: var(--glass-inner-shadow);
  opacity: 0.58;
  transform: translateX(-50%) scaleX(1);
  pointer-events: none;
  transition: opacity var(--motion-fast), transform var(--motion-standard);
}
.bottom-nav-more::after {
  content: "";
  position: absolute;
  top: 7px;
  right: calc(50% - 17px);
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--glass-active-border);
  box-shadow: var(--glass-inner-shadow);
  opacity: 0;
  transform: scale(0.78);
  transition: transform var(--motion-standard);
}
.bottom-nav-more.open::after { background: var(--glass-active-border); opacity: 0.92; transform: scale(1); }
.bottom-nav-more.active::after { opacity: 0; }
.bottom-nav-more.open:not(.active) {
  color: var(--text-primary);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.bottom-nav-more.open:not(.active):focus-visible { background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover); box-shadow: var(--glass-control-shadow-hover), var(--focus-ring); }
.bottom-nav-activity[aria-pressed="true"] {
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.bottom-nav-activity[aria-pressed="true"]:focus-visible {
  box-shadow: var(--glass-active-shadow), var(--focus-ring);
}
.bottom-nav-item.active:focus-visible {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--active-border);
  box-shadow: var(--glass-active-shadow), var(--focus-ring);
}
.bottom-nav-item.active:focus-visible::before { opacity: 0.34; transform: translateX(-50%) scaleX(0.72); }
.bottom-nav-item.active:active { box-shadow: var(--glass-active-shadow); }
.bottom-nav-item.active svg { filter: none; }
.mobile-more-overlay {
  display: none;
}
/* ===== Responsive ===== */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .bottom-nav {
    display: flex;
    padding: 6px 6px max(8px, env(safe-area-inset-bottom, 0px));
    padding-bottom: max(8px, env(safe-area-inset-bottom, 0px));
  }
  .main-content {
    margin: 0;
    border: 0;
    border-radius: 0;
    background: var(--bg-primary);
    box-shadow: none;
    padding-bottom: var(--mobile-bottom-nav-reserve);
    scroll-padding-bottom: var(--mobile-bottom-nav-reserve);
  }
  .mobile-more-overlay {
    position: fixed;
    inset: 0;
    z-index: calc(var(--z-nav) + 1);
    display: flex;
    align-items: flex-end;
    background: var(--surface-scrim);
    backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
    overscroll-behavior: contain;
    padding: 0 12px var(--mobile-bottom-nav-reserve);
  }
  .mobile-more-sheet {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    width: 100%;
    max-height: min(560px, calc(100dvh - 112px - env(safe-area-inset-bottom, 0px)));
    padding: 10px 10px 14px;
    border: 1px solid var(--border-light);
    border-radius: 22px;
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--material-glass-sheet); background-color: color-mix(in srgb, var(--bg-primary) 88%, transparent);
    box-shadow: var(--shadow-sheet);
    backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  }
  .mobile-more-sheet:focus { outline: none; }
  .mobile-more-sheet:focus-visible {
    outline: none;
    border-color: var(--glass-active-border);
    box-shadow: var(--shadow-sheet), var(--focus-ring);
  }
  .mobile-more-sheet::before {
    content: "";
    position: absolute;
    inset: 0 0 auto;
    height: 32px;
    border-radius: inherit;
    background: linear-gradient(to bottom, var(--bg-primary), transparent);
    opacity: 0.14;
    pointer-events: none;
    z-index: 1;
  }
  .mobile-more-sheet::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background:
      var(--surface-specular-edge),
      var(--surface-noise);
    opacity: var(--surface-overlay-opacity);
    pointer-events: none;
    z-index: 0;
  }
  .mobile-more-sheet > * {
    position: relative;
    z-index: 1;
  }
  .mobile-more-grabber {
    width: 38px;
    height: 4px;
    margin: 0 auto 12px;
    border-radius: 999px;
    background: var(--border-light);
  }
  .mobile-more-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
    padding: 0 2px;
  }
  .mobile-more-head h2 {
    margin: 0;
    color: var(--text-primary);
    font-size: 16px;
    letter-spacing: 0;
  }
  .mobile-more-close {
    width: 36px;
    height: 36px;
    border-radius: 999px;
    border: 1px solid var(--glass-control-border);
    background:
      var(--surface-specular-edge),
      var(--surface-noise),
      var(--material-glass-control);
    color: var(--text-primary);
    box-shadow: var(--glass-control-shadow);
    transition: transform var(--motion-standard);
  }
  .mobile-more-close svg { width: 17px; height: 17px; }
  .mobile-more-close:hover,
  .mobile-more-close:focus-visible {
    outline: none;
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--material-glass-control-hover);
    border-color: var(--glass-control-border-hover);
    box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
    transform: translateY(-1px);
  }
  .mobile-more-close:active { transform: translateY(0) scale(0.96); }
  .mobile-theme-toggle {
    width: 100%;
    min-height: 44px;
    margin-bottom: 10px;
    padding: 9px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid var(--glass-control-border);
    border-radius: 16px;
    background:
      var(--surface-specular-edge),
      var(--surface-noise),
      var(--material-glass-control); background-color: color-mix(in srgb, var(--bg-primary) 70%, transparent);
    color: var(--text-primary);
    box-shadow: var(--glass-control-shadow);
    backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
    font: inherit;
    font-size: 13px;
    font-weight: 700;
    transition: transform var(--motion-standard);
  }
  .mobile-theme-toggle:hover,
  .mobile-theme-toggle:focus-visible {
    outline: none;
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--material-glass-control-hover);
    border-color: var(--glass-control-border-hover);
    box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
    transform: translateY(-1px);
  }
  .mobile-theme-toggle:active { transform: translateY(0) scale(0.985); }
  .mobile-theme-toggle span:last-child {
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0;
  }
  .mobile-more-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    max-height: calc(min(560px, calc(100dvh - 112px - env(safe-area-inset-bottom, 0px))) - 116px);
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    -webkit-overflow-scrolling: touch;
    scroll-padding-block: 1px 10px;
    mask-image: linear-gradient(to bottom, transparent, currentColor 12px, currentColor calc(100% - 14px), transparent);
    padding: 1px;
  }
  .mobile-more-item {
    display: flex;
    min-width: 0; min-height: 66px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid var(--glass-control-border);
    border-radius: 16px;
    background:
      var(--surface-specular-edge),
      var(--surface-noise),
      var(--material-glass-control); background-color: color-mix(in srgb, var(--bg-primary) 70%, transparent);
    box-shadow: var(--glass-control-shadow);
    backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    transition: transform var(--motion-standard);
    scroll-margin-block: 12px;
  }
  .mobile-more-item svg { width: 22px; height: 22px; }
  .mobile-more-item.active {
    color: var(--text-primary);
    border-color: var(--glass-active-border);
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--glass-active-material);
    box-shadow: var(--glass-active-shadow);
  }
  .mobile-more-item:hover,
  .mobile-more-item:focus-visible {
    outline: none;
    color: var(--text-primary);
    border-color: var(--glass-control-border-hover);
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--material-glass-control-hover);
    box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
    transform: translateY(-1px);
  }
  .mobile-more-item:active {
    transform: translateY(0) scale(0.985);
  }
  .mobile-more-item.active:hover,
  .mobile-more-item.active:focus-visible {
    border-color: var(--glass-active-border);
    background:
      var(--surface-specular-edge-strong),
      var(--surface-noise),
      var(--glass-active-material);
    box-shadow: var(--glass-active-shadow), var(--focus-ring);
  }
  .mobile-more-item.active:active {
    box-shadow: var(--glass-active-shadow);
  }
  .mobile-more-enter-active,
  .mobile-more-leave-active {
    transition: opacity var(--motion-fast);
  }
  .mobile-more-enter-active .mobile-more-sheet,
  .mobile-more-leave-active .mobile-more-sheet {
    transition: transform var(--motion-standard);
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
.theme-toggle, .collapse-btn, .nav-item, .bottom-nav-item, .mobile-more-close, .mobile-theme-toggle, .mobile-more-item {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.activity-toggle {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .theme-toggle,
  .theme-toggle__orb,
  .activity-toggle,
  .collapse-btn,
  .nav-item,
  .nav-item svg,
  .bottom-nav-item,
  .bottom-nav-item svg,
  .bottom-nav-more::after,
  .bottom-nav-item.active::before,
  .nav-item.active::after,
  .mobile-more-overlay,
  .mobile-more-sheet,
  .mobile-more-close,
  .mobile-theme-toggle,
  .mobile-more-item,
  .mobile-more-enter-active,
  .mobile-more-leave-active,
  .mobile-more-enter-active .mobile-more-sheet,
  .mobile-more-leave-active .mobile-more-sheet {
    transition-duration: 1ms !important;
  }
  .theme-toggle:hover,
  .nav-item:focus-visible,
  .nav-item.active:focus-visible::after,
  .bottom-nav-item:hover svg,
  .bottom-nav-item.active::before,
  .mobile-more-close:hover,
  .mobile-theme-toggle:hover,
  .mobile-more-item:hover,
  .mobile-more-enter-from .mobile-more-sheet,
  .mobile-more-leave-to .mobile-more-sheet {
    transform: none !important;
  }
}
</style>
