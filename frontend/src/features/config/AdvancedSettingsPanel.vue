<template>
  <div class="config-section advanced-settings-stack">
    <section class="advanced-settings-group supplement-performance-group">
      <div class="advanced-settings-header">
        <h2>资料补全性能</h2>
      </div>
      <div class="settings-list">
        <label class="settings-row">
          <span class="setting-copy">
            <span class="setting-title">补全并发任务</span>
            <span class="setting-note">同时处理不同影片；同一来源仍保持单并发和冷却保护。保存后自动重启 JavInfoApi。</span>
          </span>
          <span class="settings-control settings-control--compact advanced-control--number">
            <span class="advanced-number-control">
              <input class="input" v-model.number="config.javinfo.supplement_worker_count" type="number" min="1" max="16" step="1" inputmode="numeric" />
              <span class="advanced-number-unit">任务</span>
              <span class="advanced-number-range">1-16</span>
            </span>
          </span>
        </label>
      </div>
    </section>
    <section class="advanced-settings-group export-settings-group" :aria-busy="exportingConfig" aria-live="polite">
        <div class="advanced-settings-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          <h2>配置备份</h2>
        </div>
        <div class="settings-list">
          <div class="settings-row settings-row--stacked">
            <div class="setting-copy">
              <span class="setting-title">导出前检查</span>
              <span class="setting-note">确认配置状态和备份文件处理方式。</span>
            </div>
            <div class="settings-control settings-control--wide">
              <div class="export-readiness-summary" aria-label="导出前检查">
                <div v-for="item in exportReadinessItems" :key="item.key" :class="['export-readiness-row', item.state]">
                  <span aria-hidden="true"></span>
                  <p>{{ item.label }}</p>
                </div>
              </div>
            </div>
          </div>
          <div class="settings-row settings-row--actions">
            <div class="setting-copy">
              <span class="setting-title">导出用户配置</span>
              <span class="setting-note">导出当前可见配置，敏感字段会自动脱敏。</span>
            </div>
            <div class="settings-control settings-control--wide export-action-control" :aria-busy="exportingConfig" aria-live="polite">
              <div class="export-action-buttons">
                <button class="btn btn-secondary" type="button" @click="exportUserConfig" :disabled="exportingConfig || !canSaveConfig" :aria-describedby="'config-export-note'">
                  {{ exportingConfig ? '导出中...' : '导出' }}
                </button>
              </div>
              <span id="config-export-note" class="export-action-note" :class="{ error: exportConfigStatusType === 'error' }" role="status">{{ exportActionNote }}</span>
            </div>
          </div>
        </div>
    </section>
    <section class="advanced-settings-group import-danger-zone">
        <div class="advanced-settings-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <h2>JavInfo 数据库导入</h2>
        </div>
        <div class="javinfo-import-panel" :aria-busy="javinfoImportUploading || isJavInfoImportActive(javinfoImportJob)" aria-live="polite">
          <div class="danger-summary">
            <strong>危险操作：全量替换</strong>
            <span>导入成功后会替换 JavInfoApi 当前 PostgreSQL 库。系统会自动使用临时库恢复并保留最近旧库。</span>
          </div>
          <div class="import-step-list">
            <section class="import-step">
              <div class="import-step-index" aria-hidden="true"></div>
              <div class="import-step-body">
                <div class="import-step-head">
                  <h3>连接目标数据库</h3>
                  <span class="import-step-state">必填</span>
                </div>
                <div class="settings-list">
                  <label class="settings-row">
                    <span class="setting-copy">
                      <span class="setting-title">数据库地址</span>
                      <span class="setting-note">PostgreSQL 主机名或容器服务名。</span>
                    </span>
                    <span class="settings-control">
                      <input class="input" v-model="config.javinfo.import_db.host" placeholder="postgres" />
                    </span>
                  </label>
                  <label class="settings-row">
                    <span class="setting-copy">
                      <span class="setting-title">端口</span>
                      <span class="setting-note">默认 PostgreSQL 端口为 5432。</span>
                    </span>
                    <span class="settings-control settings-control--compact advanced-control--number">
                      <span class="advanced-number-control">
                        <input class="input" v-model.number="config.javinfo.import_db.port" type="number" min="1" max="65535" step="1" inputmode="numeric" />
                        <span class="advanced-number-unit">端口</span>
                        <span class="advanced-number-range">1-65535</span>
                      </span>
                    </span>
                  </label>
                  <label class="settings-row">
                    <span class="setting-copy">
                      <span class="setting-title">目标库</span>
                      <span class="setting-note">导入完成后 JavInfoApi 使用的库。</span>
                    </span>
                    <span class="settings-control">
                      <input class="input" v-model="config.javinfo.import_db.database" placeholder="r18" />
                    </span>
                  </label>
                  <label class="settings-row">
                    <span class="setting-copy">
                      <span class="setting-title">维护库</span>
                      <span class="setting-note">用于建库、切换和恢复流程。</span>
                    </span>
                    <span class="settings-control">
                      <input class="input" v-model="config.javinfo.import_db.maintenance_database" placeholder="postgres" />
                    </span>
                  </label>
                  <label class="settings-row">
                    <span class="setting-copy">
                      <span class="setting-title">用户</span>
                      <span class="setting-note">需要恢复 dump 的数据库账号。</span>
                    </span>
                    <span class="settings-control">
                      <input class="input" v-model="config.javinfo.import_db.user" placeholder="javhub" />
                    </span>
                  </label>
                  <div class="settings-row">
                    <div class="setting-copy">
                      <span class="setting-title">密码</span>
                      <span class="setting-note">空白保存时不覆盖现有密码。</span>
                    </div>
                    <div class="settings-control">
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
                </div>
              </div>
            </section>
            <section class="import-step">
              <div class="import-step-index" aria-hidden="true"></div>
              <div class="import-step-body">
                <div class="import-step-head">
                  <h3>预检数据库</h3>
                  <span v-if="javinfoImportPreflight" class="import-status" :class="{ error: !javinfoImportPreflight.ok }">
                    {{ javinfoImportPreflight.ok ? '预检通过' : '预检未通过' }}
                  </span>
                </div>
                <span class="setting-note">导入前检查数据库连接与建库权限，确认能安全地创建临时库、切换和恢复。</span>
                <div class="import-actions import-actions--preflight" :aria-busy="javinfoImportPreflighting" aria-live="polite">
                  <div class="import-preflight-action-buttons">
                    <button class="btn btn-secondary" type="button" @click="preflightJavInfoImport" :disabled="javinfoImportPreflighting || !canSaveConfig" :aria-describedby="'javinfo-preflight-action-status'">
                      {{ javinfoImportPreflighting ? '检查中...' : '预检数据库' }}
                    </button>
                  </div>
                  <div class="import-preflight-action-copy">
                    <span id="javinfo-preflight-action-status" class="import-action-status" role="status">
                      {{ javinfoPreflightActionStatus }}
                    </span>
                  </div>
                </div>
              </div>
            </section>
            <section class="import-step">
              <div class="import-step-index" aria-hidden="true"></div>
              <div class="import-step-body">
                <div class="import-step-head">
                  <h3>选择 dump 文件</h3>
                  <span v-if="javinfoImportFile" class="import-step-state">{{ formatBytes(javinfoImportFile.size) }}</span>
                </div>
                <div class="settings-list">
                  <div class="settings-row settings-row--stacked import-file-row">
                    <div class="setting-copy">
                      <span class="setting-title">Dump 文件</span>
                      <span class="setting-note">支持 .dump / .backup / .sql / .sql.gz。</span>
                    </div>
                    <div class="settings-control settings-control--wide">
                      <div class="import-file-control" :class="{ 'is-selected': javinfoImportFile }" :aria-busy="javinfoImportFileInputDisabled" :aria-disabled="javinfoImportFileInputDisabled" @dragover.prevent @drop.prevent="onJavInfoImportFileDrop">
                        <div class="import-file-state">
                          <span class="import-file-state-dot" aria-hidden="true"></span>
                          <span id="javinfo-import-file-status" class="import-file-status" role="status">
                            {{ javinfoImportFileStatus }}
                          </span>
                        </div>
                        <button class="btn btn-secondary import-file-trigger" type="button" @click="openJavInfoImportFilePicker" :disabled="javinfoImportFileInputDisabled" aria-describedby="javinfo-import-file-status javinfo-import-file-note">
                          {{ javinfoImportFile ? '更换文件' : '选择文件' }}
                        </button>
                        <input ref="javinfoImportFileInput" class="import-file-native-input" type="file" accept=".dump,.backup,.sql,.gz" aria-hidden="true" tabindex="-1" @change="onJavInfoImportFileChange" :disabled="javinfoImportFileInputDisabled" aria-describedby="javinfo-import-file-status javinfo-import-file-note" />
                        <small id="javinfo-import-file-note" class="import-file-note">{{ javinfoImportFileNote }}</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
            <section class="import-step">
              <div class="import-step-index" aria-hidden="true"></div>
              <div class="import-step-body">
                <div class="import-step-head">
                  <h3>确认并执行</h3>
                  <span class="import-step-state">危险</span>
                </div>
                <label class="settings-row settings-row--toggle import-confirm-row">
                  <span class="setting-copy">
                    <span class="setting-title">确认全量替换</span>
                    <span class="setting-note">我确认这是全量替换导入，并已确认 dump 来源可信。</span>
                  </span>
                  <span class="settings-control settings-control--compact">
                      <span :class="['import-confirm-switch', { 'is-on': javinfoImportConfirm }]"><input type="checkbox" v-model="javinfoImportConfirm" role="switch" />
                        <span :class="['import-confirm-switch-track', { 'is-on': javinfoImportConfirm }]" aria-hidden="true"><span :class="['import-confirm-switch-thumb', { 'is-on': javinfoImportConfirm }]" aria-hidden="true"></span></span>
                      </span>
                  </span>
                </label>
                <div v-if="javinfoImportRequiresDirectConfirm" class="import-warning import-warning-direct">
                  <strong>无法使用临时库</strong>
                  <span>当前账号没有建库权限，将直接清空目标库恢复；失败不能自动回滚。</span>
                  <label class="settings-row settings-row--toggle import-confirm-row import-confirm-row--direct">
                    <span class="setting-copy">
                      <span class="setting-title">直接恢复目标库</span>
                      <span class="setting-note">我确认接受直接恢复目标库模式。</span>
                    </span>
                    <span class="settings-control settings-control--compact">
                        <span :class="['import-confirm-switch', { 'is-on': javinfoImportDirectConfirm }]"><input type="checkbox" v-model="javinfoImportDirectConfirm" role="switch" />
                          <span :class="['import-confirm-switch-track', { 'is-on': javinfoImportDirectConfirm }]" aria-hidden="true"><span :class="['import-confirm-switch-thumb', { 'is-on': javinfoImportDirectConfirm }]" aria-hidden="true"></span></span>
                        </span>
                    </span>
                  </label>
                </div>
                <div class="import-readiness-summary" aria-label="导入前检查">
                  <div v-for="item in javinfoImportReadinessItems" :key="item.key" :class="['readiness-row', item.state]">
                    <span aria-hidden="true"></span>
                    <p>{{ item.label }}</p>
                  </div>
                </div>
                <div v-if="javinfoImportJob" class="import-progress">
                  <div class="import-progress-head">
                    <span>{{ javinfoImportStatusLabel(javinfoImportJob) }}</span>
                    <strong>{{ javinfoImportProgress }}%</strong>
                  </div>
                  <div class="progress-bar" role="progressbar" aria-label="JavInfo 数据库导入进度" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="javinfoImportProgress">
                    <div class="progress-bar-fill" :style="{ transform: `scaleX(${javinfoImportProgress / 100})` }"></div>
                  </div>
                  <small v-if="javinfoImportJob.error" class="import-error">{{ javinfoImportJob.error }}</small>
                  <pre v-if="javinfoImportLogTail" class="import-log-tail">{{ javinfoImportLogTail }}</pre>
                </div>
                <div class="import-actions import-actions--danger" :aria-busy="javinfoImportDangerActionsBusy" aria-live="polite">
                  <div class="import-danger-action-buttons">
                    <button class="btn btn-danger" type="button" @click="startJavInfoImport" :disabled="!javinfoImportCanStart" aria-label="开始 JavInfo 全量替换导入" :aria-describedby="'javinfo-import-danger-action-status javinfo-import-start-note'">
                      {{ javinfoImportUploading ? '上传中...' : '开始导入' }}
                    </button>
                    <button v-if="javinfoImportJob && isJavInfoImportActive(javinfoImportJob)" class="btn btn-ghost" type="button" @click="cancelJavInfoImport">
                      取消任务
                    </button>
                  </div>
                  <div class="import-danger-action-copy">
                    <span id="javinfo-import-danger-action-status" class="import-danger-action-status" role="status">
                      {{ javinfoImportDangerActionStatus }}
                    </span>
                    <span id="javinfo-import-start-note" class="danger-action-note">{{ javinfoImportStartNote }}</span>
                  </div>
                </div>
              </div>
            </section>
            <section class="import-step">
              <div class="import-step-index" aria-hidden="true"></div>
              <div class="import-step-body">
                <div class="import-step-head">
                  <h3>重建索引与辅助表</h3>
                  <span v-if="javinfoMigrationStatus" class="import-status" :class="{ error: javinfoMigrationStatusType === 'error' }">
                    {{ javinfoMigrationStatus }}
                  </span>
                </div>
                <span class="setting-note">导入进来的 r18 只是原始目录数据。补全用的表、以及番号匹配 / 搜索 / 演员作品数等性能索引都靠这一步在其之上建立。上方导入完成后会自动执行；只有手动全量恢复的库，或发现相关查询变慢 / 报缺表时，才需要在此手动补跑。操作幂等，可安全重复。</span>
                <div class="import-actions import-actions--preflight" :aria-busy="javinfoMigrating" aria-live="polite">
                  <div class="import-preflight-action-buttons">
                    <button class="btn btn-secondary" type="button" @click="runJavInfoMigrations" :disabled="javinfoMigrating || !canSaveConfig" :aria-describedby="'javinfo-migration-action-status'">
                      {{ javinfoMigrating ? '重建中...' : '重建索引与辅助表' }}
                    </button>
                  </div>
                  <div class="import-preflight-action-copy">
                    <span id="javinfo-migration-action-status" class="import-action-status" role="status">
                      {{ javinfoMigrationActionStatus }}
                    </span>
                  </div>
                </div>
              </div>
            </section>
          </div>
          <div class="settings-list import-job-settings-list">
            <div class="settings-row settings-row--stacked import-job-summary-row">
              <div class="setting-copy">
                <span class="setting-title">最近任务</span>
                <span class="setting-note">保留最近 JavInfo 导入任务的执行状态。</span>
              </div>
              <div class="settings-control settings-control--wide import-job-control" :aria-busy="javinfoImportJobsLoading" aria-live="polite">
                <span id="javinfo-import-job-summary" class="import-action-status" role="status">
                  {{ javinfoImportJobSummary }}
                </span>
                <div class="import-job-state" :class="{ error: javinfoImportJobsError }">
                  <span class="import-job-state-dot" aria-hidden="true"></span>
                  <span>{{ javinfoImportJobsStateNote }}</span>
                  <button v-if="javinfoImportJobsError" class="btn btn-ghost import-job-retry" type="button" @click="listJavInfoImportJobs">
                    重试
                  </button>
                </div>
                <div v-if="javinfoImportJobs.length" class="import-job-items">
                  <div v-for="job in javinfoImportJobs" :key="job.id" class="import-job-row">
                    <span>
                      <strong>{{ job.filename || `任务 #${job.id}` }}</strong>
                      <small class="import-job-meta">{{ javinfoImportJobDetail(job) }}</small>
                    </span>
                    <strong>{{ javinfoImportStatusLabel(job) }}</strong>
                  </div>
                </div>
                <div v-else class="import-job-empty">
                  {{ javinfoImportJobEmptyNote }}
                </div>
              </div>
            </div>
          </div>
        </div>
    </section>
    <section class="advanced-settings-group ai-settings-group">
      <div class="advanced-settings-header">
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
      <div class="settings-list">
        <div class="settings-row">
          <div class="setting-copy">
            <span class="setting-title">接口类型</span>
            <span class="setting-note">{{ currentAiProviderHint }}</span>
          </div>
          <div class="settings-control settings-control--wide">
            <div class="segmented-mini wide ai-provider-control">
              <button
                v-for="option in aiProviderOptions"
                :key="option.value"
                type="button"
                :class="{ active: config.ai.provider === option.value }"
                @click="config.ai.provider = option.value"
              >{{ option.label }}</button>
            </div>
          </div>
        </div>
        <label class="settings-row">
          <span class="setting-copy">
            <span class="setting-title">{{ currentAiProviderLabel }} 接口地址</span>
            <span class="setting-note">连接公共或自托管智能模型 API。</span>
          </span>
          <span class="settings-control">
            <input class="input" v-model="currentAiConfig.base_url" :placeholder="currentAiProviderPlaceholder" />
          </span>
        </label>
        <label class="settings-row">
          <span class="setting-copy">
            <span class="setting-title">模型</span>
            <span class="setting-note">用于翻译兜底和演员映射判断。</span>
          </span>
          <span class="settings-control">
            <input class="input" v-model="currentAiConfig.model" :placeholder="currentAiModelPlaceholder" list="ai-model-options" />
            <datalist id="ai-model-options">
              <option v-for="model in aiModelOptions" :key="model.id" :value="model.id">{{ model.name || model.id }}</option>
            </datalist>
          </span>
        </label>
        <label class="settings-row" v-if="config.proxy.mode !== 'vless'">
          <span class="setting-copy">
            <span class="setting-title">超时（秒）</span>
            <span class="setting-note">模型调用最长等待时间。</span>
          </span>
          <span class="settings-control settings-control--compact advanced-control--number">
            <span class="advanced-number-control">
              <input class="input" v-model.number="currentAiConfig.timeout" type="number" min="1" step="1" inputmode="numeric" />
              <span class="advanced-number-unit">秒</span>
              <span class="advanced-number-range">>=1</span>
            </span>
          </span>
        </label>
        <div v-if="config.ai.provider !== 'ollama'" class="settings-row">
          <div class="setting-copy">
            <span class="setting-title">密钥</span>
            <span class="setting-note">空白保存时不覆盖现有密钥。</span>
          </div>
          <div class="settings-control">
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
          </div>
        </div>
        <div class="settings-row">
          <div class="setting-copy">
            <span class="setting-title">连接检查</span>
            <span class="setting-note">获取模型列表或发送一次测试调用。</span>
          </div>
          <div class="settings-control settings-control--wide ai-test-row" :aria-busy="aiConnectionBusy" aria-live="polite">
            <div class="ai-test-actions">
              <button
                class="btn btn-ghost"
                type="button"
                @click="loadAiModels"
                :disabled="aiLoadingModels || !canSaveConfig || !currentAiConfig.base_url"
                :aria-describedby="'ai-connection-status'"
              >
                {{ aiLoadingModels ? '获取中...' : '获取模型列表' }}
              </button>
              <button
                class="btn btn-secondary"
                type="button"
                @click="testAIModel"
                :disabled="aiTesting || !canSaveConfig || !currentAiConfig.base_url || !currentAiConfig.model"
                :aria-describedby="'ai-connection-status'"
              >
                {{ aiTesting ? '测试中...' : '测试模型调用' }}
              </button>
            </div>
            <span id="ai-connection-status" class="ai-connection-status" :class="{ error: aiTestType === 'error' }" role="status">
              {{ aiConnectionStatus }}
            </span>
          </div>
        </div>
      </div>
    </section>
    <section class="advanced-settings-group proxy-settings-group">
      <div class="advanced-settings-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
          <circle cx="12" cy="12" r="10"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
        </svg>
        <h2>网络代理</h2>
      </div>
      <div class="settings-list">
        <label class="settings-row settings-row--toggle" for="proxyEnabled">
          <span class="setting-copy">
            <span class="setting-title">启用代理</span>
            <span class="setting-note">影响后端向外部服务发起的网络请求。</span>
          </span>
          <span class="settings-control settings-control--compact">
            <input type="checkbox" id="proxyEnabled" v-model="config.proxy.enabled" role="switch" />
          </span>
        </label>
        <div class="settings-row" v-if="config.proxy.enabled">
          <span class="setting-copy"><span class="setting-title">代理类型</span><span class="setting-note">VLESS 模式由 JavHub 自动管理内置 sing-box 核心。</span></span>
          <span class="settings-control">
            <select class="input" v-model="config.proxy.mode"><option value="http">HTTP / HTTPS</option><option value="vless">VLESS / REALITY</option></select>
          </span>
        </div>
        <label class="settings-row" v-if="config.proxy.mode !== 'vless'">
          <span class="setting-copy"><span class="setting-title">HTTP 代理</span><span class="setting-note">用于普通 HTTP 请求。</span></span>
          <span class="settings-control">
            <input class="input" v-model="config.proxy.http_url" placeholder="http://127.0.0.1:7890" :disabled="!config.proxy.enabled" />
          </span>
        </label>
        <label class="settings-row" v-if="config.proxy.mode !== 'vless'">
          <span class="setting-copy"><span class="setting-title">HTTPS 代理</span><span class="setting-note">用于 HTTPS 外部请求。</span></span>
          <span class="settings-control">
            <input class="input" v-model="config.proxy.https_url" placeholder="https://127.0.0.1:7890" :disabled="!config.proxy.enabled" />
          </span>
        </label>
        <ManagedVlessSettings :proxy="config.proxy" />
      </div>
    </section>
  </div>
</template>
<script>
import api from '../../api'
import ManagedVlessSettings from './ManagedVlessSettings.vue'
import { requestConfirm } from '../../utils/confirmDialog'
import { AI_PROVIDER_OPTIONS } from './advancedConfigOptions.js'
import { aiConnectionComputed, javinfoImportJobComputed, javinfoImportJobDetail } from './advancedSettingsImportPresentation.js'
import { formatBytes, isJavInfoImportActive, javinfoImportProgress, javinfoImportStatusLabel } from '../../utils/javinfoImportPresentation.js'
export default {
  name: 'AdvancedSettingsPanel',
  components: { ManagedVlessSettings },
  props: { config: { type: Object, required: true }, canSaveConfig: { type: Boolean, default: false } },
  data() {
    return {
      exportingConfig: false,
      exportConfigStatus: '',
      exportConfigStatusType: 'info',
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
      javinfoImportJobsLoading: false,
      javinfoImportJobsError: '',
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
    ...aiConnectionComputed,
    aiConnectionStatus() {
      if (this.aiLoadingModels) return '正在获取模型列表。'
      if (this.aiTesting) return '正在发送模型测试调用。'
      if (this.aiTestMsg) return this.aiTestMsg
      if (!this.canSaveConfig) return '配置未加载成功，连接检查已暂停。'
      if (!this.currentAiConfig.base_url) return '填写接口地址后可检查连接。'
      if (!this.currentAiConfig.model) return '填写模型名称后可测试调用。'
      return '可获取模型列表或测试一次模型调用。'
    },
    exportReadinessItems() {
      return [
        { key: 'config', label: this.canSaveConfig ? '配置已加载' : '等待配置加载', state: this.canSaveConfig ? 'ready' : 'pending' },
        { key: 'redaction', label: '敏感字段会自动脱敏', state: 'ready' },
        { key: 'format', label: '将下载 YAML 备份文件', state: 'ready' },
      ]
    },
    exportActionNote() {
      if (this.exportingConfig) return '正在生成配置备份，请等待下载开始。'
      if (this.exportConfigStatus) return this.exportConfigStatus
      if (!this.canSaveConfig) return '配置未加载成功，导出已暂停。'
      return '准备就绪，导出后会下载到本机。'
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
    javinfoImportReadinessItems() {
      const preflight = this.javinfoImportPreflightCurrent()
      return [
        { key: 'file', label: this.javinfoImportFile ? `已选择 ${this.javinfoImportFile.name}` : '选择 dump 文件', state: this.javinfoImportFile ? 'ready' : 'pending' },
        { key: 'preflight', label: preflight?.ok ? '数据库预检通过' : '完成数据库预检', state: preflight?.ok ? 'ready' : 'pending' },
        { key: 'confirm', label: this.javinfoImportConfirm ? '已确认全量替换' : '确认全量替换风险', state: this.javinfoImportConfirm ? 'ready' : 'pending' },
        {
          key: 'direct',
          label: this.javinfoImportRequiresDirectConfirm
            ? (this.javinfoImportDirectConfirm ? '已确认直接恢复模式' : '确认直接恢复模式')
            : '可使用临时库恢复',
          state: this.javinfoImportRequiresDirectConfirm && !this.javinfoImportDirectConfirm ? 'pending' : 'ready',
        },
      ]
    },
    javinfoImportStartNote() {
      if (this.javinfoImportUploading) return 'Dump 正在上传，请等待任务进入恢复阶段。'
      if (this.isJavInfoImportActive(this.javinfoImportJob)) return '已有导入任务正在运行。'
      if (!this.canSaveConfig) return '配置未加载成功，导入已暂停。'
      if (!this.javinfoImportFile) return '先选择 dump 文件。'
      if (!this.javinfoImportPreflightCurrent()?.ok) return '先完成数据库预检。'
      if (!this.javinfoImportConfirm) return '需要确认全量替换风险。'
      if (this.javinfoImportRequiresDirectConfirm && !this.javinfoImportDirectConfirm) return '需要确认直接恢复模式。'
      return '准备就绪，开始后会创建导入任务。'
    },
    javinfoImportDangerActionsBusy() {
      return Boolean(this.javinfoImportUploading || this.isJavInfoImportActive(this.javinfoImportJob))
    },
    javinfoImportDangerActionStatus() {
      if (this.javinfoImportUploading) return '正在上传 dump 并创建恢复任务。'
      if (this.isJavInfoImportActive(this.javinfoImportJob)) return '导入任务正在执行，可在必要时取消。'
      if (this.javinfoImportCanStart) return '导入条件已满足。'
      return '导入暂不可开始。'
    },
    javinfoImportFileInputDisabled() {
      return Boolean(this.javinfoImportUploading || this.isJavInfoImportActive(this.javinfoImportJob))
    },
    javinfoImportFileStatus() {
      if (this.javinfoImportUploading) {
        return this.javinfoImportFile ? `正在上传 ${this.javinfoImportFile.name}` : '正在上传 dump 文件'
      }
      if (this.isJavInfoImportActive(this.javinfoImportJob)) return '导入任务正在运行，文件选择已锁定'
      if (this.javinfoImportFile) return `${this.javinfoImportFile.name} · ${this.formatBytes(this.javinfoImportFile.size)}`
      return '未选择 dump 文件'
    },
    javinfoImportFileNote() {
      if (this.javinfoImportFileInputDisabled) return '导入运行期间不能更换 dump 文件。'
      if (this.javinfoImportFile) return '更换文件会清除当前预检结果。'
      return '拖入文件或从本机选择。'
    },
    javinfoPreflightActionStatus() {
      if (this.javinfoImportPreflighting) return '正在检查数据库连接和恢复权限。'
      if (this.javinfoImportPreflightCurrent()?.ok) return '数据库预检已通过。'
      return '先运行预检，确认数据库可以安全恢复。'
    },
    javinfoMigrationActionStatus() {
      if (this.javinfoMigrating) return '正在重建索引与辅助表。'
      if (this.javinfoMigrationStatus) return this.javinfoMigrationStatus
      return '导入完成后会自动重建；此处用于手动补跑。'
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
    ...javinfoImportJobComputed,
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
      this.exportConfigStatus = ''
      this.exportConfigStatusType = 'info'
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
        this.exportConfigStatus = `已导出 ${link.download}`
        this.exportConfigStatusType = 'success'
        this.$message.success('配置已导出')
      } catch (e) {
        console.error('Failed to export config:', e)
        this.exportConfigStatus = e.response?.data?.detail || '导出失败'
        this.exportConfigStatusType = 'error'
        this.$message.error(this.exportConfigStatus)
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
    openJavInfoImportFilePicker() {
      if (this.javinfoImportFileInputDisabled) return
      this.$refs.javinfoImportFileInput?.click()
    },
    onJavInfoImportFileChange(event) {
      if (this.javinfoImportFileInputDisabled) {
        if (event?.target) event.target.value = ''
        return
      }
      this.setJavInfoImportFile(event?.target?.files?.[0] || null)
    },
    onJavInfoImportFileDrop(event) {
      if (this.javinfoImportFileInputDisabled) return
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
    javinfoImportJobDetail(job) {
      return javinfoImportJobDetail(job, this.formatBytes)
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
        this.$message.error('配置未加载成功，已阻止重建')
        return
      }
      const confirmed = await requestConfirm({
        title: '重建索引与辅助表',
        message: '确认在当前导入的目录上重建 JavHub 需要的辅助表与索引？',
        details: '导入进来的 r18 只是原始目录数据。补全用的表、以及番号匹配 / 搜索 / 演员作品数等性能索引都靠这一步在其之上建立——通过导入功能导入时会自动执行。若你是手动全量恢复的库，或发现相关查询变慢 / 报缺表，可用此按钮手动补跑。操作幂等，可安全重复。',
        confirmText: '重建',
      })
      if (!confirmed) return
      this.javinfoMigrating = true
      this.javinfoMigrationStatus = ''
      this.javinfoMigrationStatusType = 'info'
      try {
        const resp = await api.runJavInfoMigrations(false)
        this.javinfoMigrationStatus = resp.data?.ok ? '索引与辅助表已重建' : '重建已返回'
        this.javinfoMigrationStatusType = 'success'
        this.$message.success('索引与辅助表已重建')
      } catch (e) {
        const message = e.response?.data?.detail || e.message || '重建失败'
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
      this.javinfoImportJobsLoading = true
      this.javinfoImportJobsError = ''
      try {
        const resp = await api.listJavInfoImportJobs(5)
        this.javinfoImportJobs = resp.data?.data || []
      } catch (e) {
        this.javinfoImportJobs = []
        this.javinfoImportJobsError = e.response?.data?.detail || '最近任务读取失败'
      } finally {
        this.javinfoImportJobsLoading = false
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
</script><style scoped src="./advancedSettingsPanel.css"></style>
<style scoped src="./advancedSettingsAi.css"></style><style scoped src="./advancedSettingsPanelResponsive.css"></style>
