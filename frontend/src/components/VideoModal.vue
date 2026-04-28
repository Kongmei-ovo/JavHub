<template>
  <!-- 单根节点包裹，teleport 放在内部 -->
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
            
            <div class="modal-actions">
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

              <button 
                class="favorite-btn" 
                :class="{ 'is-active': isFavorited }" 
                @click="toggleFavorite"
                :title="isFavorited ? '取消收藏' : '添加收藏'"
              >
                <svg viewBox="0 0 24 24" :fill="isFavorited ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l8.84-8.84 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                <span>{{ isFavorited ? '已收藏' : '收藏' }}</span>
              </button>
            </div>
          </div>

          <!-- 标题 -->
          <div class="modal-title-block">
            <h2 v-if="video.title_ja || video.title_en" class="modal-title" v-html="titleDisplay()"></h2>
            <div v-else class="skeleton skeleton-title"></div>
          </div>

          <!-- 基本数据 -->
          <div class="modal-meta">
            <div class="meta-row">
              <span class="meta-label">DVD编号</span>
              <span v-if="video.dvd_id" class="meta-value">{{ video.dvd_id }}</span>
              <div v-else class="skeleton skeleton-text"></div>
            </div>
            <div class="meta-row">
              <span class="meta-label">发行日期</span>
              <span v-if="video.release_date" class="meta-value">{{ video.release_date }}</span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">时长</span>
              <span v-if="video.runtime_mins" class="meta-value">{{ video.runtime_mins }} 分钟</span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">工作室</span>
              <span v-if="video.maker" class="meta-value clickable" @click="$emit('navigate', { type: 'maker', item: video.maker })">
                <span v-html="itemDisplayName(video.maker)"></span>
              </span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">厂牌</span>
              <span v-if="video.label" class="meta-value clickable" @click="$emit('navigate', { type: 'maker', item: video.label })">
                <span v-html="itemDisplayName(video.label)"></span>
              </span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">系列</span>
              <span v-if="video.series" class="meta-value clickable" @click="$emit('navigate', { type: 'series', item: video.series })" v-html="itemDisplayName(video.series, 'name', 'name')"></span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">导演</span>
              <span v-if="video.director" class="meta-value">{{ video.director }}</span>
              <div v-else-if="!metadataLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">评分</span>
              <span v-if="video.score && video.score > 0" class="meta-value">
                {{ video.score.toFixed(1) }}
                <span v-if="video.meta_provider" class="meta-provider">({{ video.meta_provider }})</span>
              </span>
              <div v-else-if="!metadataLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
          </div>

          <!-- 简介 -->
          <div class="modal-section">
            <h4 class="section-title">简介</h4>
            <p v-if="video.summary" class="summary-text">{{ video.summary }}</p>
            <div v-else-if="!metadataLoaded" class="skeleton-summary">
              <div class="skeleton skeleton-line"></div>
              <div class="skeleton skeleton-line"></div>
              <div class="skeleton skeleton-line w-60"></div>
            </div>
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
                <div class="actress-name" v-html="actressNameDisplay(actress)"></div>
              </div>
            </div>
          </div>
          <div v-else-if="!videoLoaded" class="modal-section">
             <h4 class="section-title">演员</h4>
             <div class="actress-list">
               <div v-for="n in 3" :key="n" class="actress-avatar-item">
                 <div class="actress-avatar skeleton"></div>
                 <div class="skeleton skeleton-text w-60" style="margin-top: 4px"></div>
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
                <span v-html="itemDisplayName(cat)"></span>
              </span>
            </div>
          </div>
          <div v-else-if="!videoLoaded" class="modal-section">
            <h4 class="section-title">题材</h4>
            <div class="actress-list">
              <span v-for="n in 5" :key="n" class="actress-tag skeleton" style="width: 60px; height: 24px"></span>
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
          <div v-else-if="!videoLoaded" class="modal-section">
            <h4 class="section-title">剧照</h4>
            <div class="gallery-grid">
              <div v-for="n in 6" :key="n" class="gallery-item skeleton"></div>
            </div>
          </div>

          <!-- 磁力链接 -->
          <div v-if="magnets.length" class="modal-section">
            <h4 class="section-title">磁力链接</h4>
            <div class="magnets-list">
              <div v-for="(mag, idx) in magnets" :key="idx" class="magnet-item">
                <div class="magnet-info">
                  <span v-if="mag.quality || mag.resolution" class="magnet-badge">{{ mag.quality || mag.resolution }}</span>
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
          <div v-else-if="!videoLoaded" class="modal-section">
             <h4 class="section-title">磁力链接</h4>
             <div class="magnets-list">
               <div v-for="n in 2" :key="n" class="magnet-item skeleton" style="height: 44px"></div>
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

    <!-- 视频预览弹窗 -->
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
          <button class="vp-close" @click="closeVideoPlayer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
          <div class="vp-player-wrap">
            <video ref="videoEl" :src="video.sample_url" class="vp-video" controls autoplay playsinline @keydown.left.prevent="seekBackward" @keydown.right.prevent="seekForward"></video>
          </div>
          <div class="vp-info">
            <span class="vp-title">{{ video.dvd_id || video.content_id }}</span>
            <div class="vp-speed-ctrl">
              <button v-for="s in [0.5, 0.75, 1, 1.25, 1.5, 2]" :key="s" :class="['vp-speed-btn', { active: videoSpeed === s }]" @click="setSpeed(s)">{{ s === 1 ? '1x' : s + 'x' }}</button>
            </div>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script>
import { displayName, displayLang } from '../utils/displayLang.js'
import { jacketFullUrl, galleryFullUrl, galleryThumbUrl } from '../utils/imageUrl.js'
import favoriteState from '../utils/favoriteState'
import api from '../api'

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
  computed: {
    isFavorited() {
      const id = this.video.dvd_id || this.video.content_id
      return favoriteState.isFavorited('video', id)
    },
    videoLoaded() {
      // 基本信息（dvd_id / release_date）已到就认为数据可用，不等待 categories/actresses
      return !!(this.video.dvd_id || this.video.release_date || this.video.content_id)
    },
    metadataLoaded() {
      // 通过是否存在外部元数据判定扩展请求是否完成
      return !!(this.video.summary || this.video.score || this.video.director)
    },
    magnets() { return this.video?.magnets || [] },
    coverImageUrl() {
      if (!this.video) return '/placeholder.png'
      const fullUrl = this.video.jacket_full_url
      let hiResUrl = null
      if (fullUrl) hiResUrl = fullUrl.startsWith('http') ? jacketFullUrl(fullUrl) || fullUrl : jacketFullUrl(fullUrl)
      const thumbUrl = this.video.jacket_thumb_url
      if (!hiResUrl && thumbUrl) hiResUrl = thumbUrl.startsWith('http') ? jacketFullUrl(thumbUrl) || thumbUrl : jacketFullUrl(thumbUrl)
      return hiResUrl || '/placeholder.png'
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
      for (let i = firstNum; i <= lastNum; i++) { thumbs.push(`${prefix}${i}`) }
      return thumbs
    },
  },
  methods: {
    async toggleFavorite() {
      const id = this.video.dvd_id || this.video.content_id
      if (!id) return
      try {
        await favoriteState.toggle('video', id, {
          title: this.video.title_ja || this.video.title_en,
          cover_url: this.coverImageUrl
        })
      } catch (err) {
        console.error('Failed to toggle favorite:', err)
      }
    },
    actressNameDisplay(actress) {
      if (!actress) return ''
      const lang = displayLang.value
      // 演员翻译：原文换行译文
      const orig = lang === 'en' ? (actress.name_romaji || actress.name_kanji || '') : (actress.name_kanji || actress.name_romaji || '')
      const trans = lang === 'en' ? (actress.name_romaji_translated || '') : (actress.name_kanji_translated || '')
      if (trans && trans !== orig) {
        return `${this.escapeHtml(orig)}<br>${this.escapeHtml(trans)}`
      }
      return this.escapeHtml(orig)
    },
    titleDisplay() {
      if (!this.video) return ''
      const lang = displayLang.value
      const orig = lang === 'en' ? (this.video.title_en || this.video.title_ja || '') : (this.video.title_ja || this.video.title_en || '')
      const trans = lang === 'en' ? (this.video.title_en_translated || '') : (this.video.title_ja_translated || '')
      if (trans && trans !== orig) {
        return `${this.escapeHtml(orig)} / ${this.escapeHtml(trans)}`
      }
      return this.escapeHtml(orig)
    },
    escapeHtml(str) {
      if (!str) return ''
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    },
    itemDisplayName(item, jaField = 'name_ja', enField = 'name_en') {
      if (!item) return ''
      // 工作室/厂牌/系列：只显示译文（空间有限）
      const trans = item.name_translated || item[`${jaField}_translated`] || item[`${enField}_translated`] || ''
      if (trans) {
        return this.escapeHtml(trans)
      }
      // fallback 到原文
      const orig = (item[jaField] || item[enField] || item.name || '')
      return this.escapeHtml(orig)
    },

    displayName,
    handleImgError(e) { e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600"><rect fill="%231a1a2e" width="400" height="600"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>' },
    onAvatarError(e) {
      const span = document.createElement('span')
      span.className = 'avatar-placeholder'
      const name = e.target.alt || '?'
      span.textContent = name[0]
      e.target.parentNode.replaceChild(span, e.target)
    },
    onGalleryError(e) { e.target.style.display = 'none' },
    formatAvatarUrl(url) {
      if (!url) return null
      if (url.startsWith('http')) return url
      return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${url.replace(/^\//, '')}`
    },
    formatGalleryUrl(path) { return galleryFullUrl(path) || galleryThumbUrl(path) || null },
    closeVideoPlayer() { this.videoPlayerVisible = false },
    setSpeed(speed) { this.videoSpeed = speed; if (this.$refs.videoEl) this.$refs.videoEl.playbackRate = speed },
    seekForward() { if (this.$refs.videoEl) this.$refs.videoEl.currentTime += 10 },
    seekBackward() { if (this.$refs.videoEl) this.$refs.videoEl.currentTime -= 10 },
    async copyMagnet(mag) {
      try {
        await navigator.clipboard.writeText(mag.magnet || mag)
        if (this.$message) this.$message.success('磁链已复制')
      } catch (e) {}
    },
    openGalleryViewer(idx) { this.currentGalleryIndex = idx; this.galleryViewerVisible = true; window.addEventListener('keydown', this.onGalleryKeydown) },
    closeGalleryViewer() { this.galleryViewerVisible = false; window.removeEventListener('keydown', this.onGalleryKeydown) },
    prevGallery() { if (!this.galleryThumbs.length) return; this.currentGalleryIndex = (this.currentGalleryIndex - 1 + this.galleryThumbs.length) % this.galleryThumbs.length },
    nextGallery() { if (!this.galleryThumbs.length) return; this.currentGalleryIndex = (this.currentGalleryIndex + 1) % this.galleryThumbs.length },
    onGalleryKeydown(e) { if (e.key === 'Escape') this.closeGalleryViewer(); if (e.key === 'ArrowLeft') this.prevGallery(); if (e.key === 'ArrowRight') this.nextGallery() },
  },
  beforeUnmount() { window.removeEventListener('keydown', this.onGalleryKeydown) }
}
</script>

<style scoped>
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.85); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 40px; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }
.modal-container { background: var(--bg-card); border-radius: var(--radius-pro); border: var(--stroke-pro) solid var(--border-light); width: 100%; max-width: 900px; max-height: 90vh; overflow: hidden; position: relative; box-shadow: var(--ambient-glow); }
.modal-close { position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.3); border: var(--stroke-pro) solid rgba(255,255,255,0.1); width: 44px; height: 44px; border-radius: 50%; font-size: 24px; cursor: pointer; color: white; z-index: 10; transition: var(--transition-pro); backdrop-filter: blur(10px); }
.modal-close:hover { background: rgba(0,0,0,0.6); transform: scale(1.1); }
.modal-body { display: flex; flex-direction: column; max-height: 90vh; overflow-y: auto; }
.modal-gallery { width: 100%; background: var(--bg-secondary); display: flex; justify-content: center; align-items: flex-start; }
.gallery-img { width: 100%; max-height: 65vh; object-fit: contain; object-position: top center; }
.modal-content { padding: 48px 64px 64px; display: flex; flex-direction: column; gap: 48px; }
.modal-code-block { border-bottom: var(--stroke-pro) solid var(--accent); padding-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.modal-actions { display: flex; align-items: center; gap: 12px; }
.modal-code { font-size: 28px; font-weight: 700; color: var(--accent); font-family: var(--font-mono); letter-spacing: var(--ls-pro); }
.preview-btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px; background: var(--accent); color: var(--bg-primary); border-radius: 40px; font-size: 14px; font-weight: 600; text-decoration: none; transition: var(--transition-pro); flex-shrink: 0; border: none; cursor: pointer; }
.preview-btn:hover { background: var(--accent-light); transform: translateY(-2px); box-shadow: 0 10px 20px rgba(255,255,255,0.1); }
.favorite-btn { display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px; background: var(--bg-secondary); color: var(--text-primary); border-radius: 40px; font-size: 14px; font-weight: 600; transition: var(--transition-pro); flex-shrink: 0; border: var(--stroke-pro) solid var(--border); cursor: pointer; }
.favorite-btn:hover { border-color: var(--text-secondary); background: var(--white-06); }
.favorite-btn.is-active { background: rgba(212, 175, 55, 0.1); border-color: rgba(212, 175, 55, 0.4); color: #FFD60A; }
.favorite-btn.is-active:hover { background: rgba(212, 175, 55, 0.2); }
.favorite-btn svg { width: 16px; height: 16px; transition: transform 0.3s var(--ease-pro); }
.favorite-btn:active svg { transform: scale(0.8); }
.modal-title-block { border-bottom: var(--stroke-pro) solid var(--border); padding-bottom: 16px; }
.modal-title { font-size: 18px; color: var(--text-primary); font-weight: 600; line-height: 1.6; letter-spacing: var(--ls-pro); }
.modal-meta { background: var(--bg-secondary); border-radius: var(--radius-md); padding: 24px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0; position: relative; border: var(--stroke-pro) solid var(--border); }
.modal-meta::before { content: ''; position: absolute; left: 50%; top: 24px; bottom: 24px; width: 1px; background: var(--border); transform: translateX(-50%); }
.meta-row { display: flex; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.meta-row:last-child { border-bottom: none; }
.modal-meta > div:nth-last-child(-n+2) { border-bottom: none; }
.meta-label { color: var(--text-muted); font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.meta-value { color: var(--text-primary); font-size: 14px; font-family: var(--font-mono); }
.meta-value--empty { color: var(--text-muted); font-style: italic; }
.clickable { color: var(--accent); cursor: pointer; transition: color 0.2s; }
.clickable:hover { color: var(--accent-light); text-decoration: none; }
.modal-section { margin-top: 0; }
.section-title { font-size: 12px; font-weight: 700; margin-bottom: 20px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em; }
.actress-list { display: flex; flex-wrap: wrap; gap: 20px; }
.actress-avatar-item { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; }
.actress-avatar { width: 64px; height: 64px; border-radius: 50%; overflow: hidden; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; border: var(--stroke-pro) solid var(--border); transition: var(--transition-pro); }
.actress-avatar-item:hover .actress-avatar { border-color: var(--accent); transform: translateY(-4px); }
.actress-avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder { width: 64px; height: 64px; border-radius: 50%; background: var(--bg-secondary); display: flex; align-items: center; justify-content: center; font-size: 24px; color: var(--text-muted); border: var(--stroke-pro) solid var(--border); }
.actress-name { display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 13px; color: var(--text-secondary); text-align: center; max-width: 80px; overflow: hidden; text-overflow: ellipsis; transition: color 0.2s; }
.actress-name .name-orig { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.actress-name .name-translated { font-size: 11px; color: var(--accent); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.actress-avatar-item:hover .actress-name { color: var(--accent); }
.actress-tag { padding: 8px 18px; background: var(--bg-secondary); border-radius: 40px; font-size: 13px; color: var(--text-secondary); border: var(--stroke-pro) solid var(--border); transition: var(--transition-pro); }
.actress-tag:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-bg); }
.magnets-list { display: flex; flex-direction: column; gap: 12px; }
.magnet-item { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; background: var(--bg-secondary); border-radius: var(--radius-md); border: var(--stroke-pro) solid var(--border); transition: var(--transition-pro); }
.magnet-item:hover { border-color: var(--accent-light); background: var(--bg-card-hover); }
.magnet-info { display: flex; align-items: center; gap: 12px; }
.magnet-badge { padding: 4px 10px; background: var(--badge-info-bg); color: var(--badge-info-text); border: 1px solid var(--badge-info-border); font-size: 11px; font-weight: 700; border-radius: 6px; }
.magnet-badge.hd { background: var(--badge-success-bg); color: var(--badge-success-text); border-color: var(--badge-success-border); }
.magnet-badge.sub { background: var(--badge-warning-bg); color: var(--badge-warning-text); border-color: var(--badge-warning-border); }
.magnet-size { font-size: 14px; color: var(--text-secondary); font-family: var(--font-mono); }
.magnet-actions { display: flex; gap: 12px; }
.btn-copy { background: transparent; border: var(--stroke-pro) solid var(--border); padding: 8px 18px; border-radius: 40px; cursor: pointer; color: var(--text-secondary); font-size: 13px; transition: var(--transition-pro); }
.btn-copy:hover { border-color: var(--text-secondary); color: var(--text-primary); }
.btn-download { background: var(--accent); color: var(--bg-primary); border: none; padding: 8px 24px; border-radius: 40px; cursor: pointer; font-size: 14px; font-weight: 600; transition: var(--transition-pro); }
.btn-download:hover { background: var(--accent-light); transform: translateY(-2px); }
.no-magnets { text-align: center; padding: 32px; color: var(--text-muted); font-size: 15px; border: var(--stroke-pro) dashed var(--border); border-radius: var(--radius-md); }
.meta-provider { font-size: 12px; color: var(--text-muted); margin-left: 4px; }
.summary-text { font-size: 15px; line-height: 1.8; color: var(--text-secondary); background: var(--bg-secondary); border-radius: var(--radius-md); padding: 24px; margin: 0; max-height: 200px; overflow-y: auto; border: var(--stroke-pro) solid var(--border); }
.summary-text--empty { color: var(--text-muted); font-style: italic; }
.gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
.gallery-item { aspect-ratio: 16/9; overflow: hidden; border-radius: var(--radius-md); background: var(--bg-secondary); cursor: pointer; border: var(--stroke-pro) solid var(--border); transition: var(--transition-pro); }
.gallery-item:hover { border-color: var(--accent); transform: scale(1.02); }
.gallery-item img { width: 100%; height: 100%; object-fit: cover; transition: var(--transition-pro); }
.gallery-item:hover img { filter: saturate(1.2); }
.skeleton { background: var(--bg-card-hover); position: relative; overflow: hidden; border-radius: 8px; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--white-06), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
.skeleton-title { height: 32px; width: 80%; }
.skeleton-text { height: 20px; width: 60px; }
.skeleton-line { height: 16px; margin-bottom: 12px; width: 100%; }
.w-60 { width: 60% !important; }
.w-80 { width: 80% !important; }
.gallery-lightbox { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.95); display: flex; align-items: center; justify-content: center; z-index: 1001; animation: lightbox-in 0.3s var(--ease-pro); backdrop-filter: blur(20px); }
@keyframes lightbox-in { from { opacity: 0; backdrop-filter: blur(0); } to { opacity: 1; backdrop-filter: blur(20px); } }
.lightbox-img-wrap { max-width: 95vw; max-height: 90vh; display: flex; align-items: center; justify-content: center; }
.lightbox-img { max-width: 95vw; max-height: 90vh; object-fit: contain; border-radius: 8px; box-shadow: 0 20px 80px rgba(0,0,0,0.8); }
.lightbox-close { position: absolute; top: 32px; right: 32px; background: rgba(255,255,255,0.1); border: var(--stroke-pro) solid rgba(255,255,255,0.1); width: 48px; height: 48px; border-radius: 50%; font-size: 28px; color: #fff; cursor: pointer; transition: var(--transition-pro); z-index: 2; }
.lightbox-close:hover { background: rgba(255,255,255,0.2); transform: scale(1.1); }
.lightbox-prev, .lightbox-next { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(255,255,255,0.05); border: none; width: 60px; height: 100px; font-size: 40px; color: #fff; cursor: pointer; transition: var(--transition-pro); display: flex; align-items: center; justify-content: center; border-radius: 12px; }
.lightbox-prev { left: 32px; } .lightbox-next { right: 32px; }
.lightbox-prev:hover, .lightbox-next:hover { background: rgba(255,255,255,0.15); }
.lightbox-prev:disabled, .lightbox-next:disabled { opacity: 0.1; cursor: not-allowed; }
.lightbox-counter { position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,0.5); font-size: 15px; letter-spacing: 0.1em; font-family: var(--font-mono); }
.vp-overlay { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(32px) saturate(180%); -webkit-backdrop-filter: blur(32px) saturate(180%); animation: fadeIn 0.4s var(--ease-pro); }
.vp-container { position: relative; width: 90vw; max-width: 1080px; display: flex; flex-direction: column; gap: 24px; }
.vp-close { position: absolute; top: -60px; right: 0; background: rgba(255,255,255,0.08); border: var(--stroke-pro) solid rgba(255,255,255,0.12); border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.7); cursor: pointer; transition: var(--transition-pro); }
.vp-close:hover { background: rgba(255,255,255,0.15); color: #fff; transform: rotate(90deg); }
.vp-player-wrap { border-radius: 20px; overflow: hidden; box-shadow: 0 40px 120px rgba(0,0,0,0.8); background: #000; border: var(--stroke-pro) solid rgba(255,255,255,0.1); }
.vp-video { display: block; width: 100%; border-radius: 20px; background: #000; }
.vp-info { display: flex; align-items: center; justify-content: space-between; padding: 0 8px; }
.vp-title { font-size: 14px; color: rgba(255,255,255,0.5); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--font-mono); }
.vp-speed-ctrl { display: flex; align-items: center; gap: 8px; }
.vp-speed-btn { font-size: 13px; padding: 5px 14px; background: rgba(255,255,255,0.07); border: var(--stroke-pro) solid rgba(255,255,255,0.1); border-radius: 40px; color: rgba(255,255,255,0.5); cursor: pointer; transition: var(--transition-pro); }
.vp-speed-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.9); border-color: rgba(255,255,255,0.2); }
.vp-speed-btn.active { background: var(--accent); border-color: var(--accent); color: var(--bg-primary); font-weight: 700; }
</style>
