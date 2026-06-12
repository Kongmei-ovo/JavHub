<template>
  <section class="settings-group open115-settings">
    <div class="settings-group-header">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
        <path d="M4 7h16M6 3h12l2 4v13H4V7l2-4Z"/>
        <path d="M9 12h6M12 9v6"/>
      </svg>
      <h2>115 Open</h2>
      <span class="open115-state" :class="{ ready: status.verified }">{{ statusLabel }}</span>
    </div>

    <div class="settings-list">
      <label class="settings-row">
        <span class="setting-copy">
          <span class="setting-title">AppID</span>
          <span class="setting-note">保存 AppID 后可发起 115 官方扫码授权。</span>
        </span>
        <span class="settings-control">
          <input class="input" :value="appId" autocomplete="off" @input="$emit('update:appId', $event.target.value)" />
        </span>
      </label>
      <label class="settings-row">
        <span class="setting-copy">
          <span class="setting-title">资源根目录</span>
          <span class="setting-note">影片资源按稳定 ItemId 写入该目录。</span>
        </span>
        <span class="settings-control">
          <input class="input" :value="rootPath" placeholder="/JavHub" @input="$emit('update:rootPath', $event.target.value)" />
        </span>
      </label>

      <div class="settings-row settings-row--stacked">
        <div class="setting-copy">
          <span class="setting-title">账户授权</span>
          <span class="setting-note">Token 只提交给后端，状态接口不会回传任何敏感值。</span>
        </div>
        <div class="settings-control settings-control--wide open115-actions">
          <button class="btn btn-secondary" type="button" :disabled="busy || !appId.trim()" @click="startAuth">
            {{ authUid ? '重新生成二维码' : '扫码绑定' }}
          </button>
          <button class="btn btn-secondary" type="button" :disabled="busy || !status.bound" @click="testConnection">测试连接</button>
          <button class="btn btn-ghost" type="button" :disabled="busy || !status.bound" @click="unbind">解绑</button>
        </div>
      </div>

      <div v-if="qrImageUrl" class="settings-row settings-row--stacked">
        <div class="setting-copy">
          <span class="setting-title">使用 115 App 扫码</span>
          <span class="setting-note">{{ authStateLabel }}</span>
        </div>
        <div class="settings-control settings-control--wide open115-qr">
          <img :src="qrImageUrl" alt="115 Open 授权二维码" loading="lazy" decoding="async" />
        </div>
      </div>

      <div class="settings-row settings-row--stacked">
        <div class="setting-copy">
          <span class="setting-title">导入 Refresh Token</span>
          <span class="setting-note">适用于已有 Open 授权；导入后仍会执行连接测试。</span>
        </div>
        <div class="settings-control settings-control--wide open115-import">
          <input
            class="input"
            type="password"
            v-model="refreshToken"
            autocomplete="new-password"
            placeholder="不会显示已保存的 token"
          />
          <button class="btn btn-secondary" type="button" :disabled="busy || !refreshToken.trim()" @click="importToken">导入并验证</button>
        </div>
      </div>
      <p v-if="message" class="open115-message" role="status">{{ message }}</p>
    </div>
  </section>
</template>

<script>
import api, { formatApiError } from '../../api'

const EMPTY_STATUS = {
  configured: false,
  bound: false,
  verified: false,
  access_token_configured: false,
  refresh_token_configured: false,
  root_path: '/JavHub',
}

export default {
  name: 'Open115SettingsPanel',
  props: {
    appId: { type: String, default: '' },
    rootPath: { type: String, default: '/JavHub' },
  },
  emits: ['update:appId', 'update:rootPath'],
  data() {
    return {
      status: { ...EMPTY_STATUS },
      refreshToken: '',
      authUid: '',
      qrImageUrl: '',
      authState: '',
      pollTimer: null,
      busy: false,
      message: '',
    }
  },
  computed: {
    statusLabel() {
      if (this.status.verified) return '已验证，可用于下载'
      if (this.status.bound) return '已绑定，等待连接测试'
      if (this.status.configured || this.appId.trim()) return '未绑定'
      return '请先保存 AppID'
    },
    authStateLabel() {
      return {
        waiting: '等待扫码',
        scanned: '已扫码，请在 115 App 中确认',
        confirmed: '授权成功，正在验证连接',
        expired: '二维码已过期，请重新生成',
      }[this.authState] || '等待扫码'
    },
  },
  async mounted() {
    await this.loadStatus()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async loadStatus() {
      try {
        const response = await api.getOpen115Status()
        this.status = { ...EMPTY_STATUS, ...(response.data || {}) }
      } catch (error) {
        this.message = formatApiError(error, { service: '115 Open', action: '读取状态' }).message
      }
    },
    async startAuth() {
      this.busy = true
      this.stopPolling()
      try {
        const response = await api.startOpen115Auth()
        this.authUid = response.data.uid
        this.qrImageUrl = response.data.qrcode_image_url
        this.authState = 'waiting'
        this.message = ''
        this.pollTimer = window.setInterval(this.pollAuth, 1800)
      } catch (error) {
        this.message = formatApiError(error, { service: '115 Open', action: '发起授权' }).message
      } finally {
        this.busy = false
      }
    },
    async pollAuth() {
      if (!this.authUid || this.busy) return
      try {
        const response = await api.pollOpen115Auth(this.authUid)
        this.authState = response.data.status
        if (this.authState === 'confirmed') {
          this.stopPolling()
          await this.testConnection()
        } else if (this.authState === 'expired') {
          this.stopPolling()
        }
      } catch (error) {
        this.stopPolling()
        this.message = formatApiError(error, { service: '115 Open', action: '查询扫码状态' }).message
      }
    },
    stopPolling() {
      if (this.pollTimer !== null) {
        window.clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async importToken() {
      this.busy = true
      try {
        await api.importOpen115Token(this.refreshToken)
        this.refreshToken = ''
        await this.testConnection()
      } catch (error) {
        this.message = formatApiError(error, { service: '115 Open', action: '导入授权' }).message
      } finally {
        this.busy = false
      }
    },
    async testConnection() {
      this.busy = true
      try {
        const response = await api.testOpen115()
        this.message = response.data.user_name ? `连接成功：${response.data.user_name}` : '连接成功'
      } catch (error) {
        this.message = formatApiError(error, { service: '115 Open', action: '连接测试' }).message
      } finally {
        await this.loadStatus()
        this.busy = false
      }
    },
    async unbind() {
      this.busy = true
      this.stopPolling()
      try {
        await api.unbindOpen115()
        this.authUid = ''
        this.qrImageUrl = ''
        this.authState = ''
        this.message = '已解绑'
        await this.loadStatus()
      } catch (error) {
        this.message = formatApiError(error, { service: '115 Open', action: '解绑' }).message
      } finally {
        this.busy = false
      }
    },
  },
}
</script>

<style scoped>
.open115-state {
  margin-left: auto;
  color: var(--text-muted);
  font-size: var(--type-caption-1);
}
.settings-list {
  overflow: hidden;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  background: var(--card);
}
.settings-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 0.9fr);
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--hairline);
}
.settings-row:first-child {
  border-top: 0;
}
.settings-row--stacked {
  align-items: start;
}
.setting-copy,
.settings-control {
  display: grid;
  gap: var(--space-1);
}
.setting-title {
  color: var(--text-primary);
  font-weight: 600;
}
.setting-note {
  color: var(--text-muted);
  font-size: var(--type-caption-1);
}
.settings-control--wide {
  width: 100%;
}
.open115-state.ready {
  color: var(--badge-success-text);
}
.open115-actions,
.open115-import {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.open115-import .input {
  min-width: min(360px, 100%);
  flex: 1;
}
.open115-qr img {
  width: 180px;
  height: 180px;
  border-radius: var(--radius-lg);
  background: white;
}
.open115-message {
  margin: 0;
  padding: 0 var(--space-5) var(--space-4);
  color: var(--text-secondary);
}
@media (max-width: 720px) {
  .settings-row {
    grid-template-columns: 1fr;
  }
}
</style>
