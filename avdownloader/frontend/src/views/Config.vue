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
      saving: false
    }
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
  },
  methods: {
    async save() {
      this.saving = true
      try {
        this.config.telegram.allowed_user_ids = this.telegramUsers.split(',').map(s => s.trim()).filter(Boolean)
        await api.updateConfig(this.config)
        this.$message.success('配置已保存')
      } catch (e) {
        console.error('Failed to save config:', e)
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
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

.settings-actions { padding-top: 8px; }
.settings-actions .btn { width: 100%; justify-content: center; padding: 12px; font-size: 15px; }
</style>
