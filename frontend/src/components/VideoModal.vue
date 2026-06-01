<template>
  <teleport to="body" :disabled="inline">
    <div v-if="visible" class="modal-overlay" :class="{ inline }" @click.self="inline ? null : $emit('close')">
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
                class="stream-btn"
                @click="playStream"
                :disabled="streamLoading"
                title="在线播放"
              >
                <span v-if="streamLoading" class="spinner"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                <span>播放</span>
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
              <span v-if="video.label" class="meta-value clickable" @click="$emit('navigate', { type: 'label', item: video.label })">
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
              <span v-if="directorsDisplay" class="meta-value">{{ directorsDisplay }}</span>
              <div v-else-if="!metadataLoaded" class="skeleton skeleton-text"></div>
              <span v-else class="meta-value meta-value--empty">无</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">作者</span>
              <span v-if="video.authors && video.authors.length" class="meta-value">{{ authorsDisplay }}</span>
              <div v-else-if="!videoLoaded" class="skeleton skeleton-text"></div>
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
            <p v-if="summaryDisplay" class="summary-text">{{ summaryDisplay }}</p>
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

          <!-- 男优 -->
          <div v-if="video.actors && video.actors.length" class="modal-section">
            <h4 class="section-title">男优</h4>
            <div class="tag-list">
              <span
                v-for="actor in video.actors"
                :key="actor.id"
                class="actress-tag"
              >
                <span class="tag-label">{{ actor.name_kanji || actor.name_kana || '—' }}</span>
              </span>
            </div>
          </div>

          <!-- 题材 -->
          <div v-if="video.categories && video.categories.length" class="modal-section">
            <h4 class="section-title">题材</h4>
            <div class="tag-list">
              <span
                v-for="cat in video.categories"
                :key="cat.id"
                class="actress-tag clickable"
                @click="$emit('navigate', { type: 'category', item: cat })"
              >
                <span class="tag-label" v-html="itemDisplayName(cat)"></span>
              </span>
            </div>
          </div>
          <div v-else-if="!videoLoaded" class="modal-section">
            <h4 class="section-title">题材</h4>
            <div class="tag-list">
              <span v-for="n in 5" :key="n" class="actress-tag skeleton" style="width: 60px; height: 24px"></span>
            </div>
          </div>

          <VideoGallerySection
            :thumbs="galleryThumbs"
            :video-loaded="videoLoaded"
            @open="openGalleryViewer"
          />

          <VideoMagnetSection
            :magnets="magnets"
            :video-loaded="videoLoaded"
            @copy="copyMagnet"
            @download="$emit('download', $event)"
          />

          <!-- m3u8 下载 -->
          <div class="stream-actions" v-if="video">
            <button class="btn btn-primary stream-download-btn" @click="downloadStream" :disabled="streamLoading">
              <span v-if="streamLoading" class="spinner"></span>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              <span>m3u8 下载</span>
            </button>
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
      <VideoPlayerOverlay
        v-if="video.sample_url"
        ref="previewPlayer"
        :visible="videoPlayerVisible"
        :src="video.sample_url"
        :title="video.dvd_id || video.content_id"
        :speed="videoSpeed"
        @close="closeVideoPlayer"
        @speed="setSpeed"
        @seek-backward="seekBackward"
        @seek-forward="seekForward"
      />

      <!-- m3u8 在线播放弹窗 -->
      <HlsPlayerOverlay
        ref="streamPlayer"
        :visible="streamPlayerVisible"
        :title="video.dvd_id || video.content_id"
        :speed="streamSpeed"
        @close="closeStreamPlayer"
        @speed="setStreamSpeed"
      />
    </div>
  </teleport>
</template>

<script>
import { defineAsyncComponent } from 'vue'
import { displayName, displayLang } from '../utils/displayLang.js'
import { jacketFullUrl, galleryFullUrl, galleryThumbUrl } from '../utils/imageUrl.js'
import favoriteState from '../utils/favoriteState'
import api from '../api'
import { ElMessage } from '../utils/message.js'
import VideoGallerySection from '../features/video/VideoGallerySection.vue'
import VideoMagnetSection from '../features/video/VideoMagnetSection.vue'

const VideoPlayerOverlay = defineAsyncComponent(() => import('../features/video/VideoPlayerOverlay.vue'))
const HlsPlayerOverlay = defineAsyncComponent(() => import('../features/video/HlsPlayerOverlay.vue'))

function videoFavoriteId(video = {}) {
  const id = video.content_id || video.dvd_id
  const serviceCode = String(video.service_code || '').trim()
  return id && serviceCode ? `${id}::${serviceCode}` : id
}

export default {
  name: 'VideoModal',
  components: { VideoGallerySection, VideoMagnetSection, VideoPlayerOverlay, HlsPlayerOverlay },
  emits: ['close', 'download', 'navigate'],
  props: {
    visible: { type: Boolean, default: false },
    video: { type: Object, default: () => ({}) },
    inline: { type: Boolean, default: false }
  },
  data() {
    return {
      galleryViewerVisible: false,
      currentGalleryIndex: 0,
      videoPlayerVisible: false,
      videoSpeed: 1,
      streamLoading: false,
      streamPlayerVisible: false,
      streamM3u8Url: '',
      streamSpeed: 1,
      hlsInstance: null,
    }
  },
  computed: {
    isFavorited() {
      const id = videoFavoriteId(this.video)
      return favoriteState.isFavorited('video', id)
    },
    videoLoaded() {
      // 基本信息（dvd_id / release_date）已到就认为数据可用，不等待 categories/actresses
      return !!(this.video.dvd_id || this.video.release_date || this.video.content_id)
    },
    metadataLoaded() {
      if (this.video?._loading?.javinfo === false) return true
      if (this.video?._loading?.supplement === false) return true
      // 通过是否存在外部元数据判定扩展请求是否完成
      return !!(this.video.summary || this.video.score || this.video.directors?.length)
    },
    directorsDisplay() {
      if (this.video?.directors?.length) {
        return this.video.directors.map(d => d.name_kanji || d.name_romaji || d.name_kana).filter(Boolean).join('、')
      }
      return ''
    },
    authorsDisplay() {
      if (!this.video?.authors?.length) return ''
      return this.video.authors.map(a => a.name_kanji || a.name_kana).filter(Boolean).join('、')
    },
    summaryDisplay() {
      return this.video?.summary_translated || this.video?.summary || ''
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
      if (Array.isArray(this.video.sample_image_urls) && this.video.sample_image_urls.length) {
        return this.video.sample_image_urls
      }
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
  watch: {
    visible(val) {
      if (!val) {
        this.closeStreamPlayer()
        this.closeVideoPlayer()
        this.galleryViewerVisible = false
      }
    }
  },
  methods: {
    async toggleFavorite() {
      const id = videoFavoriteId(this.video)
      if (!id) return
      try {
        await favoriteState.toggle('video', id, {
          content_id: this.video.content_id || this.video.dvd_id,
          dvd_id: this.video.dvd_id,
          service_code: this.video.service_code || '',
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
    formatAvatarUrl(url) {
      if (!url) return null
      if (url.startsWith('http')) return url
      return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${url.replace(/^\//, '')}`
    },
    formatGalleryUrl(path) { return galleryFullUrl(path) || galleryThumbUrl(path) || null },
    closeVideoPlayer() { this.videoPlayerVisible = false },
    previewVideoEl() {
      return this.$refs.previewPlayer?.mediaElement?.()
    },
    streamVideoEl() {
      return this.$refs.streamPlayer?.mediaElement?.()
    },
    setSpeed(speed) { this.videoSpeed = speed; const video = this.previewVideoEl(); if (video) video.playbackRate = speed },
    seekForward() { const video = this.previewVideoEl(); if (video) video.currentTime += 10 },
    seekBackward() { const video = this.previewVideoEl(); if (video) video.currentTime -= 10 },
    async copyMagnet(mag) {
      try {
        await navigator.clipboard.writeText(mag.magnet || mag)
        ElMessage.success('磁链已复制')
      } catch (e) {}
    },
    openGalleryViewer(idx) { this.currentGalleryIndex = idx; this.galleryViewerVisible = true; window.addEventListener('keydown', this.onGalleryKeydown) },
    closeGalleryViewer() { this.galleryViewerVisible = false; window.removeEventListener('keydown', this.onGalleryKeydown) },
    prevGallery() { if (!this.galleryThumbs.length) return; this.currentGalleryIndex = (this.currentGalleryIndex - 1 + this.galleryThumbs.length) % this.galleryThumbs.length },
    nextGallery() { if (!this.galleryThumbs.length) return; this.currentGalleryIndex = (this.currentGalleryIndex + 1) % this.galleryThumbs.length },
    onGalleryKeydown(e) { if (e.key === 'Escape') this.closeGalleryViewer(); if (e.key === 'ArrowLeft') this.prevGallery(); if (e.key === 'ArrowRight') this.nextGallery() },
    async playStream() {
      const code = this.video?.dvd_id || this.video?.content_id
      if (!code) return
      this.streamLoading = true
      try {
        const resp = await api.getStreamUrl(code)
        const m3u8Url = resp.data?.data?.m3u8_url
        if (m3u8Url) {
          // 走后端代理，绕过 CORS
          this.streamM3u8Url = `/api/v1/stream/proxy?url=${encodeURIComponent(m3u8Url)}`
          this.streamPlayerVisible = true
          this.$nextTick(() => this.initHlsPlayer())
        } else {
          ElMessage.info('未找到播放地址')
        }
      } catch (e) {
        console.error('Get stream URL failed:', e)
        ElMessage.error('获取播放地址失败')
      } finally {
        this.streamLoading = false
      }
    },
    async waitForStreamVideoEl() {
      for (let i = 0; i < 20; i += 1) {
        await this.$nextTick()
        const video = this.streamVideoEl()
        if (video) return video
        await new Promise(resolve => setTimeout(resolve, 25))
      }
      return null
    },
    async initHlsPlayer() {
      const video = await this.waitForStreamVideoEl()
      if (!video) return
      if (this.hlsInstance) {
        this.hlsInstance.destroy()
        this.hlsInstance = null
      }
      const { default: Hls } = await import('hls.js/dist/hls.light.mjs')
      if (Hls.isSupported()) {
        const hls = new Hls()
        hls.loadSource(this.streamM3u8Url)
        hls.attachMedia(video)
        hls.on(Hls.Events.MANIFEST_PARSED, () => { video.play() })
        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                ElMessage.error('网络错误，视频加载失败')
                hls.startLoad()
                break
              case Hls.ErrorTypes.MEDIA_ERROR:
                ElMessage.error('视频解码错误')
                hls.recoverMediaError()
                break
              default:
                ElMessage.error('视频播放失败')
                this.closeStreamPlayer()
                break
            }
          }
        })
        this.hlsInstance = hls
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = this.streamM3u8Url
        video.addEventListener('loadedmetadata', () => { video.play() })
      }
    },
    closeStreamPlayer() {
      if (this.hlsInstance) {
        this.hlsInstance.destroy()
        this.hlsInstance = null
      }
      this.streamPlayerVisible = false
      this.streamM3u8Url = ''
    },
    setStreamSpeed(speed) {
      this.streamSpeed = speed
      const video = this.streamVideoEl()
      if (video) video.playbackRate = speed
    },
    async downloadStream() {
      const code = this.video?.dvd_id || this.video?.content_id
      if (!code) return
      this.streamLoading = true
      try {
        const resp = await api.getStreamUrl(code)
        const m3u8Url = resp.data?.data?.m3u8_url
        if (m3u8Url) {
          const a = document.createElement('a')
          a.href = m3u8Url
          a.download = `${this.video.dvd_id || this.video.content_id}.m3u8`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          ElMessage.success('m3u8 下载已开始')
        } else {
          ElMessage.info('未找到播放地址')
        }
      } catch (e) {
        console.error('Get stream URL failed:', e)
        ElMessage.error('获取播放地址失败')
      } finally {
        this.streamLoading = false
      }
    },
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onGalleryKeydown)
    if (this.hlsInstance) {
      this.hlsInstance.destroy()
      this.hlsInstance = null
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  --modal-sheet-bg: rgba(18, 18, 20, 0.64);
  --modal-sheet-fallback: rgba(18, 18, 20, 0.64);
  --modal-panel-bg: rgba(0, 0, 0, 0.24);
  --modal-panel-border: rgba(255, 255, 255, 0.18);
  --modal-gallery-bg: rgba(0, 0, 0, 0.22);
  --modal-overlay-bg: rgba(0, 0, 0, 0.20);
  --modal-text-muted: rgba(255, 255, 255, 0.58);
  --modal-action-primary-bg: var(--glass-active-material);
  --modal-action-secondary-bg: var(--material-glass-control);
  --modal-action-secondary-bg-hover: var(--material-glass-control-hover);
  --modal-action-border: var(--glass-control-border);
  --modal-action-border-hover: var(--glass-control-border-hover);
  --modal-action-color: var(--text-primary);
  --modal-action-shadow: var(--glass-control-shadow);
  --modal-action-shadow-hover: var(--glass-control-shadow-hover);
  --modal-chip-bg: var(--material-glass-control);
  --modal-chip-bg-hover: var(--material-glass-control-hover);
  --modal-chip-border: var(--glass-control-border);
  --modal-chip-border-hover: var(--glass-control-border-hover);
  --modal-chip-color: rgba(255, 255, 255, 0.82);
  --modal-chip-muted: rgba(255, 255, 255, 0.46);
  --modal-chip-shadow: var(--glass-control-shadow);
  --modal-chip-shadow-hover: var(--glass-control-shadow-hover);
  --modal-lightbox-bg: var(--surface-scrim, var(--scrim));
  --modal-lightbox-border: var(--glass-control-border);
  --modal-lightbox-image-shadow: var(--shadow-sheet);
  position: fixed;
  inset: 0;
  background: var(--modal-overlay-bg);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-lightbox);
  padding: 40px;
  transition: all 0.4s var(--ease-pro);
}

.modal-overlay.inline {
  position: static;
  inset: auto;
  z-index: auto;
  display: block;
  padding: 0;
  background: transparent;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.modal-overlay.inline .modal-container {
  width: min(100%, 980px);
  max-height: none;
  margin-inline: auto;
}

.modal-overlay.inline .modal-body {
  max-height: none;
}

:root[data-theme="dark"] .modal-overlay {
  --modal-sheet-bg: rgba(14, 14, 16, 0.68);
  --modal-sheet-fallback: rgba(14, 14, 16, 0.68);
  --modal-panel-bg: rgba(0, 0, 0, 0.28);
  --modal-panel-border: rgba(255, 255, 255, 0.14);
  --modal-gallery-bg: rgba(0, 0, 0, 0.28);
  --modal-overlay-bg: rgba(0, 0, 0, 0.26);
}

.modal-container {
  background: var(--modal-sheet-fallback);
  background: var(--modal-sheet-bg);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border-radius: var(--radius-pro);
  border: 1px solid var(--modal-panel-border);
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  overflow: hidden;
  position: relative;
  box-shadow: 0 42px 120px rgba(0, 0, 0, 0.36), inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.modal-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: var(--modal-chip-bg);
  border: 1px solid var(--modal-chip-border);
  width: 44px;
  height: 44px;
  border-radius: 50%;
  font-size: 24px;
  cursor: pointer;
  color: white;
  z-index: 10;
  box-shadow: var(--modal-chip-shadow);
  transition: var(--transition-pro);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.modal-close:hover {
  background: var(--modal-chip-bg-hover);
  border-color: var(--modal-chip-border-hover);
  box-shadow: var(--modal-chip-shadow-hover);
  transform: scale(1.1) rotate(90deg);
}

.modal-body {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow-y: auto;
  background: transparent;
}

.modal-gallery {
  width: 100%;
  background: var(--modal-gallery-bg);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.gallery-img { width: 100%; max-height: 65vh; object-fit: contain; object-position: top center; }
.modal-content { padding: 48px 64px 64px; display: flex; flex-direction: column; gap: 48px; }
.modal-code-block { border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.modal-actions { display: flex; align-items: center; gap: 12px; }
.modal-code { font-size: var(--type-entity-title); font-weight: 700; color: #ffffff; font-family: var(--font-mono); letter-spacing: 0; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }
.preview-btn,
.stream-btn,
.favorite-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: var(--modal-action-secondary-bg);
  color: var(--modal-action-color);
  border: 1px solid var(--modal-action-border);
  border-radius: var(--radius-control);
  font-size: var(--type-body);
  font-weight: 600;
  text-decoration: none;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast);
  flex-shrink: 0;
  cursor: pointer;
  box-shadow: var(--modal-action-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.preview-btn,
.stream-btn {
  background: var(--modal-action-primary-bg);
  border-color: var(--active-border);
}

.preview-btn:hover,
.stream-btn:hover:not(:disabled),
.favorite-btn:hover {
  background: var(--modal-action-secondary-bg-hover);
  border-color: var(--modal-action-border-hover);
  transform: translateY(-2px) scale(1.02);
  box-shadow: var(--modal-action-shadow-hover);
}

.preview-btn:hover,
.stream-btn:hover:not(:disabled) {
  background: var(--modal-action-primary-bg);
}

.preview-btn:active,
.stream-btn:active:not(:disabled),
.favorite-btn:active {
  transform: translateY(0) scale(0.98);
}
.stream-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.stream-btn svg { width: 16px; height: 16px; }
.favorite-btn.is-active {
  background: var(--modal-action-primary-bg);
  border-color: var(--active-border);
  color: var(--modal-action-color);
}
.favorite-btn.is-active:hover { background: var(--modal-action-primary-bg); }
.favorite-btn svg { width: 16px; height: 16px; transition: transform 0.3s var(--ease-pro); }
.favorite-btn:active svg { transform: scale(0.8); }
.modal-title-block { border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 16px; }
.modal-title { font-size: var(--type-panel-title); color: #ffffff; font-weight: 600; line-height: 1.6; letter-spacing: 0; text-shadow: 0 2px 8px rgba(0,0,0,0.4); }
.modal-meta { background: var(--modal-panel-bg); border-radius: var(--radius-lg); padding: 24px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0; position: relative; border: 1px solid var(--modal-panel-border); }
.modal-meta::before { content: ''; position: absolute; left: 50%; top: 24px; bottom: 24px; width: 1px; background: rgba(255, 255, 255, 0.08); transform: translateX(-50%); }
.meta-row { display: flex; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.meta-row:last-child { border-bottom: none; }
.modal-meta > div:nth-last-child(-n+2) { border-bottom: none; }
.meta-label { color: var(--modal-text-muted); font-size: var(--type-control); font-weight: 600; letter-spacing: 0; }
.meta-value { color: #ffffff; font-size: var(--type-body); font-family: var(--font-mono); font-weight: 500; }
.meta-value--empty { color: rgba(255, 255, 255, 0.2); font-style: italic; }
.clickable { color: #ffffff; cursor: pointer; transition: color 0.2s; text-decoration: underline; text-decoration-color: rgba(255,255,255,0.3); text-underline-offset: 4px; }
.clickable:hover { color: #ffffff; text-decoration-color: rgba(255,255,255,0.72); }
.modal-section { margin-top: 0; }
.section-title { font-size: var(--type-caption); font-weight: 650; margin-bottom: 14px; color: var(--modal-text-muted); letter-spacing: 0; }
.actress-list { display: flex; flex-wrap: wrap; gap: 20px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 12px; align-items: stretch; }
.actress-avatar-item { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; }
.actress-avatar { width: 64px; height: 64px; border-radius: 50%; overflow: hidden; background: var(--modal-chip-bg); display: flex; align-items: center; justify-content: center; border: 1px solid var(--modal-chip-border); box-shadow: var(--modal-chip-shadow); transition: var(--transition-pro); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.actress-avatar-item:hover .actress-avatar { background: var(--modal-chip-bg-hover); border-color: var(--modal-chip-border-hover); transform: translateY(-4px); box-shadow: var(--modal-chip-shadow-hover); }
.actress-avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder { width: 64px; height: 64px; border-radius: 50%; background: var(--modal-chip-bg); display: flex; align-items: center; justify-content: center; font-size: 24px; color: var(--modal-chip-muted); border: 1px solid var(--modal-chip-border); box-shadow: var(--modal-chip-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.actress-name { display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 13px; color: rgba(255, 255, 255, 0.8); text-align: center; max-width: 80px; overflow: hidden; text-overflow: ellipsis; transition: color 0.2s; }
.actress-name .name-orig { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.actress-name .name-translated { font-size: 11px; color: #ffffff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.actress-avatar-item:hover .actress-name { color: #ffffff; }
.actress-tag { display: inline-flex; align-items: center; justify-content: center; min-width: 0; max-width: 100%; padding: 8px 18px; background: var(--modal-chip-bg); border-radius: 40px; font-size: 13px; color: var(--modal-chip-color); border: 1px solid var(--modal-chip-border); box-shadow: var(--modal-chip-shadow); transition: var(--transition-pro); text-align: center; backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.actress-tag.clickable { text-decoration: none; text-decoration-color: transparent; }
.actress-tag:hover { border-color: var(--modal-chip-border-hover); color: white; background: var(--modal-chip-bg-hover); box-shadow: var(--modal-chip-shadow-hover); }
.tag-label { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; text-overflow: ellipsis; line-height: 1.35; overflow-wrap: anywhere; }
.meta-provider { font-size: 12px; color: rgba(255, 255, 255, 0.4); margin-left: 4px; }
.summary-text { font-size: 15px; line-height: 1.8; color: rgba(255, 255, 255, 0.9); background: var(--modal-panel-bg); border-radius: var(--radius-lg); padding: 24px; margin: 0; max-height: 200px; overflow-y: auto; border: 1px solid var(--modal-panel-border); }
.summary-text--empty { color: rgba(255, 255, 255, 0.3); font-style: italic; }
.skeleton { background: rgba(255, 255, 255, 0.05); position: relative; overflow: hidden; border-radius: 8px; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
.skeleton-title { height: 32px; width: 80%; }
.skeleton-text { height: 20px; width: 60px; }
.skeleton-line { height: 16px; margin-bottom: 12px; width: 100%; }
.w-60 { width: 60% !important; }
.w-80 { width: 80% !important; }
.gallery-lightbox { position: fixed; inset: 0; background: var(--modal-lightbox-bg); display: flex; align-items: center; justify-content: center; z-index: var(--z-lightbox); animation: lightbox-in 0.3s var(--ease-pro); transition: opacity var(--motion-standard), backdrop-filter var(--motion-standard); backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface)); -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface)); }
@keyframes lightbox-in { from { opacity: 0; backdrop-filter: blur(0) saturate(1); -webkit-backdrop-filter: blur(0) saturate(1); } to { opacity: 1; backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface)); -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface)); } }
.lightbox-img-wrap { max-width: 95vw; max-height: 90vh; display: flex; align-items: center; justify-content: center; }
.lightbox-img { max-width: 95vw; max-height: 90vh; object-fit: contain; border-radius: var(--radius-lg); border: 1px solid var(--modal-lightbox-border); box-shadow: var(--modal-lightbox-image-shadow); }
.lightbox-close { position: absolute; top: 32px; right: 32px; background: var(--modal-chip-bg); border: var(--stroke-pro) solid var(--modal-chip-border); width: 48px; height: 48px; border-radius: 50%; font-size: 28px; color: var(--modal-chip-color); cursor: pointer; transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast); z-index: 2; box-shadow: var(--modal-chip-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.lightbox-close:hover { background: var(--modal-chip-bg-hover); border-color: var(--modal-chip-border-hover); box-shadow: var(--modal-chip-shadow-hover); transform: scale(1.1); }
.lightbox-prev, .lightbox-next { position: absolute; top: 50%; transform: translateY(-50%); background: var(--modal-chip-bg); border: 1px solid var(--modal-chip-border); width: 60px; height: 100px; font-size: 40px; color: var(--modal-chip-color); cursor: pointer; transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast); display: flex; align-items: center; justify-content: center; border-radius: 12px; box-shadow: var(--modal-chip-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.lightbox-prev { left: 32px; } .lightbox-next { right: 32px; }
.lightbox-prev:hover, .lightbox-next:hover { background: var(--modal-chip-bg-hover); border-color: var(--modal-chip-border-hover); box-shadow: var(--modal-chip-shadow-hover); }
.lightbox-prev:disabled, .lightbox-next:disabled { opacity: 0.1; cursor: not-allowed; }
.lightbox-counter { position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%); background: var(--modal-chip-bg); border: 1px solid var(--modal-chip-border); border-radius: var(--radius-control); color: var(--modal-chip-color); font-size: 15px; letter-spacing: 0; font-family: var(--font-mono); padding: 8px 14px; box-shadow: var(--modal-chip-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.stream-actions { margin-top: 12px; }
.favorite-btn,
.stream-download-btn {
  background: var(--modal-action-secondary-bg);
  color: var(--modal-action-color);
  border: 1px solid var(--modal-action-border);
}
.stream-download-btn {
  width: 100%;
  justify-content: center;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 28px;
  border-radius: var(--radius-control);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard), opacity var(--motion-fast);
  box-shadow: var(--modal-action-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.stream-download-btn:hover:not(:disabled) {
  background: var(--modal-action-secondary-bg-hover);
  border-color: var(--modal-action-border-hover);
  transform: translateY(-2px);
  box-shadow: var(--modal-action-shadow-hover);
}
.stream-download-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
}
.stream-download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.stream-download-btn svg { width: 18px; height: 18px; }

@media (max-width: 768px) {
  .modal-overlay {
    align-items: flex-end;
    padding: 0;
    background: rgba(0, 0, 0, 0.18);
  }

  .modal-container {
    width: 100vw;
    max-width: none;
    height: 100dvh;
    max-height: 100dvh;
    border-radius: 22px 22px 0 0;
    border-inline: 0;
    border-bottom: 0;
  }

  .modal-overlay.inline .modal-container {
    width: 100%;
    height: auto;
    max-height: none;
    border-radius: 22px;
    border: 1px solid var(--modal-panel-border);
  }

  .modal-overlay.inline .modal-close {
    position: absolute;
    top: 12px;
    right: 12px;
  }

  .modal-overlay.inline .modal-body {
    height: auto;
    max-height: none;
  }

  .modal-close {
    position: fixed;
    top: calc(10px + env(safe-area-inset-top, 0px));
    right: 12px;
    width: var(--touch-target);
    height: var(--touch-target);
    font-size: 22px;
  }

  .modal-body {
    max-height: 100dvh;
    height: 100dvh;
    padding-bottom: env(safe-area-inset-bottom, 0px);
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .modal-gallery {
    height: min(42dvh, 320px);
    max-height: 42dvh;
    align-items: center;
  }

  .gallery-img {
    height: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  .modal-content {
    padding: 18px max(14px, env(safe-area-inset-right, 0px)) 28px max(14px, env(safe-area-inset-left, 0px));
    gap: 20px;
  }

  .modal-code-block {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding-bottom: 14px;
  }

  .modal-code {
    font-size: 22px;
    overflow-wrap: anywhere;
  }

  .modal-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
    gap: 8px;
    width: 100%;
  }

  .preview-btn,
  .stream-btn,
  .favorite-btn {
    justify-content: center;
    min-width: 0;
    min-height: var(--compact-toolbar-height);
    padding: 8px 10px;
    font-size: var(--type-caption);
    white-space: nowrap;
  }

  .modal-title {
    font-size: var(--type-card-title);
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .modal-meta {
    grid-template-columns: 1fr;
    padding: 12px;
    border-radius: 16px;
  }

  .modal-meta::before {
    display: none;
  }

  .modal-meta > div:nth-last-child(-n+2) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .modal-meta > div:last-child {
    border-bottom: none;
  }

  .meta-row {
    display: grid;
    grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
    gap: 10px;
    align-items: start;
    padding: 10px 6px;
  }

  .meta-label,
  .meta-value {
    overflow-wrap: anywhere;
  }

  .section-title {
    margin-bottom: 12px;
  }

  .actress-list {
    gap: 12px;
  }

  .tag-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(clamp(108px, 31vw, 148px), 1fr));
    gap: 8px;
  }

  .actress-avatar {
    width: 56px;
    height: 56px;
  }

  .avatar-placeholder {
    width: 56px;
    height: 56px;
  }

  .actress-tag {
    width: 100%;
    min-height: var(--compact-toolbar-height);
    padding: 8px 10px;
    border-radius: 14px;
    font-size: 12px;
    line-height: 1.35;
    overflow-wrap: anywhere;
    touch-action: manipulation;
  }

  .summary-text {
    max-height: none;
    padding: 16px;
    font-size: var(--type-body);
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .stream-download-btn {
    min-height: var(--compact-toolbar-height);
    padding: 12px 18px;
  }

  .lightbox-close {
    top: calc(12px + env(safe-area-inset-top, 0px));
    right: 12px;
  }

  .lightbox-prev,
  .lightbox-next {
    width: 44px;
    height: 72px;
    font-size: 30px;
  }

  .lightbox-prev { left: 8px; }
  .lightbox-next { right: 8px; }
}
</style>
