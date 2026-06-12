<template>
  <div class="settings page-shell page-shell--standard">
    <div class="settings-header">
      <div class="settings-header-meta">
        <h1>配置中心</h1>
        <p class="settings-subtitle">统一管理服务连接、自动化策略、通知、外观和高级维护。</p>
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
          <div class="config-status-banner apple-surface" :class="{ warning: !configMeta.config_loaded }">
            <div>
              <strong>{{ configStatusTitle }}</strong>
              <p>{{ configStatusDescription }}</p>
            </div>
            <code v-if="configMeta.config_path">{{ configMeta.config_path }}</code>
          </div>
          <!-- Services Section -->
          <div v-if="activeGroup === 'services'" class="config-section">
            <div class="section-header">
              <h2>常规与服务</h2>
              <p>配置基础连接与外部服务集成，包括媒体服务器和元数据来源。</p>
            </div>
            <section class="settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                  <line x1="8" y1="21" x2="16" y2="21"/>
                  <line x1="12" y1="17" x2="12" y2="21"/>
                </svg>
                <h2>Emby</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">API 地址</span>
                    <span class="setting-note">媒体服务器 HTTP 入口。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="config.emby.api_url" placeholder="http://your-emby:8096" />
                  </span>
                </label>
                <div class="settings-row">
                  <div class="setting-copy">
                    <span class="setting-title">密钥</span>
                    <span class="setting-note">用于读取媒体库和下载状态。</span>
                  </div>
                  <div class="settings-control">
                    <div class="input-password-wrap">
                      <input class="input" :type="showEmbyKey ? 'text' : 'password'" v-model="config.emby.api_key" autocomplete="off" />
                      <button class="input-eye-btn" type="button" @click="showEmbyKey = !showEmbyKey">
                        <svg v-if="!showEmbyKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </section>
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
            <div class="section-header">
              <h2>Telegram 通知</h2>
              <p>配置 Telegram Bot、接收用户和通知事件。</p>
            </div>
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
            <div class="section-header">
              <h2>自动化策略</h2>
              <p>控制候选生成后的处理强度，默认保持人工批准。</p>
            </div>
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
            <!-- 磁力索引源 -->
            <section class="settings-group torznab-settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <path d="M10 13a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07L10.9 5.03"/>
                  <path d="M14 11a5 5 0 0 0-7.07 0L4.81 13.12a5 5 0 0 0 7.07 7.07l1.22-1.22"/>
                </svg>
                <h2>磁力索引源 / Torznab</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row settings-row--toggle" for="torznabEnabled">
                  <span class="setting-copy">
                    <span class="setting-title">启用磁力索引源</span>
                    <span class="setting-note">连接 Prowlarr、Jackett 或 Torznab 服务。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                    <input type="checkbox" id="torznabEnabled" v-model="config.sources.torznab.enabled" role="switch" />
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Base URL</span>
                    <span class="setting-note">Torznab 服务地址。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="config.sources.torznab.base_url" placeholder="http://localhost:9696" />
                  </span>
                </label>
                <div class="settings-row">
                  <div class="setting-copy">
                    <span class="setting-title">API Key</span>
                    <span class="setting-note">用于访问索引源。</span>
                  </div>
                  <div class="settings-control">
                    <div class="input-password-wrap">
                      <input
                        class="input"
                        :type="showTorznabKey ? 'text' : 'password'"
                        v-model="config.sources.torznab.api_key"
                        autocomplete="off"
                      />
                      <button class="input-eye-btn" type="button" @click="showTorznabKey = !showTorznabKey" :title="showTorznabKey ? '隐藏' : '显示'">
                        <svg v-if="!showTorznabKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C5 20 1 12 1 12a21.8 21.8 0 0 1 5.06-5.94"/><path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a21.8 21.8 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 0 1-4.24-4.24"/><path d="M1 1l22 22"/></svg>
                      </button>
                    </div>
                  </div>
                </div>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Indexer</span>
                    <span class="setting-note">默认 all。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="config.sources.torznab.indexer" placeholder="all" />
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Categories</span>
                    <span class="setting-note">可留空，使用服务默认分类。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="config.sources.torznab.categories" placeholder="可留空" />
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Limit</span>
                    <span class="setting-note">单次查询返回上限。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.sources.torznab.limit" type="number" min="1" max="100" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">条</span>
                      <span class="settings-number-range">1-100</span>
                    </span>
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Timeout</span>
                    <span class="setting-note">请求等待秒数。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.sources.torznab.timeout" type="number" min="1" max="60" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">秒</span>
                      <span class="settings-number-range">1-60</span>
                    </span>
                  </span>
                </label>
              </div>
            </section>
            <!-- 爬虫 -->
            <section class="settings-group crawler-settings-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <h2>爬虫设置</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">请求间隔</span>
                    <span class="setting-note">秒，控制爬虫访问节奏。</span>
                  </span>
                  <span class="settings-control settings-control--compact settings-control--number">
                    <span class="settings-number-control">
                      <input class="input" v-model.number="config.crawler.request_interval" type="number" min="1" step="1" inputmode="numeric" />
                      <span class="settings-number-unit">秒</span>
                      <span class="settings-number-range">>=1</span>
                    </span>
                  </span>
                </label>
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">订阅检查时间</span>
                    <span class="setting-note">小时，0-23。</span>
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
            <!-- 库存对比定时任务 -->
            <section class="settings-group inventory-schedule-group">
              <div class="settings-group-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <h2>库存对比定时任务</h2>
              </div>
              <div class="settings-list">
                <label class="settings-row">
                  <span class="setting-copy">
                    <span class="setting-title">Cron 表达式</span>
                    <span class="setting-note">例：0 2 * * * 表示每天凌晨2点。</span>
                  </span>
                  <span class="settings-control">
                    <input class="input" v-model="inventoryCron" placeholder="0 2 * * *" />
                  </span>
                </label>
                <div class="settings-row settings-row--actions">
                  <div class="setting-copy">
                    <span class="setting-title">保存自动化配置</span>
                    <span class="setting-note">只提交当前自动化相关配置。</span>
                  </div>
                  <div class="settings-control settings-control--wide inventory-cron-save-row" :aria-busy="inventoryCronSaveBusy" aria-live="polite">
                    <div class="inventory-cron-actions">
                      <button
                        class="btn btn-primary"
                        type="button"
                        @click="saveInventoryCron"
                        :disabled="inventoryCronSaving || !canSaveConfig"
                        :aria-describedby="'inventory-cron-save-status'"
                      >
                        {{ inventoryCronSaving ? '保存中...' : '保存自动化配置' }}
                      </button>
                    </div>
                    <span id="inventory-cron-save-status" class="inventory-cron-status" role="status">{{ inventoryCronSaveStatus }}</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
          <!-- Appearance Section -->
          <div v-if="activeGroup === 'appearance'" class="config-section appearance-section">
            <div class="section-header">
              <h2>界面与外观</h2>
              <p>按作用范围整理全局显示、影片检索和随机探索偏好。</p>
            </div>
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
              <section class="settings-group appearance-discovery-group">
                <div class="settings-group-header">
                  <h2>随机探索</h2>
                  <button class="btn btn-ghost btn-sm" type="button" @click="resetBubbleCfg">恢复默认</button>
                </div>
                <div class="settings-list">
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">默认页签</span>
                      <span class="setting-note">默认打开 {{ defaultTabLabel }}</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="随机探索默认页签">
                        <button
                          v-for="option in defaultTabOptions"
                          :key="option.value"
                          type="button"
                          :class="{ active: bubbleCfg.defaultTab === option.value }"
                          :aria-pressed="bubbleCfg.defaultTab === option.value"
                          @click="bubbleCfg.defaultTab = option.value"
                        >{{ option.label }}</button>
                      </div>
                    </div>
                  </div>
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">演员头像</span>
                      <span class="setting-note">{{ avatarSizeHint }}</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="演员头像尺寸">
                        <button
                          v-for="option in avatarSizeOptions"
                          :key="option.value"
                          type="button"
                          :class="{ active: bubbleCfg.actressAvatarSize === option.value }"
                          :aria-pressed="bubbleCfg.actressAvatarSize === option.value"
                          @click="bubbleCfg.actressAvatarSize = option.value"
                        >{{ option.label }}</button>
                      </div>
                    </div>
                  </div>
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">演员每批数量</span>
                      <span class="setting-note">{{ bubbleCfg.actressPageSize }} 位 / 批</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="演员每批数量">
                        <button
                          v-for="size in actressPageSizeOptions"
                          :key="size"
                          type="button"
                          :class="{ active: bubbleCfg.actressPageSize === size }"
                          :aria-pressed="bubbleCfg.actressPageSize === size"
                          @click="bubbleCfg.actressPageSize = size"
                        >{{ size }}</button>
                      </div>
                    </div>
                  </div>
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">系列每批数量</span>
                      <span class="setting-note">{{ bubbleCfg.seriesPageSize }} 个 / 批</span>
                    </div>
                    <div class="settings-control">
                      <div class="segmented-mini" aria-label="系列每批数量">
                        <button
                          v-for="size in seriesPageSizeOptions"
                          :key="size"
                          type="button"
                          :class="{ active: bubbleCfg.seriesPageSize === size }"
                          :aria-pressed="bubbleCfg.seriesPageSize === size"
                          @click="bubbleCfg.seriesPageSize = size"
                        >{{ size }}</button>
                      </div>
                    </div>
                  </div>
                </div>
              </section>
              <section class="settings-group appearance-visual-group">
                <div class="settings-group-header">
                  <h2>题材 / 系列气泡</h2>
                </div>
                <div class="settings-list">
                  <div class="settings-row settings-row--stacked appearance-visual-row">
                    <div class="setting-copy">
                      <span class="setting-title">预览</span>
                      <span class="setting-note">当前数量、尺寸和间距。</span>
                    </div>
                    <div class="settings-control settings-control--wide">
                      <div class="aura-preview" :style="auraPreviewStyle">
                        <span
                          v-for="(tag, index) in previewTags"
                          :key="tag"
                          class="preview-bubble"
                          :style="previewBubbleStyle(index)"
                        >
                        {{ tag }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="settings-row settings-row--stacked appearance-visual-row">
                    <div class="setting-copy">
                      <span class="setting-title">气泡参数</span>
                      <span class="setting-note">调整随机探索中标签的显示密度。</span>
                    </div>
                    <div class="settings-control settings-control--wide">
                      <div class="tag-tuning-grid">
                        <div
                          v-for="control in tagTuningControls"
                          :key="control.key"
                          class="tuning-control"
                        >
                          <div class="tuning-copy">
                            <span>{{ control.label }}</span>
                            <strong>{{ bubbleCfg[control.key] }}{{ control.unit }}</strong>
                          </div>
                          <input
                            type="range"
                            :min="control.min"
                            :max="control.max"
                            :step="control.step"
                            v-model.number="bubbleCfg[control.key]"
                            class="threshold-slider"
                          />
                        </div>
                      </div>
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
import { DEFAULT_BUBBLE_CFG, DEFAULT_CONFIG } from '../features/config/configDefaults.js'
import { actressPageSizeOptions, avatarSizeOptions, candidateSourceOptions, defaultTabOptions, displayLangOptions, downloadPolicyOptions, pageSizeOptions, searchSortOptions, seriesPageSizeOptions, tagTuningControls } from '../features/config/configOptions.js'
const BUBBLE_CFG_KEYS = Object.keys(DEFAULT_BUBBLE_CFG)
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
      inventoryCronSaving: false,
      inventoryCron: '',
      inventoryCronSaveMsg: '',
      telegramTestMsg: '',
      showBotToken: false,
      showEmbyKey: false,
      showTorznabKey: false,
      navGroups: [
        { id: 'services', label: '常规与服务' },
        { id: 'automation', label: '自动化策略' },
        { id: 'telegram', label: 'Telegram 通知' },
        { id: 'appearance', label: '界面与外观' },
        { id: 'advanced', label: '高级设置' }
      ],
      activeGroup: 'services',
      bubbleCfg: JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG)),
      searchPrefs: { ...DEFAULT_SEARCH_PREFERENCES },
      pageSizeOptions,
      avatarSizeOptions,
      actressPageSizeOptions,
      seriesPageSizeOptions,
      defaultTabOptions,
      displayLangOptions,
      searchSortOptions,
      downloadPolicyOptions,
      candidateSourceOptions,
      tagTuningControls,
      previewTags: ['剧情', '高清', '限定', '新作', '字幕'],
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
        return '当前表单来自后端读取到的运行配置。'
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
    inventoryCronSaveBusy() {
      return this.inventoryCronSaving
    },
    inventoryCronSaveStatus() {
      if (this.inventoryCronSaving) {
        return '正在保存库存对比 Cron 表达式。'
      }
      if (this.inventoryCronSaveMsg) {
        return this.inventoryCronSaveMsg
      }
      if (!this.canSaveConfig) {
        return '配置未加载成功，自动化保存已暂停。'
      }
      return '只保存库存对比定时任务。'
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
    avatarSizeHint() {
      return this.avatarSizeOptions.find(option => option.value === this.bubbleCfg.actressAvatarSize)?.hint || ''
    },
    defaultTabLabel() {
      return this.defaultTabOptions.find(option => option.value === this.bubbleCfg.defaultTab)?.label || '题材'
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
    auraPreviewStyle() {
      return {
        '--preview-gap': `${Math.max(4, Math.min(this.bubbleCfg.spacing || 12, 28)) * 0.45}px`,
        '--preview-font': `${Math.max(11, Math.min(this.bubbleCfg.baseSize || 16, 24))}px`,
      }
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
    this.loadBubbleCfg()
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
        this.mergeSourceConfig(data.sources || {})
        this.telegramUsers = (this.config.telegram.allowed_user_ids || []).join(', ')
        this.inventoryCron = data.inventory_cron || ''
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
        const { downloaders, server, rate_limit, ...configPayload } = this.config
        await api.updateConfig(configPayload)
        this.saveBubbleCfg()
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
    mergeSourceConfig(remote = {}) {
      const base = JSON.parse(JSON.stringify(DEFAULT_CONFIG.sources))
      this.config.sources = {
        ...base,
        ...(remote || {}),
        torznab: {
          ...(base.torznab || {}),
          ...((remote && remote.torznab) || {}),
        },
      }
    },
    applyDockerJavInfoUrl() {
      this.config.javinfo.api_url = this.dockerJavInfoApiUrl
    },
    async saveInventoryCron() {
      if (!this.canSaveConfig) {
        this.inventoryCronSaveMsg = '配置未加载成功，已阻止保存'
        this.$message.error('配置未加载成功，已阻止保存')
        return
      }
      this.inventoryCronSaving = true
      this.inventoryCronSaveMsg = ''
      try {
        await api.updateConfig({ inventory_cron: this.inventoryCron })
        this.inventoryCronSaveMsg = '保存成功'
        this.$message.success('库存对比定时任务配置已保存')
      } catch (e) {
        console.error('Failed to save inventory cron:', e)
        this.inventoryCronSaveMsg = '保存失败'
        this.$message.error('保存失败')
      } finally {
        this.inventoryCronSaving = false
      }
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
    loadBubbleCfg() {
      try {
        const saved = localStorage.getItem('genres_bubble_cfg')
        if (saved) {
          const parsed = JSON.parse(saved)
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            this.bubbleCfg = BUBBLE_CFG_KEYS.reduce((cfg, key) => {
              if (Object.prototype.hasOwnProperty.call(parsed, key)) cfg[key] = parsed[key]
              return cfg
            }, JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG)))
            if (!parsed.actressPageSize && parsed.actressAvatarSize) {
              const fallbackPageSize = { small: 48, medium: 36, large: 20 }
              this.bubbleCfg.actressPageSize = fallbackPageSize[parsed.actressAvatarSize] || DEFAULT_BUBBLE_CFG.actressPageSize
            }
          }
        }
      } catch (e) {
        console.error("Failed to parse bubble cfg", e);
      }
    },
    saveBubbleCfg() {
      localStorage.setItem('genres_bubble_cfg', JSON.stringify(this.bubbleCfg))
    },
    loadSearchPrefs() {
      this.searchPrefs = loadSearchPreferences()
    },
    saveSearchPrefs() {
      this.searchPrefs = saveSearchPreferences(this.searchPrefs)
    },
    resetBubbleCfg() {
      this.bubbleCfg = JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG))
      localStorage.removeItem('genres_bubble_cfg')
      this.$message.info('已恢复默认')
    },
    setDisplayLang(lang) {
      displayLang.value = lang
    },
    previewBubbleStyle() {
      const fill = Math.max(0.7, Math.min((this.bubbleCfg.fillPercent || 50) / 100, 1.8))
      const basePaddingY = Math.round(7 * fill)
      const basePaddingX = Math.round(12 * fill)
      return {
        padding: `${basePaddingY}px ${basePaddingX}px`,
      }
    },
  }
}
</script>
<style scoped src="../features/config/config.css"></style>
<style scoped src="../features/config/configAppearance.css"></style>
