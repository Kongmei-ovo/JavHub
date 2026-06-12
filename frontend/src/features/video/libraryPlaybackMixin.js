/**
 * 云盘库播放 mixin（依附 VideoModal）。
 *
 * 铁律：libraryPlayInfo 只保留文件/进度信息；直链每次播放前实时换链，
 * 前端不缓存、不持久化（115 直链有时效且可能绑 UA/IP）。
 */
import api, { formatApiError } from '../../api'
import { ElMessage } from '../../utils/message.js'

export default {
  data() {
    return {
      libraryPlayInfo: null,
      libraryPlayLoading: false,
      playbackMode: '', // 'library' | 'online'
      progressReportHandler: null,
      lastProgressReport: 0,
      libraryRetryUsed: false,
    }
  },
  methods: {
    libraryCode() {
      return this.video?.content_id || this.video?.dvd_id || ''
    },
    async checkLibraryStatus() {
      this.libraryPlayInfo = null
      const code = this.libraryCode()
      if (!code) return
      try {
        const resp = await api.getLibraryPlay(code)
        // 只保留文件与进度信息；直链丢弃，播放时重新换链
        this.libraryPlayInfo = { file: resp.data.file, files: resp.data.files, progress: resp.data.progress }
      } catch (e) {
        this.libraryPlayInfo = null // 404 = 不在库中，静默
      }
    },
    async playLibrary(fileId = null) {
      const code = this.libraryCode()
      if (!code || this.libraryPlayLoading) return
      this.libraryPlayLoading = true
      this.libraryRetryUsed = false
      try {
        const resp = await api.getLibraryPlay(code, typeof fileId === 'number' ? fileId : null)
        const { play, progress } = resp.data
        this.playbackMode = 'library'
        this.streamSources = []
        this.streamScanDone = true // 隐藏选源 picker
        this.currentSourceName = ''
        this.streamPlayerVisible = true
        await this.attachLibrarySource(play, progress)
      } catch (e) {
        ElMessage.error(formatApiError
          ? formatApiError(e, { service: '云盘播放', action: '换链', fallback: '云盘播放失败' }).message
          : '云盘播放失败')
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
      const isHls = play.kind === 'hls' || /\.m3u8($|\?)/.test(play.url)
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
      // 直链 403/过期：重新换链一次再试，仍失败提示
      if (this.playbackMode !== 'library' || this.libraryRetryUsed) {
        if (this.playbackMode === 'library') ElMessage.error('云盘直链播放失败，可尝试外部播放器')
        return
      }
      this.libraryRetryUsed = true
      const code = this.libraryCode()
      try {
        const resp = await api.getLibraryPlay(code)
        await this.attachLibrarySource(resp.data.play, resp.data.progress)
      } catch (e) {
        ElMessage.error('云盘直链已失效且换链失败')
      }
    },
    // ── 播放进度上报（library 与 online 通用）────────────────
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
      const code = this.libraryCode()
      if (!code || !video || !video.duration || !isFinite(video.duration)) return
      const source = this.playbackMode === 'library' ? 'library' : 'online'
      api.savePlaybackProgress(code, {
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
    async copyLibraryLink() {
      const code = this.libraryCode()
      if (!code) return
      try {
        // 直链有时效，复制前重新换链
        const resp = await api.getLibraryPlay(code)
        await navigator.clipboard.writeText(resp.data.play.url)
        ElMessage.success('直链已复制（有时效，请尽快使用）')
      } catch (e) {
        ElMessage.error('获取直链失败')
      }
    },
    async openInExternalPlayer() {
      const code = this.libraryCode()
      if (!code) return
      try {
        const resp = await api.getLibraryPlay(code)
        window.location.href = `iina://weblink?url=${encodeURIComponent(resp.data.play.url)}`
      } catch (e) {
        ElMessage.error('获取直链失败')
      }
    },
  },
}
