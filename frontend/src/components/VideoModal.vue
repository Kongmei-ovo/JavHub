<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container">
      <button class="modal-close" @click="$emit('close')">×</button>

      <div class="modal-body">
        <!-- 顶部大图 -->
        <div class="modal-gallery">
          <img
            :src="coverImageUrl"
            :alt="video.dvd_id || video.content_id"
            @error="handleImgError"
            class="gallery-img"
          />
        </div>

        <!-- 下方信息 -->
        <div class="modal-content">
          <!-- 番号 -->
          <div class="modal-code-block">
            <span class="modal-code">{{ video.dvd_id || video.content_id }}</span>
            <button
              v-if="video.sample_url"
              class="preview-btn"
              title="观看预览"
              @click="videoPlayerVisible = true"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M8 5v14l11-7z"/>
              </svg>
              预览
            </button>
          </div>

          <!-- 标题 -->
          <div class="modal-title-block">
            <h2 class="modal-title" v-html="titleDisplay()"></h2>
          </div>

          <!-- 基本数据 -->
          <div class="modal-meta">
            <div v-if="video.dvd_id" class="meta-row">
              <span class="meta-label">DVD编号</span>
              <span class="meta-value">{{ video.dvd_id }}</span>
            </div>
            <div v-if="video.release_date" class="meta-row">
              <span class="meta-label">发行日期</span>
              <span class="meta-value">{{ video.release_date }}</span>
            </div>
            <div v-if="video.runtime_mins" class="meta-row">
              <span class="meta-label">时长</span>
              <span class="meta-value">{{ video.runtime_mins }} 分钟</span>
            </div>
            <div v-if="video.maker" class="meta-row">
              <span class="meta-label">工作室</span>
              <span class="meta-value clickable" @click="$emit('navigate', { type: 'maker', item: video.maker })">
                {{ displayName(video.maker) }}
              </span>
            </div>
            <div v-if="video.label" class="meta-row">
              <span class="meta-label">厂牌</span>
              <span class="meta-value">{{ displayName(video.label) }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">系列</span>
              <span v-if="video.series" class="meta-value clickable" @click="$emit('navigate', { type: 'series', item: video.series })" v-html="itemDisplayName(video.series, &quot;name&quot;, &quot;name&quot;)"></span>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">导演</span>
              <span v-if="video.director" class="meta-value">{{ video.director }}</span>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">评分</span>
              <span v-if="video.score && video.score > 0" class="meta-value">
                {{ video.score.toFixed(1) }}
                <span v-if="video.meta_provider" class="meta-provider">({{ video.meta_provider }})</span>
              </span>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
          </div>

          <!-- 简介 -->
          <div class="modal-section">
            <h4 class="section-title">简介</h4>
            <p v-if="video.summary" class="summary-text">{{ video.summary }}</p>
            <p v-else class="summary-text summary-text--empty">暂无简介</p>
          </div>

          <!-- 演员 -->
          <div v-if="video.actresses && video.actresses.length" class="modal-section">
            <h4 class="section-title">演员</h4>
            <div class="actress-list">
              <div
                v-for="actress in video.actresses"
                :key="actress.id"
                class="actress-avatar-item clickable"
                @click="$emit('navigate', { type: 'actress', item: actress })"
              >
                <div class="actress-avatar">
                  <img
                    v-if="actress.image_url"
                    :src="formatAvatarUrl(actress.image_url)"
                    :alt="displayName(actress, 'name_kanji', 'name_romaji')"
                    @error="onAvatarError($event)"
                  />
                  <span v-else class="avatar-placeholder">{{ (displayName(actress, 'name_kanji', 'name_romaji') || '?')[0] }}</span>
                </div>
                <span class="actress-name" v-html="transName(actress, 'name_kanji', 'name_romaji', 'name_kanji_translated', 'name_romaji_translated')"></span>
              </div>
            </div>
          </div>

          <!-- 题材 -->
          <div v-if="video.categories && video.categories.length" class="modal-section">
            <h4 class="section-title">题材</h4>
            <div class="actress-list">
              <span
                v-for="cat in video.categories"
                :key="cat.id"
                class="actress-tag clickable"
                @click="$emit('navigate', { type: 'category', item: cat })"
              >
                <span v-html="itemDisplayName(cat) || displayName(cat)"></span>
              </span>
            </div>
          </div>

          <!-- 剧照画廊 -->
          <div v-if="galleryThumbs.length" class="modal-section">
            <h4 class="section-title">剧照</h4>
            <div class="gallery-grid">
              <div v-for="(thumb, idx) in galleryThumbs" :key="idx" class="gallery-item" @click="openGalleryViewer(idx)">
                <img :src="formatGalleryUrl(thumb)" :alt="'剧照 ' + (idx + 1)" loading="lazy" @error="onGalleryError" />
              </div>
            </div>
          </div>

          <!-- 磁力链接 -->
          <div v-if="magnets.length" class="modal-section">
            <h4 class="section-title">磁力链接</h4>
            <div class="magnets-list">
              <div
                v-for="(mag, idx) in magnets"
                :key="idx"
                class="magnet-item"
              >
                <div class="magnet-info">
                  <span v-if="mag.quality || mag.resolution" class="magnet-badge">
                    {{ mag.quality || mag.resolution }}
                  </span>
                  <span v-if="mag.hd" class="magnet-badge hd">HD</span>
                  <span v-if="mag.subtitle" class="magnet-badge sub">字幕</span>
                  <span class="magnet-size">{{ mag.size }}</span>
                </div>
                <div class="magnet-actions">
                  <button class="btn-copy" @click="copyMagnet(mag)" title="复制磁链">复制</button>
                  <button class="btn-download" @click="$emit('download', mag)">下载</button>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="no-magnets">
            <span>暂无磁力链接</span>
          </div>
        </div>
      </div>

      <!-- 剧照 Lightbox -->
      <div v-if="galleryViewerVisible" class="gallery-lightbox" @click.self="closeGalleryViewer">
        <button class="lightbox-close" @click="closeGalleryViewer">×</button>
        <button class="lightbox-prev" @click="prevGallery" :disabled="galleryThumbs.length <= 1">‹</button>
        <div class="lightbox-img-wrap">
          <img
            :src="formatGalleryUrl(galleryThumbs[currentGalleryIndex])"
            :alt="'剧照 ' + (currentGalleryIndex + 1)"
            class="lightbox-img"
            @error="$event.target.src = galleryThumbUrl(galleryThumbs[currentGalleryIndex])"
          />
        </div>
        <button class="lightbox-next" @click="nextGallery" :disabled="galleryThumbs.length <= 1">›</button>
        <div class="lightbox-counter">{{ currentGalleryIndex + 1 }} / {{ galleryThumbs.length }}</div>
      </div>
    </div>
  </div>

  <!-- 视频预览弹窗 -->
  <el-dialog
    v-if="videoPlayerVisible && video.sample_url"
    v-model="videoPlayerVisible"
    :title="'预览 ' + (video.dvd_id || video.content_id)"
    width="860px"
    destroy-on-close
    class="video-player-dialog"
    @closed="onVideoClosed"
    @keydown.left.prevent="seekBackward"
    @keydown.right.prevent="seekForward"
    tabindex="0"
  >
    <div class="video-player-wrap" @mousemove="showControls = true" tabindex="-1">
      <video
        ref="videoPlayer"
        :src="video.sample_url"
        class="video-player"
        @timeupdate="onTimeUpdate"
        @loadedmetadata="onMetaLoaded"
        @play="playing = true"
        @pause="playing = false"
        @click="togglePlay"
        @keydown.left.prevent="seekBackward"
        @keydown.right.prevent="seekForward"
      ></video>

      <!-- 自定义控件条 -->
      <div class="vp-controls" :class="{ 'vp-controls-hide': !showControls }">
        <!-- 进度条 -->
        <div class="vp-progress" @click="seek($event)">
          <div class="vp-progress-track">
            <div class="vp-progress-fill" :style="{ width: progressPercent + '%' }"></div>
          </div>
        </div>

        <div class="vp-bottom">
          <div class="vp-left">
            <!-- 播放/暂停 -->
            <button class="vp-btn" @click="togglePlay">
              <svg v-if="!playing" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M8 5v14l11-7z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
            </button>
            <!-- 时间 -->
            <span class="vp-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
          </div>
          <div class="vp-right">
            <!-- 音量 -->
            <button class="vp-btn" @click="toggleMute">
              <svg v-if="volume === 0" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
              </svg>
            </button>
            <!-- 音量滑块 -->
            <input type="range" class="vp-volume" min="0" max="1" step="0.05" :value="volume" @input="setVolume" />

            <!-- 倍速 -->
            <el-dropdown trigger="click" @command="setSpeed">
              <button class="vp-btn vp-speed-btn">
                {{ videoSpeed === 1 ? '倍速' : videoSpeed + 'x' }}
                <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
                  <path d="M7 10l5 5 5-5z"/>
                </svg>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="s in [0.5, 0.75, 1, 1.25, 1.5, 2]" :key="s" :command="s" :class="{ 'is-active': videoSpeed === s }">
                    {{ s === 1 ? '正常' : s + 'x' }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

            <!-- 全屏 -->
            <button class="vp-btn" @click="toggleFullscreen">
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import { displayName, displayLang } from '../utils/displayLang.js'
import { jacketFullUrl, galleryFullUrl, galleryThumbUrl } from '../utils/imageUrl.js'

export default {
  name: 'VideoModal',
  props: {
    visible: { type: Boolean, default: false },
    video: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      galleryViewerVisible: false,
      currentGalleryIndex: 0,
      videoPlayerVisible: false,
      videoSpeed: 1,
      playing: false,
      currentTime: 0,
      duration: 0,
      volume: 1,
      showControls: true,
      controlsTimer: null,
    }
  },
  computed: {
    magnets() {
      return this.video?.magnets || []
    },
    coverImageUrl() {
      if (!this.video) return '/placeholder.png'
      // 优先用 jacket_full_url 构建高清
      const fullUrl = this.video.jacket_full_url
      let hiResUrl = null
      if (fullUrl) {
        hiResUrl = fullUrl.startsWith('http')
          ? jacketFullUrl(fullUrl) || fullUrl
          : jacketFullUrl(fullUrl)
      }
      // 退而求次：从 jacket_thumb_url 构建高清
      const thumbUrl = this.video.jacket_thumb_url
      if (!hiResUrl && thumbUrl) {
        hiResUrl = thumbUrl.startsWith('http')
          ? jacketFullUrl(thumbUrl) || thumbUrl
          : jacketFullUrl(thumbUrl)
      }
      if (!hiResUrl) return '/placeholder.png'
      // 高清 URL 如果是 awsimgsrc 或 pics.dmm 域名，走代理避免 CORS
      if (hiResUrl.startsWith('https://awsimgsrc.') || hiResUrl.startsWith('https://pics.')) {
        return `/api/proxy/image?url=${encodeURIComponent(hiResUrl)}`
      }
      return hiResUrl
    },
    galleryThumbs() {
      if (!this.video) return []
      const first = this.video.gallery_thumb_first
      const last = this.video.gallery_thumb_last
      if (!first || !last) return []
      const firstNum = parseInt(first.match(/(\d+)$/)?.[1] || '0')
      const lastNum = parseInt(last.match(/(\d+)$/)?.[1] || '0')
      if (isNaN(firstNum) || isNaN(lastNum) || firstNum > lastNum) return []
      const prefix = first.replace(/\d+$/, '')
      const thumbs = []
      for (let i = firstNum; i <= lastNum; i++) {
        thumbs.push(`${prefix}${i}`)
      }
      return thumbs
    },
    progressPercent() {
      if (!this.duration) return 0
      return (this.currentTime / this.duration) * 100
    },
  },
  methods: {
    // 返回翻译名称的 HTML：有译文时 "译文(原文)"，原文小字体
    transName(item, jaField, enField, jaTransField, enTransField) {
      if (!item) return ''
      const lang = displayLang.value
      const orig = lang === 'en' ? (item[enField] || item[jaField] || '') : (item[jaField] || item[enField] || '')
      const trans = lang === 'en' ? (item[enTransField] || '') : (item[jaTransField] || '')
      if (trans && trans !== orig) {
        return `${this.escapeHtml(trans)}<small class="orig-name">(${this.escapeHtml(orig)})</small>`
      }
      return this.escapeHtml(orig)
    },
    // 返回影片标题的翻译显示
    titleDisplay() {
      if (!this.video) return ''
      const lang = displayLang.value
      const orig = lang === 'en'
        ? (this.video.title_en || this.video.title_ja || '')
        : (this.video.title_ja || this.video.title_en || '')
      const trans = lang === 'en'
        ? (this.video.title_en_translated || '')
        : (this.video.title_ja_translated || '')
      if (trans && trans !== orig) {
        return `${this.escapeHtml(trans)}<small class="orig-name">(${this.escapeHtml(orig)})</small>`
      }
      return this.escapeHtml(orig)
    },
    escapeHtml(str) {
      if (!str) return ''
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    },
    // 通用的翻译+原文显示，item 可以是 actress/category/series
    itemDisplayName(item, jaField = 'name_ja', enField = 'name_en') {
      if (!item) return ''
      const lang = displayLang.value
      const orig = lang === 'en' ? (item[enField] || item[jaField] || '') : (item[jaField] || item[enField] || '')
      // 尝试找翻译字段
      const jaTrans = item[`${jaField}_translated`] || ''
      const enTrans = item[`${enField}_translated`] || ''
      const trans = lang === 'en' ? enTrans : jaTrans
      if (trans && trans !== orig) {
        return `${this.escapeHtml(trans)}<small class="orig-name">(${this.escapeHtml(orig)})</small>`
      }
      return this.escapeHtml(orig)
    },
    displayName,
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600"><rect fill="%231a1a2e" width="400" height="600"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    },
    onAvatarError(e) {
      const span = document.createElement('span')
      span.className = 'avatar-placeholder'
      const name = e.target.alt || '?'
      span.textContent = name[0]
      e.target.parentNode.replaceChild(span, e.target)
    },
    onGalleryError(e) {
      e.target.style.display = 'none'
    },
    formatAvatarUrl(url) {
      if (!url) return null
      if (url.startsWith('http')) return url
      return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${url.replace(/^\//, '')}`
    },
    formatGalleryUrl(path) {
      return galleryFullUrl(path) || galleryThumbUrl(path) || null
    },
    // ===== Video Player =====
    togglePlay() {
      const video = this.$refs.videoPlayer
      if (!video) return
      if (video.paused) {
        video.play()
      } else {
        video.pause()
      }
    },
    onTimeUpdate() {
      const video = this.$refs.videoPlayer
      if (video) this.currentTime = video.currentTime
    },
    onMetaLoaded() {
      const video = this.$refs.videoPlayer
      if (video) {
        this.duration = video.duration
        video.playbackRate = this.videoSpeed
        video.volume = this.volume
      }
    },
    seek(e) {
      const video = this.$refs.videoPlayer
      if (!video || !this.duration) return
      const rect = e.currentTarget.getBoundingClientRect()
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
      video.currentTime = ratio * this.duration
    },
    seekForward() {
      const video = this.$refs.videoPlayer
      if (video) video.currentTime = Math.min(video.currentTime + 10, this.duration)
    },
    seekBackward() {
      const video = this.$refs.videoPlayer
      if (video) video.currentTime = Math.max(video.currentTime - 10, 0)
    },
    setVolume(e) {
      this.volume = parseFloat(e.target.value)
      const video = this.$refs.videoPlayer
      if (video) video.volume = this.volume
    },
    toggleMute() {
      const video = this.$refs.videoPlayer
      if (!video) return
      if (this.volume > 0) {
        this._prevVolume = this.volume
        this.volume = 0
        video.volume = 0
      } else {
        this.volume = this._prevVolume || 1
        video.volume = this.volume
      }
    },
    setSpeed(speed) {
      this.videoSpeed = speed
      const video = this.$refs.videoPlayer
      if (video) video.playbackRate = speed
    },
    toggleFullscreen() {
      const wrap = this.$el.querySelector('.video-player-wrap')
      if (!wrap) return
      if (document.fullscreenElement) {
        document.exitFullscreen()
      } else {
        wrap.requestFullscreen()
      }
    },
    formatTime(sec) {
      if (!sec || isNaN(sec)) return '0:00'
      const m = Math.floor(sec / 60)
      const s = Math.floor(sec % 60)
      return `${m}:${s.toString().padStart(2, '0')}`
    },
    onVideoClosed() {
      const video = this.$refs.videoPlayer
      if (video) {
        video.pause()
        video.currentTime = 0
      }
      this.playing = false
      this.currentTime = 0
      this.duration = 0
    },
    async copyMagnet(mag) {
      try {
        await navigator.clipboard.writeText(mag.magnet || mag)
        if (this.$message) this.$message.success('磁链已复制')
      } catch (e) {
        if (this.$message) this.$message.error('复制失败')
      }
    },
    openGalleryViewer(idx) {
      this.currentGalleryIndex = idx
      this.galleryViewerVisible = true
      window.addEventListener('keydown', this.onGalleryKeydown)
    },
    closeGalleryViewer() {
      this.galleryViewerVisible = false
      window.removeEventListener('keydown', this.onGalleryKeydown)
    },
    prevGallery() {
      if (!this.galleryThumbs.length) return
      this.currentGalleryIndex = (this.currentGalleryIndex - 1 + this.galleryThumbs.length) % this.galleryThumbs.length
    },
    nextGallery() {
      if (!this.galleryThumbs.length) return
      this.currentGalleryIndex = (this.currentGalleryIndex + 1) % this.galleryThumbs.length
    },
    onGalleryKeydown(e) {
      if (e.key === 'Escape') this.closeGalleryViewer()
      if (e.key === 'ArrowLeft') this.prevGallery()
      if (e.key === 'ArrowRight') this.nextGallery()
    },
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onGalleryKeydown)
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 900px;
  max-height: 95vh;
  overflow: hidden;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(0,0,0,0.6);
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 22px;
  cursor: pointer;
  color: white;
  z-index: 10;
  transition: background 0.2s;
}

.modal-close:hover {
  background: rgba(0,0,0,0.8);
}


.modal-body {
  display: flex;
  flex-direction: column;
  max-height: 95vh;
  overflow-y: auto;
}

/* 顶部图片 */
.modal-gallery {
  width: 100%;
  background: var(--bg-secondary);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.gallery-img {
  width: 100%;
  max-height: 60vh;
  object-fit: contain;
  object-position: top center;
}

/* 下方信息 */
.modal-content {
  padding: 20px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.modal-code-block {
  border-bottom: 2px solid var(--accent);
  padding-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-code {
  font-size: 24px;
  font-weight: bold;
  color: var(--accent);
}

.preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  background: var(--accent);
  color: #fff;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.preview-btn:hover { opacity: 0.85; }

.modal-title-block {
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
}

.modal-title {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: normal;
  line-height: 1.5;
}

.modal-meta {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 12px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0;
  position: relative;
}

.modal-meta::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 12px;
  bottom: 12px;
  width: 1px;
  background: var(--border);
  transform: translateX(-50%);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border);
}

.meta-row:last-child {
  border-bottom: none;
}

.modal-meta > div:nth-last-child(-n+2) {
  border-bottom: none;
}

.meta-label {
  color: var(--text-muted);
  font-size: 13px;
}

.meta-value {
  color: var(--text-primary);
  font-size: 13px;
}

.meta-value--empty {
  color: var(--text-muted);
  font-style: italic;
}

.clickable {
  color: var(--accent);
  cursor: pointer;
}

.clickable:hover {
  text-decoration: underline;
}

.modal-section {
  margin-top: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.actress-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.actress-avatar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.actress-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--border);
  transition: border-color 0.2s;
}

.actress-avatar-item:hover .actress-avatar {
  border-color: var(--accent);
}

.actress-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--text-muted);
  border: 2px solid var(--border);
}

.actress-name {
  font-size: 11px;
  color: var(--text-secondary);
  text-align: center;
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actress-avatar-item:hover .actress-name {
  color: var(--accent);
}

/* 题材标签（恢复被误删的样式） */
.actress-tag {
  padding: 4px 10px;
  background: var(--bg-secondary);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.magnets-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.magnet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.magnet-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.magnet-badge {
  padding: 2px 6px;
  background: rgba(76, 175, 80, 0.2);
  color: var(--accent-light);
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
}

.magnet-badge.hd {
  background: rgba(33, 150, 243, 0.2);
  color: #42A5F5;
}

.magnet-badge.sub {
  background: rgba(255, 152, 0, 0.2);
  color: #FFA726;
}

.magnet-size {
  font-size: 12px;
  color: var(--text-muted);
}

.magnet-actions {
  display: flex;
  gap: 8px;
}

.btn-copy {
  background: none;
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 12px;
  transition: background 0.2s;
}

.btn-copy:hover {
  background: var(--bg-card);
}

.btn-download {
  background: var(--accent);
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  transition: opacity 0.2s;
}

.btn-download:hover {
  opacity: 0.9;
}

.no-magnets {
  text-align: center;
  padding: 16px;
  color: var(--text-muted);
  font-size: 13px;
}

.meta-provider {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}

.summary-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}

.summary-text--empty {
  color: var(--text-muted);
  font-style: italic;
}

/* 翻译原文小字 */
.orig-name {
  font-size: 0.75em;
  color: var(--text-muted);
  margin-left: 2px;
}

/* 剧照画廊 */
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}

.gallery-item {
  aspect-ratio: 16/9;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  cursor: pointer;
}

.gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
}

.gallery-item:hover img {
  transform: scale(1.05);
}

/* ========== Gallery Lightbox ========== */
.gallery-lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
  animation: lightbox-in 0.2s ease;
}
@keyframes lightbox-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.lightbox-img-wrap {
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lightbox-img {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.6);
}
.lightbox-close {
  position: absolute;
  top: 16px;
  right: 20px;
  background: rgba(255,255,255,0.12);
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 24px;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
  z-index: 2;
}
.lightbox-close:hover { background: rgba(255,255,255,0.22); }
.lightbox-prev,
.lightbox-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,0.1);
  border: none;
  width: 52px;
  height: 80px;
  font-size: 36px;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}
.lightbox-prev { left: 16px; }
.lightbox-next { right: 16px; }
.lightbox-prev:hover,
.lightbox-next:hover { background: rgba(255,255,255,0.22); }
.lightbox-prev:disabled,
.lightbox-next:disabled { opacity: 0.3; cursor: not-allowed; }
.lightbox-counter {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  letter-spacing: 0.05em;
}

/* ===== Video Player (iOS 26 glass style + dark theme) ===== */

/* el-dialog 遮罩层：blur 背景，视频本身不受影响 */
:deep(.el-overlay) {
  background: rgba(0, 0, 0, 0.3) !important;
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
}
:deep(.video-player-dialog) {
  background: rgba(15, 15, 28, 0.6) !important;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  box-shadow: 0 24px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
}
:deep(.el-dialog__header) {
  background: transparent;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding: 16px 20px;
}
:deep(.el-dialog__title) {
  color: rgba(255,255,255,0.9);
  font-size: 14px;
}
:deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(255,255,255,0.5);
}
:deep(.el-dialog__body) {
  background: transparent;
  padding: 0;
}

/* 播放器容器 */
.video-player-wrap {
  position: relative;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  outline: none;
}
.video-player {
  display: block;
  width: 100%;
  cursor: pointer;
}

/* 毛玻璃控件条 */
.vp-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 40px 16px 14px;
  background: linear-gradient(transparent, rgba(0,0,0,0.7));
  border-top: 1px solid rgba(255,255,255,0.06);
  transition: opacity 0.4s ease;
  border-radius: 0 0 12px 12px;
}
.vp-controls.vp-controls-hide {
  opacity: 0;
  pointer-events: none;
}

/* 进度条 */
.vp-progress {
  cursor: pointer;
  padding: 8px 0;
}
.vp-progress-track {
  height: 3px;
  background: rgba(255,255,255,0.15);
  border-radius: 3px;
  overflow: hidden;
}
.vp-progress-fill {
  height: 100%;
  background: var(--accent, #8B5CF6);
  border-radius: 3px;
  transition: width 0.05s linear;
  box-shadow: 0 0 8px var(--accent, #8B5CF6);
}
.vp-progress:hover .vp-progress-track {
  height: 5px;
}

/* 底部控件行 */
.vp-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.vp-left, .vp-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 按钮 */
.vp-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.85);
  cursor: pointer;
  padding: 5px 8px;
  border-radius: 8px;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.vp-btn:hover {
  background: rgba(255,255,255,0.15);
  color: #fff;
  border-color: rgba(255,255,255,0.2);
}

/* 时间 */
.vp-time {
  font-size: 12px;
  color: rgba(255,255,255,0.65);
  font-variant-numeric: tabular-nums;
  padding: 0 6px;
  letter-spacing: 0.02em;
}

/* 音量滑块 */
.vp-volume {
  width: 72px;
  height: 3px;
  cursor: pointer;
  accent-color: var(--accent, #8B5CF6);
  background: transparent;
}

/* 倍速按钮 */
.vp-speed-btn {
  font-size: 12px;
  padding: 5px 10px;
  gap: 4px;
}

/* el-dropdown 毛玻璃菜单 */
:deep(.el-dropdown-menu) {
  background: rgba(30, 30, 46, 0.9) !important;
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255,255,255,0.1) !important;
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
:deep(.el-dropdown-menu__item) {
  color: rgba(255,255,255,0.75);
  border-radius: 6px;
  font-size: 13px;
  padding: 6px 12px;
}
:deep(.el-dropdown-menu__item:hover),
:deep(.el-dropdown-menu__item.is-active) {
  background: rgba(139, 92, 246, 0.2) !important;
  color: var(--accent, #8B5CF6) !important;
}
</style>
