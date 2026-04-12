<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container">
      <button class="modal-close" @click="$emit('close')">×</button>

      <div class="modal-body">
        <!-- 顶部大图 -->
        <div class="modal-gallery">
          <img
            :src="video.jacket_full_url || video.jacket_thumb_url || '/placeholder.png'"
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
          </div>

          <!-- 标题 -->
          <div class="modal-title-block">
            <h2 class="modal-title">{{ video.title_en || video.title_ja }}</h2>
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
              <span class="meta-value clickable" @click="$emit('search-by-maker', video.maker.name_en || video.maker.name_ja)">
                {{ displayName(video.maker) }}
              </span>
            </div>
            <div v-if="video.label" class="meta-row">
              <span class="meta-label">厂牌</span>
              <span class="meta-value">{{ displayName(video.label) }}</span>
            </div>
            <div v-if="video.series" class="meta-row">
              <span class="meta-label">系列</span>
              <span class="meta-value clickable" @click="$emit('search-by-series', video.series.name_en || video.series.name_ja)">
                {{ displayName(video.series) }}
              </span>
            </div>
          </div>

          <!-- 演员 -->
          <div v-if="video.actresses && video.actresses.length" class="modal-section">
            <h4 class="section-title">演员</h4>
            <div class="actress-list">
              <div
                v-for="actress in video.actresses"
                :key="actress.id"
                class="actress-avatar-item clickable"
                @click="$emit('search-by-actress', actress.name_kanji || actress.name_romaji)"
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
                <span class="actress-name">{{ displayName(actress, 'name_kanji', 'name_romaji') }}</span>
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
                @click="$emit('search-by-category', cat.name_en || cat.name_ja)"
              >
                {{ displayName(cat) }}
              </span>
            </div>
          </div>

          <!-- 剧照画廊 -->
          <div v-if="galleryThumbs.length" class="modal-section">
            <h4 class="section-title">剧照</h4>
            <div class="gallery-grid">
              <div v-for="(thumb, idx) in galleryThumbs" :key="idx" class="gallery-item">
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
    </div>
  </div>
</template>

<script>
import { displayName } from '../utils/displayLang.js'

export default {
  name: 'VideoModal',
  props: {
    visible: { type: Boolean, default: false },
    video: { type: Object, default: () => ({}) }
  },
  computed: {
    magnets() {
      if (!this.video) return []
      if (this.video.magnets && Array.isArray(this.video.magnets)) {
        return this.video.magnets
      }
      return []
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
    }
  },
  methods: {
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
      return `https://awsimgsrc.dmm.com/dig/mono/actjpgs/${url.replace(/^\//, '')}`
    },
    formatGalleryUrl(path) {
      if (!path) return null
      if (path.startsWith('http')) return path
      return `https://pics.dmm.co.jp/${path}.jpg`
    },
    async copyMagnet(mag) {
      try {
        await navigator.clipboard.writeText(mag.magnet || mag)
        if (this.$message) this.$message.success('磁链已复制')
      } catch (e) {
        if (this.$message) this.$message.error('复制失败')
      }
    }
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
}

.modal-code {
  font-size: 24px;
  font-weight: bold;
  color: var(--accent);
}

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
</style>
