import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { Window } from 'happy-dom'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const componentUrl = new URL('./AppleSheet.vue', import.meta.url)
const cssUrl = new URL('../assets/sheet.css', import.meta.url)
const vueUrl = await import.meta.resolve('vue')

function readComponent() {
  assert.ok(existsSync(componentUrl), 'AppleSheet.vue should exist')
  return readFileSync(componentUrl, 'utf8')
}

function readCss() {
  assert.ok(existsSync(cssUrl), 'sheet.css should exist')
  return readFileSync(cssUrl, 'utf8')
}

function cssBlock(selector) {
  const css = readCss().replace(/\/\*[\s\S]*?\*\//g, '')
  const blocks = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(([, selectors]) => selectors
      .split(',')
      .map(part => part.trim())
      .includes(selector))
    .map(([, , block]) => block)
  assert.ok(blocks.length, `${selector} should exist in sheet.css`)
  return blocks.join('\n')
}

function installDom(t, width = 390) {
  const window = new Window({ url: 'http://localhost:5174/apple-sheet-test' })
  const previous = {
    window: globalThis.window,
    document: globalThis.document,
    CustomEvent: globalThis.CustomEvent,
    Element: globalThis.Element,
    Event: globalThis.Event,
    HTMLElement: globalThis.HTMLElement,
    Node: globalThis.Node,
    SVGElement: globalThis.SVGElement,
    TouchEvent: globalThis.TouchEvent,
  }

  Object.defineProperty(window, 'innerWidth', { value: width, configurable: true })
  globalThis.window = window
  globalThis.document = window.document
  globalThis.CustomEvent = window.CustomEvent
  globalThis.Element = window.Element
  globalThis.Event = window.Event
  globalThis.HTMLElement = window.HTMLElement
  globalThis.Node = window.Node
  globalThis.SVGElement = window.SVGElement
  globalThis.TouchEvent = window.TouchEvent || window.Event

  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[key]
      else globalThis[key] = value
    }
  })

  return window
}

async function importAppleSheet() {
  const source = readComponent()
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
      .replace(/import '\.\.\/assets\/sheet\.css'\n/g, '')
      .replace('export default', 'const script ='),
    template.code
      .replace(/from "vue"/g, `from '${vueUrl}'`)
      .replace('export function render', 'function render'),
    'script.render = render',
    'export default script',
  ].join('\n')

  return (await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`)).default
}

async function mountSheet(t, props = {}, width = 390) {
  const window = installDom(t, width)
  const { createApp, h, nextTick, ref } = await import(`${vueUrl}?sheet-${Date.now()}-${Math.random()}`)
  const AppleSheet = await importAppleSheet()
  const events = []
  const open = ref(props.open ?? true)
  const host = document.createElement('div')
  document.body.appendChild(host)

  const app = createApp({
    render() {
      return h(
        AppleSheet,
        {
          ...props,
          open: open.value,
          'onUpdate:open': value => {
            open.value = value
            events.push({ type: 'update:open', value })
          },
          onSnap: value => events.push({ type: 'snap', value }),
        },
        () => h('p', { class: 'sheet-body-copy' }, 'Sheet content')
      )
    },
  })

  app.mount(host)
  t.after(() => app.unmount())
  await nextTick()

  return {
    events,
    host,
    nextTick,
    open,
    sheet: () => host.querySelector('.apple-sheet'),
    handle: () => host.querySelector('.apple-sheet__grabber'),
    window,
  }
}

function touchEvent(window, type, clientY) {
  const event = new window.Event(type, { bubbles: true, cancelable: true })
  Object.defineProperty(event, 'touches', {
    value: type === 'touchend' ? [] : [{ clientY }],
    configurable: true,
  })
  Object.defineProperty(event, 'changedTouches', {
    value: [{ clientY }],
    configurable: true,
  })
  return event
}

test('AppleSheet exposes the shared sheet contract', () => {
  const source = readComponent()

  assert.match(source, /import '\.\.\/assets\/sheet\.css'/)
  assert.match(source, /open:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
  assert.match(source, /snapPoints:\s*\{\s*type:\s*Array,\s*default:\s*\(\)\s*=>\s*\[0\.5,\s*1\]\s*\}/)
  assert.match(source, /title:\s*\{\s*type:\s*String,\s*default:\s*''\s*\}/)
  assert.match(source, /defineEmits\(\[\s*'update:open',\s*'snap'\s*\]\)/)
  assert.doesNotMatch(source, /v-if="open"/)
  assert.match(source, /:aria-hidden="open \? undefined : 'true'"/)
  assert.match(source, /:inert="open \? undefined : ''"/)
  assert.match(source, /@touchstart="startDrag"/)
  assert.match(source, /@touchmove="moveDrag"/)
  assert.match(source, /@touchend="endDrag"/)
  assert.match(source, /emit\('update:open', false\)/)
})

test('AppleSheet renders a titled bottom sheet with grab handle and slot content', async (t) => {
  const { host } = await mountSheet(t, { title: '下载选项' })

  assert.ok(host.querySelector('.apple-sheet-shell'), 'shell should render while open')
  assert.equal(host.querySelector('.apple-sheet__title')?.textContent, '下载选项')
  assert.ok(host.querySelector('.apple-sheet__grabber'), 'grab handle should render')
  assert.equal(host.querySelector('.sheet-body-copy')?.textContent, 'Sheet content')
  assert.equal(host.querySelector('.apple-sheet')?.getAttribute('role'), 'dialog')
  assert.equal(host.querySelector('.apple-sheet')?.getAttribute('aria-modal'), 'true')
})

test('AppleSheet closes after a downward drag past 25 percent of the sheet height', async (t) => {
  const { events, handle, nextTick, sheet } = await mountSheet(t)
  Object.defineProperty(sheet(), 'offsetHeight', { value: 400, configurable: true })

  handle().dispatchEvent(touchEvent(window, 'touchstart', 120))
  handle().dispatchEvent(touchEvent(window, 'touchmove', 240))
  await nextTick()
  assert.equal(sheet().style.getPropertyValue('--apple-sheet-drag-y'), '120px')

  handle().dispatchEvent(touchEvent(window, 'touchend', 240))
  await nextTick()

  assert.deepEqual(events.filter(event => event.type === 'update:open'), [{ type: 'update:open', value: false }])
})

test('AppleSheet snaps back and emits snap when the drag is below the close threshold', async (t) => {
  const { events, handle, nextTick, sheet } = await mountSheet(t)
  Object.defineProperty(sheet(), 'offsetHeight', { value: 400, configurable: true })

  handle().dispatchEvent(touchEvent(window, 'touchstart', 100))
  handle().dispatchEvent(touchEvent(window, 'touchmove', 160))
  await nextTick()
  assert.equal(sheet().style.getPropertyValue('--apple-sheet-drag-y'), '60px')

  handle().dispatchEvent(touchEvent(window, 'touchend', 160))
  await nextTick()

  assert.equal(sheet().style.getPropertyValue('--apple-sheet-drag-y'), '0px')
  assert.deepEqual(events.filter(event => event.type === 'snap'), [{ type: 'snap', value: 0.5 }])
})

test('AppleSheet rubber-bands upward drag at half distance', async (t) => {
  const { handle, nextTick, sheet } = await mountSheet(t)

  handle().dispatchEvent(touchEvent(window, 'touchstart', 180))
  handle().dispatchEvent(touchEvent(window, 'touchmove', 120))
  await nextTick()

  assert.equal(sheet().style.getPropertyValue('--apple-sheet-drag-y'), '-30px')
})

test('AppleSheet styles use tokenized material, mobile bottom anchoring, and desktop dialog fallback', () => {
  const css = readCss()
  const root = cssBlock(':root')
  const shell = cssBlock('.apple-sheet-shell')
  const backdrop = cssBlock('.apple-sheet-backdrop')
  const sheet = cssBlock('.apple-sheet')
  const handle = cssBlock('.apple-sheet__grabber')
  const openSheet = cssBlock('.apple-sheet-shell--open .apple-sheet')
  const desktopShell = css.match(/@media \(min-width:\s*769px\)\s*\{([\s\S]*)\n\}/)?.[1] || ''
  const reducedMotion = css.match(/@media \(prefers-reduced-motion:\s*reduce\)\s*\{([\s\S]*)\n\}/)?.[1] || ''

  assert.deepEqual(css.match(/#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\s*\(/g) || [], [])
  assert.match(root, /--b3-local-backdrop:\s*var\(--surface-scrim,\s*var\(--scrim\)\)/)
  assert.match(root, /--b3-local-sheet-bg:\s*var\(--material-glass-sheet\)/)
  assert.match(root, /--b3-local-handle-bg:\s*var\(--text-muted\)/)

  assert.match(shell, /position:\s*fixed/)
  assert.match(shell, /inset:\s*0/)
  assert.match(shell, /align-items:\s*end/)
  assert.match(shell, /opacity:\s*0/)
  assert.match(shell, /transition:\s*opacity var\(--motion-standard,\s*260ms ease\)/)
  assert.doesNotMatch(shell, /transition:[^;]*\b(?:background|border-color|box-shadow|filter)\b/)

  assert.match(backdrop, /background:\s*var\(--b3-local-backdrop\)/)
  assert.match(backdrop, /opacity:\s*calc\(0\.4 \+ \(var\(--apple-sheet-progress,\s*1\) \* 0\.6\)\)/)
  assert.match(backdrop, /transition:\s*opacity var\(--motion-standard,\s*260ms ease\)/)

  assert.match(sheet, /transform:\s*translateY\(calc\(100% \+ var\(--apple-sheet-drag-y,\s*0px\)\)\)/)
  assert.match(sheet, /transition:\s*transform var\(--motion-spring,\s*280ms cubic-bezier\(0\.34,\s*1\.56,\s*0\.64,\s*1\)\),\s*opacity var\(--motion-fast,\s*140ms ease\)/)
  assert.match(sheet, /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--b3-local-sheet-bg\)/)
  assert.match(sheet, /backdrop-filter:\s*blur\(var\(--glass-blur-sheet\)\)\s*saturate\(var\(--glass-saturate-surface\)\)/)
  assert.doesNotMatch(sheet, /transition:[^;]*\b(?:background|border-color|box-shadow|filter|backdrop-filter)\b/)

  assert.match(handle, /width:\s*36px/)
  assert.match(handle, /height:\s*5px/)
  assert.match(handle, /border-radius:\s*999px/)
  assert.match(handle, /background:\s*var\(--b3-local-handle-bg\)/)
  assert.match(openSheet, /transform:\s*translateY\(var\(--apple-sheet-drag-y,\s*0px\)\)/)

  assert.match(desktopShell, /\.apple-sheet-shell\s*\{[\s\S]*align-items:\s*center/)
  assert.match(desktopShell, /\.apple-sheet\s*\{[\s\S]*max-width:\s*560px/)
  assert.match(desktopShell, /\.apple-sheet\s*\{[\s\S]*border-radius:\s*var\(--radius-3xl,\s*28px\)/)
  assert.match(desktopShell, /\.apple-sheet-shell--open \.apple-sheet\s*\{[\s\S]*transform:\s*translateY\(0\)/)

  assert.match(reducedMotion, /--apple-sheet-motion:\s*1ms linear/)
  assert.match(reducedMotion, /transition-duration:\s*1ms/)
})
