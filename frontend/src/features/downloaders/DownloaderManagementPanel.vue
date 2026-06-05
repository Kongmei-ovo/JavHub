<template>
  <div class="downloaders-panel apple-reveal">
    <div class="downloader-toolbar apple-surface">
      <div class="downloader-toolbar-copy">
        <strong>下载源</strong>
        <span>默认 {{ defaultDownloaderLabel }} · {{ enabledDownloaderCount }} 个已启用</span>
      </div>
      <div class="downloader-toolbar-actions">
        <button class="icon-action" type="button" title="刷新下载源" aria-label="刷新下载源" @click="$emit('refresh')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
        </button>
        <button class="icon-action primary" type="button" title="新增下载源" aria-label="新增下载源" @click="$emit('create')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="downloaders-list apple-surface">
      <article
        v-for="client in downloaderClients"
        :key="client.id"
        class="downloader-row"
        :class="{ disabled: !client.enabled, default: client.id === downloaders.default_id }"
        role="button"
        tabindex="0"
        @click="$emit('edit', client)"
        @keyup.enter="$emit('edit', client)"
      >
        <div class="downloader-row-main">
          <div class="downloader-avatar" :class="{ muted: !client.enabled }">
            {{ downloaderTypeMark(client.type) }}
          </div>
          <div class="downloader-copy">
            <div class="downloader-title-line">
              <strong>{{ client.name || downloaderTypeLabel(client.type) }}</strong>
              <span>{{ downloaderTypeLabel(client.type) }}</span>
            </div>
            <div class="downloader-summary">
              <span :title="client.address || ''">{{ shortDownloaderAddress(client.address) || '未配置地址' }}</span>
              <span :title="client.default_path || ''">{{ downloaderPathSummary(client) }}</span>
            </div>
          </div>
        </div>

        <div class="downloader-status-group">
          <span v-if="client.id === downloaders.default_id" class="downloader-pill default">默认</span>
          <span class="downloader-pill" :class="client.enabled ? 'enabled' : 'muted'">{{ client.enabled ? '启用' : '停用' }}</span>
          <span
            v-if="downloaderTestMessages[client.id]"
            class="downloader-pill test"
            :class="{ ok: downloaderTestMessages[client.id].ok }"
            :title="downloaderTestMessages[client.id].message"
          >
            {{ downloaderTestMessages[client.id].ok ? '已连接' : '失败' }}
          </span>
        </div>

        <label class="switch-mini switch-apple" title="启用下载源" @click.stop>
          <input type="checkbox" v-model="client.enabled" />
          <span></span>
        </label>

        <div class="downloader-row-actions" @click.stop>
          <button class="icon-action compact" type="button" :disabled="testingDownloaderId === client.id" title="测试连接" aria-label="测试连接" @click="$emit('test', client)">
            <svg v-if="testingDownloaderId !== client.id" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M22 12h-4l-3 8-6-16-3 8H2"/>
            </svg>
            <svg v-else class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M21 12a9 9 0 11-6.2-8.56"/>
            </svg>
          </button>
          <button class="icon-action compact" type="button" :disabled="client.id === downloaders.default_id" title="设为默认" aria-label="设为默认" @click="$emit('set-default', client.id)">
            <svg viewBox="0 0 24 24" :fill="client.id === downloaders.default_id ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </button>
          <button class="icon-action compact" type="button" title="编辑" aria-label="编辑" @click="$emit('edit', client)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4Z"/>
            </svg>
          </button>
          <button class="icon-action compact danger" type="button" :disabled="downloaderClients.length <= 1" title="删除" aria-label="删除" @click="$emit('remove', client.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/>
              <path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>
      </article>

      <div v-if="downloaderClients.length === 0" class="downloaders-empty">
        <strong>还没有下载源</strong>
        <span>添加一个下载器后就可以作为默认下载目标。</span>
      </div>
    </div>

    <div class="downloaders-footer apple-surface">
      <span>{{ downloaderClients.length }} 个下载源 · {{ enabledDownloaderCount }} 个启用</span>
      <button class="btn btn-primary" type="button" :disabled="savingDownloaders" @click="$emit('save')">
        {{ savingDownloaders ? '保存中...' : '保存更改' }}
      </button>
    </div>

    <div v-if="downloaderEditor.open" class="inline-dialog-overlay downloader-sheet-overlay" @click.self="$emit('close-editor')">
      <div class="inline-dialog downloader-sheet">
        <div class="inline-dialog-header">
          <div>
            <h2>{{ downloaderEditor.mode === 'new' ? '新增下载源' : '编辑下载源' }}</h2>
            <p>{{ downloaderEditor.draft?.name || downloaderTypeLabel(downloaderEditor.draft?.type) }}</p>
          </div>
          <button class="dialog-close-btn" type="button" aria-label="关闭" @click="$emit('close-editor')">×</button>
        </div>

        <div v-if="downloaderEditor.draft" class="downloader-sheet-body">
          <section class="downloader-sheet-section">
            <div class="sheet-section-title">
              <strong>基础信息</strong>
              <span>名称、类型、地址、路径</span>
            </div>
            <div class="downloader-sheet-grid">
              <label>
                名称
                <input class="input" v-model="downloaderEditor.draft.name" placeholder="家庭 qBittorrent" />
              </label>
              <label>
                类型
                <select class="input" v-model="downloaderEditor.draft.type" @change="$emit('sync-draft-defaults')">
                  <option v-for="type in downloaderTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
                </select>
              </label>
              <label class="wide-field">
                地址
                <input class="input" v-model="downloaderEditor.draft.address" :placeholder="downloaderAddressPlaceholder(downloaderEditor.draft.type)" />
              </label>
              <label class="wide-field">
                下载路径
                <input class="input" v-model="downloaderEditor.draft.default_path" :placeholder="downloaderPathPlaceholder(downloaderEditor.draft.type)" />
              </label>
            </div>
          </section>

          <section class="downloader-sheet-section">
            <div class="sheet-section-title">
              <strong>连接与选项</strong>
              <span>凭据、标签、超时、偏好</span>
            </div>
            <div class="downloader-sheet-grid">
              <label>
                用户名
                <input class="input" v-model="downloaderEditor.draft.username" autocomplete="off" />
              </label>
              <label>
                密码
                <input class="input" type="password" v-model="downloaderEditor.draft.password" autocomplete="new-password" :placeholder="downloaderEditor.draft.password_configured ? '留空不覆盖已有密码' : ''" />
              </label>
              <label v-if="downloaderEditor.draft.type === 'openlist' || downloaderEditor.draft.type === 'aria2'">
                Token
                <input class="input" type="password" v-model="downloaderEditor.draft.token" autocomplete="new-password" :placeholder="downloaderEditor.draft.token_configured ? '留空不覆盖已有 Token' : tokenPlaceholder(downloaderEditor.draft.type)" />
              </label>
              <label v-if="downloaderEditor.draft.type === 'qbittorrent'">
                分类
                <input class="input" v-model="downloaderEditor.draft.category" placeholder="可选" />
              </label>
              <label v-if="supportsDownloaderTags(downloaderEditor.draft.type)">
                标签
                <input class="input" v-model="downloaderEditor.draft.tags" placeholder="javhub,auto" />
              </label>
              <label>
                超时
                <input class="input" type="number" min="1" v-model.number="downloaderEditor.draft.timeout" />
              </label>
            </div>
            <div class="downloader-sheet-options">
              <label>
                <input type="checkbox" v-model="downloaderEditor.draft.enabled" />
                启用
              </label>
              <label>
                <input type="checkbox" v-model="downloaderEditor.draft.paused" />
                添加后暂停
              </label>
            </div>
          </section>
        </div>

        <div class="inline-dialog-actions">
          <button class="btn btn-ghost" type="button" @click="$emit('close-editor')">取消</button>
          <button class="btn btn-primary" type="button" @click="$emit('apply-editor')">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DownloaderManagementPanel',
  props: {
    downloaders: { type: Object, required: true },
    downloaderTypes: { type: Array, required: true },
    downloaderClients: { type: Array, required: true },
    enabledDownloaderCount: { type: Number, required: true },
    defaultDownloaderLabel: { type: String, required: true },
    savingDownloaders: { type: Boolean, default: false },
    testingDownloaderId: { type: String, default: '' },
    downloaderTestMessages: { type: Object, default: () => ({}) },
    downloaderEditor: { type: Object, required: true },
    downloaderTypeLabel: { type: Function, required: true },
    downloaderTypeMark: { type: Function, required: true },
    shortDownloaderAddress: { type: Function, required: true },
    downloaderPathSummary: { type: Function, required: true },
    supportsDownloaderTags: { type: Function, required: true },
    downloaderAddressPlaceholder: { type: Function, required: true },
    downloaderPathPlaceholder: { type: Function, required: true },
    tokenPlaceholder: { type: Function, required: true },
  },
  emits: [
    'refresh',
    'create',
    'edit',
    'test',
    'set-default',
    'remove',
    'save',
    'close-editor',
    'sync-draft-defaults',
    'apply-editor',
  ],
}
</script>

<style scoped>
.downloaders-panel {
  display: grid;
  gap: 16px;
}
.downloader-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.downloader-toolbar-copy strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0;
}
.downloader-toolbar-copy span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}
.downloader-toolbar-actions {
  display: flex;
  gap: 8px;
}
.icon-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), opacity var(--motion-fast);
}
.icon-action svg {
  width: 17px;
  height: 17px;
}
.icon-action:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.icon-action:focus-visible:not(:disabled) {
  outline: none;
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.icon-action.primary {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow);
}
.icon-action.primary:focus-visible {
  outline: none;
  transform: translateY(-1px);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  color: var(--text-primary);
  border-color: var(--glass-active-border);
  box-shadow: var(--glass-active-shadow), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.icon-action.compact {
  width: 38px;
  height: 38px;
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.icon-action.compact:focus-visible:not(:disabled) {
  outline: none;
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.icon-action.danger {
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
  border-color: var(--badge-error-border);
}
.icon-action.danger:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--badge-error-bg);
  box-shadow: var(--glass-control-shadow-hover);
}
.icon-action.danger:focus-visible:not(:disabled) {
  outline: none;
  transform: translateY(-1px);
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--badge-error-bg);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px color-mix(in srgb, var(--badge-error-text) 18%, transparent);
}
.icon-action:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}
.downloaders-list {
  display: grid;
  overflow: hidden;
}
.downloader-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 14px;
  min-height: 86px;
  padding: 14px 16px;
  border: 1px solid var(--glass-control-border);
  border-bottom-color: var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), opacity var(--motion-fast);
}
.downloader-row:last-child {
  border-bottom-color: var(--glass-control-border);
}
.downloader-row:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.downloader-row:focus-visible {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
  transform: translateY(-1px);
  outline: none;
}
.downloader-row.disabled {
  opacity: 0.68;
}
.downloader-row-main {
  display: flex;
  align-items: center;
  gap: 13px;
  min-width: 0;
}
.downloader-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  border-radius: 14px;
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.01em;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.downloader-avatar.muted {
  color: var(--text-muted);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-subtle);
}
.downloader-copy {
  min-width: 0;
}
.downloader-title-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.downloader-title-line strong {
  min-width: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.downloader-title-line span {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-summary {
  display: flex;
  gap: 10px;
  margin-top: 6px;
  min-width: 0;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-summary span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.downloader-summary span + span::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 3px;
  margin: 0 9px 2px 0;
  border-radius: 50%;
  background: var(--text-muted);
}
.downloader-status-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}
.downloader-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border: 1px solid var(--badge-pending-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-pending-bg);
  color: var(--badge-pending-text);
  font-size: 11px;
  font-weight: 700;
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  white-space: nowrap;
}
.downloader-pill.default,
.downloader-pill.enabled,
.downloader-pill.test.ok {
  border-color: var(--badge-success-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg);
  color: var(--badge-success-text);
}
.downloader-pill.test {
  max-width: 88px;
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
  overflow: hidden;
  text-overflow: ellipsis;
}
.downloaders-empty {
  display: grid;
  gap: 6px;
  padding: 34px 18px;
  text-align: center;
}
.downloaders-empty strong {
  color: var(--text-primary);
  font-size: 15px;
}
.downloaders-empty span {
  color: var(--text-muted);
  font-size: 13px;
}
.switch-mini {
  position: relative;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
}
.switch-mini input {
  position: absolute;
  opacity: 0;
}
.switch-mini span {
  position: absolute;
  inset: 9px 0;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
}
.switch-mini span::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--text-secondary);
  transition: transform 160ms ease, background 160ms ease;
}
.switch-mini input:checked + span {
  border-color: var(--badge-success-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--badge-success-bg);
}
.switch-mini input:checked + span::after {
  transform: translateX(20px);
  background: var(--badge-success-text);
}
.switch-apple {
  align-self: center;
}
.downloader-row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}
.downloaders-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
}
.downloaders-footer span {
  color: var(--text-muted);
  font-size: 12px;
}
.inline-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 20px;
  background: var(--surface-scrim);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
.inline-dialog {
  width: min(560px, 100%);
  border: 1px solid var(--glass-control-border);
  border-radius: 20px;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-sheet);
  box-shadow: var(--shadow-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  padding: 18px;
}
.inline-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.inline-dialog-header h2 {
  margin: 0;
  font-size: var(--type-panel-title);
  color: var(--text-primary);
  letter-spacing: 0;
}
.inline-dialog-header p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 13px;
}
.dialog-close-btn {
  width: 44px;
  height: 44px;
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 24px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.downloader-sheet {
  display: flex;
  flex-direction: column;
  width: min(720px, 100%);
  max-height: min(820px, calc(100vh - 48px));
}
.downloader-sheet-body {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}
.downloader-sheet-section {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 18px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.sheet-section-title strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}
.sheet-section-title span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-sheet-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.downloader-sheet-grid label {
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}
.downloader-sheet-grid .wide-field {
  grid-column: 1 / -1;
}
.downloader-sheet-grid .input {
  width: 100%;
  min-height: 44px;
}
.downloader-sheet-options {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 12px;
}
.downloader-sheet-options label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.inline-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}
.inline-dialog-actions .btn {
  min-height: 44px;
}
.spin-icon {
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .downloader-toolbar,
  .downloaders-footer,
  .downloader-toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .downloader-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    min-height: 118px;
    align-items: start;
  }
  .downloader-row-main {
    grid-column: 1 / -1;
  }
  .downloader-status-group {
    justify-content: flex-start;
  }
  .switch-apple {
    grid-column: 2;
    grid-row: 2;
  }
  .downloader-row-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
  .downloaders-footer .btn {
    width: 100%;
  }
  .downloader-sheet {
    width: 100%;
    max-height: calc(100vh - 96px);
  }
  .downloader-sheet-grid {
    grid-template-columns: 1fr;
  }
  .downloader-sheet-grid .wide-field {
    grid-column: auto;
  }
}
</style>
