import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { Window } from 'happy-dom'
import { compileScript, compileTemplate, parse, rewriteDefault } from '@vue/compiler-sfc'
import { installAxiosAdapter } from '../testSupport/axiosAdapter.js'

const vueSource = readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/inventory/inventory.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`
const baseVueUrl = await import.meta.resolve('vue')
const axiosUrl = await import.meta.resolve('axios')

class MockEventSource {
  static instances = []

  constructor(url) {
    this.url = url
    this.listeners = new Map()
    this.closeCalled = false
    MockEventSource.instances.push(this)
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || []
    listeners.push(listener)
    this.listeners.set(type, listeners)
  }

  removeEventListener(type, listener) {
    const listeners = this.listeners.get(type) || []
    this.listeners.set(type, listeners.filter(item => item !== listener))
  }

  emit(type, event) {
    if (type === 'message' && typeof this.onmessage === 'function') this.onmessage(event)
    if (type === 'error' && typeof this.onerror === 'function') this.onerror(event)
    for (const listener of this.listeners.get(type) || []) listener(event)
  }

  pushJob(job) {
    this.emit('message', { data: JSON.stringify(job) })
  }

  close() {
    this.closeCalled = true
  }
}

function installDom(t) {
  const window = new Window({ url: 'http://localhost:5174/inventory' })
  const originals = {
    CustomEvent: globalThis.CustomEvent,
    document: globalThis.document,
    Element: globalThis.Element,
    Event: globalThis.Event,
    EventSource: globalThis.EventSource,
    HTMLElement: globalThis.HTMLElement,
    Node: globalThis.Node,
    SVGElement: globalThis.SVGElement,
    window: globalThis.window,
  }

  globalThis.window = window
  globalThis.document = window.document
  globalThis.CustomEvent = window.CustomEvent
  globalThis.Element = window.Element
  globalThis.Event = window.Event
  globalThis.EventSource = MockEventSource
  window.EventSource = MockEventSource
  globalThis.HTMLElement = window.HTMLElement
  globalThis.Node = window.Node
  globalThis.SVGElement = window.SVGElement
  MockEventSource.instances = []

  t.after(() => {
    Object.assign(globalThis, originals)
    window.close()
  })

  return window
}

async function waitFor(condition, label, { timeout = 1500, nextTick = async () => {} } = {}) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))
    if (condition()) return
  }
  assert.fail(label)
}

async function importInventoryComponent(vueUrl) {
  const filename = new URL('./Inventory.vue', import.meta.url)
  const { descriptor } = parse(vueSource, { filename: filename.pathname })
  const id = createHash('sha1').update(filename.href).digest('hex').slice(0, 8)
  const script = compileScript(descriptor, { id })
  const template = compileTemplate({
    id,
    filename: filename.pathname,
    source: descriptor.template.content,
    compilerOptions: { bindingMetadata: script.bindings },
  })
  const scriptCode = rewriteDefault(script.content, 'script')
    .replace(/from 'vue'/g, `from '${vueUrl}'`)
    .replace(/import \{ useRouter \} from 'vue-router'\n/, 'const useRouter = () => ({ push() {} })\n')
    .replace(/import axios from 'axios'/, `import axios from '${axiosUrl}'`)
    .replace(/import \{ ElMessage \} from '\.\.\/utils\/message\.js'\n/, 'const ElMessage = { error() {}, warning() {}, success() {} }\n')
    .replace(/import api from '\.\.\/api'\n/, 'const api = { getActorMappingSummary: async () => ({ data: {} }), getDownloadCandidateSummary: async () => ({ data: {} }) }\n')
    .replace(/import \{ requestConfirm \} from '\.\.\/utils\/confirmDialog'\n/, 'const requestConfirm = async () => true\n')
    .replace(/import GlassSelect from '\.\.\/components\/GlassSelect\.vue'\n/, 'const GlassSelect = { props: ["modelValue", "options"], template: "<select></select>" }\n')
    .replace(/import AppleSkeleton from '\.\.\/components\/AppleSkeleton\.vue'\n/, 'const AppleSkeleton = { template: "<div></div>" }\n')
    .replace(/import AppleEmptyState from '\.\.\/components\/AppleEmptyState\.vue'\n/, 'const AppleEmptyState = { emits: ["action", "secondary-action"], template: "<button @click=\\"$emit(\\\'action\\\')\\">empty</button>" }\n')
    .replace(/import AppleErrorState from '\.\.\/components\/AppleErrorState\.vue'\n/, 'const AppleErrorState = { emits: ["retry", "secondary-action"], template: "<button @click=\\"$emit(\\\'retry\\\')\\">error</button>" }\n')
  const code = [
    scriptCode,
    template.code.replace(/from "vue"/g, `from '${vueUrl}'`),
    'script.render = render',
    'export default script',
  ].join('\n')
  return (await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)).default
}

async function mountInventory(t) {
  installDom(t)
  const vueUrl = `${baseVueUrl}?inventory-${Date.now()}-${Math.random()}`
  const { createApp, nextTick } = await import(vueUrl)
  installAxiosAdapter(t, async (config) => {
    if (config.url === '/api/inventory/actors') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [], total: 0, total_pages: 1 } }
    }
    if (config.url === '/api/inventory/snapshots/latest') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { snapshot_key: 'snap-1' } }
    }
    if (config.url === '/api/inventory/jobs/trigger') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { job_id: 7 } }
    }
    if (config.url === '/api/inventory/jobs') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  })
  const Inventory = await importInventoryComponent(vueUrl)
  const host = document.createElement('div')
  document.body.appendChild(host)
  const app = createApp(Inventory)
  app.mount(host)
  t.after(() => app.unmount())
  return { app, host, nextTick }
}

function cssBlocks(content, selector) {
  const contentWithoutComments = content.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...contentWithoutComments.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} block should exist`)
  return blocks
}

function cssBlock(content, selector) {
  return cssBlocks(content, selector).join('\n')
}

function backgroundIncludes(block, token) {
  const match = block.match(/background:\s*([^;]+);/)
  return Boolean(match && match[1].includes(token))
}

function assertLayeredBackground(block, token, name) {
  assert.ok(backgroundIncludes(block, token), `${name} should include ${token}`)
  assert.match(block, /var\(--surface-specular-edge/, `${name} should include a specular edge layer`)
  assert.match(block, /var\(--surface-noise\)/, `${name} should include the shared noise layer`)
}

function assertSemanticBadgeGlass(block, token, borderToken, textToken, name) {
  assertLayeredBackground(block, token, name)
  assert.match(block, new RegExp(`border:\\s*1px solid var\\(${borderToken}\\)`), `${name} should use semantic border`)
  assert.match(block, new RegExp(`color:\\s*var\\(${textToken}\\)`), `${name} should use semantic text`)
  assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
  assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use shared control blur`)
}

test('inventory page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/inventory\/inventory\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 520, 'Inventory.vue should stay below 520 lines')
  assert.ok(externalStyle.split('\n').length > 450, 'external stylesheet should contain the moved inventory styles')
})

test('inventory listens to inventory SSE jobs and renders progress updates', async (t) => {
  const { nextTick } = await mountInventory(t)
  await waitFor(() => MockEventSource.instances.length === 1, 'Inventory should open one inventory EventSource', { nextTick })

  const stream = MockEventSource.instances[0]
  assert.equal(stream.url, '/api/v1/jobs/stream?kind=inventory')

  stream.pushJob({ id: 101, kind: 'inventory', label: 'collect inventory', status: 'running', progress: 42 })
  await waitFor(() => document.body.textContent.includes('42%'), 'Inventory should render running job progress', { nextTick })

  stream.pushJob({ id: 101, kind: 'inventory', label: 'collect inventory', status: 'completed', progress: 100 })
  await waitFor(() => document.body.textContent.includes('100%'), 'Inventory should render completed job progress', { nextTick })
})

test('inventory reconnects the SSE job stream after a disconnect', async (t) => {
  const { nextTick } = await mountInventory(t)
  await waitFor(() => MockEventSource.instances.length === 1, 'Inventory should open an inventory EventSource', { nextTick })

  MockEventSource.instances[0].emit('error', new Event('error'))
  assert.equal(MockEventSource.instances[0].closeCalled, true)

  await waitFor(() => MockEventSource.instances.length === 2, 'Inventory should reconnect after the 1s backoff', { timeout: 1300, nextTick })
  assert.equal(MockEventSource.instances[1].url, '/api/v1/jobs/stream?kind=inventory')
})

test('inventory controls use shared Apple glass materials', () => {
  assert.match(source, /class="progress-ring-bg"[\s\S]*stroke="var\(--glass-control-border\)"/)
  assert.match(source, /class="progress-ring-fill"[\s\S]*stroke="var\(--glass-active-border\)"/)
  assert.doesNotMatch(source, /stroke="var\(--border\)"/)
  assert.doesNotMatch(source, /stroke="var\(--accent\)"/)

  const searchBox = cssBlock(source, '.search-box')
  const searchFocus = cssBlock(source, '.search-box:focus-within')
  const searchClear = cssBlock(source, '.search-clear')
  const inlineLink = cssBlock(source, '.inline-link')
  const pageButton = cssBlock(source, '.page-btn')
  const pageButtonHover = cssBlock(source, '.page-btn:hover:not(:disabled)')
  const jumpInput = cssBlock(source, '.jump-input')
  const jumpButton = cssBlock(source, '.jump-btn')
  const jumpButtonHover = cssBlock(source, '.jump-btn:hover')
  const jobItem = cssBlock(source, '.job-item')
  const dialogOverlay = cssBlock(source, '.dialog-overlay')
  const jobsDialog = cssBlock(source, '.jobs-dialog')
  const dialogHeader = cssBlock(source, '.dialog-header')
  const closeButton = cssBlock(source, '.close-btn')

  const controlBlocks = [searchBox, searchClear, inlineLink, pageButton, jumpInput, jumpButton, jobItem, closeButton]
  for (const block of controlBlocks) {
    assertLayeredBackground(block, '--material-glass-control', 'inventory control')
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/)
  }
  assert.doesNotMatch(controlBlocks.join('\n'), /^.*background:\s*var\(--material-glass-control\);.*$/gm)

  assert.match(searchBox, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(searchFocus, /border-color:\s*var\(--glass-control-border-hover\)/)
  assertLayeredBackground(searchFocus, '--material-glass-control-hover', 'inventory focused search')
  assert.match(searchFocus, /box-shadow:\s*var\(--glass-active-shadow\)/)

  for (const block of [pageButtonHover, jumpButtonHover]) {
    assertLayeredBackground(block, '--material-glass-control-hover', 'inventory hovered control')
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)
  }
  assert.doesNotMatch([searchFocus, pageButtonHover, jumpButtonHover].join('\n'), /^.*background:\s*var\(--material-glass-control-hover\);.*$/gm)

  // v2 内容层去玻璃：对话框面板 = 实底
  assert.match(jobsDialog, /background:\s*var\(--card\)/, 'inventory jobs dialog should be solid --card')
  assert.match(jobsDialog, /border:\s*1px solid var\(--glass-edge\)/)
  assert.match(jobsDialog, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.doesNotMatch(jobsDialog, /backdrop-filter/)
  assert.match(dialogOverlay, /background:\s*var\(--surface-scrim\)/)
  assert.match(dialogOverlay, /z-index:\s*var\(--z-modal\)/)
  assert.match(dialogOverlay, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.doesNotMatch(dialogOverlay, /rgba\(0,\s*0,\s*0|z-index:\s*\d+/)
  assert.match(dialogHeader, /border-bottom:\s*1px solid var\(--glass-edge\)/)
  assert.doesNotMatch(dialogHeader, /var\(--border\)/)

  for (const block of [searchClear, inlineLink, closeButton]) {
    assert.doesNotMatch(block, /background:\s*(?:transparent|none)/)
    assert.doesNotMatch(block, /border:\s*(?:0|none|1px solid transparent)/)
  }
})

test('inventory actor cards and skeletons use shared Apple glass surfaces', () => {
  const actorCard = cssBlock(source, '.actor-card')
  const actorCardHover = cssBlock(source, '.actor-card:hover')
  const actorCover = cssBlock(source, '.actor-cover')
  const skeletonCover = cssBlock(source, '.skeleton-cover')
  const skeletonLine = cssBlock(source, '.skeleton-line')

  assertLayeredBackground(actorCard, '--material-glass-control', 'inventory actor card')
  assert.match(actorCard, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(actorCard, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(actorCard, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assertLayeredBackground(actorCardHover, '--material-glass-control-hover', 'inventory hovered actor card')
  assert.match(actorCardHover, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(actorCardHover, /box-shadow:\s*var\(--glass-control-shadow-hover\)/)

  assert.match(actorCover, /background:\s*var\(--card\)/, 'inventory actor cover should be solid --card')
  // WAVE-4 D3: hairline divider via inset box-shadow avoids double-borders.
  assert.match(actorCover, /(?:border-bottom:\s*1px solid var\(--glass-control-border\)|box-shadow:\s*inset 0 -1px 0 var\(--glass-control-border\))/)

  for (const block of [skeletonCover, skeletonLine]) {
    assert.match(block, /background:\s*var\(--card\)/, 'inventory skeleton should be solid --card')
    assert.match(block, /border:\s*1px solid var\(--hairline\)/)
    assert.doesNotMatch(block, /var\(--bg-card-hover\)|var\(--surface-card-hover\)|rgba\(255,\s*255,\s*255/)
  }
  assert.doesNotMatch([actorCard, actorCardHover, actorCover, skeletonCover, skeletonLine].join('\n'), /^.*background:\s*var\(--(?:material-glass-control|material-glass-control-hover|material-glass-subtle)\);.*$/gm)

  for (const block of [actorCard, actorCardHover, actorCover]) {
    assert.doesNotMatch(block, /var\(--bg-card\)|var\(--bg-secondary\)|var\(--shadow-card\)/)
  }
})

test('inventory semantic status surfaces use layered badge glass', () => {
  const snapshotInfo = cssBlock(source, '.snapshot-info')
  const snapshotWarn = cssBlock(source, '.snapshot-warn')
  const missingBadge = cssBlock(source, '.missing-badge')

  assertSemanticBadgeGlass(snapshotInfo, '--badge-success-bg', '--badge-success-border', '--badge-success-text', 'inventory snapshot success')
  assertSemanticBadgeGlass(snapshotWarn, '--badge-warning-bg', '--badge-warning-border', '--badge-warning-text', 'inventory snapshot warning')
  assertSemanticBadgeGlass(missingBadge, '--badge-error-bg', '--badge-error-border', '--badge-error-text', 'inventory missing count badge')
  assert.doesNotMatch(`${snapshotInfo}\n${snapshotWarn}\n${missingBadge}`, /#fff|#ffffff|rgba\(255,\s*255,\s*255/i)
})

test('inventory interactive controls expose Apple glass keyboard focus states', () => {
  assert.match(vueSource, /class="actor-card"[\s\S]*role="button"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*tabindex="0"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*@keydown\.enter\.prevent="openActor\(actor\)"/)
  assert.match(vueSource, /class="actor-card"[\s\S]*@keydown\.space\.prevent="openActor\(actor\)"/)

  const actorFocus = cssBlock(source, '.actor-card:focus-visible')
  const pageButtonFocus = cssBlock(source, '.page-btn:focus-visible:not(:disabled)')
  const jumpButtonFocus = cssBlock(source, '.jump-btn:focus-visible')
  const searchClearFocus = cssBlock(source, '.search-clear:focus-visible')
  const inlineLinkFocus = cssBlock(source, '.inline-link:focus-visible')
  const closeButtonFocus = cssBlock(source, '.close-btn:focus-visible')

  for (const [block, label] of [
    [actorFocus, 'inventory actor card focus'],
    [pageButtonFocus, 'inventory page button focus'],
    [jumpButtonFocus, 'inventory jump button focus'],
    [searchClearFocus, 'inventory search clear focus'],
    [inlineLinkFocus, 'inventory inline link focus'],
    [closeButtonFocus, 'inventory close button focus'],
  ]) {
    assert.match(block, /outline:\s*none/, `${label} should replace the default outline`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${label} should use hover border`)
    assertLayeredBackground(block, '--material-glass-control-hover', label)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\),\s*var\(--focus-ring\)/, `${label} should expose a subtle focus ring`)
  }

  assert.match(actorFocus, /transform:\s*translateY\(-2px\)/)
  assert.match(pageButtonFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(jumpButtonFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(searchClearFocus, /transform:\s*translateY\(-1px\)/)
  assert.match(closeButtonFocus, /transform:\s*rotate\(90deg\)/)
})
