<template>
  <div class="watch-page">
    <VideoPlayerOverlay
      v-if="playerVisible"
      :src="streamUrl"
      :name="movieId"
      @close="handleClose"
    />
    <div v-else class="acquisition-waiting">
      <h2 class="acquisition-title">{{ stageLabel }}</h2>
      <ol class="acquisition-stages">
        <li :class="stageClass('searching')">搜索</li>
        <li :class="stageClass('downloading')">115 下载</li>
        <li :class="stageClass('finalizing')">登记</li>
        <li :class="stageClass('ready')">自动起播</li>
      </ol>
      <p v-if="errorMessage" class="acquisition-error">{{ errorMessage }}</p>
      <button v-if="errorMessage" class="acquisition-retry" @click="bootstrap">重试</button>
    </div>
  </div>
</template>

<script>
import api from '../api'
import VideoPlayerOverlay from '../features/video/VideoPlayerOverlay.vue'

// Maps the backend session state machine onto the four user-facing stages.
const STAGE_ORDER = ['searching', 'options_ready', 'submitted', 'downloading', 'finalizing', 'ready']
const STAGE_LABELS = {
  searching: '正在搜索资源…',
  options_ready: '正在搜索资源…',
  submitted: '已提交 115 离线…',
  downloading: '115 下载中…',
  finalizing: '登记资源中…',
  ready: '即将自动起播…',
  failed: '获取失败，可重试',
}

export default {
  name: 'Watch',
  components: { VideoPlayerOverlay },
  data() {
    return {
      movieId: String(this.$route.params.movieId || ''),
      playerVisible: false,
      streamUrl: '',
      sessionId: null,
      status: 'searching',
      errorMessage: '',
      pollTimer: null,
    }
  },
  computed: {
    stageLabel() {
      return STAGE_LABELS[this.status] || '准备中…'
    },
  },
  async mounted() {
    await this.bootstrap()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    stageClass(stage) {
      const current = STAGE_ORDER.indexOf(this.status)
      const target = STAGE_ORDER.indexOf(stage)
      if (this.status === stage) return 'is-active'
      if (target >= 0 && current > target) return 'is-done'
      return ''
    },
    readyVideo(items) {
      return (items || []).find(
        item => item.resource_type === 'video' && item.status === 'ready',
      )
    },
    playResource(resource) {
      // Has-resource shortcut: stream straight away, never opens a session.
      this.streamUrl = api.movieResourceStreamUrl(resource.id, 'auto')
      this.playerVisible = true
    },
    async bootstrap() {
      this.errorMessage = ''
      // 1. Already have a ready resource → autoplay immediately, no acquisition.
      const existing = await api.getMovieResources(this.movieId)
      const resource = this.readyVideo(existing.data?.items)
      if (resource) {
        this.playResource(resource)
        return
      }
      // 2. No resource → open (or attach to) an acquisition session, then poll.
      const started = await api.startAcquisition(this.movieId, { auto: true })
      const payload = started.data || {}
      if (payload.status === 'ready') {
        await this.loadAndPlay()
        return
      }
      this.sessionId = payload.session?.id || null
      this.status = payload.session?.status || 'searching'
      if (this.sessionId) this.startPolling()
    },
    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(() => this.poll(), 2000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async poll() {
      if (!this.sessionId) return
      try {
        const { data } = await api.getAcquisition(this.sessionId)
        this.status = data.session?.status || this.status
        if (this.status === 'ready') {
          this.stopPolling()
          await this.loadAndPlay()
        } else if (this.status === 'failed') {
          this.stopPolling()
          this.errorMessage = data.session?.error_msg || '获取失败，可重试'
        }
      } catch (err) {
        // Transient polling error — keep the interval alive and try again.
      }
    },
    async loadAndPlay() {
      const { data } = await api.getMovieResources(this.movieId)
      const resource = this.readyVideo(data?.items)
      if (resource) this.playResource(resource)
    },
    handleClose() {
      this.playerVisible = false
      this.$router.back()
    },
  },
}
</script>

<style scoped>
.watch-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.acquisition-waiting {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}
.acquisition-stages {
  display: flex;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}
.acquisition-stages li {
  padding: 6px 14px;
  color: var(--text-muted);
  font-size: var(--type-caption);
}
.acquisition-stages li.is-active {
  color: var(--accent);
  font-weight: 600;
}
.acquisition-stages li.is-done {
  color: var(--text-primary);
}
.acquisition-error {
  color: var(--text-secondary);
}
</style>
