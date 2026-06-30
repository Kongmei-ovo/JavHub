<template>
  <div class="settings page-shell page-shell--gallery">
    <div class="settings-header">
      <div class="settings-header-meta">
        <h1>配置中心</h1>
      </div>
      <!-- 配置路径挪到标题行右侧；仅未挂载(暂停保存)时升级为告警，正常态只静静显示路径。 -->
      <div v-if="configLoaded && !configLoadError" class="settings-header-status">
        <span v-if="!configMeta.config_loaded" class="shs-warn" :title="configStatusDescription">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          {{ configStatusTitle }} · 已暂停保存
        </span>
        <code v-else-if="configMeta.config_path" class="shs-path" :title="configMeta.config_path">{{ configMeta.config_path }}</code>
      </div>
    </div>
    <main class="settings-content-wide">
      <AppleSkeleton v-if="configLoading" class="settings-loading apple-surface" variant="list" :items="4" label="配置加载中" />
      <AppleErrorState
        v-else-if="configLoadError"
        :title="configLoadErrorTitle"
        :description="configLoadErrorDescription"
        :source-label="configStatusSourceLabel"
        :details="configStatusDetails"
        next-step="重新加载会读取本地配置和后端运行状态；也可以先查看运行日志定位初始化问题。"
        retry-label="重新加载"
        secondary-action-label="查看日志"
        @retry="loadConfig"
        @secondary-action="$router.push('/logs')"
      />
      <div v-else class="settings-shell">
        <nav class="settings-sidebar" aria-label="设置分组">
          <div class="settings-sidebar-list">
            <button
              type="button"
              v-for="group in navGroups"
              :key="group.id"
              class="tab-item"
              :class="{ active: activeGroup === group.id }"
              :aria-current="activeGroup === group.id ? 'page' : undefined"
              @click="activeGroup = group.id"
            >
              <span class="tab-icon">
                <svg v-if="group.id === 'services'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                  <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
                </svg>
                <svg v-else-if="group.id === 'automation'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <svg v-else-if="group.id === 'telegram'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                </svg>
                <svg v-else-if="group.id === 'appearance'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                  <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z"/>
                </svg>
                <svg v-else-if="group.id === 'advanced'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                  <path d="M20 7h-9m14 10h-9M5 7h14M5 17h14"/>
                  <circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/>
                </svg>
              </span>
              <span class="tab-label">{{ group.label }}</span>
            </button>
          </div>
        </nav>
        <section class="settings-pane" aria-live="polite">
      <transition name="fade-slide" mode="out-in">
        <div :key="activeGroup" class="active-section">
          <!-- Services Section -->
          <div v-if="activeGroup === 'services'" class="config-section">
            <Open115SettingsPanel
              v-model:app-id="config.open115.app_id"
              v-model:root-path="config.open115.root_path"
            />
            <!-- JavInfoApi -->
            <section class="settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <ellipse cx="12" cy="5" rx="9" ry="3"/>
                  <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                  <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
                <h2>数据源 / JavInfoApi</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">API 地址</span>
                    <span class="setting-note">JavInfoApi 服务入口。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="config.javinfo.api_url" placeholder="http://javinfoapi:18080" />
                  </span>
                </label>
                <div class="settings-row settings-row--stacked">
                  <div class="setting-copy">
                    <span class="setting-title">运行时状态</span>
                    <span class="setting-note">后端当前读取到的配置路径和 JavInfo API URL。</span>
                  </div>
                  <div class="settings-control settings-control--wide">
                    <div class="javinfo-runtime-panel">
                      <div class="javinfo-runtime-row">
                        <span>运行时配置路径</span>
                        <code>{{ configMeta.config_path || '未返回' }}</code>
                      </div>
                      <div class="javinfo-runtime-row">
                        <span>当前 JavInfo API URL</span>
                        <code>{{ javinfoApiUrl || '未设置' }}</code>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="javinfoRuntimeWarning" class="settings-row settings-row--warning">
                  <div class="setting-copy">
                    <span class="setting-title">Docker 地址提醒</span>
                    <span class="setting-note">{{ javinfoRuntimeWarning }}</span>
                  </div>
                  <div class="settings-control">
                    <button class="btn btn-secondary" type="button" @click="applyDockerJavInfoUrl">
                      修正为 Docker 服务地址
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>
          <!-- Telegram Section -->
          <div v-if="activeGroup === 'telegram'" class="config-section">
            <section class="settings-group telegram-settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                </svg>
                <h2>Bot 连接</h2>
              </div>
              <div class="settings-list">
                <div class="settings-row">
                  <div class="setting-copy">
                    <span class="setting-title">Bot Token</span>
                    <span class="setting-note">Telegram Bot 的访问令牌。</span>
                  </div>
                  <div class="settings-control">
                    <div class="input-password-wrap">
                      <input
                        class="input"
                        :type="showBotToken ? 'text' : 'password'"
                        v-model="config.telegram.bot_token"
                        autocomplete="off"
                      />
                      <button class="input-eye-btn" type="button" @click="showBotToken = !showBotToken" :title="showBotToken ? '隐藏' : '显示'">
                        <svg v-if="!showBotToken" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                          <circle cx="12" cy="12" r="3"/>
                        </svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
                          <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                          <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">允许的用户编号</span>
                    <span class="setting-note">用逗号分隔多个 Telegram 用户 ID。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="telegramUsers" placeholder="123456789,987654321" />
                  </span>
                </label>
                <div class="settings-row settings-row--actions">
                  <div class="setting-copy">
                    <span class="setting-title">发送测试信息</span>
                    <span class="setting-note">验证 Bot Token 和允许用户是否能收到通知。</span>
                  </div>
                  <div class="settings-control settings-control--wide telegram-test-row" :aria-busy="telegramTestBusy" aria-live="polite">
                    <div class="telegram-test-actions">
                      <button
                        class="btn btn-secondary"
                        type="button"
                        @click="testTelegram"
                        :disabled="testingTelegram || !canSaveConfig || !config.telegram.bot_token"
                        :aria-describedby="'telegram-test-status'"
                      >
                        {{ testingTelegram ? '发送中...' : '发送测试信息' }}
                      </button>
                    </div>
                    <span id="telegram-test-status" class="telegram-test-status" role="status">{{ telegramTestStatus }}</span>
                  </div>
                </div>
              </div>
            </section>
            <section class="settings-group notification-settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                  <path d="M13.73 21a2 2 0 01-3.46 0"/>
                </svg>
                <h2>通知事件</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row settings-row--toggle" for="notifEnabled">
                  <span class="setting-copy">
                    <span class="setting-title">启用通知</span>
                    <span class="setting-note">允许系统发送所有通知事件。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="notifEnabled" v-model="config.notification.enabled" role="switch" />
                  </span>
                </label>
                <label class="settings-row settings-row--toggle" for="notifTelegram">
                  <span class="setting-copy">
                    <span class="setting-title">Telegram 渠道</span>
                    <span class="setting-note">通过 Telegram Bot 发送通知。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="notifTelegram" v-model="config.notification.telegram" role="switch" />
                  </span>
                </label>
                <label class="settings-row settings-row--toggle" for="notifAutoDownload">
                  <span class="setting-copy">
                    <span class="setting-title">自动下载时通知</span>
                    <span class="setting-note">自动任务下发下载时提醒。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="notifAutoDownload" v-model="config.notification.auto_download_notify" role="switch" />
                  </span>
                </label>
                <label class="settings-row settings-row--toggle" for="notifComplete">
                  <span class="setting-copy">
                    <span class="setting-title">下载完成时通知</span>
                    <span class="setting-note">下载器报告完成后提醒。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="notifComplete" v-model="config.notification.download_complete_notify" role="switch" />
                  </span>
                </label>
                <label class="settings-row settings-row--toggle" for="notifNewMovie">
                  <span class="setting-copy">
                    <span class="setting-title">发现新片时通知</span>
                    <span class="setting-note">订阅或库存扫描发现新内容时提醒。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="notifNewMovie" v-model="config.notification.new_movie_notify" role="switch" />
                  </span>
                </label>
              </div>
            </section>
          </div>
          <!-- Automation Section -->
          <div v-if="activeGroup === 'automation'" class="config-section">
            <section class="settings-group automation-settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <path d="M3 3v18h18"/>
                  <path d="M7 15l3-3 3 2 5-7"/>
                </svg>
                <h2>下载候选处理</h2>
              </div>
              <div class="settings-list">
                <div class="settings-row">
                  <div class="setting-copy">
                    <span class="setting-title">处理策略</span>
                    <span class="setting-note">{{ currentPolicyHint }}</span>
                  </div>
                  <div class="settings-control settings-control--wide">
                    <div class="segmented-mini wide automation-policy-control" aria-label="处理策略">
                      <button
                        v-for="option in downloadPolicyOptions"
                        :key="option.value"
                        type="button"
                        :class="{ active: config.automation.download_policy === option.value }"
                        @click="config.automation.download_policy = option.value"
                      >{{ option.label }}</button>
                    </div>
                  </div>
                </div>
                <div class="settings-row settings-row--stacked">
                  <div class="setting-copy">
                    <span class="setting-title">允许自动处理的来源</span>
                    <span class="setting-note">只对勾选来源的下载候选执行自动规则。</span>
                  </div>
                  <div class="settings-control settings-control--wide source-check-list-control">
                    <div class="source-check-list" role="group" aria-label="允许自动处理的来源">
                      <label v-for="source in candidateSourceOptions" :key="source.value" :class="['source-check-item', { 'is-selected': config.automation.candidate_sources.includes(source.value) }]">
                        <input type="checkbox" :checked="config.automation.candidate_sources.includes(source.value)" @change="toggleAutomationSource(source.value)" />
                        <span class="source-check-dot" aria-hidden="true"></span>
                        <span class="source-check-label">{{ source.label }}</span>
                      </label>
                    </div>
                  </div>
                </div>
                <label class="settings-row settings-row--toggle" for="rulesRequireMagnet">
                  <span class="setting-copy">
                    <span class="setting-title">规则模式要求 magnet</span>
                    <span class="setting-note">规则模式只处理已有 magnet 的候选。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="rulesRequireMagnet" v-model="config.automation.rules_require_magnet" role="switch" />
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">自动处理间隔</span>
                    <span class="setting-note">分钟，0 表示关闭后台自动处理。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.automation.auto_process_interval_minutes" type="number" min="0" max="1440" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">分钟</span>
                      <span class="settings-number-range">0-1440</span>
                    </span>
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">单次自动下发上限</span>
                    <span class="setting-note">0 表示不限。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.automation.max_auto_downloads_per_run" type="number" min="0" max="500" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">次</span>
                      <span class="settings-number-range">0-500</span>
                    </span>
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">24 小时自动下发上限</span>
                    <span class="setting-note">0 表示不限。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.automation.max_auto_downloads_per_24h" type="number" min="0" max="5000" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">24 小时</span>
                      <span class="settings-number-range">0-5000</span>
                    </span>
                  </span>
                </label>
              </div>
            </section>
            <!-- 订阅检查 -->
            <section class="settings-group subscription-schedule-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <h2>订阅检查</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">每日检查时间</span>
                    <span class="setting-note">演员订阅每天自动检查新作的时刻（0-23 时）。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.scheduler.subscription_check_hour" type="number" min="0" max="23" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">时</span>
                      <span class="settings-number-range">0-23</span>
                    </span>
                  </span>
                </label>
              </div>
            </section>
          </div>
          <!-- Appearance Section -->
          <div v-if="activeGroup === 'appearance'" class="config-section appearance-section">
            <div class="appearance-settings-stack">
              <section class="settings-group appearance-global-group">
                <div class="settings-group-header">
                  <h2>全局偏好</h2>
                  <span class="appearance-chip">{{ displayLangLabel }}</span>
                </div>
                <div class="settings-list compact">
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">显示语言</span>
                      <span class="setting-note">{{ displayLangLabel }}</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="显示语言">
                        <button
                          v-for="option in displayLangOptions"
                          :key="option.value"
                          type="button"
                          :class="{ active: displayLangVal === option.value }"
                          :aria-pressed="displayLangVal === option.value"
                          @click="setDisplayLang(option.value)"
                        >{{ option.label }}</button>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
              <section class="settings-group appearance-search-group">
                <div class="settings-group-header">
                  <h2>影片检索</h2>
                  <span class="appearance-chip">{{ config.javinfo.page_size }} 条 / 页</span>
                </div>
                <div class="settings-list">
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">检索页数量</span>
                      <span class="setting-note">{{ config.javinfo.page_size }} 条 / 页</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="检索页数量">
                        <button
                          v-for="size in pageSizeOptions"
                          :key="size"
                          type="button"
                          :class="{ active: config.javinfo.page_size === size }"
                          :aria-pressed="config.javinfo.page_size === size"
                          @click="config.javinfo.page_size = size"
                        >{{ size }}</button>
                      </div>
                    </div>
                  </div>
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">默认排序</span>
                      <span class="setting-note">{{ searchSortLabel }}</span>
                    </div>
                    <div class="settings-control">
                      <GlassSelect
                        v-model="searchPrefs.defaultSort"
                        :options="searchSortOptions"
                        class="glass-select-control glass-select-control--wide"
                        placement="right"
                        aria-label="影片检索默认排序"
                      />
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
          <AdvancedSettingsPanel
            v-if="activeGroup === 'advanced'"
            :config="config"
            :can-save-config="canSaveConfig"
          />
        </div>
      </transition>
        </section>
      </div>
    </main>
    <Teleport to="body">
      <!-- Global Floating Footer for Actions -->
      <div v-if="canSaveConfig" class="settings-footer" :aria-busy="saving" aria-live="polite">
        <div class="footer-content page-rail page-rail--standard">
          <div id="config-save-status" class="settings-save-status" role="status">
            <strong>{{ saveFooterTitle }}</strong>
            <span>{{ saveFooterNote }}</span>
          </div>
          <div class="settings-save-actions">
            <button class="btn btn-primary" type="button" @click="save" :disabled="saving || !canSaveConfig" :aria-describedby="'config-save-status'">
              <span v-if="saving" class="spinner save-spinner"></span>
              <span>{{ saving ? '正在保存' : '保存所有更改' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
<script>
import api from '../api'
import { displayLang } from '../utils/displayLang.js'
import { DEFAULT_SEARCH_PREFERENCES, loadSearchPreferences, saveSearchPreferences } from '../utils/searchPreferences.js'
import AppleErrorState from '../components/AppleErrorState.vue'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import GlassSelect from '../components/GlassSelect.vue'
import { AdvancedSettingsPanel } from '../features/config/advancedSettingsAsync.js'
import Open115SettingsPanel from '../features/config/Open115SettingsPanel.vue'
import { DEFAULT_CONFIG } from '../features/config/configDefaults.js'
import { candidateSourceOptions, displayLangOptions, downloadPolicyOptions, pageSizeOptions, searchSortOptions } from '../features/config/configOptions.js'
const AI_PROVIDER_KEYS = ['openai_compatible', 'gemini', 'ollama']
export default {
  name: 'Config',
  components: { AdvancedSettingsPanel, AppleErrorState, AppleSkeleton, GlassSelect, Open115SettingsPanel },
  data() {
    return {
      config: JSON.parse(JSON.stringify(DEFAULT_CONFIG)),
      telegramUsers: '',
      configLoading: true,
      configLoaded: false,
      configLoadError: '',
      configMeta: {
        config_path: '',
        config_loaded: false,
        config_load_error: '',
      },
      saving: false,
      testingTelegram: false,
      telegramTestMsg: '',
      showBotToken: false,
      navGroups: [
        { id: 'services', label: '常规与服务' },
        { id: 'automation', label: '自动化策略' },
        { id: 'telegram', label: 'Telegram 通知' },
        { id: 'appearance', label: '界面与外观' },
        { id: 'advanced', label: '高级设置' }
      ],
      activeGroup: 'services',
      searchPrefs: { ...DEFAULT_SEARCH_PREFERENCES },
      pageSizeOptions,
      displayLangOptions,
      searchSortOptions,
      downloadPolicyOptions,
      candidateSourceOptions,
    }
  },
  computed: {
    displayLangVal() { return displayLang.value },
    canSaveConfig() {
      return this.configLoaded && !this.configLoading && !this.configLoadError && this.configMeta.config_loaded
    },
    configLoadErrorTitle() {
      return this.configMeta.config_loaded === false ? '配置文件未挂载或不可读取' : '配置加载失败'
    },
    configLoadErrorDescription() {
      if (this.configMeta.config_loaded === false) {
        return '后端正在使用默认值兜底，保存已暂停以避免覆盖现有设置。请检查部署里的 config.yaml 挂载路径。'
      }
      return '无法确认当前配置，保存已暂停以避免覆盖现有设置。'
    },
    configStatusTitle() {
      return this.configMeta.config_loaded ? '配置已读取' : '配置文件未挂载或不可读取'
    },
    configStatusDescription() {
      if (this.javinfoRuntimeWarning) {
        return '配置已读取，但 JavInfoApi URL 可能不适用于 Docker/远端部署。'
      }
      if (this.configMeta.config_loaded) {
        return ''
      }
      return '后端只返回了默认配置，界面已禁止保存，避免把默认值写回覆盖真实配置。'
    },
    saveFooterTitle() {
      return this.saving ? '正在保存更改' : '有可保存的设置'
    },
    saveFooterNote() {
      if (this.saving) {
        return '正在写入后端配置，并同步本地外观偏好。'
      }
      return '保存会更新当前配置文件，同时保留本页的外观与检索偏好。'
    },
    telegramTestBusy() {
      return this.testingTelegram
    },
    telegramTestStatus() {
      if (this.testingTelegram) {
        return '正在发送 Telegram 测试信息。'
      }
      if (this.telegramTestMsg) {
        return this.telegramTestMsg
      }
      if (!this.canSaveConfig) {
        return '配置未加载成功，测试已暂停。'
      }
      if (!this.config.telegram.bot_token) {
        return '填写 Bot Token 后可发送测试信息。'
      }
      return '可发送一次测试信息。'
    },
    configStatusSourceLabel() {
      return this.configMeta.config_path ? `路径 ${this.configMeta.config_path}` : ''
    },
    configStatusDetails() {
      return this.configMeta.config_load_error || ''
    },
    javinfoApiUrl() {
      return String(this.config?.javinfo?.api_url || '').trim()
    },
    dockerJavInfoApiUrl() {
      return 'http://javinfoapi:18080'
    },
    javinfoRuntimeWarning() {
      if (!this.configMeta.config_loaded || !this.javinfoApiUrl) return ''
      try {
        const parsed = new URL(this.javinfoApiUrl)
        const host = parsed.hostname.toLowerCase()
        const port = parsed.port || (parsed.protocol === 'https:' ? '443' : '80')
        if ((host === 'localhost' || host === '127.0.0.1') && port === '18080') {
          return `当前地址是 ${this.javinfoApiUrl}。Docker/远端部署中 localhost:18080 指向 JavHub 容器自身，不是 JavInfoApi 容器；请改成 ${this.dockerJavInfoApiUrl} 后保存。`
        }
      } catch (e) {
        return ''
      }
      return ''
    },
    searchSortLabel() {
      return this.searchSortOptions.find(option => option.value === this.searchPrefs.defaultSort)?.label || '随机'
    },
    displayLangLabel() {
      return this.displayLangOptions.find(option => option.value === this.displayLangVal)?.label || '日文'
    },
    currentPolicyHint() {
      return this.downloadPolicyOptions.find(option => option.value === this.config.automation.download_policy)?.hint || ''
    },
  },
  created() {
    this.syncActiveGroupFromRoute()
  },
  watch: {
    '$route.query.tab': 'syncActiveGroupFromRoute',
  },
  async mounted() {
    await this.loadConfig()
    this.loadSearchPrefs()
  },
  methods: {
    syncActiveGroupFromRoute() {
      const tab = String(this.$route?.query?.tab || '').trim()
      const routeGroupMap = {
        'javinfo-import': 'advanced',
      }
      const group = routeGroupMap[tab] || tab
      if (this.navGroups.some(item => item.id === group)) {
        this.activeGroup = group
      }
    },
    async loadConfig() {
      this.configLoading = true
      this.configLoadError = ''
      try {
        const resp = await api.getConfig()
        const data = { ...(resp.data || {}) }
        const meta = data._meta || {}
        delete data._meta
        this.configMeta = {
          config_path: meta.config_path || '',
          config_loaded: meta.config_loaded !== false,
          config_load_error: meta.config_load_error || '',
        }
        if (!this.configMeta.config_loaded) {
          this.configLoaded = false
          this.configLoadError = 'missing_config_file'
          return
        }
        this.config = {
          ...JSON.parse(JSON.stringify(DEFAULT_CONFIG)),
          ...data
        }
        for (const key in DEFAULT_CONFIG) {
          if (typeof DEFAULT_CONFIG[key] === 'object' && !Array.isArray(DEFAULT_CONFIG[key])) {
            this.config[key] = {
              ...JSON.parse(JSON.stringify(DEFAULT_CONFIG[key])),
              ...(data[key] || {})
            }
          }
        }
        this.mergeJavInfoConfig(data.javinfo || {})
        this.mergeAiConfig(data.ai || {})
        this.telegramUsers = (this.config.telegram.allowed_user_ids || []).join(', ')
        this.configLoaded = true
      } catch (e) {
        console.error('Failed to load config:', e)
        this.configLoaded = false
        this.configLoadError = 'load_failed'
        this.$message?.error?.('配置加载失败，请重试')
      } finally {
        this.configLoading = false
      }
    },
    async save() {
      if (!this.canSaveConfig) {
        this.$message.error('配置未加载成功，已阻止保存')
        return
      }
      this.saving = true
      try {
        this.config.telegram.allowed_user_ids = this.telegramUsers.split(',').map(s => s.trim()).filter(Boolean)
        // 磁力索引源（sources.torznab）已迁到下载中心管理，此处不写回，避免覆盖
        const { downloaders, server, rate_limit, sources, ...configPayload } = this.config
        await api.updateConfig(configPayload)
        this.saveSearchPrefs()
        this.$message.success('配置已保存')
      } catch (e) {
        console.error('Failed to save config:', e)
        this.$message.error('保存失败')
      } finally {
        this.saving = false
      }
    },
    mergeAiConfig(remote = {}) {
      const base = JSON.parse(JSON.stringify(DEFAULT_CONFIG.ai))
      this.config.ai = { ...base, ...(remote || {}) }
      if (!AI_PROVIDER_KEYS.includes(this.config.ai.provider)) {
        this.config.ai.provider = 'openai_compatible'
      }
      for (const key of AI_PROVIDER_KEYS) {
        this.config.ai[key] = { ...(base[key] || {}), ...((remote && remote[key]) || {}) }
      }
    },
    mergeJavInfoConfig(remote = {}) {
      const base = JSON.parse(JSON.stringify(DEFAULT_CONFIG.javinfo))
      this.config.javinfo = {
        ...base,
        ...(remote || {}),
        import_db: {
          ...(base.import_db || {}),
          ...((remote && remote.import_db) || {}),
        },
      }
    },
    applyDockerJavInfoUrl() {
      this.config.javinfo.api_url = this.dockerJavInfoApiUrl
    },
    toggleAutomationSource(source) {
      const current = this.config.automation.candidate_sources || []
      if (current.includes(source)) {
        this.config.automation.candidate_sources = current.filter(item => item !== source)
      } else {
        this.config.automation.candidate_sources = [...current, source]
      }
    },
    async testTelegram() {
      if (!this.canSaveConfig) {
        this.telegramTestMsg = '配置未加载成功，请先重新加载'
        return
      }
      if (!this.config.telegram.bot_token) {
        this.telegramTestMsg = '请先填写 Bot Token'
        return
      }
      this.testingTelegram = true
      this.telegramTestMsg = ''
      try {
        await api.testTelegramBot(this.config.telegram.bot_token)
        this.telegramTestMsg = '发送成功'
        this.$message.success('测试信息已发送')
      } catch (e) {
        this.telegramTestMsg = '发送失败'
        this.$message.error('发送失败，请检查 Token 和用户 ID')
      } finally {
        this.testingTelegram = false
      }
    },
    loadSearchPrefs() {
      this.searchPrefs = loadSearchPreferences()
    },
    saveSearchPrefs() {
      this.searchPrefs = saveSearchPreferences(this.searchPrefs)
    },
    setDisplayLang(lang) {
      displayLang.value = lang
    },
  }
}
</script>
<style scoped src="../features/config/config.css"></style>
<style scoped src="../features/config/configAppearance.css"></style>
