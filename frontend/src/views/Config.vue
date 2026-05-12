<template>
  <div class="settings">
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
              <p>配置基础连接与外部服务集成，包括云盘、媒体服务器及机器人通知。</p>
            </div>

            <!-- OpenList -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  <h2>OpenList / 115云盘</h2>
                </div>
                <div class="form-slot">
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
                      <div class="input-password-wrap">
                        <input class="input" :type="showOpenlistPwd ? 'text' : 'password'" v-model="config.openlist.password" autocomplete="off" />
                        <button class="input-eye-btn" type="button" @click="showOpenlistPwd = !showOpenlistPwd">
                          <svg v-if="!showOpenlistPwd" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div class="form-group">
                    <label>默认下载路径</label>
                    <input class="input" v-model="config.openlist.default_path" placeholder="/115/AV" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Emby -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.78 7.78 5.5 5.5 0 017.78-7.78z"/>
                    <path d="M15 7l-3.5 3.5"/>
                    <path d="M19 4l-7.5 7.5"/>
                  </svg>
                  <h2>JavHub API Key</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>本机访问密钥</label>
                    <div class="input-password-wrap">
                      <input class="input" :type="showLocalApiKey ? 'text' : 'password'" v-model="localApiKey" autocomplete="off" />
                      <button class="input-eye-btn" type="button" @click="showLocalApiKey = !showLocalApiKey" :title="showLocalApiKey ? '隐藏' : '显示'">
                        <svg v-if="!showLocalApiKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      </button>
                    </div>
                  </div>
                  <button class="btn btn-secondary" type="button" @click="saveLocalApiKey">
                    保存本机密钥
                  </button>
                </div>
              </div>
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
                    <label>API Key</label>
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
                    <input class="input" v-model="config.javinfo.api_url" placeholder="http://localhost:8080" />
                  </div>
                </div>
              </div>
            </div>

            <!-- MetaTube -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                  </svg>
                  <h2>MetaTube / 数据增强</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>服务器地址</label>
                    <input class="input" v-model="config.metatube.host" placeholder="localhost" />
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>端口</label>
                      <input class="input" v-model.number="config.metatube.port" type="number" placeholder="8081" />
                    </div>
                  </div>
                  <div class="form-group">
                    <label>Token（无Token则留空）</label>
                    <div class="input-password-wrap">
                      <input class="input" :type="showMetatubeToken ? 'text' : 'password'" v-model="config.metatube.token" autocomplete="off" placeholder="可选" />
                      <button class="input-eye-btn" type="button" @click="showMetatubeToken = !showMetatubeToken">
                        <svg v-if="!showMetatubeToken" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Telegram -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                  </svg>
                  <h2>Telegram Bot</h2>
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
                    <label>允许的用户 ID（逗号分隔）</label>
                    <input class="input" v-model="telegramUsers" placeholder="123456789,987654321" />
                  </div>
                  <div class="form-group">
                    <button class="btn btn-secondary" type="button" @click="testTelegram" :disabled="testingTelegram || !canSaveConfig || !config.telegram.bot_token">
                      {{ testingTelegram ? '发送中...' : '发送测试信息' }}
                    </button>
                    <span v-if="telegramTestMsg" class="telegram-test-msg">{{ telegramTestMsg }}</span>
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
              <section class="preference-section apple-surface">
                <div class="preference-section-header">
                  <div>
                    <p class="eyebrow">Global</p>
                    <h3>全局偏好</h3>
                  </div>
                  <span class="appearance-chip">{{ displayLangLabel }} · {{ currentThemeConfig.labelEn }}</span>
                </div>

                <div class="appearance-scope-grid">
                  <div class="scope-card">
                    <div class="scope-card-header">
                      <span class="setting-title">全局主题</span>
                      <span class="setting-note">{{ currentThemeConfig.labelEn }}</span>
                    </div>
                    <div class="theme-option-grid">
                      <button
                        v-for="(theme, key) in themes"
                        :key="key"
                        class="theme-option"
                        type="button"
                        :class="{ active: currentTheme === key }"
                        :aria-pressed="currentTheme === key"
                        @click="switchTheme(key)"
                      >
                        <span
                          class="theme-card-preview theme-swatch"
                          :style="themeSwatchStyle(theme)"
                        >
                          <span class="theme-swatch-card"></span>
                          <span class="theme-swatch-line"></span>
                        </span>
                        <span class="theme-option-copy">
                          <span class="theme-label">{{ theme.label }}</span>
                          <span class="theme-label-en">{{ theme.labelEn }}</span>
                        </span>
                        <span v-if="currentTheme === key" class="theme-check">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="13" height="13">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        </span>
                      </button>
                    </div>
                  </div>

                  <div class="scope-card compact-card">
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
                </div>
              </section>

              <section class="preference-section apple-surface">
                <div class="preference-section-header">
                  <div>
                    <p class="eyebrow">Search</p>
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

              <section class="preference-section apple-surface">
                <div class="preference-section-header">
                  <div>
                    <p class="eyebrow">Discovery</p>
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
                      <span class="setting-title">题材 / 系列气泡视觉</span>
                      <span class="setting-note">系列只复用颜色、尺寸和间距，不参与题材稀有度分层</span>
                    </div>
                    <span class="appearance-chip">{{ bubbleCfg.colorMode === 'legendary' ? 'Rarity' : 'Palette' }}</span>
                  </div>

                  <div class="aura-preview" :style="auraPreviewStyle">
                    <span
                      v-for="(tag, index) in previewTags"
                      :key="tag"
                      class="preview-bubble"
                      :class="previewBubbleClass(index)"
                      :style="previewBubbleStyle(index)"
                    >
                    {{ tag }}</span>
                  </div>

                  <div class="appearance-setting-list">
                  <div class="appearance-setting-row">
                    <div class="setting-copy">
                      <span class="setting-title">视觉风格</span>
                      <span class="setting-note">{{ bubbleCfg.colorMode === 'legendary' ? '按稀有度分层' : '按色系流动' }}</span>
                    </div>
                    <div class="segmented-mini wide" aria-label="题材视觉风格">
                      <button
                        type="button"
                        :class="{ active: bubbleCfg.colorMode === 'random' }"
                        :aria-pressed="bubbleCfg.colorMode === 'random'"
                        @click="bubbleCfg.colorMode = 'random'"
                      >柔和色彩</button>
                      <button
                        type="button"
                        :class="{ active: bubbleCfg.colorMode === 'legendary' }"
                        :aria-pressed="bubbleCfg.colorMode === 'legendary'"
                        @click="bubbleCfg.colorMode = 'legendary'"
                      >灵动金传说</button>
                    </div>
                  </div>

                  <template v-if="bubbleCfg.colorMode === 'random'">
                    <div class="appearance-setting-row">
                      <div class="setting-copy">
                        <span class="setting-title">色系预设</span>
                        <span class="setting-note">{{ paletteLabel }}</span>
                      </div>
                      <div class="palette-select-wrap">
                        <GlassSelect
                          v-model="bubbleCfg.palette"
                          :options="paletteOptions"
                          class="glass-select-control glass-select-control--wide"
                          placement="right"
                          aria-label="题材色系预设"
                        />
                        <div class="palette-color-bar" :style="{ background: currentPalettePreview }"></div>
                      </div>
                    </div>

                    <div v-if="bubbleCfg.palette === '__custom__'" class="appearance-setting-row vertical">
                      <div class="setting-copy">
                        <span class="setting-title">自定义材质</span>
                        <span class="setting-note">用逗号分隔颜色或 linear-gradient</span>
                      </div>
                      <textarea
                        class="input custom-gradients-input"
                        v-model="bubbleCfg.customGradientsText"
                        rows="3"
                        placeholder="#7aaec0,#c4b5d8,linear-gradient(135deg,#111,#777)"
                      ></textarea>
                    </div>
                  </template>

                  <template v-if="bubbleCfg.colorMode === 'legendary'">
                    <div class="legendary-colors-grid">
                      <label
                        v-for="rarity in rarityOptions"
                        :key="rarity.key"
                        class="legendary-color-item"
                      >
                        <span class="legendary-dot" :style="{ background: bubbleCfg.rarityColors[rarity.key] }"></span>
                        <span>{{ rarity.label }}</span>
                        <input
                          type="color"
                          v-model="bubbleCfg.rarityColors[rarity.key]"
                          class="rarity-color-input"
                          :title="`${rarity.label}颜色`"
                        />
                      </label>
                    </div>

                    <div class="rarity-thresholds">
                      <div
                        v-for="rarity in rarityThresholdOptions"
                        :key="rarity.key"
                        class="rarity-threshold-row"
                      >
                        <span class="rarity-dot" :style="{ background: bubbleCfg.rarityColors[rarity.key] }"></span>
                        <span class="threshold-label">{{ rarity.label }}</span>
                        <input
                          type="range"
                          :min="rarity.min"
                          :max="rarity.max"
                          step="1"
                          v-model.number="bubbleCfg.rarityThresholds[rarity.key]"
                          class="threshold-slider"
                        />
                        <span class="threshold-value">{{ bubbleCfg.rarityThresholds[rarity.key] }}%</span>
                      </div>
                    </div>
                  </template>

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
              <p>进阶功能设置，包括网络代理、数据映射及系统通知。</p>
            </div>

            <!-- 翻译映射 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M5 8l6 6"/>
                    <path d="M4 14l6-6 2-2"/>
                    <path d="M2 5h12"/>
                    <path d="M7 2v3"/>
                    <path d="M22 22l-5-10-5 10"/>
                    <path d="M14 18h6"/>
                  </svg>
                  <h2>翻译映射</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>映射类型</label>
                    <div class="form-row">
                      <GlassSelect
                        v-model="translationType"
                        :options="translationTypeOptions"
                        class="translation-type-select"
                        aria-label="翻译映射类型"
                      />
                      <button class="btn btn-ghost trans-refresh-btn" type="button" @click="loadTransStats" title="刷新">↻</button>
                    </div>
                  </div>
                  <div v-if="transStats[translationType] !== undefined" class="trans-stat">
                    当前 {{ translationTypeLabels[translationType] }} 已翻译 <strong>{{ transStats[translationType] }}</strong> 条
                  </div>
                  <div class="trans-actions">
                    <button class="btn btn-ghost" type="button" @click="exportTranslation">
                      导出 {{ translationTypeLabels[translationType] }}
                    </button>
                    <label class="btn btn-ghost trans-import-btn">
                      导入 {{ translationTypeLabels[translationType] }}
                      <input class="visually-hidden-file" type="file" accept=".json" @change="importTranslation" />
                    </label>
                  </div>
                  <div v-if="transMsg" class="trans-msg" :class="transMsgType">{{ transMsg }}</div>
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

            <!-- API 访问控制 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <path d="M9 12l2 2 4-4"/>
                  </svg>
                  <h2>API 访问控制</h2>
                </div>
                <div class="form-slot">
                  <div class="form-group">
                    <label>服务端 API Key</label>
                    <div class="input-password-wrap">
                      <input class="input" :type="showServerApiKey ? 'text' : 'password'" v-model="config.server.api_key" autocomplete="off" />
                      <button class="input-eye-btn" type="button" @click="showServerApiKey = !showServerApiKey">
                        <svg v-if="!showServerApiKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      </button>
                    </div>
                  </div>
                  <div class="form-group checkbox">
                    <input type="checkbox" id="authDisabled" v-model="config.server.auth_disabled" />
                    <label for="authDisabled">显式禁用 API 认证</label>
                  </div>
                  <div class="form-group">
                    <label>前端 Origin</label>
                    <input class="input" v-model="config.server.frontend_origin" placeholder="http://localhost:5173" />
                  </div>
                  <div class="form-row">
                    <div class="form-group checkbox">
                      <input type="checkbox" id="rateLimitEnabled" v-model="config.rate_limit.enabled" />
                      <label for="rateLimitEnabled">启用速率限制</label>
                    </div>
                    <div class="form-group">
                      <label>每分钟补充令牌</label>
                      <input class="input" v-model.number="config.rate_limit.requests_per_minute" type="number" min="1" />
                    </div>
                    <div class="form-group">
                      <label>突发容量</label>
                      <input class="input" v-model.number="config.rate_limit.burst" type="number" min="1" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 通知 -->
            <div class="settings-card">
              <div class="card-content">
                <div class="settings-card-header">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
                    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 01-3.46 0"/>
                  </svg>
                  <h2>通知设置</h2>
                </div>
                <div class="form-slot">
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
        </div>
      </transition>
    </main>

    <!-- Global Floating Footer for Actions -->
    <div v-if="canSaveConfig" class="settings-footer">
      <div class="footer-content">
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
import { THEMES, applyTheme, resolveThemeKey } from '../assets/themes.js'
import { displayLang } from '../utils/displayLang.js'
import { DEFAULT_SEARCH_PREFERENCES, loadSearchPreferences, saveSearchPreferences } from '../utils/searchPreferences.js'
import { getStoredApiKey, saveStoredApiKey } from '../utils/apiKey.js'
import AppleErrorState from '../components/AppleErrorState.vue'
import GlassSelect from '../components/GlassSelect.vue'

const DEFAULT_CONFIG = {
  openlist: { api_url: '', username: '', password: '', default_path: '/115/AV' },
  emby: { api_url: '', api_key: '' },
  telegram: { bot_token: '', allowed_user_ids: [] },
  crawler: { request_interval: 3 },
  scheduler: { subscription_check_hour: 2 },
  automation: {
    download_policy: 'manual',
    candidate_sources: ['subscription', 'inventory', 'supplement'],
    rules_require_magnet: true,
    auto_process_interval_minutes: 30,
    max_auto_downloads_per_run: 20,
    max_auto_downloads_per_24h: 100,
  },
  actor_mapping: {
    auto_match_after_collect: true,
    auto_confirm_policy: 'conservative',
    candidate_per_actor: 3,
    candidate_min_confidence: 0.55,
    auto_confirm_confidence: 0.98,
    auto_confirm_gap: 0.08,
  },
  notification: { enabled: false, telegram: true, auto_download_notify: true, download_complete_notify: true, new_movie_notify: true },
  javinfo: { api_url: 'http://localhost:8080', page_size: 30 },
  metatube: { host: 'localhost', port: 8081, token: '' },
  proxy: { enabled: false, http_url: '', https_url: '' },
  server: { frontend_origin: 'http://localhost:5173', auth_disabled: false, api_key: '' },
  rate_limit: { enabled: false, requests_per_minute: 60, burst: 10 },
}

const DEFAULT_BUBBLE_CFG = {
  baseSize: 16, fillPercent: 50, spacing: 16,
  colorMode: 'legendary', palette: 'monet',
  customGradients: [], customGradientsText: '',
  bubbleCount: 36,
  defaultTab: 'genre',
  rarityThresholds: { legendary: 5, epic: 20, rare: 50 },
  actressAvatarSize: 'medium', // 'small' | 'medium' | 'large'
  actressPageSize: 36,
  seriesPageSize: 60,
  rarityColors: {
    legendary: '#c89a30',
    epic: '#7040a0',
    rare: '#3070a8',
    common: '#607080',
  },
}

const TRANSLATION_TYPE_LABELS = { actress: '演员', category: '题材', series: '系列', title: '标题' }

function parseGradientList(value = '') {
  const items = []
  let depth = 0
  let current = ''

  for (const char of value) {
    if (char === '(') depth += 1
    if (char === ')') depth = Math.max(0, depth - 1)

    if (char === ',' && depth === 0) {
      const item = current.trim()
      if (item) items.push(item)
      current = ''
      continue
    }

    current += char
  }

  const last = current.trim()
  if (last) items.push(last)
  return items.filter(item => item.startsWith('linear-gradient') || item.startsWith('#'))
}

export default {
  name: 'Config',
  components: { AppleErrorState, GlassSelect },
  data() {
    return {
      config: JSON.parse(JSON.stringify(DEFAULT_CONFIG)),
      telegramUsers: '',
      translationType: 'actress',
      translationTypeLabels: TRANSLATION_TYPE_LABELS,
      transStats: {},
      transMsg: '',
      transMsgType: 'info',
      configLoading: true,
      configLoaded: false,
      configLoadError: '',
      saving: false,
      testingTelegram: false,
      inventoryCron: '',
      telegramTestMsg: '',
      showBotToken: false,
      showOpenlistPwd: false,
      showEmbyKey: false,
      showMetatubeToken: false,
      showLocalApiKey: false,
      showServerApiKey: false,
      localApiKey: getStoredApiKey(),
      themes: THEMES,
      currentTheme: resolveThemeKey(localStorage.getItem('javhub_theme')),
      navGroups: [
        { id: 'services', label: '常规与服务', icon: '🌐' },
        { id: 'automation', label: '自动化策略', icon: '⚙️' },
        { id: 'appearance', label: '界面与外观', icon: '🎨' },
        { id: 'advanced', label: '高级设置', icon: '🛠️' }
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
      seriesPageSizeOptions: [30, 60, 90, 100],
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
      rarityOptions: [
        { key: 'legendary', label: '传奇' },
        { key: 'epic', label: '史诗' },
        { key: 'rare', label: '稀有' },
        { key: 'common', label: '基础' },
      ],
      rarityThresholdOptions: [
        { key: 'legendary', label: '传奇', min: 1, max: 30 },
        { key: 'epic', label: '史诗', min: 5, max: 60 },
        { key: 'rare', label: '稀有', min: 20, max: 85 },
      ],
      tagTuningControls: [
        { key: 'bubbleCount', label: '显示数量', min: 12, max: 120, step: 6, unit: '' },
        { key: 'baseSize', label: '基础尺寸', min: 8, max: 48, step: 1, unit: 'px' },
        { key: 'fillPercent', label: '填充间距', min: 30, max: 200, step: 5, unit: '%' },
        { key: 'spacing', label: '标签间距', min: 0, max: 48, step: 2, unit: 'px' },
      ],
      previewTags: ['剧情', '高清', '限定', '新作', '字幕'],
      palettes: [
        { key: 'monet',    label: '莫奈',    colors: ['#c4b5d8', '#d4c4e0'] },
        { key: 'sunset',   label: '夕阳',    colors: ['#c89080', '#c87868'] },
        { key: 'ocean',   label: '海洋',    colors: ['#7aaec0', '#88c0b0'] },
        { key: 'forest',   label: '森林',    colors: ['#90b898', '#7aa888'] },
        { key: 'gold',    label: '金色',    colors: ['#a88050', '#c89050'] },
        { key: 'anime',   label: '动漫',    colors: ['#e8a0c8', '#c0a0e0'] },
        { key: 'retro',    label: '复古',    colors: ['#c89050', '#8b7355'] },
        { key: 'cyber',   label: '赛博',    colors: ['#00c8ff', '#8000ff'] },
        { key: 'pastel',  label: '马卡龙',  colors: ['#f0b8c0', '#b8d0f0'] },
        { key: 'nord',    label: 'Nord',    colors: ['#88c0d0', '#a3be8c'] },
        { key: 'neon',    label: '霓虹',    colors: ['#ff0080', '#00ff80'] },
        { key: 'earth',   label: '大地',    colors: ['#8b7355', '#6b8e5a'] },
        { key: 'candy',   label: '糖果',    colors: ['#ffb8d0', '#b8e0ff'] },
      ],
    }
  },
  computed: {
    displayLangVal() { return displayLang.value },
    canSaveConfig() {
      return this.configLoaded && !this.configLoading && !this.configLoadError
    },
    currentThemeConfig() {
      return this.themes[this.currentTheme] || Object.values(this.themes)[0]
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
    paletteLabel() {
      if (this.bubbleCfg.palette === '__all__') return '艺术随机'
      if (this.bubbleCfg.palette === '__custom__') return '自定义材质'
      return this.palettes.find(p => p.key === this.bubbleCfg.palette)?.label || '莫奈'
    },
    auraPreviewStyle() {
      return {
        '--preview-gap': `${Math.max(4, Math.min(this.bubbleCfg.spacing || 12, 28)) * 0.45}px`,
        '--preview-font': `${Math.max(11, Math.min(this.bubbleCfg.baseSize || 16, 24))}px`,
      }
    },
    // 下拉选中色系的颜色预览条
    currentPalettePreview() {
      if (this.bubbleCfg.palette === '__all__') {
        // 完全随机：展示所有色系的混合渐变
        return 'var(--accent)'
      }
      if (this.bubbleCfg.palette === '__custom__') {
        return 'var(--text-muted)'
      }
      const p = this.palettes.find(p => p.key === this.bubbleCfg.palette)
      if (!p) return 'var(--text-muted)'
      const [c1, c2] = p.colors
      return c1
    },
    paletteOptions() {
      return [
        { value: '__all__', label: '艺术随机', color: 'var(--accent)' },
        ...this.palettes.map(palette => ({
          value: palette.key,
          label: palette.label,
          color: palette.colors?.[0],
        })),
        { value: '__custom__', label: '自定义材质', color: 'var(--text-muted)' },
      ]
    },
    translationTypeOptions() {
      return Object.entries(this.translationTypeLabels).map(([value, label]) => ({ value, label }))
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
    await this.loadConfig()
    this.loadBubbleCfg()
    this.loadSearchPrefs()
    this.loadTransStats()
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
        this.saveLocalApiKey({ silent: true })
        this.config.telegram.allowed_user_ids = this.telegramUsers.split(',').map(s => s.trim()).filter(Boolean)
        await api.updateConfig(this.config)
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
    loadBubbleCfg() {
      try {
        const saved = localStorage.getItem('genres_bubble_cfg')
        if (saved) {
          const parsed = JSON.parse(saved)
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            this.bubbleCfg = {
              ...JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG)),
              ...parsed,
            }
            if (!parsed.actressPageSize && parsed.actressAvatarSize) {
              const fallbackPageSize = { small: 48, medium: 36, large: 20 }
              this.bubbleCfg.actressPageSize = fallbackPageSize[parsed.actressAvatarSize] || DEFAULT_BUBBLE_CFG.actressPageSize
            }
            if (Array.isArray(parsed.customGradients)) {
              this.bubbleCfg.customGradients = parsed.customGradients
              this.bubbleCfg.customGradientsText = parsed.customGradients.join(',')
            }
          }
        }
      } catch (e) {
        console.error("Failed to parse bubble cfg", e);
      }
    },
    saveBubbleCfg() {
      this.bubbleCfg.customGradients = parseGradientList(this.bubbleCfg.customGradientsText)
      localStorage.setItem('genres_bubble_cfg', JSON.stringify(this.bubbleCfg))
    },
    loadSearchPrefs() {
      this.searchPrefs = loadSearchPreferences()
    },
    saveSearchPrefs() {
      this.searchPrefs = saveSearchPreferences(this.searchPrefs)
    },
    saveLocalApiKey({ silent = false } = {}) {
      this.localApiKey = saveStoredApiKey(this.localApiKey)
      if (!silent) this.$message.success('本机 API Key 已保存')
    },
    resetBubbleCfg() {
      this.bubbleCfg = JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG))
      localStorage.removeItem('genres_bubble_cfg')
      this.$message.info('已恢复默认')
    },
    setDisplayLang(lang) {
      displayLang.value = lang
    },
    switchTheme(key) {
      this.currentTheme = applyTheme(key)
    },
    themeSwatchStyle(theme) {
      const vars = theme?.vars || {}
      return {
        '--theme-bg': vars['--bg-primary'] || '#000',
        '--theme-surface': vars['--bg-secondary'] || vars['--bg-card'] || '#111',
        '--theme-card': vars['--bg-card'] || 'rgba(255,255,255,0.08)',
        '--theme-accent': vars['--accent'] || '#fff',
      }
    },
    previewBubbleClass(index) {
      if (this.bubbleCfg.colorMode !== 'legendary') return 'soft'
      return ['legendary', 'epic', 'rare', 'common', 'rare'][index] || 'common'
    },
    previewBubbleStyle(index) {
      const fill = Math.max(0.7, Math.min((this.bubbleCfg.fillPercent || 50) / 100, 1.8))
      const basePaddingY = Math.round(7 * fill)
      const basePaddingX = Math.round(12 * fill)
      if (this.bubbleCfg.colorMode === 'legendary') {
        const rarity = this.previewBubbleClass(index)
        return {
          background: this.bubbleCfg.rarityColors[rarity],
          padding: `${basePaddingY}px ${basePaddingX}px`,
        }
      }
      const gradients = this.previewGradients()
      return {
        background: gradients[index % gradients.length],
        padding: `${basePaddingY}px ${basePaddingX}px`,
      }
    },
    previewGradients() {
      if (this.bubbleCfg.palette === '__custom__' && this.bubbleCfg.customGradientsText) {
        const custom = parseGradientList(this.bubbleCfg.customGradientsText)
        if (custom.length) return custom
      }
      if (this.bubbleCfg.palette === '__all__') {
        return this.palettes.flatMap(p => p.colors)
      }
      return this.palettes.find(p => p.key === this.bubbleCfg.palette)?.colors || this.palettes[0].colors
    },
    async loadTransStats() {
      try {
        const resp = await api.getTranslationStats()
        this.transStats = resp.data
      } catch (e) {
        console.error('Failed to load translation stats:', e)
      }
    },
    async exportTranslation() {
      try {
        const resp = await api.exportTranslations(this.translationType)
        const url = window.URL.createObjectURL(new Blob([resp.data]))
        const a = document.createElement('a')
        a.href = url
        a.download = `translations_${this.translationType}.json`
        a.click()
        window.URL.revokeObjectURL(url)
        this.transMsg = `导出成功：translations_${this.translationType}.json`
        this.transMsgType = 'success'
      } catch (e) {
        console.error('Export failed:', e)
        this.transMsg = '导出失败'
        this.transMsgType = 'error'
      }
    },
    async importTranslation(event) {
      const file = event.target.files[0]
      if (!file) return
      try {
        const resp = await api.importTranslations(this.translationType, file)
        this.transMsg = `导入成功：${resp.data.imported} 条已更新`
        this.transMsgType = 'success'
        await this.loadTransStats()
      } catch (e) {
        console.error('Import failed:', e)
        this.transMsg = '导入失败：' + (e.response?.data?.detail || e.message)
        this.transMsgType = 'error'
      }
      event.target.value = ''
    }
  }
}
</script>

<style scoped>
.settings {
  width: 100%;
  max-width: 1400px;
  padding: 28px;
  margin: 0 auto;
  min-height: 100vh;
  position: relative;
  padding-bottom: 120px; /* Space for footer */
}

.settings-header {
  margin-bottom: 32px;
}

.settings-header h1 { 
  font-size: 32px; 
  font-weight: 700; 
  color: var(--text-primary);
  margin-bottom: 32px; 
}

.settings-tabs { 
  display: flex; 
  gap: 8px; 
  border-bottom: 1px solid var(--border); 
  padding-bottom: 1px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-light) transparent;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
}

.tab-item:hover {
  color: var(--text-primary);
}

.tab-item.active { 
  color: var(--accent); 
}

.tab-item.active::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0; 
  right: 0;
  height: 2px;
  background: var(--accent);
}

.tab-icon {
  font-size: 18px;
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
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-header p {
  font-size: 14px;
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
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
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
.form-group label { display: block; margin-bottom: 8px; font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.bubble-control-row { margin-top: 16px; }
.form-group-fill { flex: 1; }
.translation-type-select {
  flex: 1;
  min-width: 0;
}
.visually-hidden-file {
  display: none;
}

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
  width: 100%;
  max-width: 1400px;
  padding: 0 28px;
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
    width: 100%;
    padding: 24px 20px 112px;
  }
  .settings-header h1 { font-size: 28px; }
  .settings-tabs {
    margin: 0 -20px;
    padding: 0 20px 8px;
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
    z-index: 90;
  }
  .footer-content {
    max-width: none;
    padding: 0 20px;
  }
  .footer-content .btn {
    width: 100%;
    min-height: 44px;
    justify-content: center;
  }
}

.trans-refresh-btn { padding: 6px 10px; font-size: 14px; flex-shrink: 0; }
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
.form-group.checkbox label { margin: 0; font-size: 14px; color: var(--text-primary); cursor: pointer; }
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
}

.preference-section {
  padding: 16px;
  border-radius: 18px;
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
  background: var(--material-glass-subtle);
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
  background: var(--material-glass-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.theme-option-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.theme-option {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  min-height: 84px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--material-glass-subtle);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--motion-fast), background var(--motion-fast), transform var(--motion-fast);
}

.theme-option:hover {
  border-color: var(--border-light);
  background: var(--surface-card-hover);
}

.theme-option.active {
  border-color: var(--accent);
  background: var(--material-glass-elevated);
  box-shadow: inset 0 0 0 1px var(--accent-glow);
}

.theme-card-preview.theme-swatch {
  position: relative;
  display: block;
  width: 100%;
  height: 34px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: var(--theme-bg);
}

.theme-swatch::before {
  content: "";
  position: absolute;
  inset: 6px 7px auto;
  height: 8px;
  border-radius: 4px;
  background: var(--theme-surface);
}

.theme-swatch-card {
  position: absolute;
  left: 7px;
  right: 7px;
  bottom: 6px;
  height: 14px;
  border-radius: 6px;
  background: var(--theme-card);
}

.theme-swatch-line {
  position: absolute;
  left: 14px;
  right: 30px;
  bottom: 11px;
  height: 3px;
  border-radius: var(--radius-control);
  background: var(--theme-accent);
}

.theme-option-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding-right: 22px;
}

.theme-label {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.theme-label-en {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.theme-check {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent);
  color: var(--bg-primary);
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
  min-height: 54px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.026);
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
  gap: 3px;
  padding: 3px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.035);
}

.segmented-mini.wide {
  min-width: 230px;
}

.segmented-mini button {
  min-width: 38px;
  min-height: 30px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--motion-fast), background var(--motion-fast);
}

.segmented-mini button.active {
  background: var(--accent);
  color: var(--bg-primary);
}

.palette-select-wrap {
  position: relative;
  flex: 0 0 214px;
  min-width: 0;
}

.palette-color-bar {
  position: relative;
  z-index: 1;
  left: 0;
  right: 0;
  bottom: 3px;
  width: calc(100% - 24px);
  height: 3px;
  margin: -7px 12px 0;
  border-radius: 999px;
  pointer-events: none;
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
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: var(--radius-control);
  color: #fff;
  font-size: var(--preview-font);
  font-weight: 700;
  line-height: 1;
  text-shadow: 0 1px 8px rgba(0,0,0,0.35);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.16), 0 12px 28px rgba(0,0,0,0.22);
}

.preview-bubble.legendary {
  border-color: rgba(255,255,255,0.34);
}

.legendary-colors-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.legendary-color-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 7px 8px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--material-glass-subtle);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.legendary-dot,
.rarity-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.18);
}

.rarity-color-input {
  width: 22px;
  height: 22px;
  margin-left: auto;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}

.rarity-color-input::-webkit-color-swatch-wrapper { padding: 2px; }
.rarity-color-input::-webkit-color-swatch { border: none; border-radius: 5px; }

.rarity-thresholds {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--material-glass-subtle);
}

.rarity-threshold-row {
  display: grid;
  grid-template-columns: 10px 38px minmax(0, 1fr) 38px;
  align-items: center;
  gap: 10px;
}

.threshold-label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.threshold-slider {
  width: 100%;
  min-width: 0;
  accent-color: var(--accent);
  cursor: pointer;
}

.threshold-value {
  color: var(--text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  text-align: right;
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

.custom-gradients-input {
  resize: vertical;
  min-height: 76px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
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

  .theme-option-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .theme-option {
    min-height: 76px;
    padding: 7px;
  }

  .theme-card-preview.theme-swatch {
    height: 28px;
  }

  .theme-option-copy {
    padding-right: 16px;
  }

  .theme-label {
    font-size: 11px;
  }

  .theme-label-en {
    display: none;
  }

  .theme-check {
    right: 7px;
    bottom: 7px;
    width: 16px;
    height: 16px;
  }

  .appearance-setting-row {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .segmented-mini,
  .segmented-mini.wide,
  .palette-select-wrap {
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

  .legendary-colors-grid,
  .tag-tuning-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .legendary-color-item {
    min-width: 0;
  }

  .legendary-color-item span:nth-child(2) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rarity-threshold-row {
    grid-template-columns: 10px 34px minmax(0, 1fr) 36px;
    gap: 8px;
  }
}

/* 翻译映射 */
.trans-stat {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px;
}
.trans-stat strong {
  color: var(--accent);
}
.trans-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.trans-import-btn {
  cursor: pointer;
}
.trans-msg {
  margin-top: 10px;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}
.trans-msg.success {
  background: var(--badge-success-bg);
  color: var(--badge-success-text);
  border-color: var(--badge-success-border);
}
.trans-msg.error {
  background: var(--badge-error-bg);
  color: var(--badge-error-text);
  border-color: var(--badge-error-border);
}
.trans-msg.info {
  background: var(--badge-info-bg);
  color: var(--badge-info-text);
  border-color: var(--badge-info-border);
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
