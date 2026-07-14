import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { Window } from 'happy-dom'
import { compileScript, compileTemplate, parse, rewriteDefault } from '@vue/compiler-sfc'
import { createSourceDraft, validateSourceDraft } from './sourcePresentation.js'

const componentUrl = new URL('./IndexerSourcePanel.vue', import.meta.url)
const source = readFileSync(componentUrl, 'utf8')
const baseVueUrl = await import.meta.resolve('vue')

function installDom(t) {
  const window = new Window({ url: 'http://localhost:5174/downloads?tab=indexer' })
  const previous = {}
  for (const key of ['CustomEvent', 'document', 'Document', 'Element', 'Event', 'HTMLElement', 'Node', 'ShadowRoot', 'SVGElement', 'window']) {
    previous[key] = globalThis[key]
    globalThis[key] = key === 'window' ? window : window[key]
  }
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
    window.close()
  })
}

async function importPanel(vueUrl) {
  const { descriptor } = parse(source, { filename: componentUrl.pathname })
  const id = createHash('sha1').update(componentUrl.href).digest('hex').slice(0, 8)
  const script = compileScript(descriptor, { id })
  const template = compileTemplate({
    id,
    filename: componentUrl.pathname,
    source: descriptor.template.content,
    compilerOptions: { bindingMetadata: script.bindings },
  })
  assert.equal(template.errors.length, 0, template.errors.join('\n'))

  const scriptCode = rewriteDefault(script.content, 'script')
    .replace("from './sourcePresentation'", `from '${new URL('./sourcePresentation.js', import.meta.url).href}'`)
    .replace("from './avdbPresentation'", `from '${new URL('./avdbPresentation.js', import.meta.url).href}'`)
  const code = [
    scriptCode,
    template.code.replace(/from "vue"/g, `from '${vueUrl}'`),
    'script.render = render',
    'export default script',
  ].join('\n')
  return (await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)).default
}

async function mountPanel(t, overrides = {}) {
  installDom(t)
  const vueUrl = `${baseVueUrl}?indexer-panel-${Date.now()}-${Math.random()}`
  const { createApp, nextTick } = await import(vueUrl)
  const Panel = await importPanel(vueUrl)
  const events = []
  const props = {
    snapshot: {
      builtins: [{ id: 'm3u8', type: 'm3u8', name: '在线 M3U8', enabled: true, available: true }],
      sources: [],
      types: ['torznab', 'avdb'],
    },
    editor: { open: false, mode: 'new', draft: createSourceDraft() },
    onCreate: () => events.push({ type: 'create' }),
    onEdit: value => events.push({ type: 'edit', value }),
    onToggle: value => events.push({ type: 'toggle', value }),
    onRemove: value => events.push({ type: 'remove', value }),
    onSaveEditor: value => events.push({ type: 'save-editor', value }),
    onCloseEditor: () => events.push({ type: 'close-editor' }),
    onViewAvdbJob: () => events.push({ type: 'view-avdb-job' }),
    ...overrides,
  }
  const host = document.createElement('div')
  document.body.appendChild(host)
  const app = createApp(Panel, props)
  app.mount(host)
  t.after(() => app.unmount())
  await nextTick()
  return { events, host, nextTick, props }
}

test('source panel exposes the persisted-management component contract', () => {
  assert.match(source, /name:\s*'IndexerSourcePanel'/)
  assert.match(source, /snapshot:\s*\{\s*type:\s*Object,\s*required:\s*true\s*\}/)
  assert.match(source, /loading:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /busySourceId:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(source, /editor:\s*\{\s*type:\s*Object,\s*required:\s*true\s*\}/)
  assert.match(source, /editorError:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(source, /avdbStatus:\s*\{\s*type:\s*Object,\s*default:\s*\(\)\s*=>\s*\(\{\}\)\s*\}/)
  for (const event of ['refresh', 'create', 'edit', 'toggle', 'remove', 'save-editor', 'close-editor', 'view-avdb-job']) {
    assert.match(source, new RegExp(`['"]${event}['"]`), `missing ${event} event`)
  }
})

test('source panel keeps HLS built in and renders only persisted sources', () => {
  assert.match(source, /v-for="builtin in snapshot\.builtins"/)
  assert.match(source, /在线 M3U8/)
  assert.match(source, /v-for="item in snapshot\.sources"/)
  assert.doesNotMatch(source, /selectedSource/)
  assert.doesNotMatch(source, /class="source-detail"/)
  assert.doesNotMatch(source, /saveTorznab|setup-avdb|save-avdb/)
})

test('toolbar describes automatic selection and summarizes enabled and total sources', () => {
  assert.match(source, /<strong>下载源<\/strong>/)
  assert.match(source, /默认自动优选/)
  assert.match(source, /enabledSourceCount/)
  assert.match(source, /totalSourceCount/)
  assert.match(source, /title="刷新下载源" aria-label="刷新下载源"/)
  assert.match(source, /title="新增下载源" aria-label="新增下载源"/)
  assert.doesNotMatch(source, /\$emit\('save'\)/)
})

test('source rows expose provider, host, state and guarded accessible actions', () => {
  assert.match(source, /sourceTypeMark\(item\)/)
  assert.match(source, /sourceTypeLabel\(item\)/)
  assert.match(source, /sourceHost\(item\)/)
  assert.match(source, /busySourceId === item\.id/)
  assert.match(source, /\$emit\('edit', item\)/)
  assert.match(source, /\$emit\('toggle', item\)/)
  assert.match(source, /\$emit\('remove', item\)/)

  const iconButtons = [...source.matchAll(/<button\b[\s\S]*?>/g)]
    .map(match => match[0])
    .filter(tag => /source-icon-action|source-dialog-close/.test(tag))
  assert.ok(iconButtons.length >= 6)
  for (const tag of iconButtons) {
    assert.match(tag, /(?:^|\s):?title=/, `icon button needs title: ${tag}`)
    assert.match(tag, /(?:^|\s):?aria-label=/, `icon button needs aria-label: ${tag}`)
  }
})

test('source editor saves before a row can be added', () => {
  assert.match(source, /editor\.open/)
  assert.match(source, /downloader-sheet-overlay/)
  assert.match(source, /editor\.mode === 'new' \? '新增下载源' : '编辑下载源'/)
  assert.match(source, /editor\.mode === 'new' \? '保存并添加' : '保存更改'/)
  assert.match(source, /\$emit\('save-editor', \{ \.\.\.editor\.draft \}\)/)
  assert.match(source, /editorError/)
  assert.match(source, /\$emit\('close-editor'\)/)
})

test('AVDB is singleton and first add explains synchronization without navigating early', () => {
  assert.match(source, /AVDB 公开库/)
  assert.match(source, /添加并前往首次同步/)
  assert.match(source, /添加来源/)
  assert.match(source, /avdbAlreadyAdded/)
  assert.match(source, /\$emit\('view-avdb-job'\)/)
  assert.match(source, /avdbState\(/)
  for (const copy of ['数据版本', '索引记录', '来源计数', '上次同步']) assert.match(source, new RegExp(copy))
  assert.match(source, /lastError/)

  const submitMethod = source.match(/submitEditor\(\)\s*\{[\s\S]*?\n\s*\},\n\s*\}/)?.[0] || ''
  assert.match(submitMethod, /validateSourceDraft/)
  assert.match(submitMethod, /save-editor/)
  assert.doesNotMatch(submitMethod, /view-avdb-job/)
})

test('source draft validation rejects every constrained field and permits configured edit keys', () => {
  assert.deepEqual(validateSourceDraft(createSourceDraft()), {
    name: '请输入来源名称',
    base_url: '请输入有效的 HTTP(S) URL',
    api_key: '请输入 API Key',
  })

  const invalid = validateSourceDraft({
    ...createSourceDraft(),
    name: '家庭索引',
    base_url: 'ftp://indexer.test',
    api_key: 'secret',
    limit: 101,
    timeout: 0,
  })
  assert.deepEqual(Object.keys(invalid).sort(), ['base_url', 'limit', 'timeout'])

  assert.deepEqual(validateSourceDraft({
    ...createSourceDraft(),
    id: 'source-prowlarr',
    name: '家庭索引',
    base_url: 'https://indexer.test',
    api_key_configured: true,
  }), {})
  assert.deepEqual(validateSourceDraft(createSourceDraft('avdb')), {})
})

test('invalid editor submission renders field errors, keeps the draft, and emits nothing', async (t) => {
  const draft = createSourceDraft()
  const editor = { open: true, mode: 'new', draft }
  const { events, host, nextTick } = await mountPanel(t, { editor })
  const submit = host.querySelector('.source-editor-submit')
  assert.ok(submit)
  submit.click()
  await nextTick()

  assert.equal(events.some(event => event.type === 'save-editor'), false)
  assert.equal(editor.draft, draft)
  assert.match(host.textContent, /请输入来源名称/)
  assert.match(host.textContent, /请输入有效的 HTTP\(S\) URL/)
  assert.match(host.textContent, /请输入 API Key/)
})

test('AVDB submit emits one cloned draft and leaves first-sync navigation to the parent', async (t) => {
  const draft = createSourceDraft('avdb')
  const editor = { open: true, mode: 'new', draft }
  const { events, host, nextTick } = await mountPanel(t, {
    editor,
    avdbStatus: { status: 'never', available: false },
  })
  assert.match(host.querySelector('.source-editor-submit')?.textContent || '', /添加并前往首次同步/)
  host.querySelector('.source-editor-submit').click()
  await nextTick()

  assert.deepEqual(events.filter(event => event.type === 'save-editor').map(event => event.value), [{
    id: '',
    type: 'avdb',
    enabled: false,
  }])
  assert.notEqual(events.find(event => event.type === 'save-editor').value, draft)
  assert.equal(events.some(event => event.type === 'view-avdb-job'), false)
})

test('type switching uses fresh drafts and removes stale fields', async (t) => {
  const draft = {
    ...createSourceDraft(),
    name: '待重置索引',
    base_url: 'https://stale.test',
    api_key: 'stale-secret',
  }
  const editor = { open: true, mode: 'new', draft }
  const { host, nextTick } = await mountPanel(t, { editor })

  host.querySelector('[data-source-type="avdb"]').click()
  await nextTick()
  assert.equal(editor.draft, draft)
  assert.deepEqual(editor.draft, createSourceDraft('avdb'))

  host.querySelector('[data-source-type="torznab"]').click()
  await nextTick()
  assert.deepEqual(editor.draft, createSourceDraft('torznab'))
})

test('AVDB singleton and busy states disable every affected action without mutation', async (t) => {
  const saved = {
    ...createSourceDraft(),
    id: 'source-home',
    name: '家庭索引',
    base_url: 'https://indexer.test',
    api_key_configured: true,
  }
  const avdb = { id: 'avdb', type: 'avdb', name: 'avdb', enabled: false, available: true, status: 'failed' }
  const snapshot = {
    builtins: [{ id: 'm3u8', type: 'm3u8', name: '在线 M3U8', enabled: true, available: true }],
    sources: [saved, avdb],
    types: ['torznab', 'avdb'],
  }
  const editor = { open: true, mode: 'new', draft: { ...saved, api_key: 'stale-secret' } }
  const { events, host, nextTick } = await mountPanel(t, {
    snapshot,
    editor,
    busySourceId: 'source-home',
    avdbStatus: { status: 'failed', available: true },
  })

  const avdbChoice = host.querySelector('[data-source-type="avdb"]')
  assert.ok(avdbChoice.disabled, 'existing AVDB disables the singleton editor choice')
  for (const button of host.querySelectorAll('[data-source-id="source-home"] .source-icon-action')) {
    assert.ok(button.disabled, 'busy row actions stay disabled')
  }
  assert.equal(host.querySelector('[data-source-id="avdb"] [data-action="view-job"]')?.disabled, false)

  const torznabToggle = host.querySelector('[data-source-id="source-home"] [data-action="toggle"]')
  torznabToggle.click()
  await nextTick()
  assert.equal(events.some(event => event.type === 'toggle'), false)
  assert.equal(snapshot.sources[0].enabled, true)
})
