<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>翻译源</h2>
      </div>
      <div class="panel-actions">
        <label class="mini-toggle">
          <input v-model="translationConfig.enabled" type="checkbox" />
          <span>启用翻译</span>
        </label>
        <button class="btn btn-primary btn-sm" type="button" :disabled="savingConfig" @click="$emit('save')">
          {{ savingConfig ? '保存中...' : '保存翻译源' }}
        </button>
      </div>
    </div>

    <div class="source-layout">
      <section class="source-section">
        <div class="source-section-head">
          <div>
            <strong>低成本批量源</strong>
            <span>用于标题、演员、题材、系列和厂商名。</span>
          </div>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>目标语言</span>
            <input v-model="translationConfig.target_language" class="input" placeholder="zh-CN" />
          </label>
          <label class="field">
            <span>实时模式</span>
            <input v-model="translationConfig.realtime_mode" class="input" disabled />
          </label>
          <label class="field">
            <span>批量并发</span>
            <input v-model.number="translationConfig.batch_concurrency" class="input" type="number" min="1" max="64" />
          </label>
          <label class="field">
            <span>单批行数</span>
            <input v-model.number="translationConfig.batch_size" class="input" type="number" min="1" max="200" />
          </label>
          <label class="field">
            <span>单批字符</span>
            <input v-model.number="translationConfig.batch_char_limit" class="input" type="number" min="500" max="24000" />
          </label>
          <label class="field">
            <span>源页大小</span>
            <input v-model.number="translationConfig.source_page_size" class="input" type="number" min="20" max="1000" />
          </label>
          <label class="field">
            <span>扫描页组</span>
            <input v-model.number="translationConfig.scan_pages_per_batch" class="input" type="number" min="1" max="64" />
          </label>
        </div>
        <div class="source-settings">
          <label class="check-row boxed">
            <input v-model="translationConfig.google_free.enabled" type="checkbox" />
            <span>Google 免费接口</span>
          </label>
          <input v-model="translationConfig.google_free.base_url" class="input" placeholder="https://translate.googleapis.com/translate_a/single" />
          <div class="form-grid">
            <label class="check-row boxed">
              <input v-model="translationConfig.baidu.enabled" type="checkbox" />
              <span>启用百度翻译</span>
            </label>
            <input v-model.number="translationConfig.baidu.timeout" class="input" type="number" min="1" placeholder="超时（秒）" />
            <input v-model.number="translationConfig.baidu.qps" class="input" type="number" min="0" step="0.5" placeholder="每秒请求数" />
          </div>
          <input v-model="translationConfig.baidu.app_id" class="input" placeholder="百度翻译 APP ID" autocomplete="off" />
          <input v-model="translationConfig.baidu.secret" class="input" :type="showBaiduSecret ? 'text' : 'password'" placeholder="百度翻译 Secret，空白保存不覆盖现有密钥" autocomplete="off" />
          <input v-model="translationConfig.baidu.endpoint" class="input" placeholder="https://fanyi-api.baidu.com/api/trans/vip/translate" />
          <div class="form-grid">
            <label class="check-row boxed">
              <input v-model="translationConfig.deepl.enabled" type="checkbox" />
              <span>启用 DeepL</span>
            </label>
            <label class="check-row boxed">
              <input v-model="translationConfig.deepl.free_api" type="checkbox" />
              <span>免费接口</span>
            </label>
          </div>
          <input v-model="translationConfig.deepl.api_key" class="input" :type="showDeeplKey ? 'text' : 'password'" placeholder="DeepL 密钥，可选" autocomplete="off" />
          <div class="form-grid">
            <label class="check-row boxed">
              <input v-model="translationConfig.microsoft.enabled" type="checkbox" />
              <span>启用 Microsoft</span>
            </label>
            <input v-model="translationConfig.microsoft.region" class="input" placeholder="Azure 区域，例如 eastasia" />
          </div>
          <input v-model="translationConfig.microsoft.api_key" class="input" :type="showMicrosoftKey ? 'text' : 'password'" placeholder="Microsoft 密钥，可选" autocomplete="off" />
        </div>
        <div class="key-actions left">
          <button class="btn btn-ghost btn-sm" type="button" @click="showBaiduSecret = !showBaiduSecret">{{ showBaiduSecret ? '隐藏百度 Secret' : '显示百度 Secret' }}</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="showDeeplKey = !showDeeplKey">{{ showDeeplKey ? '隐藏 DeepL 密钥' : '显示 DeepL 密钥' }}</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="showMicrosoftKey = !showMicrosoftKey">{{ showMicrosoftKey ? '隐藏 Microsoft 密钥' : '显示 Microsoft 密钥' }}</button>
        </div>
      </section>

      <section class="source-section">
        <div class="source-section-head">
          <div>
            <strong>实时兜底</strong>
            <span>公共智能翻译参数在设置页维护，这里只用于状态检测和手动测试。</span>
          </div>
          <span class="provider-status">{{ aiProviderStatusLabel }}</span>
        </div>
        <div class="source-settings">
          <textarea v-model="translationTestText" class="input test-textarea" rows="3" placeholder="输入一小段文本测试实时翻译"></textarea>
          <div class="key-actions left">
            <button class="btn btn-primary btn-sm" type="button" :disabled="testingTranslation || !translationTestText.trim()" @click="testTranslation">
              {{ testingTranslation ? '测试中...' : '测试实时翻译' }}
            </button>
          </div>
          <div v-if="translationTestMsg" class="message-line" :class="translationTestType">{{ translationTestMsg }}</div>
        </div>
      </section>
    </div>
  </section>
</template>

<script>
import api from '../../api'

export default {
  name: 'TranslationSourcesPanel',
  props: {
    translationConfig: { type: Object, required: true },
    savingConfig: { type: Boolean, default: false },
    selectedProvider: { type: String, default: '' },
    aiProviderStatusLabel: { type: String, default: '未检测' },
  },
  emits: ['save'],
  data() {
    return {
      showBaiduSecret: false,
      showDeeplKey: false,
      showMicrosoftKey: false,
      testingTranslation: false,
      translationTestText: 'これは翻訳テストです。',
      translationTestMsg: '',
      translationTestType: 'info',
    }
  },
  methods: {
    async testTranslation() {
      this.testingTranslation = true
      this.translationTestMsg = ''
      this.translationTestType = 'info'
      try {
        const resp = await api.testTranslation(this.translationTestText.trim(), this.selectedProvider)
        const translated = resp.data?.translated_text || ''
        this.translationTestMsg = translated ? `译文：${translated}` : '测试完成，但没有返回译文'
        this.translationTestType = translated ? 'success' : 'error'
      } catch (error) {
        console.error('Failed to test translation:', error)
        this.translationTestMsg = error.response?.data?.detail || '实时翻译测试失败，请检查兜底配置'
        this.translationTestType = 'error'
      } finally {
        this.testingTranslation = false
      }
    },
  },
}
</script>

<style scoped src="./translationPanelControls.css"></style>
<style scoped src="./translationSourcesPanel.css"></style>
