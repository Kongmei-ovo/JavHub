<template>
  <div class="video-detail-page page-shell page-shell--standard">
    <div class="video-detail-toolbar">
      <button class="back-btn" type="button" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回
      </button>
      <div>
        <h1>{{ videoCode }}</h1>
        <p>具体版本详情，收藏粒度按当前版本保存。</p>
      </div>
    </div>

    <div class="version-notice">
      <span class="version-badge">{{ versionLabel }}</span>
      <span>同番号不同版本会分别收藏为具体版本。</span>
    </div>

    <AppleErrorState
      v-if="error"
      title="影片详情加载失败"
      description="JavInfo 服务当前没有返回可用详情。"
      retry-label="重试"
      @retry="loadVideo"
    />

    <VideoModal
      v-else
      inline
      :visible="true"
      :video="video"
      @close="goBack"
      @download="handleDownload"
      @navigate="handleNavigate"
    />
  </div>
</template>

<script>
import api from '../api'
import VideoModal from '../components/VideoModal.vue'
import AppleErrorState from '../components/AppleErrorState.vue'
import { createRequestSequence } from '../utils/requestSequence.js'
import { normalizeVideo } from '../utils/videoNormalize.js'
import { ElMessage } from '../utils/message.js'

const SERVICE_LABELS = {
  digital: '数字',
  mono: 'DVD',
  rental: '租赁',
  ebook: '写真',
}

export default {
  name: 'VideoDetail',
  components: { VideoModal, AppleErrorState },
  data() {
    return {
      video: normalizeVideo({ content_id: this.$route.params.contentId, dvd_id: this.$route.params.contentId }),
      loading: false,
      error: '',
      requestSequence: createRequestSequence(),
    }
  },
  computed: {
    videoCode() {
      return this.video?.dvd_id || this.video?.content_id || this.$route.params.contentId
    },
    selectedServiceCode() {
      return String(this.video?.service_code || this.$route.query.service_code || '')
    },
    versionLabel() {
      return SERVICE_LABELS[this.selectedServiceCode] || '具体版本'
    },
  },
  mounted() {
    this.loadVideo()
  },
  beforeUnmount() {
    this.requestSequence.invalidate()
  },
  watch: {
    '$route.params.contentId'() {
      this.video = normalizeVideo({ content_id: this.$route.params.contentId, dvd_id: this.$route.params.contentId })
      this.loadVideo()
    },
    '$route.query.service_code'() {
      this.loadVideo()
    },
  },
  methods: {
    async loadVideo() {
      const contentId = this.$route.params.contentId
      const serviceCode = this.$route.query.service_code
      const token = this.requestSequence.next()
      this.loading = true
      this.error = ''
      this.video = {
        ...normalizeVideo({ content_id: contentId, dvd_id: contentId }),
        service_code: serviceCode || '',
        _loading: { javinfo: true, cover: true, gallery: false },
        _errors: { javinfo: null, cover: null, gallery: null, stream: null },
      }
      try {
        const resp = await api.getVideo(contentId, { service_code: serviceCode })
        if (!this.requestSequence.isCurrent(token)) return
        this.video = {
          ...this.video,
          ...(resp.data || {}),
          _loading: { ...this.video._loading, javinfo: false },
        }
      } catch (e) {
        if (!this.requestSequence.isCurrent(token)) return
        console.error('Load video detail failed:', e)
        this.error = 'load_failed'
        this.video = {
          ...this.video,
          _loading: { ...this.video._loading, javinfo: false },
          _errors: { ...this.video._errors, javinfo: '详情加载失败' },
        }
      } finally {
        if (this.requestSequence.isCurrent(token)) this.loading = false
      }
    },
    goBack() {
      if (window.history.state?.back) {
        this.$router.back()
      } else {
        this.$router.replace('/search')
      }
    },
    async handleDownload(magnet) {
      try {
        await api.createDownload({
          content_id: this.video.content_id || this.video.dvd_id,
          title: this.video.title_en || this.video.title_ja || this.videoCode,
          magnet: magnet.magnet || magnet,
        })
        ElMessage.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
      }
    },
    handleNavigate({ type, item }) {
      const name = item.name_kanji || item.name_romaji || item.name_ja || item.name_en || item.name || ''
      const value = item.id || item.actress_id || name
      if (!value) return
      if (type === 'actress') {
        this.$router.push({
          path: `/actor/${encodeURIComponent(name || value)}`,
          query: item.id || item.actress_id ? { name, actress_id: item.id || item.actress_id } : { name },
        })
        return
      }
      this.$router.push({
        name: 'DiscoveryDetail',
        params: { type, value: String(value) },
        query: name ? { name } : {},
      })
    },
  },
}
</script>

<style scoped>
.video-detail-page {
  --page-top-space: 18px;
  min-height: 100dvh;
}

.video-detail-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.video-detail-toolbar h1 {
  color: var(--text-primary);
  font-size: var(--type-section-title);
  letter-spacing: 0;
  margin: 0;
}

.video-detail-toolbar p,
.version-notice span:last-child {
  color: var(--text-muted);
  font-size: var(--type-control);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 44px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-secondary);
  cursor: pointer;
}

.version-notice {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.version-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid var(--active-border);
  border-radius: 999px;
  background: var(--active-bg);
  color: var(--text-primary);
  font-size: var(--type-caption);
  font-weight: 700;
}
</style>
