<template>
  <div class="drive page-rail page-rail--standard">
    <!-- 头部:面包屑 + 工具栏 -->
    <div class="drive-head">
      <div class="crumbs">
        <button class="crumb" type="button" @click="goRoot">115 网盘</button>
        <template v-for="(crumb, i) in stack" :key="crumb.cid + ':' + i">
          <span class="crumb-sep">/</span>
          <button class="crumb" type="button" @click="goCrumb(i)">{{ crumb.name || '未命名' }}</button>
        </template>
      </div>
      <div class="drive-tools">
        <div class="search-box">
          <input
            v-model="keywordInput"
            class="search-input"
            type="search"
            placeholder="搜索当前目录…"
            @keyup.enter="runSearch"
          />
          <button v-if="searchActive" class="ghost-btn" type="button" @click="clearSearch">清除</button>
        </div>

        <!-- 排序 -->
        <div class="sort-control" title="排序">
          <select v-model="sortKey" class="sort-select" @change="applySort(sortKey)">
            <option value="name">名称</option>
            <option value="size">大小</option>
            <option value="type">类型</option>
            <option value="time">修改时间</option>
          </select>
          <button class="icon-toggle" type="button" :title="sortAsc ? '升序' : '降序'" @click="toggleSortDir">
            {{ sortAsc ? '↑' : '↓' }}
          </button>
        </div>

        <!-- 视图切换 -->
        <div class="view-toggle" role="group" aria-label="视图切换">
          <button class="icon-toggle" :class="{ active: view === 'grid' }" type="button" title="网格视图" @click="setView('grid')">▦</button>
          <button class="icon-toggle" :class="{ active: view === 'list' }" type="button" title="列表视图" @click="setView('list')">☰</button>
        </div>

        <button class="ghost-btn" type="button" :class="{ active: showOffline }" @click="showOffline = !showOffline">离线任务</button>
        <button class="ghost-btn" type="button" @click="openAddSheet">＋ 离线下载</button>
        <button class="ghost-btn" type="button" @click="askNewFolder" :disabled="loading">新建文件夹</button>
        <button class="ghost-btn" type="button" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </div>

    <!-- 离线任务面板 -->
    <OfflinePanel v-if="showOffline" ref="offlinePanel" @add="openAddSheet" @changed="refresh" />

    <!-- 选中态批量操作条 -->
    <div v-if="selected.length" class="select-bar">
      <span class="select-count">已选 {{ selected.length }} 项</span>
      <button class="ghost-btn" type="button" @click="openPicker('move')">移动</button>
      <button class="ghost-btn" type="button" @click="openPicker('copy')">复制</button>
      <button v-if="selected.length === 1" class="ghost-btn" type="button" @click="askRename">重命名</button>
      <button class="ghost-btn danger" type="button" @click="doDelete">删除</button>
      <button class="ghost-btn" type="button" @click="clearSelection">取消</button>
    </div>

    <!-- 主体 -->
    <AppleSkeleton v-if="loading" class="loading-wrap" variant="list" :items="8" label="加载中" />

    <AppleEmptyState
      v-else-if="error === 'unbound'"
      title="115 尚未绑定"
      description="去设置页扫码绑定 115 后即可浏览网盘文件。"
      action-label="去绑定"
      @action="goSettings"
    />
    <AppleEmptyState
      v-else-if="error === 'failed'"
      title="加载失败"
      description="115 网盘数据源暂时不可用。"
      action-label="重试"
      @action="refresh"
    />
    <AppleEmptyState
      v-else-if="!items.length"
      :title="searchActive ? '没有匹配的文件' : '这个文件夹是空的'"
      :description="searchActive ? '换个关键词再试试。' : '还没有内容。'"
    />

    <DriveList
      v-else-if="view === 'list'"
      :files="displayFiles"
      :selected="selected"
      :sort-key="sortKey"
      :sort-asc="sortAsc"
      @open="openFile"
      @toggle="toggleSelect"
      @sort="applySort"
    />
    <DriveGrid
      v-else
      :files="displayFiles"
      :selected="selected"
      @open="openFile"
      @toggle="toggleSelect"
    />

    <div v-if="hasMore && !loading" class="more-row">
      <button class="ghost-btn" type="button" @click="loadMore" :disabled="loadingMore">
        {{ loadingMore ? '加载中…' : '加载更多' }}
      </button>
    </div>

    <!-- 视频预览 -->
    <div v-if="preview.kind === 'video'" class="overlay overlay--dark" @click.self="closePreview">
      <div class="player">
        <button class="overlay-close" type="button" @click="closePreview">✕</button>
        <video ref="previewVideo" class="player-video" controls autoplay playsinline @error="onVideoError"></video>
        <div class="player-bar">
          <span class="player-title">{{ preview.name }}</span>
          <div class="defs">
            <button
              v-for="s in preview.sources"
              :key="s.url"
              class="def-btn"
              :class="{ active: s.url === preview.current }"
              type="button"
              @click="switchDefinition(s)"
            >{{ s.desc || s.definition }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览 -->
    <div v-if="preview.kind === 'image'" class="overlay overlay--dark" @click.self="closePreview">
      <button class="overlay-close" type="button" @click="closePreview">✕</button>
      <img class="lightbox" :src="preview.imageUrl" :alt="preview.name" loading="lazy" decoding="async" />
    </div>

    <!-- 目录选择(移动/复制目标) -->
    <div v-if="picker.open" class="overlay" @click.self="closePicker">
      <div class="sheet">
        <div class="sheet-head">{{ picker.mode === 'move' ? '移动到' : '复制到' }}</div>
        <div class="crumbs sheet-crumbs">
          <button class="crumb" type="button" @click="pickerGoRoot">根目录</button>
          <template v-for="(crumb, i) in picker.stack" :key="'p' + crumb.cid + ':' + i">
            <span class="crumb-sep">/</span>
            <button class="crumb" type="button" @click="pickerGoCrumb(i)">{{ crumb.name || '未命名' }}</button>
          </template>
        </div>
        <div class="sheet-list">
          <div v-if="picker.loading" class="sheet-hint">加载中…</div>
          <div v-else-if="!picker.dirs.length" class="sheet-hint">没有子文件夹</div>
          <button
            v-for="dir in picker.dirs"
            :key="dir.file_id"
            class="sheet-row"
            type="button"
            @click="pickerEnter(dir)"
          >📁 {{ dir.name }}</button>
        </div>
        <div class="sheet-actions">
          <button class="ghost-btn" type="button" @click="closePicker">取消</button>
          <button class="primary-btn" type="button" @click="pickerConfirm" :disabled="picker.busy">
            {{ picker.mode === 'move' ? '移动到这里' : '复制到这里' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 名称输入(新建/重命名) -->
    <div v-if="nameModal.open" class="overlay" @click.self="nameModal.open = false">
      <div class="sheet sheet-narrow">
        <div class="sheet-head">{{ nameModal.mode === 'folder' ? '新建文件夹' : '重命名' }}</div>
        <input
          ref="nameInput"
          v-model="nameModal.value"
          class="search-input wide"
          type="text"
          placeholder="输入名称"
          @keyup.enter="submitName"
        />
        <div class="sheet-actions">
          <button class="ghost-btn" type="button" @click="nameModal.open = false">取消</button>
          <button class="primary-btn" type="button" @click="submitName" :disabled="!nameModal.value.trim()">确定</button>
        </div>
      </div>
    </div>

    <AddDownloadSheet
      :open="showAddSheet"
      locked-downloader-type="open115"
      :default-cid="cid"
      @close="showAddSheet = false"
      @added="onOfflineAdded"
    />
  </div>
</template>

<script>
import api from '../api'
import { ElMessage } from '../utils/message.js'
import { requestConfirm } from '../utils/confirmDialog'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import DriveGrid from '../features/drive/DriveGrid.vue'
import DriveList from '../features/drive/DriveList.vue'
import OfflinePanel from '../features/drive/OfflinePanel.vue'
import AddDownloadSheet from '../features/downloads/AddDownloadSheet.vue'
import { kindOf, sortFilesByType } from '../features/drive/driveFormat'

const PAGE_SIZE = 100
// 排序键 → 115 服务端 o 字段。类型 115 无原生排序,用 file_name 拉取后页内再排。
const SERVER_ORDER = { name: 'file_name', size: 'file_size', time: 'user_utime', type: 'file_name' }
const VIEW_KEY = 'drive115:view'
const SORT_KEY = 'drive115:sort'

function readPref(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw == null ? fallback : raw
  } catch {
    return fallback
  }
}

export default {
  name: 'Drive115',
  components: { AppleSkeleton, AppleEmptyState, DriveGrid, DriveList, OfflinePanel, AddDownloadSheet },
  data() {
    let sortKey = 'time'
    let sortAsc = false
    try {
      const saved = JSON.parse(readPref(SORT_KEY, '') || 'null')
      if (saved && SERVER_ORDER[saved.key]) { sortKey = saved.key; sortAsc = Boolean(saved.asc) }
    } catch { /* ignore */ }
    return {
      cid: '0',
      stack: [],
      items: [],
      loading: false,
      loadingMore: false,
      error: '',
      offset: 0,
      total: 0,
      keywordInput: '',
      searchActive: false,
      selected: [],
      view: readPref(VIEW_KEY, 'grid') === 'list' ? 'list' : 'grid',
      sortKey,
      sortAsc,
      showOffline: false,
      showAddSheet: false,
      preview: { kind: '', name: '', sources: [], current: '', imageUrl: '' },
      playPick: '',
      triedHls: false,
      picker: { open: false, mode: 'move', cid: '0', stack: [], dirs: [], loading: false, busy: false },
      nameModal: { open: false, mode: 'folder', value: '' },
    }
  },
  computed: {
    hasMore() {
      return !this.searchActive && this.items.length < this.total
    },
    serverOrder() {
      return SERVER_ORDER[this.sortKey] || 'user_utime'
    },
    // 文件夹永远置顶;"类型"在已加载页内做完整排序,其余键服务端已排好,这里只做稳定的目录置顶。
    displayFiles() {
      if (this.sortKey === 'type') return sortFilesByType(this.items, this.sortAsc)
      const dirs = this.items.filter((f) => f.is_dir)
      const files = this.items.filter((f) => !f.is_dir)
      return [...dirs, ...files]
    },
  },
  mounted() {
    this.load('0', [])
  },
  beforeUnmount() {
    this.destroyHls()
  },
  methods: {
    kindOf,
    isSelected(id) {
      return this.selected.includes(id)
    },
    toggleSelect(id) {
      this.selected = this.selected.includes(id)
        ? this.selected.filter((x) => x !== id)
        : [...this.selected, id]
    },
    clearSelection() {
      this.selected = []
    },
    setView(view) {
      this.view = view
      try { localStorage.setItem(VIEW_KEY, view) } catch { /* ignore */ }
    },
    persistSort() {
      try { localStorage.setItem(SORT_KEY, JSON.stringify({ key: this.sortKey, asc: this.sortAsc })) } catch { /* ignore */ }
    },
    applySort(key) {
      if (this.sortKey === key) {
        this.sortAsc = !this.sortAsc
      } else {
        this.sortKey = key
        // 时间默认倒序(最新在前),其余默认升序
        this.sortAsc = key !== 'time'
      }
      this.persistSort()
      this.reloadCurrent()
    },
    toggleSortDir() {
      this.sortAsc = !this.sortAsc
      this.persistSort()
      this.reloadCurrent()
    },
    reloadCurrent() {
      if (this.searchActive) this.load(this.cid, this.stack, { keyword: this.keywordInput.trim() })
      else this.load(this.cid, this.stack)
    },
    async load(cid, stack, { keyword = '' } = {}) {
      this.loading = true
      this.error = ''
      this.clearSelection()
      try {
        const { data } = await api.listOpen115Files({
          cid, offset: 0, limit: PAGE_SIZE, keyword,
          order: this.serverOrder, asc: this.sortAsc,
        })
        this.cid = cid
        this.stack = stack
        this.items = data.files || []
        this.total = data.count || this.items.length
        this.offset = this.items.length
        this.searchActive = Boolean(keyword)
      } catch (e) {
        this.items = []
        this.error = e?.response?.status === 409 ? 'unbound' : 'failed'
      } finally {
        this.loading = false
      }
    },
    async loadMore() {
      if (this.loadingMore || !this.hasMore) return
      this.loadingMore = true
      try {
        const { data } = await api.listOpen115Files({
          cid: this.cid, offset: this.offset, limit: PAGE_SIZE,
          order: this.serverOrder, asc: this.sortAsc,
        })
        const more = data.files || []
        this.items = [...this.items, ...more]
        this.offset += more.length
        this.total = data.count || this.total
      } catch {
        ElMessage.error('加载更多失败')
      } finally {
        this.loadingMore = false
      }
    },
    refresh() {
      this.reloadCurrent()
    },
    enterFolder(file) {
      this.keywordInput = ''
      this.load(file.file_id, [...this.stack, { cid: file.file_id, name: file.name }])
    },
    goRoot() {
      this.keywordInput = ''
      this.load('0', [])
    },
    goCrumb(i) {
      this.keywordInput = ''
      const target = this.stack[i]
      this.load(target.cid, this.stack.slice(0, i + 1))
    },
    runSearch() {
      const kw = this.keywordInput.trim()
      if (!kw) return
      this.load(this.cid, this.stack, { keyword: kw })
    },
    clearSearch() {
      this.keywordInput = ''
      this.load(this.cid, this.stack)
    },
    openFile(file) {
      if (file.is_dir) { this.enterFolder(file); return }
      const kind = this.kindOf(file)
      if (kind === 'video') this.playVideo(file)
      else if (kind === 'image') this.previewImage(file)
      else ElMessage.info('该类型暂不支持预览')
    },
    previewImage(file) {
      this.preview = { kind: 'image', name: file.name, sources: [], current: '', imageUrl: api.open115ImageUrl(file.pick_code, file.extension) }
    },
    browserNative(ext) {
      return ['mp4', 'm4v', 'mov', 'webm'].includes(String(ext || '').toLowerCase())
    },
    async playVideo(file) {
      this.preview = { kind: 'video', name: file.name, sources: [], current: '', imageUrl: '' }
      this.playPick = file.pick_code
      this.triedHls = false
      if (this.browserNative(file.extension)) await this.attachDirect(file.pick_code)
      else await this.playViaHls(file.pick_code)
    },
    async playViaHls(pickCode) {
      this.triedHls = true
      try {
        const { data } = await api.getOpen115VideoSources(pickCode)
        const sources = data.sources || []
        if (sources.length) { this.preview.sources = sources; await this.attach(sources[0]); return }
      } catch { /* fall through to direct */ }
      await this.attachDirect(pickCode)
    },
    async attachDirect(pickCode) {
      await this.$nextTick()
      const video = this.$refs.previewVideo
      if (!video) return
      this.destroyHls()
      this.preview.sources = []
      this.preview.current = ''
      video.src = api.open115StreamUrl(pickCode)
      video.play().catch(() => {})
    },
    onVideoError() {
      if (!this.triedHls && this.playPick) this.playViaHls(this.playPick)
    },
    proxied(url) {
      return `/api/v1/stream/proxy?url=${encodeURIComponent(url)}`
    },
    async attach(source) {
      this.preview.current = source.url
      await this.$nextTick()
      const video = this.$refs.previewVideo
      if (!video) return
      this.destroyHls()
      const url = this.proxied(source.url)
      const { default: Hls } = await import('hls.js/dist/hls.light.mjs')
      if (Hls.isSupported()) {
        const hls = new Hls()
        hls.loadSource(url)
        hls.attachMedia(video)
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}))
        this._hls = hls
      } else {
        video.src = url
        video.play().catch(() => {})
      }
    },
    switchDefinition(source) {
      if (source.url !== this.preview.current) this.attach(source)
    },
    destroyHls() {
      if (this._hls) { this._hls.destroy(); this._hls = null }
    },
    closePreview() {
      this.destroyHls()
      this.preview = { kind: '', name: '', sources: [], current: '', imageUrl: '' }
    },
    openAddSheet() {
      this.showAddSheet = true
    },
    onOfflineAdded() {
      // 添加后刷新离线面板配额/进度;文件要等离线完成才出现,这里不强刷目录。
      this.$refs.offlinePanel?.reload?.()
    },
    askNewFolder() {
      this.nameModal = { open: true, mode: 'folder', value: '' }
      this.$nextTick(() => this.$refs.nameInput?.focus())
    },
    askRename() {
      const file = this.items.find((f) => f.file_id === this.selected[0])
      if (!file) return
      this.nameModal = { open: true, mode: 'rename', value: file.name }
      this.$nextTick(() => this.$refs.nameInput?.focus())
    },
    async submitName() {
      const value = this.nameModal.value.trim()
      if (!value) return
      const mode = this.nameModal.mode
      this.nameModal.open = false
      try {
        if (mode === 'folder') {
          await api.createOpen115Folder(this.cid, value)
          ElMessage.success('已新建文件夹')
        } else {
          await api.renameOpen115File(this.selected[0], value)
          ElMessage.success('已重命名')
        }
        this.refresh()
      } catch {
        /* global error toast already shown */
      }
    },
    async doDelete() {
      const ids = [...this.selected]
      if (!ids.length) return
      const ok = await requestConfirm({
        title: '删除文件',
        message: `确定删除选中的 ${ids.length} 项?此操作会移入 115 回收站。`,
        confirmText: '删除',
        tone: 'danger',
      })
      if (!ok) return
      try {
        await api.deleteOpen115Files(ids, this.cid)
        ElMessage.success(`已删除 ${ids.length} 项`)
        this.refresh()
      } catch {
        /* global error toast */
      }
    },
    // ---- 目录选择器 ----
    openPicker(mode) {
      this.picker = { open: true, mode, cid: '0', stack: [], dirs: [], loading: false, busy: false }
      this.pickerLoad('0', [])
    },
    closePicker() {
      this.picker.open = false
    },
    async pickerLoad(cid, stack) {
      this.picker.loading = true
      try {
        const { data } = await api.listOpen115Files({ cid, limit: PAGE_SIZE })
        this.picker.cid = cid
        this.picker.stack = stack
        this.picker.dirs = (data.files || []).filter((f) => f.is_dir)
      } catch {
        this.picker.dirs = []
      } finally {
        this.picker.loading = false
      }
    },
    pickerEnter(dir) {
      this.pickerLoad(dir.file_id, [...this.picker.stack, { cid: dir.file_id, name: dir.name }])
    },
    pickerGoRoot() {
      this.pickerLoad('0', [])
    },
    pickerGoCrumb(i) {
      const target = this.picker.stack[i]
      this.pickerLoad(target.cid, this.picker.stack.slice(0, i + 1))
    },
    async pickerConfirm() {
      const ids = [...this.selected]
      const toCid = this.picker.cid
      if (!ids.length) { this.closePicker(); return }
      this.picker.busy = true
      try {
        if (this.picker.mode === 'move') {
          await api.moveOpen115Files(ids, toCid)
          ElMessage.success(`已移动 ${ids.length} 项`)
        } else {
          await api.copyOpen115Files(ids, toCid)
          ElMessage.success(`已复制 ${ids.length} 项`)
        }
        this.closePicker()
        this.refresh()
      } catch {
        /* global error toast */
      } finally {
        this.picker.busy = false
      }
    },
    goSettings() {
      this.$router.push('/settings')
    },
  },
}
</script>

<style scoped>
.drive { --page-max: 1200px; padding-block: 20px; display: flex; flex-direction: column; gap: 14px; }

.drive-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.crumbs { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.crumb { background: none; border: none; color: var(--text-secondary); font-size: var(--type-control); cursor: pointer; padding: 2px 4px; border-radius: var(--radius-xs); }
.crumb:hover { color: var(--text-primary); }
.crumb:last-child { color: var(--text-primary); font-weight: 600; }
.crumb-sep { color: var(--text-muted); }

.drive-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.search-box { display: flex; align-items: center; gap: 6px; }
.search-input { background: var(--surface-input); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 12px; color: var(--text-primary); font-size: var(--type-caption); outline: none; min-width: 180px; }
.search-input:focus { background: var(--surface-input-focus); border-color: var(--accent); }
.search-input.wide { width: 100%; }

.sort-control { display: flex; align-items: center; gap: 4px; }
.sort-select { background: var(--surface-control); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 10px; color: var(--text-primary); font-size: var(--type-caption); outline: none; cursor: pointer; }
.sort-select:focus { border-color: var(--accent); }
.view-toggle { display: inline-flex; gap: 2px; }
.icon-toggle { background: var(--surface-control); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 10px; color: var(--text-secondary); font-size: var(--type-control); cursor: pointer; line-height: 1; }
.icon-toggle:hover { background: var(--surface-control-hover); color: var(--text-primary); }
.icon-toggle.active { background: var(--surface-control-hover); color: var(--accent); border-color: var(--accent); }

.ghost-btn { background: var(--surface-control); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 14px; color: var(--text-primary); font-size: var(--type-caption); cursor: pointer; transition: background var(--motion-fast, .15s); white-space: nowrap; }
.ghost-btn:hover:not(:disabled) { background: var(--surface-control-hover); }
.ghost-btn:disabled { opacity: .4; cursor: not-allowed; }
.ghost-btn.active { color: var(--accent); border-color: var(--accent); }
.ghost-btn.danger { color: var(--badge-error-text); }
.primary-btn { background: var(--accent); border: none; border-radius: var(--radius-control); padding: 7px 16px; color: var(--text-on-accent-solid); font-size: var(--type-caption); cursor: pointer; }
.primary-btn:disabled { opacity: .5; cursor: not-allowed; }

.select-bar { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-card); flex-wrap: wrap; }
.select-count { color: var(--text-primary); font-weight: 600; font-size: var(--type-caption); margin-right: auto; }

.loading-wrap { margin-top: 12px; }
.more-row { display: flex; justify-content: center; padding: 8px 0; }

.overlay { position: fixed; inset: 0; z-index: var(--z-lightbox); background: var(--surface-scrim, var(--scrim)); display: flex; align-items: center; justify-content: center; padding: 24px; }
.overlay--dark { background: var(--media-caption-scrim-strong); }
.overlay-close { position: absolute; top: 18px; right: 22px; width: 38px; height: 38px; border-radius: 50%; border: none; background: var(--vp-control-bg, var(--surface-control)); color: var(--text-on-accent-solid); font-size: var(--type-card-title); cursor: pointer; z-index: 2; }
.player { width: min(960px, 92vw); display: flex; flex-direction: column; gap: 10px; }
.player-video { width: 100%; max-height: 78vh; background: var(--media-blackout); border-radius: var(--radius-md); }
.player-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--text-on-accent-solid); }
.player-title { font-size: var(--type-control); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.defs { display: flex; gap: 6px; }
.def-btn { background: var(--vp-control-bg, var(--surface-control)); border: none; color: var(--text-on-accent-solid); border-radius: var(--radius-xs); padding: 4px 10px; font-size: var(--type-caption); cursor: pointer; }
.def-btn.active { background: var(--accent); }
.lightbox { max-width: 92vw; max-height: 88vh; object-fit: contain; border-radius: var(--radius-md); }

.sheet { background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-sheet); width: min(440px, 92vw); padding: 18px; display: flex; flex-direction: column; gap: 12px; box-shadow: var(--shadow-sheet); }
.sheet-narrow { width: min(360px, 92vw); }
.sheet-head { font-size: var(--type-card-title); font-weight: 600; color: var(--text-primary); }
.sheet-crumbs { font-size: var(--type-caption); }
.sheet-list { max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.sheet-hint { color: var(--text-muted); font-size: var(--type-caption); padding: 16px 4px; text-align: center; }
.sheet-row { text-align: left; background: none; border: none; color: var(--text-primary); font-size: var(--type-caption); padding: 9px 10px; border-radius: var(--radius-control); cursor: pointer; }
.sheet-row:hover { background: var(--surface-control-hover); }
.sheet-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
