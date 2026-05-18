<template>
  <div class="settings page-shell page-shell--standard">
    <!-- Header Aligned with Main App Rhythm -->
    <div class="settings-header">
      <h1>设置</h1>
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
        title="配置加载失败"
        description="无法确认当前配置，保存已暂停以避免覆盖现有设置。"
        retry-label="重新加载"
        @retry="loadConfig"
      />

      <transition v-else name="fade-slide" mode="out-in">
        <div :key="activeGroup" class="active-section">
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
                    <input class="input" v-model="config.javinfo.api_url" placeholder="http://localhost:18080" />
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
              <p>按作用范围整理全局显示、影片检索和个性推荐偏好。</p>
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
                    <h3>个性推荐</h3>
                  </div>
                  <button class="btn btn-ghost btn-sm" type="button" @click="resetBubbleCfg">恢复默认</button>
                </div>

                <div class="discovery-preference-grid">
                  <section class="scope-card">
                    <div class="scope-card-header">
                      <span class="setting-title">推荐入口</span>
                      <span class="setting-note">默认打开 {{ defaultTabLabel }}</span>
                    </div>
                    <div class="appearance-setting-row">
                      <div class="setting-copy">
                        <span class="setting-title">默认页签</span>
                        <span class="setting-note">{{ defaultTabLabel }}</span>
                      </div>
                      <div class="segmented-mini" aria-label="个性推荐默认页签">
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
                    <span>导入成功后会替换 JavInfoApi 当前 PostgreSQL 库。优先使用临时库恢复并保留最近旧库。</span>
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
                  <div class="form-row">
                    <div class="form-group compact-number">
                      <label>并行恢复</label>
                      <input class="input" v-model.number="config.javinfo.import_db.max_parallel_jobs" type="number" min="1" max="8" />
                    </div>
                    <div class="form-group compact-number">
                      <label>保留旧库</label>
                      <input class="input" v-model.number="config.javinfo.import_db.keep_previous_databases" type="number" min="0" max="5" />
                    </div>
                  </div>

                  <div class="import-actions">
                    <button class="btn btn-secondary" type="button" @click="preflightJavInfoImport" :disabled="javinfoImportPreflighting || !canSaveConfig">
                      {{ javinfoImportPreflighting ? '检查中...' : '预检数据库' }}
                    </button>
                    <span v-if="javinfoImportPreflight" class="import-status" :class="{ error: !javinfoImportPreflight.ok }">
                      {{ javinfoImportPreflight.ok ? '预检通过' : '预检未通过' }}
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
import { displayLang } from '../utils/displayLang.js'
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
      showImportPassword: false,
      javinfoImportFile: null,
      javinfoImportConfirm: false,
      javinfoImportDirectConfirm: false,
      javinfoImportPreflight: null,
      javinfoImportPreflighting: false,
      javinfoImportUploading: false,
      javinfoImportUploadProgress: 0,
      javinfoImportJob: null,
      javinfoImportJobs: [],
      javinfoImportPollTimer: null,
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
      return this.configLoaded && !this.configLoading && !this.configLoadError
    },
    javinfoImportCanStart() {
      return Boolean(
        this.canSaveConfig
        && this.javinfoImportFile
        && this.javinfoImportConfirm
        && this.javinfoImportPreflight?.ok
        && (!this.javinfoImportRequiresDirectConfirm || this.javinfoImportDirectConfirm)
        && !this.javinfoImportUploading
        && !this.isJavInfoImportActive(this.javinfoImportJob)
      )
    },
    javinfoImportRequiresDirectConfirm() {
      return Boolean(
        this.javinfoImportPreflight?.ok
        && this.javinfoImportPreflight?.checks?.database?.can_create_database === false
      )
    },
    javinfoImportLogTail() {
      return (this.javinfoImportJob?.logs || []).slice(-12).join('\n')
    },
    javinfoImportProgress() {
      const job = this.javinfoImportJob || {}
      if (job.status === 'completed') return 100
      if (this.javinfoImportUploading) return Math.max(0, Math.min(100, Math.round(this.javinfoImportUploadProgress)))
      const total = Number(job.file_size || this.javinfoImportFile?.size || 0)
      const uploaded = Number(job.uploaded_bytes || 0)
      if (total > 0) return Math.max(0, Math.min(100, Math.round(uploaded * 100 / total)))
      if (this.isJavInfoImportActive(job)) return 10
      return 0
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
    async loadConfig() {
      this.configLoading = true
      this.configLoadError = ''
      try {
        const resp = await api.getConfig()
        const data = resp.data

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
    async preflightJavInfoImport() {
      if (!this.canSaveConfig) {
        this.$message.error('配置未加载成功，已阻止预检')
        return
      }
      this.javinfoImportPreflighting = true
      this.javinfoImportPreflight = null
      this.javinfoImportDirectConfirm = false
      try {
        const resp = await api.preflightJavInfoImport(
          this.config.javinfo.import_db,
          this.javinfoImportFile?.size || 0,
        )
        this.javinfoImportPreflight = resp.data
        if (resp.data?.ok) {
          this.$message.success('JavInfo 数据库预检通过')
        } else {
          this.$message.warning('JavInfo 数据库预检未通过')
        }
      } catch (e) {
        this.javinfoImportPreflight = { ok: false, error: e.response?.data?.detail || e.message }
      } finally {
        this.javinfoImportPreflighting = false
      }
    },
    async startJavInfoImport() {
      if (!this.javinfoImportCanStart) return
      this.javinfoImportUploading = true
      this.javinfoImportUploadProgress = 0
      try {
        const createResp = await api.createJavInfoImportJob({
          filename: this.javinfoImportFile.name,
          file_size: this.javinfoImportFile.size,
          import_db: this.config.javinfo.import_db,
          confirm_replace: this.javinfoImportConfirm,
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
        this.stopJavInfoImportPolling()
        await this.listJavInfoImportJobs()
      } catch (e) {
        this.$message.error(e.response?.data?.detail || '取消失败')
      }
    },
    isJavInfoImportActive(job) {
      return ['pending', 'uploading', 'uploaded', 'restoring', 'stopping', 'swapping', 'restarting', 'migrating'].includes(job?.status)
    },
    javinfoImportStatusLabel(job) {
      const status = job?.status || 'pending'
      const stage = job?.stage || status
      const labels = {
        pending: '等待上传',
        uploading: '上传中',
        uploaded: '已上传',
        restoring: '恢复中',
        stopping: '停止 JavInfoApi',
        swapping: '切换数据库',
        restarting: '重启 JavInfoApi',
        migrating: '更新 JavInfoApi',
        completed: '已完成',
        failed: '失败',
        canceled: '已取消',
      }
      return labels[stage] || labels[status] || status
    },
    formatBytes(value) {
      const size = Number(value || 0)
      if (size >= 1024 ** 3) return `${(size / 1024 ** 3).toFixed(2)} GB`
      if (size >= 1024 ** 2) return `${(size / 1024 ** 2).toFixed(1)} MB`
      if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${size} B`
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

<style scoped>
.settings {
  min-height: 100dvh;
  position: relative;
  padding-bottom: 120px; /* Space for footer */
}

.settings-header {
  margin-bottom: 32px;
}

.settings-header h1 { 
  font-size: var(--type-page-title); 
  font-weight: 700; 
  color: var(--text-primary);
  margin-bottom: 32px; 
  letter-spacing: 0;
}

.settings-tabs {
  display: inline-flex;
  gap: 5px;
  padding: 5px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--glass-control-bg);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(22px) saturate(165%);
  -webkit-backdrop-filter: blur(22px) saturate(165%);
  scrollbar-width: thin;
  scrollbar-color: var(--border-light) transparent;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 16px;
  background: var(--glass-subtle-bg);
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: var(--type-body);
  font-weight: 650;
  cursor: pointer;
  position: relative;
  box-shadow: inset 0 1px 0 var(--glass-highlight);
  transition: color var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}

.tab-item:hover {
  color: var(--text-primary);
  background: var(--glass-control-bg-hover);
  border-color: var(--glass-control-border-hover);
}

.tab-item.active {
  background: var(--glass-active-bg);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
  transform: translateY(-1px);
}

.tab-icon {
  font-size: var(--type-panel-title);
}

.settings-content-wide {
  width: 100%;
}

.settings-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  gap: 12px;
  color: var(--text-secondary);
}

.spinner-large {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.config-section {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-header {
  margin-bottom: 32px;
}

.section-header h2 {
  font-size: var(--type-section-title);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
  letter-spacing: 0;
}

.section-header p {
  font-size: var(--type-body);
  color: var(--text-muted);
}

.settings-card {
  margin-bottom: 32px;
  width: 100%;
}

.card-content {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px;
  box-shadow: var(--shadow-sm);
}

.form-slot {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 24px;
  border: 1px solid var(--border-light);
}
.settings-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.settings-card-header h2 {
  font-size: var(--type-panel-title);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0;
}

.settings-sub-section {
  padding: 24px 0;
  border-top: 1px solid var(--border);
}
.settings-sub-section:first-child {
  border-top: none;
  padding-top: 0;
}

.settings-sub-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-group { margin-bottom: 20px; }
.form-group:last-child { margin-bottom: 0; }
.form-group label { display: block; margin-bottom: 8px; font-size: var(--type-control); color: var(--text-secondary); font-weight: 500; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.bubble-control-row { margin-top: 16px; }
.form-group-fill { flex: 1; }
.settings-footer {
  position: fixed;
  bottom: 0;
  left: var(--sidebar-width);
  right: 0;
  background: var(--material-glass-sheet);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  padding: 20px 0;
  z-index: 100;
  display: flex;
  justify-content: center;
}

.footer-content {
  display: flex;
  justify-content: flex-end;
}

.save-spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@media (max-width: 768px) {
  .settings {
    padding-bottom: 112px;
  }
  .settings-header h1 { font-size: var(--type-page-title-mobile); }
  .settings-tabs {
    margin: 0 -20px;
    padding: 5px;
    max-width: calc(100vw - 40px);
    overflow-x: auto;
    scroll-snap-type: x proximity;
    -webkit-overflow-scrolling: touch;
  }
  .tab-item {
    flex: 0 0 auto;
    min-height: 44px;
    padding: 10px 12px;
    white-space: nowrap;
    scroll-snap-align: start;
  }
  .form-row { grid-template-columns: 1fr; gap: 16px; }
  .card-content,
  .form-slot {
    padding: 20px;
  }
  .settings-footer {
    left: 0;
    bottom: calc(61px + env(safe-area-inset-bottom, 0px));
    padding: 10px 0;
    z-index: var(--z-nav);
  }
  .footer-content {
    width: min(var(--page-max-standard), calc(100% - (var(--page-gutter) * 2)));
  }
  .footer-content .btn {
    width: 100%;
    min-height: 44px;
    justify-content: center;
  }
}

.input-password-wrap { position: relative; display: flex; align-items: center; }
.input-password-wrap .input { padding-right: 58px; }
.input-eye-btn {
  position: absolute; right: 8px; background: none; border: none;
  cursor: pointer; color: var(--text-muted); padding: 4px;
  display: flex; align-items: center; justify-content: center;
  width: 44px;
  height: 44px;
}
.input-eye-btn:hover { color: var(--text-primary); }

.form-group.checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  cursor: pointer;
}
.form-group.checkbox input { width: 18px; height: 18px; accent-color: var(--accent); cursor: pointer; }
.form-group.checkbox label { margin: 0; font-size: var(--type-body); color: var(--text-primary); cursor: pointer; }
.telegram-test-row,
.ai-test-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.telegram-test-msg,
.ai-test-msg {
  color: var(--text-secondary);
  font-size: 13px;
}
.ai-test-msg.error {
  color: var(--badge-error-text);
}
.notification-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 18px;
}
.notification-grid .form-group.checkbox {
  margin: 0;
  min-height: 44px;
}
.automation-policy-control {
  width: min(100%, 420px);
  margin-bottom: 8px;
}
.automation-policy-control button {
  flex: 1;
  min-width: 88px;
}
.source-check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}
.source-check-item {
  display: flex !important;
  align-items: center;
  gap: 8px;
  margin: 0 !important;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-card);
  color: var(--text-primary) !important;
  cursor: pointer;
}
.source-check-item input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
}

.appearance-section .section-header {
  margin-bottom: 22px;
}

.preference-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.preference-section {
  padding: 18px;
  border-radius: 22px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card);
}

.preference-section-header,
.scope-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.preference-section-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 17px;
  letter-spacing: 0;
}

.appearance-scope-grid,
.discovery-preference-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: stretch;
}

.discovery-preference-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 12px;
}

.scope-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface-control);
}

.scope-card.compact-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.scope-card-header {
  align-items: flex-start;
}

.scope-card-header > div,
.scope-card-header .setting-title,
.scope-card-header .setting-note {
  min-width: 0;
}

.scope-card-header .setting-title,
.scope-card-header .setting-note {
  display: block;
}

.visual-card {
  margin-top: 12px;
}

.appearance-chip {
  min-height: 26px;
  padding: 4px 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--surface-control);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.appearance-setting-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.appearance-setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 9px 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--glass-control-bg);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(18px) saturate(155%);
  -webkit-backdrop-filter: blur(18px) saturate(155%);
}

.appearance-setting-row.vertical {
  align-items: stretch;
  flex-direction: column;
}

.setting-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 3px;
}

.setting-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}

.setting-note {
  color: var(--text-muted);
  font-size: 12px;
}

.segmented-mini {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--glass-control-bg);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(18px) saturate(155%);
  -webkit-backdrop-filter: blur(18px) saturate(155%);
}

.segmented-mini.wide {
  min-width: 230px;
}

.segmented-mini button {
  min-width: 38px;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background: var(--glass-subtle-bg);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: inset 0 1px 0 var(--glass-highlight);
  transition: color var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}

.segmented-mini button:hover {
  color: var(--text-primary);
  background: var(--glass-control-bg-hover);
  border-color: var(--glass-control-border-hover);
}

.segmented-mini button.active {
  background: var(--glass-active-bg);
  border-color: var(--glass-active-border);
  color: var(--text-primary);
  box-shadow: var(--glass-active-shadow);
}

.aura-preview {
  display: flex;
  align-items: center;
  align-content: center;
  flex-wrap: wrap;
  gap: var(--preview-gap);
  min-height: 118px;
  margin-bottom: 10px;
  padding: 16px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    radial-gradient(circle at top left, rgba(255,255,255,0.10), transparent 32%),
    var(--material-glass-subtle);
}

.preview-bubble {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-control);
  color: var(--text-primary);
  background: var(--surface-card);
  font-size: var(--preview-font);
  font-weight: 700;
  line-height: 1;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.16);
}

.threshold-slider {
  width: 100%;
  min-width: 0;
  accent-color: var(--accent);
  cursor: pointer;
}

.tag-tuning-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.tuning-control {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--material-glass-subtle);
}

.tuning-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.tuning-copy strong {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.javinfo-import-panel {
  gap: 14px;
}

.import-warning {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid rgba(244, 63, 94, 0.28);
  border-radius: 12px;
  background: rgba(244, 63, 94, 0.08);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.import-warning strong {
  color: var(--text-primary);
  font-size: 14px;
}

.import-warning-direct {
  border-color: rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.1);
}

.compact-number {
  max-width: 220px;
}

.import-file-drop {
  padding: 10px;
  border: 1px dashed var(--border);
  border-radius: 12px;
  background: var(--material-glass-subtle);
}

.file-input {
  padding-top: 10px;
}

.import-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.import-status {
  color: var(--badge-success-text);
  font-size: 13px;
  font-weight: 700;
}

.import-status.error,
.import-error {
  color: var(--badge-error-text);
}

.import-confirm {
  align-items: flex-start;
}

.import-progress {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--material-glass-subtle);
}

.import-progress-head,
.import-job-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 13px;
}

.import-progress-head strong,
.import-job-row strong {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.import-log-tail {
  max-height: 180px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-control);
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.import-job-list {
  display: grid;
  gap: 8px;
  padding-top: 4px;
}

.import-job-list-title {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.import-job-row {
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-card);
}

.import-job-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .appearance-scope-grid,
  .discovery-preference-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .preference-section {
    padding: 14px;
    border-radius: 18px;
  }

  .preference-section-header,
  .scope-card-header {
    align-items: center;
  }

  .appearance-setting-row {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .segmented-mini,
  .segmented-mini.wide {
    width: 100%;
    flex-basis: auto;
    min-width: 0;
  }

  .segmented-mini {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 1fr;
  }

  .segmented-mini button {
    min-width: 0;
    padding: 0 8px;
  }

  .tag-tuning-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* Fade Slide Transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
