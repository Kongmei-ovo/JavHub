import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { Window } from 'happy-dom'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { installAxiosAdapter } from '../../testSupport/axiosAdapter.js'

const vueUrl = await import.meta.resolve('vue')
const useJobStreamUrl = new URL('./useJobStream.js', import.meta.url).href
let sharedWindow = null

class MockEventSource {
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = 0
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
    this.readyState = 2
  }
}

function installDom(t) {
  if (sharedWindow) {
    sharedWindow.document.body.innerHTML = ''
    MockEventSource.instances = []
    return sharedWindow
  }

  sharedWindow = new Window({ url: 'http://localhost:5174/' })
  globalThis.window = sharedWindow
  globalThis.document = sharedWindow.document
  globalThis.CustomEvent = sharedWindow.CustomEvent
  globalThis.Element = sharedWindow.Element
  globalThis.Event = sharedWindow.Event
  globalThis.EventSource = MockEventSource
  globalThis.HTMLElement = sharedWindow.HTMLElement
  globalThis.Node = sharedWindow.Node
  globalThis.requestAnimationFrame = (callback) => setTimeout(callback, 0)
  globalThis.SVGElement = sharedWindow.SVGElement
  MockEventSource.instances = []

  return sharedWindow
}

async function waitFor(condition, label) {
  const { nextTick } = await import(vueUrl)
  const deadline = Date.now() + 1000
  while (Date.now() < deadline) {
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))
    if (condition()) return
  }
  assert.fail(label)
}

async function importActivityCenter() {
  const filename = new URL('./ActivityCenter.vue', import.meta.url)
  const source = readFileSync(filename, 'utf8')
  const { descriptor } = parse(source, { filename: filename.pathname })
  const id = createHash('sha1').update(filename.href).digest('hex').slice(0, 8)
  const script = compileScript(descriptor, { id })
  const template = compileTemplate({
    id,
    filename: filename.pathname,
    source: descriptor.template.content,
    compilerOptions: { bindingMetadata: script.bindings },
  })
  const css = compileStyle({
    id,
    filename: filename.pathname,
    source: descriptor.styles.map(style => style.content).join('\n'),
  }).code
  const code = [
    script.content
      .replace(/from 'vue'/g, `from '${vueUrl}'`)
      .replace(/from '\.\/useJobStream\.js'/g, `from '${useJobStreamUrl}'`)
      .replace(/import '\.\/activityCenter\.css'\n/g, '')
      .replace('export default', 'const script ='),
    template.code
      .replace(/from "vue"/g, `from '${vueUrl}'`)
      .replace('export function render', 'function render'),
    'const style = document.createElement("style")',
    `style.textContent = ${JSON.stringify(css)}`,
    'document.head.appendChild(style)',
    'script.render = render',
    'export default script',
  ].join('\n')
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(code).toString('base64')}`
  return (await import(moduleUrl)).default
}

test('activity API exposes snapshot and stream helpers for global jobs', async (t) => {
  installDom(t)
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`../../api/index.js?activity-jobs-${Date.now()}`)
  await api.getJobs({ limit: 10, status: 'running' })
  const stream = api.streamJobs({ limit: 10 })

  assert.equal(calls[0].url, '/v1/jobs')
  assert.deepEqual(calls[0].params, { limit: 10, status: 'running' })
  assert.equal(stream.url, '/api/v1/jobs/stream?limit=10')
  assert.equal(stream instanceof MockEventSource, true)
})

test('useJobStream updates jobs by id from EventSource messages and retries with backoff', async (t) => {
  installDom(t)
  const { nextTick } = await import(vueUrl)
  const { useJobStream } = await import(`./useJobStream.js?stream-${Date.now()}`)
  const stream = useJobStream({ autoStart: false, eventSourceFactory: (url) => new MockEventSource(url), loadInitial: false })

  await stream.start()
  assert.equal(MockEventSource.instances[0].url, '/api/v1/jobs/stream')
  MockEventSource.instances[0].pushJob({ id: 7, kind: 'inventory', label: '采集 Emby', status: 'running', progress: 42 })
  await nextTick()

  assert.equal(stream.jobs.value.get(7).progress, 42)
  MockEventSource.instances[0].pushJob({ id: 7, kind: 'inventory', label: '采集 Emby', status: 'completed', progress: 100 })
  await nextTick()
  assert.equal(stream.jobs.value.get(7).status, 'completed')
  assert.equal(stream.jobs.value.get(7).progress, 100)

  MockEventSource.instances[0].emit('error', new Event('error'))
  assert.equal(MockEventSource.instances[0].closeCalled, true)
  assert.equal(stream.nextRetryDelayMs.value, 1000)
  stream.stop()
})

test('ActivityCenter renders EventSource job progress and stays mounted across route content changes', async (t) => {
  const window = installDom(t)
  installAxiosAdapter(t, async (config) => {
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })
  const { createApp, nextTick, ref } = await import(vueUrl)
  const ActivityCenter = await importActivityCenter()
  const host = document.createElement('div')
  document.body.appendChild(host)
  const routeText = ref('影片检索')
  const app = createApp({
    components: { ActivityCenter },
    setup: () => ({ routeText }),
    template: `
      <main data-testid="route">{{ routeText }}</main>
      <ActivityCenter :initial-expanded="true" />
    `,
  })

  app.mount(host)
  await waitFor(() => MockEventSource.instances.length === 1, 'ActivityCenter should open a jobs EventSource')
  MockEventSource.instances[0].pushJob({
    id: 7,
    kind: 'inventory',
    label: '采集 Emby',
    status: 'running',
    progress: 42,
    created_at: '2026-06-06T12:00:00Z',
  })
  await waitFor(() => document.body.textContent.includes('42%'), 'ActivityCenter should render EventSource progress updates')

  assert.match(document.body.textContent, /1 个进行中/)
  assert.match(document.body.textContent, /inventory/)
  assert.match(document.body.textContent, /采集 Emby/)
  assert.equal(document.querySelector('.activity-job-progressbar')?.getAttribute('aria-valuenow'), '42')

  routeText.value = '配置中心'
  await nextTick()
  assert.match(window.document.body.textContent, /配置中心/)
  assert.match(window.document.body.textContent, /采集 Emby/)

  app.unmount()
  assert.equal(MockEventSource.instances[0].closeCalled, true)
})
