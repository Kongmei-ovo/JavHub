<template>
  <div class="app-layout">
    <!-- 左侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span v-if="!sidebarCollapsed" class="logo-text">JavHub</span>
        </div>
        <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
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
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script>
import { h, ref, defineComponent } from 'vue'
import { useRoute } from 'vue-router'

// Icon components (inline SVG)
const IconHome = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z' }), h('polyline', { points: '9 22 9 12 15 12 15 22' })]) })
const IconSearch = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('circle', { cx: '11', cy: '11', r: '8' }), h('path', { d: 'm21 21-4.35-4.35' })]) })
const IconGenres = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M4 19.5A2.5 2.5 0 016.5 17H20' }), h('path', { d: 'M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z' })]) })
const IconDownload = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }), h('polyline', { points: '7 10 12 15 17 10' }), h('line', { x1: '12', y1: '15', x2: '12', y2: '3' })]) })
const IconList = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('line', { x1: '8', y1: '6', x2: '21', y2: '6' }), h('line', { x1: '8', y1: '12', x2: '21', y2: '12' }), h('line', { x1: '8', y1: '18', x2: '21', y2: '18' }), h('line', { x1: '3', y1: '6', x2: '3.01', y2: '6' }), h('line', { x1: '3', y1: '12', x2: '3.01', y2: '12' }), h('line', { x1: '3', y1: '18', x2: '3.01', y2: '18' })]) })
const IconParse = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z' }), h('polyline', { points: '14 2 14 8 20 8' }), h('line', { x1: '16', y1: '13', x2: '8', y2: '13' }), h('line', { x1: '16', y1: '17', x2: '8', y2: '17' }), h('polyline', { points: '10 9 9 9 8 9' })]) })
const IconStar = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2' }), h('circle', { cx: '9', cy: '7', r: '4' }), h('path', { d: 'M23 21v-2a4 4 0 00-3-3.87' }), h('path', { d: 'M16 3.13a4 4 0 010 7.75' })]) })
const IconHeart = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z' })]) })
const IconSettings = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('circle', { cx: '12', cy: '12', r: '3' }), h('path', { d: 'M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z' })]) })
// 库存对比图标：两个箭头对比
const IconInventory = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5' })]) })
// 归一化图标：合并/alias
const IconNormalize = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('path', { d: 'M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z' })]) })
// 缺失图标：感叹号
const IconMissing = defineComponent({ render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [h('circle', { cx: '12', cy: '12', r: '10' }), h('line', { x1: '12', y1: '8', x2: '12', y2: '12' }), h('line', { x1: '12', y1: '16', x2: '12.01', y2: '16' })]) })

export default {
  name: 'App',
  setup() {
    const sidebarCollapsed = ref(false)
    const route = useRoute()

    const navItems = [
      { path: '/genres', label: '个性推荐', icon: IconGenres },
      { path: '/search', label: '影片检索', icon: IconSearch },
      { path: '/parse', label: '磁链解析', icon: IconParse },
      { path: '/favorites', label: '我的收藏', icon: IconHeart },
      { path: '/subscription', label: '订阅演员', icon: IconStar },
      { path: '/inventory', label: '库存对比', icon: IconInventory },
      { path: '/normalize', label: '归一化', icon: IconNormalize },
      { path: '/missing', label: '缺失演员', icon: IconMissing },
      { path: '/downloads', label: '下载管理', icon: IconHome },
      { path: '/settings', label: '设置', icon: IconSettings },
    ]

    const bottomNavItems = [
      { path: '/genres', label: '推荐', icon: IconGenres },
      { path: '/search', label: '检索', icon: IconSearch },
      { path: '/favorites', label: '收藏', icon: IconHeart },
      { path: '/parse', label: '解析', icon: IconParse },
      { path: '/subscription', label: '订阅', icon: IconStar },
      { path: '/inventory', label: '库存', icon: IconInventory },
      { path: '/normalize', label: '归一', icon: IconNormalize },
      { path: '/downloads', label: '下载', icon: IconHome },
      { path: '/settings', label: '我的', icon: IconSettings },
    ]

    // Get favorites count for badge
    const favoritesCount = ref(0)
    try {
      const fav = localStorage.getItem('movieFavorites')
      favoritesCount.value = fav ? JSON.parse(fav).length : 0
    } catch (e) {}

    return { sidebarCollapsed, navItems, bottomNavItems, favoritesCount }
  }
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
}

/* ===== Sidebar ===== */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, min-width 0.3s ease, background 0.3s ease;
  z-index: 100;
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
  border-bottom: 1px solid var(--border);
  min-height: 72px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  letter-spacing: -0.02em;
}

.collapse-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  transition: var(--transition);
  flex-shrink: 0;
}
.collapse-btn:hover { color: var(--text-primary); background: var(--white-06); }

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
  padding: 12px 14px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: var(--transition);
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}
.nav-item:hover { background: var(--white-06); color: var(--text-primary); }
.nav-item.active { background: var(--nav-active-bg); color: var(--accent); }
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
}
.nav-item svg { width: 20px; height: 20px; flex-shrink: 0; }
.nav-badge {
  margin-left: auto;
  background: var(--accent);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border);
}
.version { font-size: 11px; color: var(--text-muted); text-align: center; }

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-width: 0;
}

/* ===== Bottom Nav (Mobile) ===== */
.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  z-index: 100;
  padding: 8px 0 env(safe-area-inset-bottom, 8px);
}

.bottom-nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 10px;
  font-weight: 500;
  padding: 6px 0;
  transition: var(--transition);
}
.bottom-nav-item svg { width: 22px; height: 22px; }
.bottom-nav-item.active { color: var(--accent); }

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .bottom-nav { display: flex; }
  .main-content { padding-bottom: 70px; }
}
</style>
