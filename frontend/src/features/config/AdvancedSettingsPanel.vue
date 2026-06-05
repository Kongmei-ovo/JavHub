<template>
  <div class="config-section">
    <div class="section-header">
      <h2>高级配置</h2>
      <p>进阶功能设置，包括配置备份、数据库导入、公共智能模型和网络代理。</p>
    </div>

    <div class="settings-card">
      <div class="card-content">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <h2>配置备份</h2>
        </div>
        <div class="form-slot">
          <div class="form-group">
            <button class="btn btn-secondary" type="button" @click="exportUserConfig" :disabled="exportingConfig || !canSaveConfig">
              {{ exportingConfig ? '导出中...' : '导出用户配置' }}
            </button>
            <small>导出当前可见配置，敏感字段会自动脱敏。</small>
          </div>
        </div>
      </div>
    </div>

    <div class="settings-card">
      <div class="card-content">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <h2>JavInfo 数据库导入</h2>
        </div>
        <div class="form-slot javinfo-import-panel">
          <div class="import-warning">
            <strong>危险操作：全量替换</strong>
            <span>导入成功后会替换 JavInfoApi 当前 PostgreSQL 库。系统会自动使用临时库恢复并保留最近旧库。</span>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>数据库地址</label>
              <input class="input" v-model="config.javinfo.import_db.host" placeholder="postgres" />
            </div>
            <div class="form-group compact-number">
              <label>端口</label>
              <input class="input" v-model.number="config.javinfo.import_db.port" type="number" min="1" max="65535" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>目标库</label>
              <input class="input" v-model="config.javinfo.import_db.database" placeholder="r18" />
            </div>
            <div class="form-group">
              <label>维护库</label>
              <input class="input" v-model="config.javinfo.import_db.maintenance_database" placeholder="postgres" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>用户</label>
              <input class="input" v-model="config.javinfo.import_db.user" placeholder="javhub" />
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="input-password-wrap">
                <input
                  class="input"
                  :type="showImportPassword ? 'text' : 'password'"
                  v-model="config.javinfo.import_db.password"
                  autocomplete="off"
                  placeholder="空白保存不覆盖现有密码"
                />
                <button class="input-eye-btn" type="button" @click="showImportPassword = !showImportPassword" :title="showImportPassword ? '隐藏' : '显示'">
                  <svg v-if="!showImportPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                </button>
              </div>
            </div>
          </div>
          <div class="import-actions">
            <button class="btn btn-secondary" type="button" @click="preflightJavInfoImport" :disabled="javinfoImportPreflighting || !canSaveConfig">
              {{ javinfoImportPreflighting ? '检查中...' : '预检数据库' }}
            </button>
            <button class="btn btn-secondary" type="button" @click="runJavInfoMigrations" :disabled="javinfoMigrating || !canSaveConfig">
              {{ javinfoMigrating ? '运行中...' : '运行 JavInfo 迁移' }}
            </button>
            <span v-if="javinfoImportPreflight" class="import-status" :class="{ error: !javinfoImportPreflight.ok }">
              {{ javinfoImportPreflight.ok ? '预检通过' : '预检未通过' }}
            </span>
            <span v-if="javinfoMigrationStatus" class="import-status" :class="{ error: javinfoMigrationStatusType === 'error' }">
              {{ javinfoMigrationStatus }}
            </span>
          </div>

          <div
            class="form-group import-file-drop"
            @dragover.prevent
            @drop.prevent="onJavInfoImportFileDrop"
          >
            <label>Dump 文件（.dump / .backup / .sql / .sql.gz）</label>
            <input class="input file-input" type="file" accept=".dump,.backup,.sql,.gz" @change="onJavInfoImportFileChange" />
            <small v-if="javinfoImportFile">{{ javinfoImportFile.name }} · {{ formatBytes(javinfoImportFile.size) }}</small>
          </div>

          <label class="form-group checkbox import-confirm">
            <input type="checkbox" v-model="javinfoImportConfirm" />
            <span>我确认这是全量替换导入，并已确认 dump 来源可信。</span>
          </label>

          <div v-if="javinfoImportRequiresDirectConfirm" class="import-warning import-warning-direct">
            <strong>无法使用临时库</strong>
            <span>当前账号没有建库权限，将直接清空目标库恢复；失败不能自动回滚。</span>
            <label class="checkbox import-confirm">
              <input type="checkbox" v-model="javinfoImportDirectConfirm" />
              <span>我确认接受直接恢复目标库模式。</span>
            </label>
          </div>

          <div v-if="javinfoImportJob" class="import-progress">
            <div class="import-progress-head">
              <span>{{ javinfoImportStatusLabel(javinfoImportJob) }}</span>
              <strong>{{ javinfoImportProgress }}%</strong>
            </div>
            <div class="progress-bar">
              <div class="progress-bar-fill" :style="{ transform: `scaleX(${javinfoImportProgress / 100})` }"></div>
            </div>
            <small v-if="javinfoImportJob.error" class="import-error">{{ javinfoImportJob.error }}</small>
            <pre v-if="javinfoImportLogTail" class="import-log-tail">{{ javinfoImportLogTail }}</pre>
          </div>

          <div class="import-actions">
            <button class="btn btn-primary" type="button" @click="startJavInfoImport" :disabled="!javinfoImportCanStart">
              {{ javinfoImportUploading ? '上传中...' : '开始导入' }}
            </button>
            <button v-if="javinfoImportJob && isJavInfoImportActive(javinfoImportJob)" class="btn btn-ghost" type="button" @click="cancelJavInfoImport">
              取消任务
            </button>
          </div>

          <div v-if="javinfoImportJobs.length" class="import-job-list">
            <div class="import-job-list-title">最近任务</div>
            <div v-for="job in javinfoImportJobs" :key="job.id" class="import-job-row">
              <span>{{ job.filename || `任务 #${job.id}` }}</span>
              <strong>{{ javinfoImportStatusLabel(job) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="settings-card">
      <div class="card-content">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
            <path d="M12 2v4"/>
            <path d="M12 18v4"/>
            <path d="M4.93 4.93l2.83 2.83"/>
            <path d="M16.24 16.24l2.83 2.83"/>
            <path d="M2 12h4"/>
            <path d="M18 12h4"/>
            <path d="M4.93 19.07l2.83-2.83"/>
            <path d="M16.24 7.76l2.83-2.83"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          <h2>公共智能模型</h2>
        </div>
        <div class="form-slot">
          <div class="form-group">
            <label>接口类型</label>
            <div class="segmented-mini wide ai-provider-control">
              <button
                v-for="option in aiProviderOptions"
                :key="option.value"
                type="button"
                :class="{ active: config.ai.provider === option.value }"
                @click="config.ai.provider = option.value"
              >{{ option.label }}</button>
            </div>
            <small>{{ currentAiProviderHint }}</small>
          </div>
          <div class="form-group">
            <label>{{ currentAiProviderLabel }} 接口地址</label>
            <input class="input" v-model="currentAiConfig.base_url" :placeholder="currentAiProviderPlaceholder" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>模型</label>
              <input class="input" v-model="currentAiConfig.model" :placeholder="currentAiModelPlaceholder" list="ai-model-options" />
              <datalist id="ai-model-options">
                <option v-for="model in aiModelOptions" :key="model.id" :value="model.id">{{ model.name || model.id }}</option>
              </datalist>
            </div>
            <div class="form-group">
              <label>超时（秒）</label>
              <input class="input" v-model.number="currentAiConfig.timeout" type="number" min="1" />
            </div>
          </div>
          <div v-if="config.ai.provider !== 'ollama'" class="form-group">
            <label>密钥</label>
            <div class="input-password-wrap">
              <input
                class="input"
                :type="showAiKey ? 'text' : 'password'"
                v-model="currentAiConfig.api_key"
                autocomplete="off"
                placeholder="空白保存不覆盖现有密钥"
              />
              <button class="input-eye-btn" type="button" @click="showAiKey = !showAiKey" :title="showAiKey ? '隐藏' : '显示'">
                <svg v-if="!showAiKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
            <small>用于智能翻译兜底、演员映射判断等智能功能。</small>
          </div>
          <div class="form-group ai-test-row">
            <button
              class="btn btn-ghost"
              type="button"
              @click="loadAiModels"
              :disabled="aiLoadingModels || !canSaveConfig || !currentAiConfig.base_url"
            >
              {{ aiLoadingModels ? '获取中...' : '获取模型列表' }}
            </button>
            <button
              class="btn btn-secondary"
              type="button"
              @click="testAIModel"
              :disabled="aiTesting || !canSaveConfig || !currentAiConfig.base_url || !currentAiConfig.model"
            >
              {{ aiTesting ? '测试中...' : '测试模型调用' }}
            </button>
            <span v-if="aiTestMsg" class="ai-test-msg" :class="{ error: aiTestType === 'error' }">{{ aiTestMsg }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="settings-card">
      <div class="card-content">
        <div class="settings-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
            <circle cx="12" cy="12" r="10"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
          </svg>
          <h2>网络代理</h2>
        </div>
        <div class="form-slot">
          <div class="form-group checkbox">
            <input type="checkbox" id="proxyEnabled" v-model="config.proxy.enabled" />
            <label for="proxyEnabled">启用代理</label>
          </div>
          <div class="form-group">
            <label>HTTP 代理</label>
            <input class="input" v-model="config.proxy.http_url" placeholder="http://127.0.0.1:7890" :disabled="!config.proxy.enabled" />
          </div>
          <div class="form-group">
            <label>HTTPS 代理</label>
            <input class="input" v-model="config.proxy.https_url" placeholder="https://127.0.0.1:7890" :disabled="!config.proxy.enabled" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../../api'
import { requestConfirm } from '../../utils/confirmDialog'
import { formatBytes, isJavInfoImportActive, javinfoImportProgress, javinfoImportStatusLabel } from '../../utils/javinfoImportPresentation.js'

const AI_PROVIDER_OPTIONS = [
  { value: 'openai_compatible', label: 'OpenAI 兼容', hint: '适合 OpenAI、One API、LiteLLM、OpenRouter 等兼容接口。', placeholder: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  { value: 'gemini', label: 'Gemini', hint: '使用 Google Gemini 原生 generateContent 接口。', placeholder: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-2.0-flash' },
  { value: 'ollama', label: 'Ollama', hint: '连接本机或局域网 Ollama 服务。', placeholder: 'http://localhost:11434', model: 'qwen2.5:7b' },
]

export default {
  name: 'AdvancedSettingsPanel',
  props: {
    config: { type: Object, required: true },
    canSaveConfig: { type: Boolean, default: false },
  },
  data() {
    return {
      exportingConfig: false,
      javinfoImportPreflighting: false,
      javinfoMigrating: false,
      javinfoImportPreflight: null,
      javinfoMigrationStatus: '',
      javinfoMigrationStatusType: 'info',
      showImportPassword: false,
      javinfoImportFile: null,
      javinfoImportConfirm: false,
      javinfoImportDirectConfirm: false,
      javinfoImportPreflightSignature: '',
      javinfoImportUploading: false,
      javinfoImportUploadProgress: 0,
      javinfoImportJob: null,
      javinfoImportJobs: [],
      javinfoImportPollTimer: null,
      aiProviderOptions: AI_PROVIDER_OPTIONS,
      aiModelOptions: [],
      showAiKey: false,
      aiLoadingModels: false,
      aiTesting: false,
      aiTestMsg: '',
      aiTestType: 'info',
    }
  },
  computed: {
    currentAiProvider() {
      return this.aiProviderOptions.find(option => option.value === this.config.ai.provider) || this.aiProviderOptions[0]
    },
    currentAiProviderLabel() {
      return this.currentAiProvider.label
    },
    currentAiProviderHint() {
      return this.currentAiProvider.hint
    },
    currentAiProviderPlaceholder() {
      return this.currentAiProvider.placeholder
    },
    currentAiModelPlaceholder() {
      return this.currentAiProvider.model
    },
    currentAiConfig() {
      const provider = this.config.ai.provider || 'openai_compatible'
      return this.config.ai[provider] || this.config.ai.openai_compatible
    },
    javinfoImportCanStart() {
      return Boolean(
        this.canSaveConfig
        && this.javinfoImportFile
        && this.javinfoImportConfirm
        && this.javinfoImportPreflightCurrent()?.ok
        && (!this.javinfoImportRequiresDirectConfirm || this.javinfoImportDirectConfirm)
        && !this.javinfoImportUploading
        && !this.isJavInfoImportActive(this.javinfoImportJob)
      )
    },
    javinfoImportRequiresDirectConfirm() {
      return Boolean(
        this.javinfoImportPreflightCurrent()?.ok
        && this.javinfoImportPreflightCurrent()?.checks?.database?.can_create_database === false
      )
    },
    javinfoImportLogTail() {
      return (this.javinfoImportJob?.logs || []).slice(-12).join('\n')
    },
    javinfoImportProgress() {
      return javinfoImportProgress({
        job: this.javinfoImportJob,
        uploading: this.javinfoImportUploading,
        uploadProgress: this.javinfoImportUploadProgress,
        fileSize: this.javinfoImportFile?.size,
      })
    },
  },
  mounted() {
    this.listJavInfoImportJobs()
  },
  unmounted() {
    this.stopJavInfoImportPolling()
  },
  methods: {
    formatBytes,
    isJavInfoImportActive,
    javinfoImportStatusLabel,
    async exportUserConfig() {
      if (!this.canSaveConfig) {
        this.$message.error('配置未加载成功，已阻止导出')
        return
      }
      this.exportingConfig = true
      try {
        const resp = await api.exportConfig()
        const blob = resp.data instanceof Blob
          ? resp.data
          : new Blob([resp.data], { type: 'application/x-yaml;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
        link.href = url
        link.download = `javhub-config-${stamp}.yaml`
        document.body.appendChild(link)
        link.click()
        link.remove()
        URL.revokeObjectURL(url)
        this.$message.success('配置已导出')
      } catch (e) {
        console.error('Failed to export config:', e)
        this.$message.error(e.response?.data?.detail || '导出失败')
      } finally {
        this.exportingConfig = false
      }
    },
    async testAIModel() {
      if (!this.canSaveConfig) {
        this.aiTestMsg = '配置未加载成功，请先重新加载'
        this.aiTestType = 'error'
        return
      }
      this.aiTesting = true
      this.aiTestMsg = ''
      this.aiTestType = 'info'
      try {
        const resp = await api.testAiModel(this.config.ai)
        const latency = resp.data?.latency_ms ? ` · ${resp.data.latency_ms}ms` : ''
        const model = resp.data?.model || this.currentAiConfig.model
        const provider = resp.data?.provider || this.config.ai.provider
        this.aiTestMsg = `调用成功：${provider} / ${model}${latency}`
        this.aiTestType = 'success'
        this.$message.success('模型调用正常')
      } catch (e) {
        this.aiTestMsg = e.response?.data?.detail || '模型调用失败'
        this.aiTestType = 'error'
      } finally {
        this.aiTesting = false
      }
    },
    async loadAiModels() {
      if (!this.canSaveConfig) {
        this.aiTestMsg = '配置未加载成功，请先重新加载'
        this.aiTestType = 'error'
        return
      }
      this.aiLoadingModels = true
      this.aiTestMsg = ''
      this.aiTestType = 'info'
      try {
        const resp = await api.listAiModels(this.config.ai)
        this.aiModelOptions = resp.data?.models || []
        if (this.aiModelOptions.length && !this.currentAiConfig.model) {
          this.currentAiConfig.model = this.aiModelOptions[0].id
        }
        this.aiTestMsg = this.aiModelOptions.length ? `已获取 ${this.aiModelOptions.length} 个模型` : '没有返回可用模型'
        this.aiTestType = this.aiModelOptions.length ? 'success' : 'info'
      } catch (e) {
        this.aiTestMsg = e.response?.data?.detail || '获取模型列表失败'
        this.aiTestType = 'error'
      } finally {
        this.aiLoadingModels = false
      }
    },
    setJavInfoImportFile(file) {
      this.javinfoImportFile = file
      this.javinfoImportPreflight = null
      this.javinfoImportPreflightSignature = ''
      this.javinfoImportDirectConfirm = false
      this.javinfoImportUploadProgress = 0
      this.javinfoImportJob = null
    },
    onJavInfoImportFileChange(event) {
      this.setJavInfoImportFile(event?.target?.files?.[0] || null)
    },
    onJavInfoImportFileDrop(event) {
      this.setJavInfoImportFile(event?.dataTransfer?.files?.[0] || null)
    },
    javinfoImportRequestSignature() {
      return JSON.stringify({
        import_db: this.config.javinfo.import_db,
        file_size: this.javinfoImportFile?.size || 0,
      })
    },
    javinfoImportPreflightCurrent() {
      if (this.javinfoImportPreflightSignature !== this.javinfoImportRequestSignature()) return null
      return this.javinfoImportPreflight
    },
    async preflightJavInfoImport() {
      if (!this.canSaveConfig) {
        this.$message.error('配置未加载成功，已阻止预检')
        return
      }
      this.javinfoImportPreflighting = true
      this.javinfoImportPreflight = null
      this.javinfoImportPreflightSignature = ''
      this.javinfoImportDirectConfirm = false
      try {
        const signature = this.javinfoImportRequestSignature()
        const resp = await api.preflightJavInfoImport(
          this.config.javinfo.import_db,
          this.javinfoImportFile?.size || 0,
        )
        this.javinfoImportPreflight = resp.data
        this.javinfoImportPreflightSignature = signature
        if (resp.data?.ok) {
          this.$message.success('JavInfo 数据库预检通过')
        } else {
          this.$message.warning('JavInfo 数据库预检未通过')
        }
      } catch (e) {
        this.javinfoImportPreflight = { ok: false, error: e.response?.data?.detail || e.message }
        this.javinfoImportPreflightSignature = this.javinfoImportRequestSignature()
      } finally {
        this.javinfoImportPreflighting = false
      }
    },
    async runJavInfoMigrations() {
      if (!this.canSaveConfig) {
        this.$message.error('配置未加载成功，已阻止迁移')
        return
      }
      const confirmed = await requestConfirm({
        title: '运行 JavInfo 迁移',
        message: '确认让 JavInfoApi 应用缺失的辅助表和索引？',
        details: '此操作会复用 JavInfoApi 的幂等 migrations，适合修复导入后缺少派生统计表的问题。',
        confirmText: '运行迁移',
      })
      if (!confirmed) return
      this.javinfoMigrating = true
      this.javinfoMigrationStatus = ''
      this.javinfoMigrationStatusType = 'info'
      try {
        const resp = await api.runJavInfoMigrations(false)
        this.javinfoMigrationStatus = resp.data?.ok ? 'JavInfo 迁移已完成' : 'JavInfo 迁移已返回'
        this.javinfoMigrationStatusType = 'success'
        this.$message.success('JavInfo 迁移已完成')
      } catch (e) {
        const message = e.response?.data?.detail || e.message || 'JavInfo 迁移失败'
        this.javinfoMigrationStatus = message
        this.javinfoMigrationStatusType = 'error'
        this.$message.error(message)
      } finally {
        this.javinfoMigrating = false
      }
    },
    async startJavInfoImport() {
      if (!this.javinfoImportCanStart) return
      const confirmed = await requestConfirm({
        title: '开始 JavInfo 全量导入',
        message: `确认用 ${this.javinfoImportFile?.name || 'dump 文件'} 替换目标库 ${this.config.javinfo.import_db.database || '未命名数据库'}？`,
        details: this.javinfoImportRequiresDirectConfirm
          ? '当前为直接恢复模式，会清空目标库；失败不能自动回滚。'
          : '系统会上传 dump 并启动恢复任务，成功后切换 JavInfoApi 使用的新库。',
        confirmText: '开始导入',
        tone: this.javinfoImportRequiresDirectConfirm ? 'danger' : 'default',
      })
      if (!confirmed) return
      this.javinfoImportUploading = true
      this.javinfoImportUploadProgress = 0
      try {
        const createResp = await api.createJavInfoImportJob({
          filename: this.javinfoImportFile.name,
          file_size: this.javinfoImportFile.size,
          import_db: this.config.javinfo.import_db,
          confirm_replace: this.javinfoImportConfirm,
          confirm_direct_restore: this.javinfoImportDirectConfirm,
        })
        this.javinfoImportJob = createResp.data
        const uploadResp = await api.uploadJavInfoImportDump(
          createResp.data.id,
          this.javinfoImportFile,
          (event) => {
            if (event.total) {
              this.javinfoImportUploadProgress = Math.round(event.loaded * 100 / event.total)
            }
          },
        )
        this.javinfoImportJob = uploadResp.data
        this.startJavInfoImportPolling(createResp.data.id)
        await this.listJavInfoImportJobs()
        this.$message.success('Dump 已上传，开始恢复数据库')
      } catch (e) {
        const message = e.response?.data?.detail || e.message || '导入启动失败'
        this.$message.error(message)
        if (this.javinfoImportJob) {
          this.javinfoImportJob = { ...this.javinfoImportJob, status: 'failed', error: message }
        }
      } finally {
        this.javinfoImportUploading = false
      }
    },
    startJavInfoImportPolling(jobId) {
      this.stopJavInfoImportPolling()
      this.javinfoImportPollTimer = setInterval(async () => {
        try {
          const resp = await api.getJavInfoImportJob(jobId)
          this.javinfoImportJob = resp.data
          if (!this.isJavInfoImportActive(resp.data)) {
            this.stopJavInfoImportPolling()
            await this.listJavInfoImportJobs()
          }
        } catch (e) {
          this.stopJavInfoImportPolling()
        }
      }, 2000)
    },
    stopJavInfoImportPolling() {
      if (this.javinfoImportPollTimer) {
        clearInterval(this.javinfoImportPollTimer)
        this.javinfoImportPollTimer = null
      }
    },
    async listJavInfoImportJobs() {
      try {
        const resp = await api.listJavInfoImportJobs(5)
        this.javinfoImportJobs = resp.data?.data || []
      } catch (e) {
        this.javinfoImportJobs = []
      }
    },
    async cancelJavInfoImport() {
      if (!this.javinfoImportJob?.id) return
      try {
        const resp = await api.cancelJavInfoImportJob(this.javinfoImportJob.id)
        this.javinfoImportJob = resp.data
        const stillActive = this.isJavInfoImportActive(resp.data)
        if (!stillActive) {
          this.stopJavInfoImportPolling()
        } else {
          this.startJavInfoImportPolling(this.javinfoImportJob.id)
        }
        await this.listJavInfoImportJobs()
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '取消失败')
      }
    },
  },
}
</script>
