<template>
  <div ref="mount" class="art-mount"></div>
</template>

<script>
// Vue3 对 Artplayer 的薄封装(抄自 OpenList 的播放器内核,换成 Vue 用法)。
// 两种用法:
//   - 自管(owned):传 :url(+:type),播放器自己加载;m3u8 走 customType + hls.js。
//   - 外挂(external):不传 url,调用方拿 mediaElement() 自己 attach(VideoModal 的 115/在线 m3u8 走这条,
//     沿用既有 hls 生命周期与进度上报,保持契约不动)。
// 永远 expose mediaElement() → 底层 <video>,让既有 seek / 进度逻辑无缝继续工作。
export default {
  name: 'ArtPlayer',
  props: {
    url: { type: String, default: '' },
    type: { type: String, default: 'auto' }, // 'auto' | 'native' | 'hls'
    title: { type: String, default: '' },
    poster: { type: String, default: '' },
    autoplay: { type: Boolean, default: true },
    startTime: { type: Number, default: 0 },
    subtitles: { type: Array, default: () => [] }, // [{url,label,srclang,default,type}]
    qualities: { type: Array, default: () => [] }, // [{html|label,url,default}]
  },
  emits: ['ready', 'timeupdate', 'ended', 'video-error', 'error'],
  data() {
    return { art: null }
  },
  watch: {
    url(next) {
      if (next && this.art) this.load(next, this.type)
    },
  },
  async mounted() {
    await this.create()
  },
  beforeUnmount() {
    this.destroy()
  },
  methods: {
    mediaElement() {
      return this.art?.video || null
    },
    instance() {
      return this.art
    },
    artType(url, type) {
      if (type === 'hls') return 'm3u8'
      if (type === 'native') return ''
      return /\.m3u8(\?|$)/i.test(url || '') ? 'm3u8' : ''
    },
    subType(sub) {
      if (sub?.type) return sub.type
      const u = String(sub?.url || '')
      if (/\.ass(\?|$)/i.test(u)) return 'ass'
      if (/\.srt(\?|$)/i.test(u)) return 'srt'
      return 'vtt'
    },
    async ensureHls() {
      if (!this._Hls) this._Hls = (await import('hls.js/dist/hls.light.mjs')).default
      return this._Hls
    },
    mapQualities(list) {
      return list.map((q, i) => ({
        html: q.html || q.label || `源 ${i + 1}`,
        url: q.url,
        default: q.default ?? i === 0,
      }))
    },
    accentTheme() {
      // 主题色取自设计 token --accent(运行时解析,不在源码里写裸色)。
      try {
        return getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()
      } catch {
        return ''
      }
    },
    subtitleSettings() {
      if (!this.subtitles.length) return []
      const self = this
      const def = this.subtitles.find((s) => s.default) || this.subtitles[0]
      return [{
        width: 220,
        html: '字幕',
        tooltip: def?.label || '字幕',
        selector: [
          { html: '关闭', url: '' },
          ...this.subtitles.map((s) => ({
            html: s.label || '字幕',
            url: s.url,
            type: self.subType(s),
            default: Boolean(s.default),
          })),
        ],
        onSelect(item) {
          const art = self.art
          if (!art) return item.html
          if (!item.url) {
            art.subtitle.show = false
            return '关闭'
          }
          art.subtitle.show = true
          art.subtitle.switch(item.url, { name: item.html, type: item.type })
          return item.html
        },
      }]
    },
    async create() {
      const Artplayer = (await import('artplayer')).default
      const self = this
      const ownsUrl = Boolean(this.url)
      const ownsHls = this.artType(this.url, this.type) === 'm3u8'
        || this.qualities.some((q) => /\.m3u8(\?|$)/i.test(q.url || ''))
      if (ownsHls) await this.ensureHls()

      const def = this.subtitles.find((s) => s.default) || this.subtitles[0]
      const option = {
        container: this.$refs.mount,
        url: ownsUrl ? this.url : '',
        type: ownsUrl ? this.artType(this.url, this.type) : '',
        poster: this.poster || '',
        title: this.title || '',
        volume: 1,
        autoplay: this.autoplay,
        autoSize: false,
        autoMini: false,
        loop: false,
        flip: true,
        playbackRate: true,
        aspectRatio: true,
        setting: true,
        hotkey: true,
        pip: true,
        mutex: true,
        fullscreen: true,
        fullscreenWeb: true,
        miniProgressBar: true,
        playsInline: true,
        screenshot: true,
        airplay: true,
        theme: this.accentTheme(),
        // 不要 crossOrigin:115 等 CDN 的 302 直链不带 CORS 头,设了反而会被浏览器拦掉,
        // 网页播放(像 alist 那样字节直连 CDN、不过服务器)就放不出来。
        moreVideoAttr: { playsInline: true },
        quality: this.qualities.length ? this.mapQualities(this.qualities) : [],
        settings: this.subtitleSettings(),
        subtitle: def ? { url: def.url, type: this.subType(def), encoding: 'utf-8', escape: false } : {},
        customType: {
          m3u8(video, url) {
            const Hls = self._Hls
            if (Hls && Hls.isSupported()) {
              if (self._hls) self._hls.destroy()
              const hls = new Hls()
              hls.loadSource(url)
              hls.attachMedia(video)
              // 致命错误(代理 502 / 转码不可用等)上抛,让调用方退到外连原片,别黑屏卡转圈。
              hls.on(Hls.Events.ERROR, (event, data) => { if (data && data.fatal) self.$emit('video-error', data) })
              self._hls = hls
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
              video.src = url
            }
          },
        },
      }

      const art = new Artplayer(option)
      this.art = art
      art.on('ready', () => {
        if (this.startTime > 0 && isFinite(this.startTime)) {
          try { art.currentTime = this.startTime } catch { /* ignore */ }
        }
        this.$emit('ready', art)
      })
      art.on('video:timeupdate', () => this.$emit('timeupdate', art.video))
      art.on('video:ended', () => this.$emit('ended'))
      art.on('video:error', (e) => this.$emit('video-error', e))
      art.on('error', (e) => this.$emit('error', e))
    },
    async load(url, type) {
      if (!this.art) return
      const t = this.artType(url, type)
      if (t === 'm3u8') await this.ensureHls()
      this.art.type = t
      this.art.switchUrl(url)
    },
    destroy() {
      if (this._hls) { try { this._hls.destroy() } catch { /* ignore */ } this._hls = null }
      if (this.art) { try { this.art.destroy(true) } catch { /* ignore */ } this.art = null }
    },
  },
}
</script>

<style scoped>
.art-mount {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--media-blackout);
}
.art-mount :deep(.art-video-player) {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  font-family: var(--font-sans, inherit);
}
</style>
