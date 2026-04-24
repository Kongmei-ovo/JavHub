// 全局显示语言配置：'ja' = 日文优先 | 'en' = 英文优先 | 'zh' = 中文优先（翻译字段）
// 模块级响应式，所有引用者共享同一个实例
import { ref, watch } from 'vue'

const DISPLAY_LANG_KEY = 'javhub_display_lang'

function createDisplayLang() {
  const stored = localStorage.getItem(DISPLAY_LANG_KEY)
  const lang = ref(stored === 'en' ? 'en' : (stored === 'zh' ? 'zh' : 'ja')) // 默认日文

  watch(lang, (val) => {
    localStorage.setItem(DISPLAY_LANG_KEY, val)
  })

  return lang
}

export const displayLang = createDisplayLang()

/**
 * 根据全局语言设置，返回合适的名字字段
 * @param {object} item - 含有 name_ja/name_en 或 name_kanji/name_romaji 的对象
 * @param {string} jaField - 日文字段名，如 'name_ja' 或 'name_kanji'
 * @param {string} enField - 英文字段名，如 'name_en' 或 'name_romaji'
 */
export function displayName(item, jaField = 'name_ja', enField = 'name_en') {
  if (!item) return ''
  const ja = item[jaField]
  const en = item[enField]
  // zh 模式优先取翻译字段
  if (displayLang.value === 'zh') {
    const jaTrans = item[`${jaField}_translated`]
    const enTrans = item[`${enField}_translated`]
    return jaTrans || enTrans || ja || en || ''
  }
  return displayLang.value === 'en' ? (en || ja || '') : (ja || en || '')
}

/**
 * 返回翻译后的显示名称。
 * 有译文时格式："译文(原文)"，原文小字体。
 * 无译文时直接返回原文。
 * @param {object} item - 含字段的对象
 * @param {string} jaField - 日文原文字段名
 * @param {string} enField - 英文原文字段名
 * @param {string} jaTranslatedField - 日文译文字段名（可选）
 * @param {string} enTranslatedField - 英文译文字段名（可选）
 */
export function translatedName(item, jaField = 'name_ja', enField = 'name_en',
                               jaTranslatedField = null, enTranslatedField = null) {
  if (!item) return ''
  const ja = item[jaField] || ''
  const en = item[enField] || ''
  const jaTrans = jaTranslatedField ? (item[jaTranslatedField] || '') : ''
  const enTrans = enTranslatedField ? (item[enTranslatedField] || '') : ''

  let useTrans, useOrig
  if (displayLang.value === 'zh') {
    useTrans = jaTrans
    useOrig = ja
  } else {
    useTrans = displayLang.value === 'en' ? enTrans : jaTrans
    useOrig = displayLang.value === 'en' ? en : ja
  }

  if (useTrans && useTrans !== useOrig) {
    return { translated: useTrans, original: useOrig }
  }
  return { translated: useOrig, original: '' }
}
