import api, { formatApiError } from '../../api'
import { mergeMagnetResults, selectableMagnetSources } from '../downloads/sourcePresentation.js'

export default {
  data() {
    return {
      sourceSnapshot: { builtins: [], sources: [], types: [] },
      selectedMagnetSource: 'auto',
      searchedMagnets: [],
      magnetSearchLoading: false,
      magnetSearchError: '',
      magnetSearchSummary: '',
      magnetSearchRequestId: 0,
    }
  },
  computed: {
    magnets() { return mergeMagnetResults(this.video?.magnets || [], this.searchedMagnets) },
    magnetSourceOptions() { return selectableMagnetSources(this.sourceSnapshot) },
  },
  watch: {
    visible(value) {
      if (!value) this.resetMagnetSearch()
      else { this.resetMagnetSearch(); this.loadMagnetSources() }
    },
    'video.content_id'() { if (this.visible) { this.resetMagnetSearch(); this.loadMagnetSources() } },
    'video.dvd_id'(value, previous) { if (value !== previous && this.visible) { this.resetMagnetSearch(); this.loadMagnetSources() } },
  },
  methods: {
    resetMagnetSearch() {
      this.magnetSearchRequestId += 1
      this.selectedMagnetSource = 'auto'
      this.searchedMagnets = []
      this.magnetSearchLoading = false
      this.magnetSearchError = ''
      this.magnetSearchSummary = ''
    },
    async loadMagnetSources() {
      const requestId = this.magnetSearchRequestId
      try {
        const response = await api.getSourceConfig()
        if (requestId !== this.magnetSearchRequestId || !this.visible) return
        this.sourceSnapshot = response?.data || response || { builtins: [], sources: [], types: [] }
        if (!this.magnetSourceOptions.some(option => option.value === this.selectedMagnetSource)) this.selectedMagnetSource = 'auto'
      } catch (_) { /* Existing movie magnets remain usable. */ }
    },
    async searchMagnets() {
      const keyword = this.video?.dvd_id || this.video?.content_id
      if (!keyword || this.magnetSearchLoading || this.magnetSourceOptions.length <= 1) return
      const requestId = ++this.magnetSearchRequestId
      const videoIdentity = `${this.video?.content_id || ''}:${this.video?.dvd_id || ''}`
      this.magnetSearchLoading = true
      this.magnetSearchError = ''
      this.magnetSearchSummary = ''
      try {
        const response = await api.searchSources({ keyword, source_id: this.selectedMagnetSource })
        const payload = response?.data || response || {}
        const currentIdentity = `${this.video?.content_id || ''}:${this.video?.dvd_id || ''}`
        if (requestId !== this.magnetSearchRequestId || !this.visible || currentIdentity !== videoIdentity) return
        this.searchedMagnets = Array.isArray(payload.items) ? payload.items : []
        const failed = (Array.isArray(payload.errors) ? payload.errors : []).map(item => item?.source_name || item?.source || item?.name).filter(Boolean)
        this.magnetSearchSummary = `找到 ${this.searchedMagnets.length} 个结果${failed.length ? `；失败：${failed.join('、')}` : ''}`
      } catch (error) {
        if (requestId !== this.magnetSearchRequestId || !this.visible) return
        this.magnetSearchError = formatApiError(error, { service: '下载源', action: '查找磁力', fallback: '磁力查找失败' }).message
      } finally {
        if (requestId === this.magnetSearchRequestId) this.magnetSearchLoading = false
      }
    },
  },
}
