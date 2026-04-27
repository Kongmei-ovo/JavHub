<template>
  <div class="settings">
    <div class="page-header">
      <h1>设置</h1>
      <div class="page-header-actions">
        <button class="btn btn-primary" @click="save" :disabled="saving">
          <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
          <span v-else>保存配置</span>
        </button>
      </div>
    </div>

    <div class="config-container">
      <aside class="config-sidebar">
        <nav class="config-nav">
          <button 
            v-for="group in navGroups" 
            :key="group.id"
            class="nav-item"
            :class="{ active: activeGroup === group.id }"
            @click="activeGroup = group.id"
          >
            <span class="nav-icon">{{ group.icon }}</span>
            <span class="nav-label">{{ group.label }}</span>
          </button>
        </nav>
      </aside>

      <main class="config-main">
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                        <svg v-if="!showOpenlistPwd" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                      <svg v-if="!showEmbyKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <h2>MetaTube / 数据增强</h2>
              </div>
              <div class="form-slot">
                <div class="form-group">
                  <label>服务器地址</label>
                  <input class="input" v-model="config.metatube.host" placeholder="154.23.255.204" />
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
                      <svg v-if="!showMetatubeToken" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                      <svg v-if="!showBotToken" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
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
                  <button class="btn btn-secondary" @click="testTelegram" :disabled="testingTelegram || !config.telegram.bot_token">
                    {{ testingTelegram ? '发送中...' : '发送测试信息' }}
                  </button>
                  <span v-if="telegramTestMsg" class="telegram-test-msg">{{ telegramTestMsg }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="section-footer">
            <button class="btn btn-primary" @click="save" :disabled="saving">
              <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
              <span v-else>保存所有配置</span>
            </button>
          </div>
        </div>

        <!-- Automation Section -->
        <div v-if="activeGroup === 'automation'" class="config-section">
          <div class="section-header">
            <h2>自动化任务</h2>
            <p>管理后台运行的定时任务与数据抓取频率。</p>
          </div>

          <!-- 爬虫 -->
          <div class="settings-card">
            <div class="card-content">
              <div class="settings-card-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                <button class="btn btn-primary" @click="saveInventoryCron">保存定时任务</button>
              </div>
            </div>
          </div>

          <div class="section-footer">
            <button class="btn btn-primary" @click="save" :disabled="saving">
              <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
              <span v-else>保存所有配置</span>
            </button>
          </div>
        </div>

        <!-- Appearance Section -->
        <div v-if="activeGroup === 'appearance'" class="config-section">
          <div class="section-header">
            <h2>外观设计</h2>
            <p>自定义界面主题、色彩模式及交互视觉效果。</p>
          </div>

          <!-- 页面设计 -->
          <div class="settings-card">
            <div class="card-content">
              <div class="settings-card-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 2a10 10 0 010 20z" fill="currentColor" opacity="0.3"/>
                </svg>
                <h2>页面设计</h2>
              </div>

              <div class="settings-sub-section">
                <div class="settings-sub-header">主题选择</div>
                <div class="theme-grid">
                  <div 
                    v-for="(theme, key) in themes" 
                    :key="key"
                    class="theme-card"
                    :class="{ active: currentTheme === key }"
                    @click="switchTheme(key)"
                  >
                    <div class="theme-card-preview" :style="{ background: theme.vars['--bg-primary'] }">
                      <div class="preview-accent" :style="{ background: theme.vars['--accent'] }"></div>
                      <div class="preview-secondary" :style="{ background: theme.vars['--bg-secondary'] }"></div>
                    </div>
                    <div class="theme-card-info">
                      <div class="theme-icon">{{ theme.icon }}</div>
                      <div class="theme-names">
                        <span class="theme-label">{{ theme.label }}</span>
                        <span class="theme-label-en">{{ theme.labelEn }}</span>
                      </div>
                      <div class="theme-check" v-if="currentTheme === key">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="14" height="14">
                          <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="settings-sub-section">
                <div class="settings-sub-header">检索页数量</div>
                <div class="form-slot">
                  <div class="form-group">
                    <select class="input" v-model.number="config.javinfo.page_size">
                      <option value="15">15</option>
                      <option value="30">30</option>
                      <option value="50">50</option>
                      <option value="100">100</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 题材气泡设置 -->
          <div class="settings-card">
            <div class="card-content">
              <div class="settings-card-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                <h2>题材气泡设置</h2>
              </div>

              <div class="form-slot">
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

                <!-- 金色传说说明 + 颜色自定义 -->
                <div v-if="bubbleCfg.colorMode === 'legendary'" class="legendary-hint">
                  <div class="legendary-colors-grid">
                    <div class="legendary-color-item">
                      <span class="legendary-dot legendary" :style="{ background: bubbleCfg.rarityColors.legendary }"></span>
                      <span>传奇</span>
                      <input type="color" v-model="bubbleCfg.rarityColors.legendary" class="rarity-color-input" title="传奇颜色" />
                    </div>
                    <div class="legendary-color-item">
                      <span class="legendary-dot epic" :style="{ background: bubbleCfg.rarityColors.epic }"></span>
                      <span>史诗</span>
                      <input type="color" v-model="bubbleCfg.rarityColors.epic" class="rarity-color-input" title="史诗颜色" />
                    </div>
                    <div class="legendary-color-item">
                      <span class="legendary-dot rare" :style="{ background: bubbleCfg.rarityColors.rare }"></span>
                      <span>稀有</span>
                      <input type="color" v-model="bubbleCfg.rarityColors.rare" class="rarity-color-input" title="稀有颜色" />
                    </div>
                    <div class="legendary-color-item">
                      <span class="legendary-dot common" :style="{ background: bubbleCfg.rarityColors.common }"></span>
                      <span>普通</span>
                      <input type="color" v-model="bubbleCfg.rarityColors.common" class="rarity-color-input" title="普通颜色" />
                    </div>
                  </div>
                  <div class="legendary-hint-text">
                    <span class="legendary-dot legendary" :style="{ background: bubbleCfg.rarityColors.legendary }"></span> 传奇 — 影片库中出现极少，琥珀金呼吸光效
                    <br/>
                    <span class="legendary-dot epic" :style="{ background: bubbleCfg.rarityColors.epic }"></span> 史诗 — 影片库中出现较少，紫色呼吸光效
                    <br/>
                    <span class="legendary-dot rare" :style="{ background: bubbleCfg.rarityColors.rare }"></span> 稀有 — 影片库中出现一般，蓝色微光
                    <br/>
                    <span class="legendary-dot common" :style="{ background: bubbleCfg.rarityColors.common }"></span> 普通 — 影片库中出现频繁，无光效
                  </div>
                  <div class="rarity-thresholds">
                    <div class="rarity-threshold-row">
                      <span class="rarity-dot legendary" :style="{ background: bubbleCfg.rarityColors.legendary }"></span>
                      <span class="threshold-label">传奇</span>
                      <input
                        type="range"
                        min="1"
                        max="30"
                        step="1"
                        v-model.number="bubbleCfg.rarityThresholds.legendary"
                        class="threshold-slider"
                      />
                      <span class="threshold-value">{{ bubbleCfg.rarityThresholds.legendary }}%</span>
                    </div>
                    <div class="rarity-threshold-row">
                      <span class="rarity-dot epic" :style="{ background: bubbleCfg.rarityColors.epic }"></span>
                      <span class="threshold-label">史诗</span>
                      <input
                        type="range"
                        min="5"
                        max="60"
                        step="1"
                        v-model.number="bubbleCfg.rarityThresholds.epic"
                        class="threshold-slider"
                      />
                      <span class="threshold-value">{{ bubbleCfg.rarityThresholds.epic }}%</span>
                    </div>
                    <div class="rarity-threshold-row">
                      <span class="rarity-dot rare" :style="{ background: bubbleCfg.rarityColors.rare }"></span>
                      <span class="threshold-label">稀有</span>
                      <input
                        type="range"
                        min="20"
                        max="85"
                        step="1"
                        v-model.number="bubbleCfg.rarityThresholds.rare"
                        class="threshold-slider"
                      />
                      <span class="threshold-value">{{ bubbleCfg.rarityThresholds.rare }}%</span>
                    </div>
                  </div>
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
                  <div class="form-group" style="flex:1">
                    <label>演员头像尺寸</label>
                    <div class="avatar-size-btns">
                      <button class="size-btn" :class="{ active: bubbleCfg.actressAvatarSize === 'small' }" @click="bubbleCfg.actressAvatarSize = 'small'">小</button>
                      <button class="size-btn" :class="{ active: bubbleCfg.actressAvatarSize === 'medium' }" @click="bubbleCfg.actressAvatarSize = 'medium'">中</button>
                      <button class="size-btn" :class="{ active: bubbleCfg.actressAvatarSize === 'large' }" @click="bubbleCfg.actressAvatarSize = 'large'">大</button>
                    </div>
                    <div class="size-hint">{{ { small: '4行 · 约48个', medium: '3行 · 约36个', large: '2行 · 约24个' }[bubbleCfg.actressAvatarSize] }}</div>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group" style="flex:1">
                    <label>显示语言</label>
                    <div class="avatar-size-btns">
                      <button class="size-btn" :class="{ active: displayLangVal === 'ja' }" @click="setDisplayLang('ja')">日文</button>
                      <button class="size-btn" :class="{ active: displayLangVal === 'zh' }" @click="setDisplayLang('zh')">中文</button>
                      <button class="size-btn" :class="{ active: displayLangVal === 'en' }" @click="setDisplayLang('en')">英文</button>
                    </div>
                  </div>
                </div>
                <div class="form-row">
                  <button class="btn btn-secondary" @click="resetBubbleCfg">恢复默认气泡设置</button>
                </div>
              </div>
            </div>
          </div>

          <div class="section-footer">
            <button class="btn btn-primary" @click="save" :disabled="saving">
              <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
              <span v-else>保存所有配置</span>
            </button>
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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
                    <select class="input" v-model="translationType" style="flex:1; min-width:0">
                      <option value="actress">演员</option>
                      <option value="category">题材</option>
                      <option value="series">系列</option>
                      <option value="title">标题</option>
                    </select>
                    <button class="btn btn-ghost trans-refresh-btn" @click="loadTransStats" title="刷新">↻</button>
                  </div>
                </div>
                <div v-if="transStats[translationType] !== undefined" class="trans-stat">
                  当前 {{ translationTypeLabels[translationType] }} 已翻译 <strong>{{ transStats[translationType] }}</strong> 条
                </div>
                <div class="trans-actions">
                  <button class="btn btn-ghost" @click="exportTranslation">
                    导出 {{ translationTypeLabels[translationType] }}
                  </button>
                  <label class="btn btn-ghost trans-import-btn">
                    导入 {{ translationTypeLabels[translationType] }}
                    <input type="file" accept=".json" style="display:none" @change="importTranslation" />
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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

          <!-- 通知 -->
          <div class="settings-card">
            <div class="card-content">
              <div class="settings-card-header">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
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

          <div class="section-footer">
            <button class="btn btn-primary" @click="save" :disabled="saving">
              <span v-if="saving" class="spinner" style="width:16px;height:16px;border-width:2px"></span>
              <span v-else>保存所有配置</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { THEMES, applyTheme } from '../assets/themes.js'
import { displayLang } from '../utils/displayLang.js'

const DEFAULT_CONFIG = {
  openlist: { api_url: '', username: '', password: '', default_path: '/115/AV' },
  emby: { api_url: '', api_key: '' },
  telegram: { bot_token: '', allowed_user_ids: [] },
  crawler: { request_interval: 3 },
  scheduler: { subscription_check_hour: 2 },
  notification: { enabled: false, telegram: true, auto_download_notify: true, download_complete_notify: true, new_movie_notify: true },
  javinfo: { api_url: 'http://localhost:8080', page_size: 30 },
  metatube: { host: '154.23.255.204', port: 8081, token: '' },
  proxy: { enabled: false, http_url: '', https_url: '' },
}

const DEFAULT_BUBBLE_CFG = {
  baseSize: 16, fillPercent: 50, spacing: 16,
  colorMode: 'legendary', palette: 'monet',
  customGradients: [], customGradientsText: '',
  bubbleCount: 36,
  rarityThresholds: { legendary: 5, epic: 20, rare: 50 },
  actressAvatarSize: 'medium', // 'small' | 'medium' | 'large'
  rarityColors: {
    legendary: '#c89a30',
    epic: '#7040a0',
    rare: '#3070a8',
    common: '#607080',
  },
}

const TRANSLATION_TYPE_LABELS = { actress: '演员', category: '题材', series: '系列', title: '标题' }

export default {
  name: 'Config',
  data() {
    return {
      config: JSON.parse(JSON.stringify(DEFAULT_CONFIG)),
      telegramUsers: '',
      translationType: 'actress',
      translationTypeLabels: TRANSLATION_TYPE_LABELS,
      transStats: {},
      transMsg: '',
      transMsgType: 'info',
      saving: false,
      testingTelegram: false,
      inventoryCron: '',
      telegramTestMsg: '',
      showBotToken: false,
      showOpenlistPwd: false,
      showEmbyKey: false,
      showMetatubeToken: false,
      themes: THEMES,
      currentTheme: localStorage.getItem('javhub_theme') || 'midnight',
      navGroups: [
        { id: 'services', label: '常规与服务', icon: '🌐' },
        { id: 'automation', label: '自动化任务', icon: '⚙️' },
        { id: 'appearance', label: '界面与外观', icon: '🎨' },
        { id: 'advanced', label: '高级设置', icon: '🛠️' }
      ],
      activeGroup: 'services',
      bubbleCfg: JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG)),
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
      
      // Merge with DEFAULT_CONFIG to ensure all fields exist
      this.config = {
        ...JSON.parse(JSON.stringify(DEFAULT_CONFIG)),
        ...data
      }
      
      // Handle sub-objects to ensure they are also merged
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
    } catch (e) {
      console.error('Failed to load config:', e)
    }
    this.loadBubbleCfg()
    this.loadTransStats()
    },
    methods: {
    async save() {      this.saving = true
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
    async saveInventoryCron() {
      try {
        await api.updateConfig({ inventory_cron: this.inventoryCron })
        this.$message.success('库存对比定时任务配置已保存')
      } catch (e) {
        console.error('Failed to save inventory cron:', e)
        this.$message.error('保存失败')
      }
    },
    async testTelegram() {
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
      this.bubbleCfg = JSON.parse(JSON.stringify(DEFAULT_BUBBLE_CFG))
      localStorage.removeItem('genres_bubble_cfg')
      this.$message.info('已恢复默认')
    },
    setDisplayLang(lang) {
      displayLang.value = lang
    },
    switchTheme(key) {
      applyTheme(key)
      this.currentTheme = key
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
.settings { padding: 0; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 40px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
  z-index: 10;
}
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.page-header-actions { display: flex; gap: 8px; align-items: center; }

.config-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.config-sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  padding: 24px 12px;
  overflow-y: auto;
}

.config-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  width: 100%;
}

.nav-item:hover {
  background: var(--white-06);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent);
  color: var(--bg-primary);
}

.nav-icon {
  font-size: 18px;
  width: 24px;
  display: flex;
  justify-content: center;
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
}

.config-main {
  flex: 1;
  padding: 40px;
  overflow-y: auto;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.config-section {
  width: 100%;
  max-width: 1000px;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-header {
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--border-light);
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

.section-footer {
  margin-top: 40px;
  padding: 24px 0;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  margin-bottom: 80px;
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

@media (max-width: 768px) {
  .config-sidebar { width: 64px; padding: 12px 8px; }
  .nav-label { display: none; }
  .config-main { padding: 24px; }
  .form-row { grid-template-columns: 1fr; gap: 16px; }
}

.trans-refresh-btn { padding: 6px 10px; font-size: 14px; flex-shrink: 0; }
.input-password-wrap { position: relative; display: flex; align-items: center; }
.input-password-wrap .input { padding-right: 36px; }
.input-eye-btn {
  position: absolute; right: 8px; background: none; border: none;
  cursor: pointer; color: var(--text-muted); padding: 4px;
  display: flex; align-items: center; justify-content: center;
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
  color: var(--bg-primary);
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

.avatar-size-btns {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.size-btn {
  flex: 1;
  padding: 8px 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: var(--transition);
}
.size-btn:hover { border-color: var(--accent); color: var(--text-primary); }
.size-btn.active { background: var(--accent); border-color: var(--accent); color: var(--bg-primary); font-weight: 600; }
.size-hint { font-size: 11px; color: var(--text-muted); margin-top: 6px; }

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

.legendary-colors-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}

.legendary-color-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legendary-color-item .legendary-dot {
  flex-shrink: 0;
  transition: background 0.2s;
}

.rarity-color-input {
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  background: none;
}

.rarity-color-input::-webkit-color-swatch-wrapper { padding: 2px; }
.rarity-color-input::-webkit-color-swatch { border: none; border-radius: 2px; }

.legendary-hint-text { line-height: 1.9; }

.rarity-thresholds {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.rarity-threshold-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.rarity-threshold-row .rarity-dot {
  flex-shrink: 0;
}
.threshold-label {
  width: 36px;
  font-size: 12px;
  color: var(--text-secondary);
}
.threshold-slider {
  flex: 1;
  height: 4px;
  accent-color: var(--accent);
  cursor: pointer;
}
.threshold-value {
  width: 32px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;
}

.legendary-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}

.legendary-dot.legendary { background: #c89a30; }
.legendary-dot.epic { background: #7040a0; }
.legendary-dot.rare { background: #3070a8; }
.legendary-dot.common { background: #607080; }

.custom-gradients-input {
  resize: vertical;
  font-family: monospace;
  font-size: 11px;
  line-height: 1.5;
  min-height: 60px;
}

/* Theme Selection Grid */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
  margin-top: 12px;
}

.theme-card {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0, 1);
  position: relative;
}

.theme-card:hover {
  border-color: var(--accent-light);
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.theme-card.active {
  border-color: var(--accent);
  border-width: 2px;
  background: var(--bg-card);
}

.theme-card-preview {
  height: 60px;
  position: relative;
  border-bottom: 1px solid var(--border);
  padding: 8px;
  display: flex;
  gap: 4px;
  align-items: flex-end;
}

.preview-accent {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--border-light);
}

.preview-secondary {
  width: 40px;
  height: 8px;
  border-radius: 4px;
  opacity: 0.5;
}

.theme-card-info {
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.theme-icon {
  font-size: 18px;
}

.theme-names {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.theme-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.theme-label-en {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.theme-check {
  width: 20px;
  height: 20px;
  background: var(--accent);
  color: var(--bg-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
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
</style>
