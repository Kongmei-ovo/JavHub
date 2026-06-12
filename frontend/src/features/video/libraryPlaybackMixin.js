/**
 * ItemId-bound 115 playback for VideoModal.
 *
 * The browser only keeps durable resource metadata and JavHub stable playback
 * entries. 115 signed URLs are created after the final player request arrives.
 */
import api, { formatApiError } from '../../api'
import { ElMessage } from '../../utils/message.js'

const WEB_ORIGINAL_EXTENSIONS = new Set(['mp4', 'webm'])

export default {
  data() {
    return {
      libraryPlayInfo: null,
      libraryPlayLoading: false,
      playbackMode: '', // 'library' | 'online'
      progressReportHandler: null,
      lastProgressReport: 0,
      libraryRetryUsed: false,
      activeLibraryResourceId: null,
    }
  },
  methods: {
    libraryCode() {
      return this.video?.content_id || this.video?.dvd_id || ''
    },
    readyVideoResources(items = []) {
      return items.filter(item => item.resource_type === 'video' && item.status === 'ready')
    },
    defaultLibraryResource() {
      const files = this.libraryPlayInfo?.files || []
      return files.find(item => item.is_default) || files[0] || null
    },
    resourceById(resourceId) {
      const files = this.libraryPlayInfo?.files || []
      return files.find(item => Number(item.id) === Number(resourceId)) || null
    },
    async checkLibraryStatus() {
      this.libraryPlayInfo = null
      const movieId = this.libraryCode()
      if (!movieId) return
      try {
        const [resourceResp, progressResp] = await Promise.all([
          api.getMovieResources(movieId),
          api.getPlaybackProgress(movieId, 'library').catch(() => ({ data: null })),
        ])
        const files = this.readyVideoResources(resourceResp.data?.items || [])
        if (!files.length) return
        const file = files.find(item => item.is_default) || files[0]
        this.libraryPlayInfo = { file, files, progress: progressResp.data || null }
      } catch (e) {
        this.libraryPlayInfo = null
      }
    },
    resourcePlayDescriptor(resource) {
      const extension = String(resource?.extension || '').toLowerCase().replace(/^\./, '')
      return {
        url: api.movieResourceStreamUrl(resource.id, 'auto'),
        kind: WEB_ORIGINAL_EXTENSIONS.has(extension) ? 'original' : 'hls',
      }
    },
    async playLibrary(resourceId = null) {
      if (this.libraryPlayLoading) return
      const resource = resourceId == null
        ? this.defaultLibraryResource()
        : this.resourceById(resourceId)
      if (!resource) return
      this.libraryPlayLoading = true
      this.libraryRetryUsed = false
      this.activeLibraryResourceId = resource.id
      try {
        this.playbackMode = 'library'
        this.streamSources = []
        this.streamScanDone = true
        this.currentSourceName = ''
        this.streamPlayerVisible = true
        await this.attachLibrarySource(
          this.resourcePlayDescriptor(resource),
          this.libraryPlayInfo?.progress,
        )
      } catch (e) {
        ElMessage.error(formatApiError
          ? formatApiError(e, { service: '115 播放', action: '打开', fallback: '115 播放失败' }).message
          : '115 播放失败')
        this.streamPlayerVisible = false
        this.playbackMode = ''
      } finally {
        this.libraryPlayLoading = false
      }
    },
    async attachLibrarySource(play, progress = null) {
      const video = await this.waitForStreamVideoEl()
      if (!video) return
      if (this.hlsInstance) { this.hlsInstance.destroy(); this.hlsInstance = null }
      const isHls = play.kind === 'hls'
      if (isHls) {
        const { default: Hls } = await import('hls.js/dist/hls.light.mjs')
        if (Hls.isSupported()) {
          const hls = new Hls()
          hls.loadSource(play.url)
          hls.attachMedia(video)
          hls.on(Hls.Events.MANIFEST_PARSED, () => { video.play() })
          this.hlsInstance = hls
        } else {
          video.src = play.url
        }
      } else {
        video.src = play.url
      }
      const resumeAt = Number(progress?.position_seconds || 0)
      const onMeta = () => {
        if (resumeAt > 30 && !progress?.completed && resumeAt < video.duration - 10) {
          video.currentTime = resumeAt
          ElMessage.success(`从 ${this.formatPlayTime(resumeAt)} 继续播放`)
        }
        video.play().catch(() => {})
      }
      video.addEventListener('loadedmetadata', onMeta, { once: true })
      video.addEventListener('error', this.onLibraryPlayError)
      this.setupProgressReporting(video)
    },
    async onLibraryPlayError() {
      if (this.playbackMode !== 'library' || this.libraryRetryUsed) {
        if (this.playbackMode === 'library') ElMessage.error('115 播放失败，可尝试外部播放器')
        return
      }
      this.libraryRetryUsed = true
      const resource = this.resourceById(this.activeLibraryResourceId) || this.defaultLibraryResource()
      if (!resource) return
      try {
        await this.attachLibrarySource(
          this.resourcePlayDescriptor(resource),
          this.libraryPlayInfo?.progress,
        )
      } catch (e) {
        ElMessage.error('115 播放入口重试失败')
      }
    },
    setupProgressReporting(video) {
      this.teardownProgressReporting()
      const handler = () => {
        const now = Date.now()
        if (now - this.lastProgressReport < 10000) return
        this.lastProgressReport = now
        this.reportProgress(video)
      }
      video.addEventListener('timeupdate', handler)
      video.addEventListener('pause', () => this.reportProgress(video))
      this.progressReportHandler = { video, handler }
    },
    teardownProgressReporting() {
      if (this.progressReportHandler) {
        const { video, handler } = this.progressReportHandler
        try { video.removeEventListener('timeupdate', handler) } catch (e) {}
        this.progressReportHandler = null
      }
    },
    reportProgress(video) {
      const movieId = this.libraryCode()
      if (!movieId || !video || !video.duration || !isFinite(video.duration)) return
      const source = this.playbackMode === 'library' ? 'library' : 'online'
      api.savePlaybackProgress(movieId, {
        source,
        position_seconds: video.currentTime,
        duration_seconds: video.duration,
      }).catch(() => {})
    },
    formatPlayTime(seconds) {
      const s = Math.floor(seconds % 60)
      const m = Math.floor((seconds / 60) % 60)
      const h = Math.floor(seconds / 3600)
      const mm = String(m).padStart(2, '0')
      const ss = String(s).padStart(2, '0')
      return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`
    },
    formatResourceSize(size) {
      const value = Number(size || 0)
      if (value <= 0) return '未知大小'
      const units = ['B', 'KB', 'MB', 'GB', 'TB']
      const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
      return `${(value / (1024 ** index)).toFixed(index >= 3 ? 2 : 0)} ${units[index]}`
    },
    stableResourceUrl(resource = null) {
      const selected = resource || this.defaultLibraryResource()
      if (!selected) return ''
      return new URL(api.movieResourceStreamUrl(selected.id, 'auto'), window.location.origin).toString()
    },
    async makeDefaultLibraryResource(resource) {
      const movieId = this.libraryCode()
      if (!movieId || !resource || resource.is_default) return
      try {
        await api.setDefaultMovieResource(movieId, resource.id)
        const files = (this.libraryPlayInfo?.files || []).map(item => ({
          ...item,
          is_default: Number(item.id) === Number(resource.id) ? 1 : 0,
        }))
        this.libraryPlayInfo = { ...this.libraryPlayInfo, file: resource, files }
        ElMessage.success('默认 115 资源已更新')
      } catch (e) {
        ElMessage.error('设置默认资源失败')
      }
    },
    async copyLibraryLink() {
      const url = this.stableResourceUrl()
      if (!url) return
      try {
        await navigator.clipboard.writeText(url)
        ElMessage.success('JavHub 稳定播放链接已复制')
      } catch (e) {
        ElMessage.error('复制播放链接失败')
      }
    },
    async openInExternalPlayer() {
      const url = this.stableResourceUrl()
      if (!url) return
      window.location.href = `iina://weblink?url=${encodeURIComponent(url)}`
    },
  },
}
