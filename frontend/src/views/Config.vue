<template>
  <div class="settings page-shell page-shell--standard">
    <!-- Header Aligned with Main App Rhythm -->
    <div class="settings-header">
      <h1>配置中心</h1>
      <p class="settings-subtitle">统一管理服务连接、自动化策略、通知、外观和高级维护。</p>
      <div class="settings-tabs">
        <button
          type="button"
          v-for="group in navGroups" 
          :key="group.id"
          class="tab-item"
          :class="{ active: activeGroup === group.id }"
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
    </div>

    <!-- Main Content: Frameless & Wide -->
    <main class="settings-content-wide">
      <div v-if="configLoading" class="settings-loading apple-surface">
        <div class="spinner-large"></div>
        <p>正在加载配置...</p>
      </div>

      <AppleErrorState
        v-else-if="configLoadError"
        :title="configLoadErrorTitle"
        :description="configLoadErrorDescription"
        :source-label="configStatusSourceLabel"
        :details="configStatusDetails"
        retry-label="重新加载"
        @retry="loadConfig"
      />

      <transition v-else name="fade-slide" mode="out-in">
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

            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                    <line x1="8" y1="21" x2="16" y2="21"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                  <h2>Emby</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>API 地址</label>
                    <input class="input" v-model="config.emby.api_url" placeholder="http://your-emby:8096" />
                  </div>
                  <div class="form-group">
                    <label>密钥</label>
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
            </div>

            <!-- JavInfoApi -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <ellipse cx="12" cy="5" rx="9" ry="3"/>
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                  </svg>
                  <h2>数据源 / JavInfoApi</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>API 地址</label>
                    <input class="input" v-model="config.javinfo.api_url" placeholder="http://javinfoapi:18080" />
                  </div>
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
                  <div v-if="javinfoRuntimeWarning" class="javinfo-runtime-warning">
                    <strong>JavInfoApi 地址可能不适用于 Docker</strong>
                    <p>{{ javinfoRuntimeWarning }}</p>
                    <button class="btn btn-secondary" type="button" @click="applyDockerJavInfoUrl">
                      修正为 Docker 服务地址
                    </button>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- Telegram Section -->
          <div v-if="activeGroup === 'telegram'" class="config-section">
            <div class="section-header">
              <h2>Telegram 通知</h2>
              <p>配置 Telegram Bot、接收用户和通知事件。</p>
            </div>

            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                  </svg>
                  <h2>Bot 连接</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>Bot Token</label>
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
                  <div class="form-group">
                    <label>允许的用户编号（逗号分隔）</label>
                    <input class="input" v-model="telegramUsers" placeholder="123456789,987654321" />
                  </div>
                  <div class="form-group telegram-test-row">
                    <button class="btn btn-secondary" type="button" @click="testTelegram" :disabled="testingTelegram || !canSaveConfig || !config.telegram.bot_token">
                      {{ testingTelegram ? '发送中...' : '发送测试信息' }}
                    </button>
                    <span v-if="telegramTestMsg" class="telegram-test-msg">{{ telegramTestMsg }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 01-3.46 0"/>
                  </svg>
                  <h2>通知事件</h2>
                </div>
                <div class="form-slot notification-grid">
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
              </div>
            </div>
          </div>

          <!-- Automation Section -->
          <div v-if="activeGroup === 'automation'" class="config-section">
            <div class="section-header">
              <h2>自动化策略</h2>
              <p>控制候选生成后的处理强度，默认保持人工批准。</p>
            </div>

            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M3 3v18h18"/>
                    <path d="M7 15l3-3 3 2 5-7"/>
                  </svg>
                  <h2>下载候选处理</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>处理策略</label>
                    <div class="segmented-mini wide automation-policy-control">
                      <button
                        v-for="option in downloadPolicyOptions"
                        :key="option.value"
                        type="button"
                        :class="{ active: config.automation.download_policy === option.value }"
                        @click="config.automation.download_policy = option.value"
                      >{{ option.label }}</button>
                    </div>
                    <small>{{ currentPolicyHint }}</small>
                  </div>
                  <div class="form-group">
                    <label>允许自动处理的来源</label>
                    <div class="source-check-grid">
                      <label v-for="source in candidateSourceOptions" :key="source.value" class="source-check-item">
                        <input
                          type="checkbox"
                          :checked="config.automation.candidate_sources.includes(source.value)"
                          @change="toggleAutomationSource(source.value)"
                        />
                        <span>{{ source.label }}</span>
                      </label>
                    </div>
                  </div>
                  <div class="form-group checkbox">
                    <input type="checkbox" id="rulesRequireMagnet" v-model="config.automation.rules_require_magnet" />
                    <label for="rulesRequireMagnet">规则模式只处理已有 magnet 的候选</label>
                  </div>
                  <div class="form-group">
                    <label>自动处理间隔（分钟，0 表示关闭后台自动处理）</label>
                    <input class="input" v-model.number="config.automation.auto_process_interval_minutes" type="number" min="0" max="1440" />
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>单次自动下发上限（0 表示不限）</label>
                      <input class="input" v-model.number="config.automation.max_auto_downloads_per_run" type="number" min="0" max="500" />
                    </div>
                    <div class="form-group">
                      <label>24 小时自动下发上限（0 表示不限）</label>
                      <input class="input" v-model.number="config.automation.max_auto_downloads_per_24h" type="number" min="0" max="5000" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 磁力索引源 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M10 13a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07L10.9 5.03"/>
                    <path d="M14 11a5 5 0 0 0-7.07 0L4.81 13.12a5 5 0 0 0 7.07 7.07l1.22-1.22"/>
                  </svg>
                  <h2>磁力索引源 / Torznab</h2>
                </div>
                <div class="form-slot">
                  <small>连接你自己的 Prowlarr、Jackett 或 Torznab 服务。</small>
                  <div class="form-group checkbox">
                    <input type="checkbox" id="torznabEnabled" v-model="config.sources.torznab.enabled" />
                    <label for="torznabEnabled">启用磁力索引源</label>
                  </div>
                  <div class="form-group">
                    <label>Base URL</label>
                    <input class="input" v-model="config.sources.torznab.base_url" placeholder="http://localhost:9696" />
                  </div>
                  <div class="form-group">
                    <label>API Key</label>
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
                  <div class="form-row">
                    <div class="form-group">
                      <label>Indexer</label>
                      <input class="input" v-model="config.sources.torznab.indexer" placeholder="all" />
                    </div>
                    <div class="form-group">
                      <label>Categories</label>
                      <input class="input" v-model="config.sources.torznab.categories" placeholder="可留空" />
                    </div>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>Limit</label>
                      <input class="input" v-model.number="config.sources.torznab.limit" type="number" min="1" max="100" />
                    </div>
                    <div class="form-group">
                      <label>Timeout（秒）</label>
                      <input class="input" v-model.number="config.sources.torznab.timeout" type="number" min="1" max="60" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 爬虫 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  <h2>爬虫设置</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>请求间隔（秒）</label>
                    <input class="input" v-model="config.crawler.request_interval" type="number" min="1" />
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>订阅检查时间（小时，0-23）</label>
                      <input class="input" v-model="config.scheduler.subscription_check_hour" type="number" min="0" max="23" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 库存对比定时任务 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  <h2>库存对比定时任务</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>Cron 表达式</label>
                    <input class="input" v-model="inventoryCron" placeholder="0 2 * * *" />
                    <small>例：0 2 * * * 表示每天凌晨2点</small>
                  </div>
                  <button class="btn btn-primary" type="button" @click="save" :disabled="saving || !canSaveConfig">保存自动化配置</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Appearance Section -->
          <div v-if="activeGroup === 'appearance'" class="config-section appearance-section">
            <div class="section-header">
              <h2>界面与外观</h2>
              <p>按作用范围整理全局显示、影片检索和随机探索偏好。</p>
            </div>

            <div class="preference-stack">
              <section class="preference-section">
                <div class="preference-section-header">
                  <div>
                    <h3>全局偏好</h3>
                  </div>
                  <span class="appearance-chip">{{ displayLangLabel }}</span>
                </div>

                <div class="appearance-setting-list compact">
                  <div class="appearance-setting-row">
                    <div class="setting-copy">
                      <span class="setting-title">显示语言</span>
                      <span class="setting-note">{{ displayLangLabel }}</span>
                    </div>
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
              </section>

              <section class="preference-section">
                <div class="preference-section-header">
                  <div>
                    <h3>影片检索</h3>
                  </div>
                  <span class="appearance-chip">{{ config.javinfo.page_size }} 条 / 页</span>
                </div>

                <div class="appearance-setting-list">
                  <div class="appearance-setting-row">
                    <div class="setting-copy">
                      <span class="setting-title">检索页数量</span>
                      <span class="setting-note">{{ config.javinfo.page_size }} 条 / 页</span>
                    </div>
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

                  <div class="appearance-setting-row">
                    <div class="setting-copy">
                      <span class="setting-title">默认排序</span>
                      <span class="setting-note">{{ searchSortLabel }}</span>
                    </div>
                    <GlassSelect
                      v-model="searchPrefs.defaultSort"
                      :options="searchSortOptions"
                      class="glass-select-control glass-select-control--wide"
                      placement="right"
                      aria-label="影片检索默认排序"
                    />
                  </div>

                  <div class="appearance-setting-row">
                    <div class="setting-copy">
                      <span class="setting-title">默认版本筛选</span>
                      <span class="setting-note">{{ searchServiceLabel }}</span>
                    </div>
                    <GlassSelect
                      v-model="searchPrefs.defaultServiceCode"
                      :options="searchServiceOptions"
                      class="glass-select-control glass-select-control--wide"
                      placement="right"
                      aria-label="影片检索默认版本筛选"
                    />
                  </div>
                </div>
              </section>

              <section class="preference-section">
                <div class="preference-section-header">
                  <div>
                    <h3>随机探索</h3>
                  </div>
                  <button class="btn btn-ghost btn-sm" type="button" @click="resetBubbleCfg">恢复默认</button>
                </div>

                <div class="discovery-preference-grid">
                  <section class="scope-card">
                    <div class="scope-card-header">
                      <span class="setting-title">探索入口</span>
                      <span class="setting-note">默认打开 {{ defaultTabLabel }}</span>
                    </div>
                    <div class="appearance-setting-row">
                      <div class="setting-copy">
                        <span class="setting-title">默认页签</span>
                        <span class="setting-note">{{ defaultTabLabel }}</span>
                      </div>
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
                  </section>

                  <section class="scope-card">
                    <div class="scope-card-header">
                      <span class="setting-title">演员</span>
                      <span class="setting-note">{{ avatarSizeHint }} · 每批 {{ bubbleCfg.actressPageSize }}</span>
                    </div>
                    <div class="appearance-setting-list">
                      <div class="appearance-setting-row">
                        <div class="setting-copy">
                          <span class="setting-title">演员头像</span>
                          <span class="setting-note">{{ avatarSizeHint }}</span>
                        </div>
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

                      <div class="appearance-setting-row">
                        <div class="setting-copy">
                          <span class="setting-title">演员每批数量</span>
                          <span class="setting-note">{{ bubbleCfg.actressPageSize }} 位 / 批</span>
                        </div>
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
                  </section>

                  <section class="scope-card">
                    <div class="scope-card-header">
                      <span class="setting-title">系列</span>
                      <span class="setting-note">每批 {{ bubbleCfg.seriesPageSize }} 个</span>
                    </div>
                    <div class="appearance-setting-row">
                      <div class="setting-copy">
                        <span class="setting-title">系列每批数量</span>
                        <span class="setting-note">{{ bubbleCfg.seriesPageSize }} 个 / 批</span>
                      </div>
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
                  </section>
                </div>

                <section class="scope-card visual-card">
                  <div class="scope-card-header">
                    <div>
                      <span class="setting-title">题材 / 系列气泡</span>
                      <span class="setting-note">数量、尺寸和间距</span>
                    </div>
                  </div>

                  <div class="aura-preview" :style="auraPreviewStyle">
                    <span
                      v-for="(tag, index) in previewTags"
                      :key="tag"
                      class="preview-bubble"
                      :style="previewBubbleStyle(index)"
                    >
                    {{ tag }}</span>
                  </div>

                  <div class="appearance-setting-list">
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
                </section>
              </section>
            </div>
          </div>

          <!-- Advanced Section -->
          <div v-if="activeGroup === 'advanced'" class="config-section">
            <div class="section-header">
              <h2>高级配置</h2>
              <p>进阶功能设置，包括配置备份、数据库导入、公共智能模型和网络代理。</p>
            </div>

            <!-- 配置备份 -->
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

            <!-- JavInfo PostgreSQL Import -->
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
                      <div class="progress-bar-fill" :style="{ width: `${javinfoImportProgress}%` }"></div>
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

            <!-- 公共智能模型设置 -->
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
                        :type="showAIKey ? 'text' : 'password'"
                        v-model="currentAiConfig.api_key"
                        autocomplete="off"
                        placeholder="空白保存不覆盖现有密钥"
                      />
                      <button class="input-eye-btn" type="button" @click="showAIKey = !showAIKey" :title="showAIKey ? '隐藏' : '显示'">
                        <svg v-if="!showAIKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
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
                      :disabled="loadingAIModels || !canSaveConfig || !currentAiConfig.base_url"
                    >
                      {{ loadingAIModels ? '获取中...' : '获取模型列表' }}
                    </button>
                    <button
                      class="btn btn-secondary"
                      type="button"
                      @click="testAIModel"
                      :disabled="testingAI || !canSaveConfig || !currentAiConfig.base_url || !currentAiConfig.model"
                    >
                      {{ testingAI ? '测试中...' : '测试模型调用' }}
                    </button>
                    <span v-if="aiTestMsg" class="ai-test-msg" :class="{ error: aiTestType === 'error' }">{{ aiTestMsg }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 网络代理设置 -->
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
        </div>
      </transition>
    </main>

    <!-- Global Floating Footer for Actions -->
    <div v-if="canSaveConfig" class="settings-footer">
      <div class="footer-content page-rail page-rail--standard">
        <button class="btn btn-primary" type="button" @click="save" :disabled="saving || !canSaveConfig">
          <span v-if="saving" class="spinner save-spinner"></span>
          <span v-else>保存所有更改</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import { displayLang } from '../utils/displayLang.js'
import { formatBytes, isJavInfoImportActive, javinfoImportProgress, javinfoImportStatusLabel } from '../utils/javinfoImportPresentation.js'
import { DEFAULT_SEARCH_PREFERENCES, loadSearchPreferences, saveSearchPreferences } from '../utils/searchPreferences.js'
import AppleErrorState from '../components/AppleErrorState.vue'
import GlassSelect from '../components/GlassSelect.vue'
import { DEFAULT_BUBBLE_CFG, DEFAULT_CONFIG } from '../features/config/configDefaults.js'

const BUBBLE_CFG_KEYS = Object.keys(DEFAULT_BUBBLE_CFG)

export default {
  name: 'Config',
  components: { AppleErrorState, GlassSelect },
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
      exportingConfig: false,
      testingTelegram: false,
      testingAI: false,
      loadingAIModels: false,
      aiModelOptions: [],
      inventoryCron: '',
      telegramTestMsg: '',
      aiTestMsg: '',
      aiTestType: 'info',
      showBotToken: false,
      showEmbyKey: false,
      showAIKey: false,
      showTorznabKey: false,
      showImportPassword: false,
      javinfoImportFile: null,
      javinfoImportConfirm: false,
      javinfoImportDirectConfirm: false,
      javinfoImportPreflight: null,
      javinfoImportPreflightSignature: '',
      javinfoImportPreflighting: false,
      javinfoImportUploading: false,
      javinfoImportUploadProgress: 0,
      javinfoImportJob: null,
      javinfoImportJobs: [],
      javinfoImportPollTimer: null,
      javinfoMigrating: false,
      javinfoMigrationStatus: '',
      javinfoMigrationStatusType: 'info',
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
      pageSizeOptions: [15, 30, 50, 100],
      avatarSizeOptions: [
        { value: 'small', label: '小', hint: '头像 60px' },
        { value: 'medium', label: '中', hint: '头像 80px' },
        { value: 'large', label: '大', hint: '头像 100px' },
      ],
      actressPageSizeOptions: [24, 36, 48, 60],
      seriesPageSizeOptions: [12, 24, 36, 48],
      defaultTabOptions: [
        { value: 'genre', label: '题材' },
        { value: 'actress', label: '演员' },
        { value: 'series', label: '系列' },
      ],
      displayLangOptions: [
        { value: 'ja', label: '日文' },
        { value: 'zh', label: '中文' },
        { value: 'en', label: '英文' },
      ],
      searchSortOptions: [
        { value: 'random', label: '随机' },
        { value: 'none', label: '无排序' },
        { value: 'release_date_desc', label: '发行日新到旧' },
        { value: 'release_date_asc', label: '发行日旧到新' },
        { value: 'title_ja_asc', label: '标题 A-Z' },
        { value: 'title_ja_desc', label: '标题 Z-A' },
        { value: 'runtime_mins_desc', label: '时长长到短' },
        { value: 'runtime_mins_asc', label: '时长短到长' },
      ],
      searchServiceOptions: [
        { value: '', label: '全部版本' },
        { value: 'digital', label: '数字版' },
        { value: 'mono', label: '单体版' },
        { value: 'rental', label: '租赁版' },
        { value: 'ebook', label: '写真' },
      ],
      aiProviderOptions: [
        { value: 'openai_compatible', label: 'OpenAI 兼容', hint: '适合 OpenAI、One API、LiteLLM、OpenRouter 等兼容接口。', placeholder: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
        { value: 'gemini', label: 'Gemini', hint: '使用 Google Gemini 原生 generateContent 接口。', placeholder: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-2.0-flash' },
        { value: 'ollama', label: 'Ollama', hint: '连接本机或局域网 Ollama 服务。', placeholder: 'http://localhost:11434', model: 'qwen2.5:7b' },
      ],
      downloadPolicyOptions: [
        { value: 'manual', label: '人工批准', hint: '只生成候选，下载必须手动批准。' },
        { value: 'rules', label: '规则自动', hint: '自动处理允许来源中符合规则的候选。' },
        { value: 'auto', label: '全自动', hint: '自动补磁力并下发允许来源中的候选。' },
      ],
      candidateSourceOptions: [
        { value: 'subscription', label: '订阅发现' },
        { value: 'inventory', label: '库存发现' },
        { value: 'supplement', label: '补全发现' },
        { value: 'manual', label: '手动加入' },
      ],
      tagTuningControls: [
        { key: 'bubbleCount', label: '显示数量', min: 12, max: 120, step: 6, unit: '' },
        { key: 'baseSize', label: '基础尺寸', min: 8, max: 48, step: 1, unit: 'px' },
        { key: 'fillPercent', label: '填充间距', min: 30, max: 200, step: 5, unit: '%' },
        { key: 'spacing', label: '标签间距', min: 0, max: 48, step: 2, unit: 'px' },
      ],
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
    avatarSizeHint() {
      return this.avatarSizeOptions.find(option => option.value === this.bubbleCfg.actressAvatarSize)?.hint || ''
    },
    defaultTabLabel() {
      return this.defaultTabOptions.find(option => option.value === this.bubbleCfg.defaultTab)?.label || '题材'
    },
    searchSortLabel() {
      return this.searchSortOptions.find(option => option.value === this.searchPrefs.defaultSort)?.label || '随机'
    },
    searchServiceLabel() {
      return this.searchServiceOptions.find(option => option.value === this.searchPrefs.defaultServiceCode)?.label || '全部版本'
    },
    displayLangLabel() {
      return this.displayLangOptions.find(option => option.value === this.displayLangVal)?.label || '日文'
    },
    currentPolicyHint() {
      return this.downloadPolicyOptions.find(option => option.value === this.config.automation.download_policy)?.hint || ''
    },
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
    await this.listJavInfoImportJobs()
  },
  unmounted() {
    this.stopJavInfoImportPolling()
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
        const { downloaders, openlist, server, rate_limit, ...configPayload } = this.config
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
    mergeAiConfig(remote = {}) {
      const base = JSON.parse(JSON.stringify(DEFAULT_CONFIG.ai))
      this.config.ai = { ...base, ...(remote || {}) }
      if (!this.aiProviderOptions.some(option => option.value === this.config.ai.provider)) {
        this.config.ai.provider = 'openai_compatible'
      }
      for (const key of ['openai_compatible', 'gemini', 'ollama']) {
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
        this.$message.error('配置未加载成功，已阻止保存')
        return
      }
      try {
        await api.updateConfig({ inventory_cron: this.inventoryCron })
        this.$message.success('库存对比定时任务配置已保存')
      } catch (e) {
        console.error('Failed to save inventory cron:', e)
        this.$message.error('保存失败')
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
    async testAIModel() {
      if (!this.canSaveConfig) {
        this.aiTestMsg = '配置未加载成功，请先重新加载'
        this.aiTestType = 'error'
        return
      }
      this.testingAI = true
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
        this.testingAI = false
      }
    },
    async loadAiModels() {
      if (!this.canSaveConfig) {
        this.aiTestMsg = '配置未加载成功，请先重新加载'
        this.aiTestType = 'error'
        return
      }
      this.loadingAIModels = true
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
        this.loadingAIModels = false
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
    isJavInfoImportActive(job) {
      return isJavInfoImportActive(job)
    },
    javinfoImportStatusLabel(job) {
      return javinfoImportStatusLabel(job)
    },
    formatBytes(value) {
      return formatBytes(value)
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
