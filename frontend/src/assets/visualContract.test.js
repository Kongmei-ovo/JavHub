import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'

const srcRoot = new URL('../', import.meta.url)
const tokenSourceNames = new Set([
  'src/assets/main.css',
  'src/assets/themes.js',
])

function productionUiFiles(dirUrl = srcRoot) {
  return readdirSync(dirUrl, { withFileTypes: true }).flatMap((entry) => {
    const entryUrl = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, dirUrl)
    if (entry.isDirectory()) return productionUiFiles(entryUrl)
    if (!/\.(css|vue|js)$/.test(entry.name) || /\.test\.js$/.test(entry.name)) return []
    return [entryUrl]
  })
}

function srcName(fileUrl) {
  return fileUrl.pathname.replace(/^.*\/frontend\/src\//, 'src/')
}

function lineFor(source, index) {
  return source.slice(0, index).split('\n').length
}

function wcLineCount(source) {
  return (source.match(/\n/g) ?? []).length
}

function collectMatches(files, pattern, { ignore = () => false } = {}) {
  const offenders = []

  for (const fileUrl of files) {
    const name = srcName(fileUrl)
    const source = readFileSync(fileUrl, 'utf8')
    for (const match of source.matchAll(pattern)) {
      if (ignore({ name, source, match })) continue
      offenders.push(`${name}:${lineFor(source, match.index)}:${match[0].trim()}`)
    }
  }

  return offenders
}

function customProperties(source) {
  const properties = new Map()
  for (const match of source.matchAll(/^\s*(--[\w-]+):\s*([^;]+);/gm)) {
    properties.set(match[1], match[2].trim())
  }
  return properties
}

function resolveCustomProperty(token, properties, depth = 0) {
  if (depth > 4) return ''
  const value = properties.get(token)
  if (!value) return ''
  const nested = value.match(/^var\((--[\w-]+)\)$/)
  if (!nested) return value
  return resolveCustomProperty(nested[1], properties, depth + 1) || value
}

function isGlassSurfaceToken(token) {
  if (/(?:border|divider|shadow|scrim|blackout|fallback|player-bg|lightbox-bg)$/.test(token)) return false
  return /(?:glass|material|content-material|operations-warning-material|vp-control-bg|subscription-(?:control|sheet|active|sticky)-bg)/.test(token)
}

function hasLayeredGlass(value) {
  return /var\(--surface-specular-edge(?:-strong)?\)\s*,\s*var\(--surface-noise\)\s*,/.test(value)
}

test('production UI styles keep raw colors centralized in theme tokens', () => {
  const rawColor = /#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)/g
  const offenders = collectMatches(productionUiFiles(), rawColor, {
    ignore: ({ name, source, match }) => {
      if (tokenSourceNames.has(name)) return true
      // 颜色函数的色相来自 token(如 rgba(var(--accent-rgb), 0.16) 这类 v2 语义 tint)
      // —— 色相已集中,只有 alpha 是字面量,不算裸色,放行。
      if (match[0].includes('var(')) return true
      // 动态计算色(模板字面量插值,如 HSL-from-id 头像)无法固化成静态 token —— 放行;
      // 静态裸色(行内无 ${ 插值)仍然必须集中到主题 token。
      const lineStart = source.lastIndexOf('\n', match.index) + 1
      const lineEnd = source.indexOf('\n', match.index)
      const line = source.slice(lineStart, lineEnd === -1 ? source.length : lineEnd)
      return line.includes('${')
    },
  })

  // 历史 token 债基线:ratchet 锁当前裸色数量、挡新增;存量裸色待专门视觉精修轮迁成主题 token。
  assert.equal(offenders.length, 25, offenders.join('\n'))
})

test('glass and material backgrounds stay visibly layered', () => {
  const offenders = []

  for (const fileUrl of productionUiFiles()) {
    const name = srcName(fileUrl)
    if (tokenSourceNames.has(name)) continue
    const source = readFileSync(fileUrl, 'utf8')
    const properties = customProperties(source)

    for (const match of source.matchAll(/^\s*background:\s*var\((--[\w-]+)\)\s*;\s*$/gm)) {
      const token = match[1]
      if (!isGlassSurfaceToken(token)) continue
      const resolved = resolveCustomProperty(token, properties)
      if (hasLayeredGlass(resolved)) continue
      offenders.push(`${name}:${lineFor(source, match.index)}:${match[0].trim()}`)
    }
  }

  // 未分层玻璃债已清零；锁为零，避免后续回退到单层材质。
  assert.equal(offenders.length, 0, offenders.join('\n'))
})

test('production source files stay reviewable below the large-file line', () => {
  const maxLines = 900
  const existingLargeFileCaps = new Map([
    ['src/App.vue', 1320],
    ['src/assets/main.css', 1296],
    ['src/features/config/AdvancedSettingsPanel.vue', 938],
    ['src/features/config/advancedSettingsPanel.css', 939],
    ['src/features/config/config.css', 1158],
    ['src/features/search/search.css', 1191],
    ['src/features/candidates/downloadCandidatePanel.css', 1100],
    ['src/features/supplement/supplementManagement.css', 1209],
    ['src/features/translations/translationJobs.css', 1159],
    ['src/views/Config.vue', 1227],
    ['src/views/TranslationJobs.vue', 1092],
  ])
  const offenders = productionUiFiles()
    .map((fileUrl) => {
      const source = readFileSync(fileUrl, 'utf8')
      return [srcName(fileUrl), wcLineCount(source)]
    })
    .filter(([name, lines]) => lines > (existingLargeFileCaps.get(name) ?? maxLines))
    .map(([name, lines]) => `${name}:${lines}`)

  assert.deepEqual(offenders, [])
})

test('visual contract tests cover the requested style regressions', () => {
  const requiredTests = new Map([
    ['raw colors', /raw colors centralized/],
    ['layered glass', /glass and material backgrounds stay visibly layered/],
    ['transition-all', /transition-all repaint traps/],
    ['large files', /large-file line/],
    ['negative letter spacing', /negative letter spacing/],
    ['horizontal overflow', /viewport horizontal overflow/],
  ])
  const testSources = [
    new URL('./visualContract.test.js', import.meta.url),
    new URL('./typography.test.js', import.meta.url),
    new URL('./horizontalOverflow.test.js', import.meta.url),
  ].map((fileUrl) => readFileSync(fileUrl, 'utf8')).join('\n')

  for (const [label, pattern] of requiredTests) {
    assert.match(testSources, pattern, `${label} should have a source-level regression test`)
  }
})
