import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { Window } from 'happy-dom'
import { compileScript, compileTemplate, parse, rewriteDefault } from '@vue/compiler-sfc'

const source = readFileSync(new URL('./JobsTab.vue', import.meta.url), 'utf8')
const baseVueUrl = await import.meta.resolve('vue')

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
  const window = new Window({ url: 'http://localhost:5174/supplement/jobs' })
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

async function importJobsTab(vueUrl) {
  const filename = new URL('./JobsTab.vue', import.meta.url)
  const { descriptor } = parse(source, { filename: filename.pathname })
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
    .replace(/import GlassSelect from '\.\.\/\.\.\/components\/GlassSelect\.vue'\n/, 'const GlassSelect = { props: ["modelValue", "options"], template: "<select></select>" }\n')
    .replace(/import SupplementJobList from '\.\/SupplementJobList\.vue'\n/, `const SupplementJobList = {
      props: ["jobs", "loading", "actorContext", "jobLabel", "statusLabel", "contextLabel", "totalCount"],
      emits: ["retry", "cancel", "actor", "refresh", "start-supplement"],
      template: "<section><article v-for=\\"job in jobs\\" :key=\\"job.id\\"><strong>{{ jobLabel(job) }}</strong><span>{{ statusLabel(job.status) }}</span><span>{{ job.progress }}%</span></article></section>"
    }\n`)
    .replace(/import \{ useSupplementApi \} from '\.\/useSupplementApi\.js'\n/, `const useSupplementApi = () => {
      const jobs = ref([])
      return {
        jobs,
        jobsLoading: ref(false),
        jobsError: ref(''),
        jobsTotalCount: ref(0),
        jobsTotalPages: ref(1),
        recovering: ref(false),
        loadJobs: async () => {},
        retryJob: async () => {},
        cancelJob: async () => {},
        recoverStale: async () => {},
        statusLabel: status => ({ queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败' }[status] || status || '待开始'),
        gfriendsAvatarJob: ref(null),
        gfriendsAvatarSyncing: ref(false),
        isGfriendsAvatarJobRunning: ref(false),
        loadGfriendsAvatarJob: async () => {},
        syncGfriendsAvatars: async () => {},
        formatActionTime: () => '',
      }
    }\n`)
    .replace(/import \{ requestConfirm \} from '\.\.\/\.\.\/utils\/confirmDialog'\n/, 'const requestConfirm = async () => false\n')
  const code = [
    scriptCode,
    template.code.replace(/from "vue"/g, `from '${vueUrl}'`),
    'script.render = render',
    'export default script',
  ].join('\n')
  return (await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)).default
}

async function mountJobsTab(t) {
  installDom(t)
  const vueUrl = `${baseVueUrl}?jobs-tab-${Date.now()}-${Math.random()}`
  const { createApp, nextTick } = await import(vueUrl)
  const JobsTab = await importJobsTab(vueUrl)
  const host = document.createElement('div')
  document.body.appendChild(host)
  const app = createApp(JobsTab, { globalQueue: true })
  app.mount(host)
  t.after(() => app.unmount())
  return { app, host, nextTick }
}

test('JobsTab owns queue loading and shared job operations through useSupplementApi', () => {
  assert.match(source, /name:\s*'JobsTab'/)
  assert.match(source, /useSupplementApi\(/)
  assert.match(source, /loadJobs\(/)
  assert.match(source, /retryJob/)
  assert.match(source, /cancelJob/)
  assert.match(source, /recoverStale/)
  assert.match(source, /jobsLoading/)
  assert.match(source, /jobsTotalCount/)
  assert.match(source, /jobsTotalPages/)
  assert.match(source, /SupplementJobList/)
  assert.match(source, /emit\('actor'/)
  assert.match(source, /emit\('start-supplement'/)
})

test('JobsTab keeps filter state local and exposes route-friendly updates', () => {
  assert.match(source, /jobFilters/)
  assert.match(source, /jobStatusOptions/)
  assert.match(source, /applyJobFilters/)
  assert.match(source, /page:\s*jobPage\.value/)
  assert.match(source, /filters:\s*jobFilters/)
  assert.match(source, /emit\('filters-change'/)
  assert.match(source, /GlassSelect/)
  assert.match(source, /全局队列状态筛选|任务状态筛选/)
})

test('JobsTab hosts the gfriends avatar override job (moved from source health)', () => {
  assert.match(source, /class="avatar-job-card"/)
  assert.match(source, /头像覆盖作业/)
  assert.match(source, /同步演员头像/)
  assert.match(source, /confirmSyncAvatars/)
  assert.match(source, /requestConfirm/)
  assert.match(source, /gfriendsAvatarJob/)
  assert.match(source, /loadGfriendsAvatarJob/)
  assert.match(source, /toggleAvatarJobFilter/)
  assert.match(source, /'gfriends'/)
})

test('JobsTab listens to supplement SSE jobs and updates the visible queue', async (t) => {
  const { nextTick } = await mountJobsTab(t)
  await waitFor(() => MockEventSource.instances.length === 1, 'JobsTab should open one supplement EventSource', { nextTick })

  const stream = MockEventSource.instances[0]
  assert.equal(stream.url, '/api/v1/jobs/stream?kind=supplement')

  stream.pushJob({
    id: 21,
    kind: 'supplement',
    label: 'supplement pipeline',
    status: 'running',
    progress: 37,
    source_actor_name: 'Alice',
  })
  await waitFor(() => document.body.textContent.includes('37%'), 'JobsTab should render running supplement job progress', { nextTick })

  stream.pushJob({
    id: 21,
    kind: 'supplement',
    label: 'supplement pipeline',
    status: 'succeeded',
    progress: 100,
    source_actor_name: 'Alice',
  })
  await waitFor(() => document.body.textContent.includes('100%'), 'JobsTab should render completed supplement job progress', { nextTick })
})

test('JobsTab reconnects the supplement SSE stream after a disconnect', async (t) => {
  const { nextTick } = await mountJobsTab(t)
  await waitFor(() => MockEventSource.instances.length === 1, 'JobsTab should open a supplement EventSource', { nextTick })

  MockEventSource.instances[0].emit('error', new Event('error'))
  assert.equal(MockEventSource.instances[0].closeCalled, true)

  await waitFor(() => MockEventSource.instances.length === 2, 'JobsTab should reconnect after the 1s backoff', { timeout: 1300, nextTick })
  assert.equal(MockEventSource.instances[1].url, '/api/v1/jobs/stream?kind=supplement')
})
