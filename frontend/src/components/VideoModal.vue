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
            loading="eager"
            decoding="async"
            @error="handleImgError"
            class="gallery-img"
          />
        </div>

        <!-- 下方信息 -->
        <div class="modal-content">
          <!-- 番号 -->
          <div class="modal-code-block">
            <span class="modal-code">{{ video.dvd_id || video.content_id }}</span>
            <span v-if="libraryPlayInfo" class="library-badge" title="已绑定 115 播放资源">
              115 · {{ libraryPlayInfo.files.length }} 个文件
            </span>

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

              <button v-if="libraryPlayInfo" class="stream-btn library-play-btn" @click="playLibrary()" :disabled="libraryPlayLoading" title="播放默认 115 资源">
                <span v-if="libraryPlayLoading" class="spinner"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                <span>115 播放</span>
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
                class="actress-avatar-item"
                :class="{ 'is-subscribed': isActressSubscribed(actress.id) }"
              >
                <div
                  class="actress-avatar clickable"
                  @click="$emit('navigate', { type: 'actress', item: actress })"
                >
                  <img
                    v-if="actress.image_url"
                    :src="formatAvatarUrl(actress.image_url)"
                    :alt="displayName(actress, 'name_kanji', 'name_romaji')"
                    loading="lazy"
                    decoding="async"
                    @error="onAvatarError($event)"
                  />
                  <span v-else class="avatar-placeholder">{{ (displayName(actress, 'name_kanji', 'name_romaji') || '?')[0] }}</span>
                </div>
                <div
                  class="actress-name clickable"
                  @click="$emit('navigate', { type: 'actress', item: actress })"
                  v-html="actressNameDisplay(actress)"
                ></div>
                <button
                  class="actress-sub-btn"
                  type="button"
                  :class="{ 'is-subscribed': isActressSubscribed(actress.id), 'is-busy': isActressSubBusy(actress.id) }"
                  :disabled="!actress.id || isActressSubBusy(actress.id)"
                  :aria-pressed="isActressSubscribed(actress.id)"
                  :title="isActressSubscribed(actress.id) ? '取消订阅' : '订阅该演员'"
                  @click.stop="toggleActressSub(actress)"
                >{{ isActressSubscribed(actress.id) ? '已订阅' : '订阅' }}</button>
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

          <VideoResourcePanel v-if="libraryPlayInfo" :resources="libraryPlayInfo.files"
            @play="playLibrary" @make-default="makeDefaultLibraryResource" />
          <div class="stream-actions" v-if="video">
            <button class="btn btn-primary stream-download-btn" @click="downloadStream" :disabled="streamLoading">
              <span v-if="streamLoading" class="spinner"></span>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              <span>m3u8 下载</span>
            </button>
            <template v-if="libraryPlayInfo">
              <button class="btn stream-download-btn" @click="copyLibraryLink" title="复制 JavHub 稳定播放链接">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span>复制稳定链接</span>
              </button>
              <OpenWithMenu :url="stableResourceUrl()" :name="libraryCode()" @launch="closeStreamPlayer" />
            </template>
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
            loading="eager"
            decoding="async"
            class="lightbox-img"
            @error="handleGalleryImgError"
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
        @close="closeVideoPlayer"
        @seek-backward="seekBackward"
        @seek-forward="seekForward"
      />

      <!-- m3u8 在线播放弹窗:选源 picker 通过 props 内嵌进 toolbar,不走 slot -->
      <HlsPlayerOverlay
        ref="streamPlayer"
        :visible="streamPlayerVisible"
        :title="video.dvd_id || video.content_id"
        :sources="streamSources"
        :current-source="currentSourceName"
        :scan-done="streamScanDone"
        @close="closeStreamPlayer"
        @switch-source="switchStreamSource"
      />
    </div>
  </teleport>
</template>
<script>
import { defineAsyncComponent } from 'vue'
import { displayName, displayLang } from '../utils/displayLang.js'
import { jacketFullUrl, galleryFullUrl, galleryThumbUrl } from '../utils/imageUrl.js'
import { applyImageFallback } from '../utils/imageFallback.js'
import favoriteState from '../utils/favoriteState'
import subscriptionState from '../utils/subscriptionState'
import api, { formatApiError } from '../api'
import { ElMessage } from '../utils/message.js'
import VideoGallerySection from '../features/video/VideoGallerySection.vue'
import VideoMagnetSection from '../features/video/VideoMagnetSection.vue'
import VideoResourcePanel from '../features/video/VideoResourcePanel.vue'
import OpenWithMenu from '../features/video/OpenWithMenu.vue'
import { createStreamSession, triggerM3u8Download, formatStreamFailure } from '../features/video/streamSourcesHelper.js'
import libraryPlaybackMixin from '../features/video/libraryPlaybackMixin.js'
const VideoPlayerOverlay = defineAsyncComponent(() => import('../features/video/VideoPlayerOverlay.vue'))
const HlsPlayerOverlay = defineAsyncComponent(() => import('../features/video/HlsPlayerOverlay.vue'))
function videoFavoriteId(video = {}) {
  const id = video.content_id || video.dvd_id
  const serviceCode = String(video.service_code || '').trim()
  return id && serviceCode ? `${id}::${serviceCode}` : id
}

export default {
  name: 'VideoModal',
  mixins: [libraryPlaybackMixin],
  components: { VideoGallerySection, VideoMagnetSection, VideoResourcePanel, VideoPlayerOverlay, HlsPlayerOverlay, OpenWithMenu },
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
      streamLoading: false,
      streamPlayerVisible: false,
      streamM3u8Url: '',
      hlsInstance: null,
      streamSession: null,
      streamSources: [],
      streamScanDone: false,
      currentSourceName: '',
      // P1-2: subBusy is a Set re-assigned on each mutation so Vue re-renders.
      subBusy: new Set(),
    }
  },
  mounted() {
    // P1-2: 幂等拉一次订阅 registry,失败不致命(按钮显示为未订阅,后续仍可点)。
    subscriptionState.init().catch(() => {})
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
      } else {
        this.checkLibraryStatus()
      }
    },
    'video.content_id'() {
      if (this.visible) this.checkLibraryStatus()
    },
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
    isActressSubscribed(id) {
      return id ? subscriptionState.isSubscribed(id) : false
    },
    isActressSubBusy(id) {
      return id ? this.subBusy.has(String(id)) : false
    },
    async toggleActressSub(actress) {
      const id = actress?.id
      if (!id) return
      const key = String(id)
      if (this.subBusy.has(key)) return
      this.subBusy.add(key)
      this.subBusy = new Set(this.subBusy)
      const wasSubscribed = this.isActressSubscribed(id)
      try {
        const actressName = this.displayName(actress, 'name_kanji', 'name_romaji') || ''
        await subscriptionState.toggle(id, actressName)
        ElMessage.success(wasSubscribed ? '已取消订阅' : '已订阅')
      } catch (err) {
        const detail = formatApiError
          ? formatApiError(err, { service: '订阅', action: '更新', fallback: '订阅操作失败' }).message
          : '订阅操作失败'
        ElMessage.error(detail)
      } finally {
        this.subBusy.delete(key)
        this.subBusy = new Set(this.subBusy)
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
    handleImgError(e) { applyImageFallback(e, { label: '暂无封面' }) },
    handleGalleryImgError(e) {
      const img = e?.target
      if (!img) return
      const thumb = galleryThumbUrl(this.galleryThumbs[this.currentGalleryIndex])
      if (thumb && img.dataset?.galleryThumbFallback !== 'true') {
        img.dataset.galleryThumbFallback = 'true'
        img.src = thumb
        return
      }
      applyImageFallback(e, { label: `剧照 ${this.currentGalleryIndex + 1}` })
    },
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
    playStream() {
      const code = this.video?.dvd_id || this.video?.content_id
      if (!code) return
      this.closeStreamSession()
      this.playbackMode = 'online'
      this.streamLoading = true
      this.streamSources = []
      this.streamScanDone = false
      this.currentSourceName = ''
      this.streamM3u8Url = ''
      this.streamPlayerVisible = true
      this.streamSession = createStreamSession({
        code,
        onItem: (item) => this.streamSources.push(item),
        onFirstOk: (item) => this.switchStreamSource(item.source),
        onDone: () => { this.streamScanDone = true; this.streamLoading = false; this.streamSession = null },
        onAllError: (sources) => { this.streamPlayerVisible = false; ElMessage.error(formatStreamFailure(sources)) },
      })
    },
    switchStreamSource(sourceName) {
      const item = this.streamSources.find(s => s.source === sourceName && s.status === 'ok')
      if (!item || !item.m3u8_url) return
      this.currentSourceName = sourceName
      this.streamM3u8Url = `/api/v1/stream/proxy?url=${encodeURIComponent(item.m3u8_url)}`
      this.$nextTick(() => this.initHlsPlayer())
    },
    closeStreamSession() {
      if (this.streamSession) { this.streamSession.close(); this.streamSession = null }
    },
    async waitForStreamVideoEl() {
      for (let i = 0; i < 60; i += 1) {
        await this.$nextTick()
        const video = this.streamVideoEl()
        if (video) return video
        await new Promise(resolve => setTimeout(resolve, 50))
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
        this.setupProgressReporting(video)
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = this.streamM3u8Url
        video.addEventListener('loadedmetadata', () => { video.play() })
        this.setupProgressReporting(video)
      }
    },
    closeStreamPlayer() {
      // 关闭前上报最终进度
      const video = this.streamVideoEl()
      if (video) {
        this.reportProgress(video)
        try { video.removeEventListener('error', this.onLibraryPlayError) } catch (e) {}
      }
      this.teardownProgressReporting()
      this.closeStreamSession()
      if (this.hlsInstance) { this.hlsInstance.destroy(); this.hlsInstance = null }
      this.streamPlayerVisible = false
      this.streamM3u8Url = ''
      this.streamSources = []
      this.streamScanDone = false
      this.currentSourceName = ''
      this.streamLoading = false
      this.playbackMode = ''
      this.libraryRetryUsed = false
      // 进度可能变化，刷新入库状态里的 progress
      if (this.visible) this.checkLibraryStatus()
    },
    downloadStream() {
      const code = this.video?.dvd_id || this.video?.content_id
      if (!code) return
      this.streamLoading = true
      let session
      session = createStreamSession({
        code,
        onFirstOk: (item) => {
          triggerM3u8Download(item.m3u8_url, code)
          ElMessage.success(`m3u8 下载已开始 (源: ${item.source})`)
          this.streamLoading = false
          session?.close()
        },
        onAllError: (sources) => { this.streamLoading = false; ElMessage.error(formatStreamFailure(sources)) },
      })
    },
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onGalleryKeydown)
    this.closeStreamSession()
    if (this.hlsInstance) {
      this.hlsInstance.destroy()
      this.hlsInstance = null
    }
  }
}
</script>

<style scoped src="../features/videoModal/videoModal.css"></style>
