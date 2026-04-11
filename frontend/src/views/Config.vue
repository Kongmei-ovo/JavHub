<template>
  <div class="settings">
    <div class="page-header">
      <h1>设置</h1>
    </div>

    <div class="settings-content">
      <!-- OpenList -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <h2>OpenList / 115云盘</h2>
        </div>
        <div class="form-group">
          <label>API 地址</label>
          <input class="input" v-model="config.openlist.api_url" placeholder="https://fox.oplist.org" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>用户名</label>
            <input class="input" v-model="config.openlist.username" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input class="input" v-model="config.openlist.password" type="password" />
          </div>
        </div>
        <div class="form-group">
          <label>默认下载路径</label>
          <input class="input" v-model="config.openlist.default_path" placeholder="/115/AV" />
        </div>
      </div>

      <!-- Emby -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <h2>Emby</h2>
        </div>
        <div class="form-group">
          <label>API 地址</label>
          <input class="input" v-model="config.emby.api_url" placeholder="http://your-emby:8096" />
        </div>
        <div class="form-group">
          <label>API Key</label>
          <input class="input" v-model="config.emby.api_key" type="password" />
        </div>
      </div>

      <!-- Telegram -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <h2>Telegram Bot</h2>
        </div>
        <div class="form-group">
          <label>Bot Token</label>
          <input class="input" v-model="config.telegram.bot_token" />
        </div>
        <div class="form-group">
          <label>允许的用户 ID（逗号分隔）</label>
          <input class="input" v-model="telegramUsers" placeholder="123456789,987654321" />
        </div>
      </div>

      <!-- 通知 -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 01-3.46 0"/>
          </svg>
          <h2>通知设置</h2>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="notifEnabled" v-model="config.notification.enabled" />
          <label for="notifEnabled">启用通知</label>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="notifTelegram" v-model="config.notification.telegram" />
          <label for="notifTelegram">通过 Telegram 发送通知</label>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="notifAutoDownload" v-model="config.notification.auto_download_notify" />
          <label for="notifAutoDownload">自动下载时通知</label>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="notifComplete" v-model="config.notification.download_complete_notify" />
          <label for="notifComplete">下载完成时通知</label>
        </div>
        <div class="form-group checkbox">
          <input type="checkbox" id="notifNewMovie" v-model="config.notification.new_movie_notify" />
          <label for="notifNewMovie">发现新片时通知</label>
        </div>
      </div>

      <!-- 爬虫 -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          <h2>爬虫设置</h2>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>请求间隔（秒）</label>
            <input class="input" v-model="config.crawler.request_interval" type="number" min="1" />
          </div>
          <div class="form-group">
            <label>订阅检查时间（小时，0-23）</label>
            <input class="input" v-model="config.scheduler.subscription_check_hour" type="number" min="0" max="23" />
          </div>
        </div>
      </div>

      <!-- 气泡云设置 -->
      <div class="settings-card">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          <h2>气泡云设置</h2>
        </div>

        <!-- 颜色模式 -->
        <div class="form-group">
          <label>颜色模式</label>
          <div class="color-mode-tabs">
            <button
              class="mode-tab"
              :class="{ active: bubbleCfg.colorMode === 'random' }"
              @click="bubbleCfg.colorMode = 'random'"
            >随机颜色</button>
            <button
              class="mode-tab"
              :class="{ active: bubbleCfg.colorMode === 'legendary' }"
              @click="bubbleCfg.colorMode = 'legendary'"
            >金色传说</button>
          </div>
        </div>

        <!-- 随机颜色：下拉选择色系 -->
        <template v-if="bubbleCfg.colorMode === 'random'">
          <div class="form-group">
            <label>色系</label>
            <div class="palette-select-wrap">
              <select class="palette-select" v-model="bubbleCfg.palette">
                <option value="__all__">🌈 完全随机（混合全部色系）</option>
                <option
                  v-for="p in palettes"
                  :key="p.key"
                  :value="p.key"
                >
                  {{ p.label }}
                </option>
                <option value="__custom__">✏️ 自定义色</option>
              </select>
              <div class="palette-color-bar" :style="{ background: currentPalettePreview }"></div>
            </div>
          </div>
          <!-- 自定义色输入（选中"自定义色"时显示） -->
          <div v-if="bubbleCfg.palette === '__custom__'" class="form-group">
            <label>自定义渐变（逗号分隔，CSS渐变）</label>
            <textarea
              class="input custom-gradients-input"
              v-model="bubbleCfg.customGradientsText"
              placeholder="linear-gradient(#ff0000, #0000ff),linear-gradient(#00ff00, #ffff00)"
              rows="3"
            ></textarea>
          </div>
        </template>

        <!-- 金色传说说明 -->
        <div v-if="bubbleCfg.colorMode === 'legendary'" class="legendary-hint">
          <span class="legendary-dot legendary"></span> 传奇 — 影片库中出现极少，琥珀金呼吸光效
          <br/>
          <span class="legendary-dot epic"></span> 史诗 — 影片库中出现较少，紫色呼吸光效
          <br/>
          <span class="legendary-dot rare"></span> 稀有 — 影片库中出现一般，蓝色微光
          <br/>
          <span class="legendary-dot common"></span> 普通 — 影片库中出现频繁，无光效
        </div>

        <div class="form-row" style="margin-top: 16px;">
          <div class="form-group">
            <label>每页气泡数量</label>
            <input class="input" v-model.number="bubbleCfg.bubbleCount" type="number" min="12" max="120" step="6" />
          </div>
          <div class="form-group">
            <label>气泡大小（px）</label>
            <input class="input" v-model.number="bubbleCfg.baseSize" type="number" min="8" max="48" step="1" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>气体填充（%）</label>
            <input class="input" v-model.number="bubbleCfg.fillPercent" type="number" min="30" max="200" step="5" />
          </div>
          <div class="form-group">
            <label>气泡间距（px）</label>
            <input class="input" v-model.number="bubbleCfg.spacing" type="number" min="0" max="48" step="2" />
          </div>
        </div>
        <div class="form-row">
          <button class="btn btn-secondary" @click="resetBubbleCfg">恢复默认</button>
        </div>
      </div>

      <div class="settings-actions">
        <button class="btn btn-primary" @click="save" :disabled="saving">
          <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
          <span v-else>保存配置</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Config',
  data() {
    return {
      config: {
        openlist: { api_url: '', username: '', password: '', default_path: '/115/AV' },
        emby: { api_url: '', api_key: '' },
        telegram: { bot_token: '', allowed_user_ids: [] },
        crawler: { request_interval: 3 },
        scheduler: { subscription_check_hour: 2 },
        notification: { enabled: false, telegram: true, auto_download_notify: true, download_complete_notify: true, new_movie_notify: true }
      },
      telegramUsers: '',
      saving: false,
      bubbleCfg: {
        baseSize: 16, fillPercent: 50, spacing: 16,
        colorMode: 'legendary', palette: 'monet',
        customGradients: [], customGradientsText: '',
        goldLegend: true, bubbleCount: 36,
      },
      palettes: [
        { key: 'monet',    label: '莫奈',    colors: ['linear-gradient(135deg, #c4b5d8, #a5b4c8)', 'linear-gradient(135deg, #d4c4e0, #b8c5d6)'] },
        { key: 'sunset',   label: '夕阳',    colors: ['linear-gradient(135deg, #c89080, #d8a898)', 'linear-gradient(135deg, #c87868, #d8a088)'] },
        { key: 'ocean',   label: '海洋',    colors: ['linear-gradient(135deg, #7aaec0, #8cbcc8)', 'linear-gradient(135deg, #88c0b0, #a0d0c0)'] },
        { key: 'forest',   label: '森林',    colors: ['linear-gradient(135deg, #90b898, #a0c8a8)', 'linear-gradient(135deg, #7aa888, #8ab898)'] },
        { key: 'gold',    label: '金色',    colors: ['linear-gradient(135deg, #a88050, #c8a068)', 'linear-gradient(135deg, #c89050, #d8b070)'] },
        { key: 'anime',   label: '动漫',    colors: ['linear-gradient(135deg, #e8a0c8, #f0b8d8)', 'linear-gradient(135deg, #c0a0e0, #d0b0f0)'] },
        { key: 'retro',    label: '复古',    colors: ['linear-gradient(135deg, #c89050, #d0a068)', 'linear-gradient(135deg, #8b7355, #a08060)'] },
        { key: 'cyber',   label: '赛博',    colors: ['linear-gradient(135deg, #00c8ff, #0080ff)', 'linear-gradient(135deg, #8000ff, #c000ff)'] },
        { key: 'pastel',  label: '马卡龙',  colors: ['linear-gradient(135deg, #f0b8c0, #f8d0d8)', 'linear-gradient(135deg, #b8d0f0, #c8e0f8)'] },
        { key: 'nord',    label: 'Nord',    colors: ['linear-gradient(135deg, #88c0d0, #81a1c1)', 'linear-gradient(135deg, #a3be8c, #b48ead)'] },
        { key: 'neon',    label: '霓虹',    colors: ['linear-gradient(135deg, #ff0080, #ff4000)', 'linear-gradient(135deg, #00ff80, #00c0ff)'] },
        { key: 'earth',   label: '大地',    colors: ['linear-gradient(135deg, #8b7355, #a08060)', 'linear-gradient(135deg, #6b8e5a, #7a9e68)'] },
        { key: 'candy',   label: '糖果',    colors: ['linear-gradient(135deg, #ffb8d0, #ffc8e0)', 'linear-gradient(135deg, #b8e0ff, #c8f0ff)'] },
      ],
    }
  },
  computed: {
    // 下拉选中色系的颜色预览条
    currentPalettePreview() {
      if (this.bubbleCfg.palette === '__all__') {
        // 完全随机：展示所有色系的混合渐变
        return 'linear-gradient(90deg, #c4b5d8 0%, #e8a0c8 14%, #7aaec0 28%, #90b898 42%, #a88050 57%, #ff0080 71%, #00c8ff 85%, #ffb8d0 100%)'
      }
      if (this.bubbleCfg.palette === '__custom__') {
        return 'linear-gradient(90deg, #888, #aaa)'
      }
      const p = this.palettes.find(p => p.key === this.bubbleCfg.palette)
      if (!p) return 'linear-gradient(90deg, #888, #aaa)'
      const [c1, c2] = p.colors
      return `${c1}, ${c2}`
    },
  },
  watch: {
    'bubbleCfg.palette'(newVal) {
      // __all__ 和 __custom__ 是独立于 palettes 数组的特殊值，直接放行
      if (newVal === '__all__' || newVal === '__custom__') return
      // 防止旧数据中已删除的 palette 值导致白屏
      if (!this.palettes.find(p => p.key === newVal)) {
        this.bubbleCfg.palette = 'monet'
      }
    },
  },
  async mounted() {
    try {
      const resp = await api.getConfig()
      const data = resp.data
      this.config = {
        openlist: data.openlist || { api_url: '', username: '', password: '', default_path: '/115/AV' },
        emby: data.emby || { api_url: '', api_key: '' },
        telegram: data.telegram || { bot_token: '', allowed_user_ids: [] },
        crawler: data.crawler || { request_interval: 3 },
        scheduler: data.scheduler || { subscription_check_hour: 2 },
        notification: data.notification || { enabled: false, telegram: true, auto_download_notify: true, download_complete_notify: true, new_movie_notify: true }
      }
      this.telegramUsers = (this.config.telegram.allowed_user_ids || []).join(', ')
    } catch (e) {
      console.error('Failed to load config:', e)
    }
    this.loadBubbleCfg()
  },
  methods: {
    async save() {
      this.saving = true
      try {
        this.config.telegram.allowed_user_ids = this.telegramUsers.split(',').map(s => s.trim()).filter(Boolean)
        await api.updateConfig(this.config)
        this.saveBubbleCfg()
        this.$message.success('配置已保存')
      } catch (e) {
        console.error('Failed to save config:', e)
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
    },
    loadBubbleCfg() {
      try {
        const saved = localStorage.getItem('genres_bubble_cfg')
        if (saved) {
          const parsed = JSON.parse(saved)
          this.bubbleCfg = {
            ...{ baseSize: 16, fillPercent: 50, spacing: 16, colorMode: 'legendary', palette: 'monet', customGradients: [], customGradientsText: '', goldLegend: true, bubbleCount: 36 },
            ...parsed,
          }
          if (parsed.customGradients) {
            this.bubbleCfg.customGradients = parsed.customGradients
            this.bubbleCfg.customGradientsText = parsed.customGradients.join(',')
          }
        }
      } catch {}
    },
    saveBubbleCfg() {
      // Parse custom gradients text into array before saving
      if (this.bubbleCfg.customGradientsText) {
        this.bubbleCfg.customGradients = this.bubbleCfg.customGradientsText
          .split(',')
          .map(s => s.trim())
          .filter(s => s.startsWith('linear-gradient') || s.startsWith('#'))
      }
      localStorage.setItem('genres_bubble_cfg', JSON.stringify(this.bubbleCfg))
    },
    resetBubbleCfg() {
      this.bubbleCfg = { baseSize: 16, fillPercent: 50, spacing: 16, colorMode: 'legendary', palette: 'monet', customGradients: [], customGradientsText: '', goldLegend: true, bubbleCount: 36 }
      localStorage.removeItem('genres_bubble_cfg')
      this.$message.info('已恢复默认')
    }
  }
}
</script>

<style scoped>
.settings { padding: 24px; max-width: 800px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.settings-content { display: flex; flex-direction: column; gap: 16px; }

.settings-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
}
.settings-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  color: var(--accent);
}
.settings-card-header h2 { font-size: 15px; font-weight: 600; color: var(--text-primary); }

.form-group { margin-bottom: 14px; }
.form-group:last-child { margin-bottom: 0; }
.form-group label { display: block; margin-bottom: 6px; font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.form-group.checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  cursor: pointer;
}
.form-group.checkbox input { width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; }
.form-group.checkbox label { margin: 0; font-size: 14px; color: var(--text-primary); cursor: pointer; }

.color-mode-tabs {
  display: flex;
  gap: 8px;
}

.mode-tab {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: var(--transition);
}

.mode-tab.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.mode-tab:hover:not(.active) {
  border-color: var(--accent);
  color: var(--accent);
}

/* 色系下拉框 */
.palette-select-wrap {
  position: relative;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border);
}

.palette-select {
  width: 100%;
  padding: 8px 36px 8px 12px;
  background: var(--bg-card);
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
}

.palette-select:focus {
  outline: none;
  border-color: var(--accent);
}

.palette-select-wrap::after {
  content: '';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid var(--text-muted);
  pointer-events: none;
}

/* 下拉选中色的颜色预览条 */
.palette-color-bar {
  height: 8px;
  width: 100%;
}

.legendary-hint {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.8;
  padding: 10px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.legendary-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.legendary-dot.legendary { background: linear-gradient(135deg, #b88040, #d8a868); }
.legendary-dot.epic { background: linear-gradient(135deg, #9060c0, #7040a0); }
.legendary-dot.rare { background: linear-gradient(135deg, #4890c8, #3070a8); }
.legendary-dot.common { background: linear-gradient(135deg, #8090a0, #607080); }

.custom-gradients-input {
  resize: vertical;
  font-family: monospace;
  font-size: 11px;
  line-height: 1.5;
  min-height: 60px;
}

.settings-actions { padding-top: 8px; }
.settings-actions .btn { width: 100%; justify-content: center; padding: 12px; font-size: 15px; }
</style>
