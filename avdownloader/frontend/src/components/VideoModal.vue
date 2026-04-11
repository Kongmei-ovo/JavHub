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
            <div v-if="video.release_date" class="meta-row">
              <span class="meta-label">发行日期</span>
              <span class="meta-value">{{ video.release_date }}</span>
            </div>
            <div v-if="video.runtime_mins" class="meta-row">
              <span class="meta-label">时长</span>
              <span class="meta-value">{{ video.runtime_mins }} 分钟</span>
            </div>
            <div v-if="video.maker" class="meta-row">
              <span class="meta-label">厂商</span>
              <span class="meta-value clickable" @click="$emit('search-by-maker', video.maker.id)">
                {{ video.maker.name_en || video.maker.name_ja }}
              </span>
            </div>
            <div v-if="video.label" class="meta-row">
              <span class="meta-label">品牌</span>
              <span class="meta-value">{{ video.label.name_en || video.label.name_ja }}</span>
            </div>
            <div v-if="video.series" class="meta-row">
              <span class="meta-label">系列</span>
              <span class="meta-value clickable" @click="$emit('search-by-series', video.series.id)">
                {{ video.series.name_en || video.series.name_ja }}
              </span>
            </div>
          </div>

          <!-- 演员 -->
          <div v-if="video.actresses && video.actresses.length" class="modal-section">
            <h4 class="section-title">演员</h4>
            <div class="actress-list">
              <span
                v-for="actress in video.actresses"
                :key="actress.id"
                class="actress-tag clickable"
                @click="$emit('search-by-actress', actress.id)"
              >
                {{ actress.name_kanji || actress.name_romaji }}
              </span>
            </div>
          </div>

          <!-- 题材 -->
          <div v-if="video.categories && video.categories.length" class="modal-section">
            <h4 class="section-title">题材</h4>
            <div class="actress-list">
              <span
                v-for="cat in video.categories"
                :key="cat.id"
                class="actress-tag"
              >
                {{ cat.name_en || cat.name_ja }}
              </span>
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
    }
  },
  methods: {
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="600" viewBox="0 0 400 600"><rect fill="%231a1a2e" width="400" height="600"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
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
}

.meta-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}

.meta-row:last-child {
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
  gap: 6px;
}

.actress-tag {
  padding: 4px 10px;
  background: var(--bg-secondary);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.actress-tag.clickable {
  cursor: pointer;
  transition: background 0.2s;
}

.actress-tag.clickable:hover {
  background: var(--accent);
  color: white;
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
</style>
