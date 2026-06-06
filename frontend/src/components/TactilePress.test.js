import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { Window } from 'happy-dom'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const componentUrl = new URL('./TactilePress.vue', import.meta.url)
const cssUrl = new URL('../assets/tactilePress.css', import.meta.url)
const vueUrl = await import.meta.resolve('vue')

function installDom(t) {
  const window = new Window({ url: 'http://localhost:5174/tactile-press-test' })
  const previous = {
    window: globalThis.window,
    document: globalThis.document,
    CustomEvent: globalThis.CustomEvent,
    Element: globalThis.Element,
    Event: globalThis.Event,
    HTMLElement: globalThis.HTMLElement,
    Node: globalThis.Node,
    PointerEvent: globalThis.PointerEvent,
    SVGElement: globalThis.SVGElement,
  }

  globalThis.window = window
  globalThis.document = window.document
  globalThis.CustomEvent = window.CustomEvent
  globalThis.Element = window.Element
  globalThis.Event = window.Event
  globalThis.HTMLElement = window.HTMLElement
  globalThis.Node = window.Node
  globalThis.PointerEvent = window.PointerEvent || window.MouseEvent
  globalThis.SVGElement = window.SVGElement

  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
  })

  return window
}

async function importTactilePress() {
  assert.ok(existsSync(componentUrl), 'TactilePress.vue should exist')
  const source = readFileSync(componentUrl, 'utf8')
  const { descriptor } = parse(source, { filename: componentUrl.pathname })
  const id = createHash('sha1').update(componentUrl.href).digest('hex').slice(0, 8)
  const script = compileScript(descriptor, { id })
  const template = compileTemplate({
    id,
    filename: componentUrl.pathname,
    source: descriptor.template.content,
    compilerOptions: { bindingMetadata: script.bindings },
  })
  const code = [
    script.content
      .replace(/from 'vue'/g, `from '${vueUrl}'`)
      .replace(/import '\.\.\/assets\/tactilePress\.css'\n/g, '')
      .replace('export default', 'const script ='),
    template.code
      .replace(/from "vue"/g, `from '${vueUrl}'`)
      .replace('export function render', 'function render'),
    'script.render = render',
    'export default script',
  ].join('\n')

  return (await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)).default
}

async function mountTactilePress(t, props = {}) {
  installDom(t)
  const { createApp, h, nextTick } = await import(`${vueUrl}?tactile-${Date.now()}-${Math.random()}`)
  const TactilePress = await importTactilePress()
  const events = []
  const host = document.createElement('div')
  document.body.appendChild(host)

  const app = createApp({
    render() {
      return h(
        TactilePress,
        {
          ...props,
          onPress: event => events.push({ type: 'press', event }),
          onRelease: event => events.push({ type: 'release', event }),
          onTap: event => events.push({ type: 'tap', event }),
        },
        () => h('button', { class: 'movie-card', type: 'button' }, [
          h('span', { class: 'movie-card-title' }, 'MIAA-784'),
        ])
      )
    },
  })

  app.mount(host)
  t.after(() => app.unmount())
  await nextTick()

  return {
    child: host.querySelector('.movie-card'),
    events,
    nextTick,
  }
}

function pointer(type, options = {}) {
  return new PointerEvent(type, { bubbles: true, pointerId: 1, ...options })
}

function cssBlock(selector) {
  const cssSource = readTactilePressCss()
  const content = cssSource.replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...content.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist`)
  return blocks.join('\n')
}

function readTactilePressCss() {
  assert.ok(existsSync(cssUrl), 'tactilePress.css should exist')
  return readFileSync(cssUrl, 'utf8')
}

test('TactilePress marks its child while pressed and emits press, release, and short tap', async (t) => {
  const { child, events, nextTick } = await mountTactilePress(t)

  child.dispatchEvent(pointer('pointerdown'))
  await nextTick()
  assert.equal(child.dataset.press, 'true')
  assert.deepEqual(events.map(event => event.type), ['press'])

  child.dispatchEvent(pointer('pointerup'))
  await nextTick()
  assert.equal(child.hasAttribute('data-press'), false)
  assert.deepEqual(events.map(event => event.type), ['press', 'release', 'tap'])
})

test('TactilePress applies press state to the slot root from nested pointer targets', async (t) => {
  const { child, nextTick } = await mountTactilePress(t)
  const nested = child.querySelector('.movie-card-title')

  nested.dispatchEvent(pointer('pointerdown'))
  await nextTick()

  assert.equal(child.dataset.press, 'true')
  assert.equal(nested.hasAttribute('data-press'), false)
})

test('TactilePress ignores pointer events when disabled', async (t) => {
  const { child, events, nextTick } = await mountTactilePress(t, { disabled: true })

  child.dispatchEvent(pointer('pointerdown'))
  child.dispatchEvent(pointer('pointerup'))
  child.dispatchEvent(pointer('pointerleave'))
  await nextTick()

  assert.equal(child.hasAttribute('data-press'), false)
  assert.deepEqual(events, [])
})

test('TactilePress releases on pointerleave without firing tap', async (t) => {
  const { child, events, nextTick } = await mountTactilePress(t)

  child.dispatchEvent(pointer('pointerdown'))
  await nextTick()
  assert.equal(child.dataset.press, 'true')

  child.dispatchEvent(pointer('pointerleave'))
  await nextTick()
  assert.equal(child.hasAttribute('data-press'), false)
  assert.deepEqual(events.map(event => event.type), ['press', 'release'])
})

test('TactilePress does not emit tap for long presses', async (t) => {
  const { child, events } = await mountTactilePress(t)

  child.dispatchEvent(pointer('pointerdown'))
  await new Promise(resolve => setTimeout(resolve, 220))
  child.dispatchEvent(pointer('pointerup'))

  assert.deepEqual(events.map(event => event.type), ['press', 'release'])
})

test('tactile press CSS gives pressed children tactile depth and intensity levels', () => {
  const cssSource = readTactilePressCss()
  const base = cssBlock('[data-press="true"][data-press-intensity]:not([data-press-disabled])')
  const light = cssBlock('[data-press-intensity="light"][data-press="true"]')
  const medium = cssBlock('[data-press-intensity="medium"][data-press="true"]')
  const strong = cssBlock('[data-press-intensity="strong"][data-press="true"]')
  const reducedMotion = cssSource.match(/@media \(prefers-reduced-motion: reduce\)\s*\{([\s\S]*?)\n\}/)?.[1] || ''
  const rawColorPattern = new RegExp(`#[0-9A-Fa-f]{3,8}|r${'gba?'}\\(|h${'sla?'}\\(`)

  assert.doesNotMatch(cssSource, rawColorPattern)
  assert.match(cssSource, /--b5-tactile-shadow-light:\s*var\(--glass-control-shadow\)/)
  assert.match(cssSource, /--b5-tactile-shadow-medium:\s*var\(--glass-inner-shadow\)/)
  assert.match(cssSource, /--b5-tactile-shadow-strong:\s*var\(--glass-inner-shadow\)/)
  assert.match(base, /transform:\s*translateY\(0\.5px\)\s*scale\(var\(--tactile-press-scale,\s*0\.985\)\)/)
  assert.match(base, /box-shadow:\s*var\(--tactile-press-shadow,\s*var\(--b5-tactile-shadow-medium,\s*var\(--glass-inner-shadow\)\)\)/)
  assert.match(base, /filter:\s*brightness\(0\.985\)/)
  assert.match(base, /transition:\s*transform var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\),\s*box-shadow var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\),\s*filter var\(--motion-fast,\s*140ms ease\)/)
  assert.match(light, /--tactile-press-scale:\s*0\.992/)
  assert.match(light, /--tactile-press-shadow:\s*var\(--b5-tactile-shadow-light,\s*var\(--glass-control-shadow\)\)/)
  assert.match(medium, /--tactile-press-scale:\s*0\.985/)
  assert.match(medium, /--tactile-press-shadow:\s*var\(--b5-tactile-shadow-medium,\s*var\(--glass-inner-shadow\)\)/)
  assert.match(strong, /--tactile-press-scale:\s*0\.972/)
  assert.match(strong, /--tactile-press-shadow:\s*var\(--b5-tactile-shadow-strong,\s*var\(--glass-inner-shadow\)\)/)
  assert.match(reducedMotion, /\[data-press="true"\]\[data-press-intensity\]:not\(\[data-press-disabled\]\)\s*\{[\s\S]*transition:\s*none/)
})
