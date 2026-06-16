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
        <button class="ghost-btn" type="button" @click="askNewFolder" :disabled="loading">新建文件夹</button>
        <button class="ghost-btn" type="button" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </div>

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

    <div v-else class="file-grid">
      <div
        v-for="file in items"
        :key="file.file_id"
        class="file-cell"
        :class="{ selected: isSelected(file.file_id) }"
        @click="openFile(file)"
      >
        <label class="pick" @click.stop>
          <input type="checkbox" :checked="isSelected(file.file_id)" @change="toggleSelect(file.file_id)" />
        </label>
        <div class="file-ico" :class="kindOf(file)">
          <img
            v-if="kindOf(file) === 'image'"
            :src="thumbUrl(file)"
            alt=""
            loading="lazy"
            @error="onThumbError"
          />
          <span v-else class="ico-glyph">{{ glyph(file) }}</span>
          <span v-if="file.duration" class="dur">{{ formatDuration(file.duration) }}</span>
        </div>
        <div class="file-name" :title="file.name">{{ file.name }}</div>
        <div class="file-meta">{{ file.is_dir ? '文件夹' : formatSize(file.size) }}</div>
      </div>
    </div>

    <div v-if="hasMore && !loading" class="more-row">
      <button class="ghost-btn" type="button" @click="loadMore" :disabled="loadingMore">
        {{ loadingMore ? '加载中…' : '加载更多' }}
      </button>
    </div>

    <!-- 视频预览 -->
    <div v-if="preview.kind === 'video'" class="overlay" @click.self="closePreview">
      <div class="player">
        <button class="overlay-close" type="button" @click="closePreview">✕</button>
        <video ref="previewVideo" class="player-video" controls autoplay playsinline></video>
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
    <div v-if="preview.kind === 'image'" class="overlay" @click.self="closePreview">
      <button class="overlay-close" type="button" @click="closePreview">✕</button>
      <img class="lightbox" :src="preview.imageUrl" :alt="preview.name" />
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
  </div>
</template>

<script>
import api from '../api'
import { ElMessage } from '../utils/message.js'
import { requestConfirm } from '../utils/confirmDialog'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'

const VIDEO_EXT = new Set(['mp4', 'mkv', 'avi', 'wmv', 'ts', 'm4v', 'mov', 'flv', 'rmvb', 'webm', 'mpg', 'mpeg'])
const IMAGE_EXT = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'heif', 'avif'])
const PAGE_SIZE = 100

export default {
  name: 'Drive115',
  components: { AppleSkeleton, AppleEmptyState },
  data() {
    return {
      cid: '0',
      stack: [], // [{cid, name}]
      items: [],
      loading: false,
      loadingMore: false,
      error: '',
      offset: 0,
      total: 0,
      keywordInput: '',
      searchActive: false,
      selected: [],
      preview: { kind: '', name: '', sources: [], current: '', imageUrl: '' },
      picker: { open: false, mode: 'move', cid: '0', stack: [], dirs: [], loading: false, busy: false },
      nameModal: { open: false, mode: 'folder', value: '' },
    }
  },
  computed: {
    hasMore() {
      return !this.searchActive && this.items.length < this.total
    },
  },
  mounted() {
    this.load('0', [])
  },
  beforeUnmount() {
    this.destroyHls()
  },
  methods: {
    kindOf(file) {
      if (file.is_dir) return 'folder'
      const ext = String(file.extension || '').toLowerCase()
      if (VIDEO_EXT.has(ext)) return 'video'
      if (IMAGE_EXT.has(ext)) return 'image'
      return 'file'
    },
    glyph(file) {
      return { folder: '📁', video: '🎬', image: '🖼', file: '📄' }[this.kindOf(file)]
    },
    thumbUrl(file) {
      return api.open115ImageUrl(file.pick_code, file.extension)
    },
    onThumbError(e) {
      const el = e?.target
      if (el) el.style.visibility = 'hidden'
    },
    formatSize(bytes) {
      const n = Number(bytes || 0)
      if (!n) return '—'
      const units = ['B', 'KB', 'MB', 'GB', 'TB']
      let v = n
      let i = 0
      while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
      return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
    },
    formatDuration(sec) {
      const s = Math.round(Number(sec || 0))
      if (!s) return ''
      const h = Math.floor(s / 3600)
      const m = Math.floor((s % 3600) / 60)
      const ss = s % 60
      const pad = (x) => String(x).padStart(2, '0')
      return h ? `${h}:${pad(m)}:${pad(ss)}` : `${m}:${pad(ss)}`
    },
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
    async load(cid, stack, { keyword = '' } = {}) {
      this.loading = true
      this.error = ''
      this.clearSelection()
      try {
        const { data } = await api.listOpen115Files({ cid, offset: 0, limit: PAGE_SIZE, keyword })
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
        const { data } = await api.listOpen115Files({ cid: this.cid, offset: this.offset, limit: PAGE_SIZE })
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
      if (this.searchActive) this.load(this.cid, this.stack, { keyword: this.keywordInput.trim() })
      else this.load(this.cid, this.stack)
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
    async playVideo(file) {
      this.preview = { kind: 'video', name: file.name, sources: [], current: '', imageUrl: '' }
      try {
        const { data } = await api.getOpen115VideoSources(file.pick_code)
        const sources = data.sources || []
        if (sources.length) {
          this.preview.sources = sources
          await this.attach(sources[0])
        } else {
          // 115 hasn't transcoded this video — play the original via the range proxy.
          await this.attachDirect(file.pick_code)
        }
      } catch {
        ElMessage.error('无法获取播放地址')
        this.closePreview()
      }
    },
    async attachDirect(pickCode) {
      await this.$nextTick()
      const video = this.$refs.previewVideo
      if (!video) return
      this.destroyHls()
      video.src = api.open115StreamUrl(pickCode)
      video.play().catch(() => {})
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
.crumb { background: none; border: none; color: var(--text-secondary); font-size: 14px; cursor: pointer; padding: 2px 4px; border-radius: var(--radius-xs); }
.crumb:hover { color: var(--text-primary); }
.crumb:last-child { color: var(--text-primary); font-weight: 600; }
.crumb-sep { color: var(--text-muted); }

.drive-tools { display: flex; align-items: center; gap: 8px; }
.search-box { display: flex; align-items: center; gap: 6px; }
.search-input { background: var(--surface-input); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 12px; color: var(--text-primary); font-size: 13px; outline: none; min-width: 180px; }
.search-input:focus { background: var(--surface-input-focus); border-color: var(--accent); }
.search-input.wide { width: 100%; }

.ghost-btn { background: var(--surface-control); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 14px; color: var(--text-primary); font-size: 13px; cursor: pointer; transition: background var(--motion-fast, .15s); white-space: nowrap; }
.ghost-btn:hover:not(:disabled) { background: var(--surface-control-hover); }
.ghost-btn:disabled { opacity: .4; cursor: not-allowed; }
.ghost-btn.danger { color: #e5484d; }
.primary-btn { background: var(--accent); border: none; border-radius: var(--radius-control); padding: 7px 16px; color: #fff; font-size: 13px; cursor: pointer; }
.primary-btn:disabled { opacity: .5; cursor: not-allowed; }

.select-bar { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-card); flex-wrap: wrap; }
.select-count { color: var(--text-primary); font-weight: 600; font-size: 13px; margin-right: auto; }

.loading-wrap { margin-top: 12px; }

.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.file-cell { position: relative; background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 12px; cursor: pointer; transition: background var(--motion-fast, .15s), border-color var(--motion-fast, .15s); display: flex; flex-direction: column; gap: 6px; }
.file-cell:hover { background: var(--surface-card-hover); }
.file-cell.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.pick { position: absolute; top: 8px; left: 8px; z-index: 2; opacity: 0; transition: opacity var(--motion-fast, .15s); }
.file-cell:hover .pick, .file-cell.selected .pick { opacity: 1; }
.pick input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }

.file-ico { position: relative; aspect-ratio: 1 / 1; border-radius: var(--radius-md); background: var(--surface-control); display: flex; align-items: center; justify-content: center; overflow: hidden; }
.file-ico img { width: 100%; height: 100%; object-fit: cover; }
.ico-glyph { font-size: 38px; line-height: 1; }
.dur { position: absolute; right: 5px; bottom: 5px; background: rgba(0,0,0,.66); color: #fff; font-size: 11px; padding: 1px 5px; border-radius: 4px; }

.file-name { font-size: 13px; color: var(--text-primary); line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.file-meta { font-size: 11px; color: var(--text-muted); }

.more-row { display: flex; justify-content: center; padding: 8px 0; }

.overlay { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,.7); display: flex; align-items: center; justify-content: center; padding: 24px; }
.overlay-close { position: absolute; top: 18px; right: 22px; width: 38px; height: 38px; border-radius: 50%; border: none; background: rgba(255,255,255,.14); color: #fff; font-size: 18px; cursor: pointer; z-index: 2; }
.player { width: min(960px, 92vw); display: flex; flex-direction: column; gap: 10px; }
.player-video { width: 100%; max-height: 78vh; background: #000; border-radius: var(--radius-md); }
.player-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: #fff; }
.player-title { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.defs { display: flex; gap: 6px; }
.def-btn { background: rgba(255,255,255,.14); border: none; color: #fff; border-radius: var(--radius-xs); padding: 4px 10px; font-size: 12px; cursor: pointer; }
.def-btn.active { background: var(--accent); }
.lightbox { max-width: 92vw; max-height: 88vh; object-fit: contain; border-radius: var(--radius-md); }

.sheet { background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-sheet); width: min(440px, 92vw); padding: 18px; display: flex; flex-direction: column; gap: 12px; box-shadow: var(--shadow-sheet); }
.sheet-narrow { width: min(360px, 92vw); }
.sheet-head { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.sheet-crumbs { font-size: 13px; }
.sheet-list { max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.sheet-hint { color: var(--text-muted); font-size: 13px; padding: 16px 4px; text-align: center; }
.sheet-row { text-align: left; background: none; border: none; color: var(--text-primary); font-size: 13px; padding: 9px 10px; border-radius: var(--radius-control); cursor: pointer; }
.sheet-row:hover { background: var(--surface-control-hover); }
.sheet-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
