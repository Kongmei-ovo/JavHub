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

  <!-- 视频预览弹窗：Teleport 避免 el-dialog 样式污染 -->
  <teleport to="body">
    <div
      v-if="videoPlayerVisible && video.sample_url"
      class="vp-overlay"
      @click.self="closeVideoPlayer"
      @keydown.esc="closeVideoPlayer"
      @keydown.left.prevent="seekBackward"
      @keydown.right.prevent="seekForward"
      tabindex="0"
      ref="vpOverlay"
    >
      <div class="vp-container">
        <!-- 关闭按钮 -->
        <button class="vp-close" @click="closeVideoPlayer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>

        <!-- 原生播放器：最稳定，macOS Safari/Chrome 兼容性最好 -->
        <div class="vp-player-wrap">
          <video
            ref="videoEl"
            :src="video.sample_url"
            class="vp-video"
            controls
            autoplay
            playsinline
            @keydown.left.prevent="seekBackward"
            @keydown.right.prevent="seekForward"
          ></video>
        </div>

        <!-- 底部信息栏 -->
        <div class="vp-info">
          <span class="vp-title">{{ video.dvd_id || video.content_id }}</span>
          <div class="vp-speed-ctrl">
            <button
              v-for="s in [0.5, 0.75, 1, 1.25, 1.5, 2]"
              :key="s"
              :class="['vp-speed-btn', { active: videoSpeed === s }]"
              @click="setSpeed(s)"
            >{{ s === 1 ? '1x' : s + 'x' }}</button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
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
    }
  },
  watch: {
    videoPlayerVisible(val) {
      if (!val) {
        // 关闭时暂停视频
        const v = this.$refs.videoEl
        if (v) { v.pause(); v.currentTime = 0 }
      }
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
    closeVideoPlayer() {
      this.videoPlayerVisible = false
    },
    setSpeed(speed) {
      this.videoSpeed = speed
      const v = this.$refs.videoEl
      if (v) v.playbackRate = speed
    },
    seekForward() {
      const v = this.$refs.videoEl
      if (v) v.currentTime = Math.min(v.currentTime + 10, v.duration || Infinity)
    },
    seekBackward() {
      const v = this.$refs.videoEl
      if (v) v.currentTime = Math.max(v.currentTime - 10, 0)
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

/* ===== Video Player (Apple QuickTime style — Teleport + Native) ===== */

.vp-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
}

.vp-container {
  position: relative;
  width: 90vw;
  max-width: 960px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.vp-close {
  position: absolute;
  top: -50px;
  right: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 50%;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.vp-close:hover {
  background: rgba(255,255,255,0.15);
  color: #fff;
}

.vp-player-wrap {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 32px 100px rgba(0,0,0,0.7);
  background: #000;
}

/* 原生 video 控件样式重写 */
.vp-video {
  display: block;
  width: 100%;
  border-radius: 12px;
  background: #000;
}

/* 底部信息栏 */
.vp-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.vp-title {
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  font-weight: 500;
  letter-spacing: 0.06em;
}

.vp-speed-ctrl {
  display: flex;
  align-items: center;
  gap: 4px;
}

.vp-speed-btn {
  font-size: 12px;
  padding: 3px 10px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.vp-speed-btn:hover {
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.9);
  border-color: rgba(255,255,255,0.2);
}
.vp-speed-btn.active {
  background: rgba(139,92,246,0.25);
  border-color: rgba(139,92,246,0.5);
  color: var(--accent, #8B5CF6);
}
</style>
