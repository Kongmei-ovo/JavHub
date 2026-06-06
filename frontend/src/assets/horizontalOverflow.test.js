import test from 'node:test'
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const baseUrl = process.env.JAVHUB_FRONTEND_URL || 'http://127.0.0.1:5174'

const routes = [
  '/',
  '/search',
  '/genres',
  '/favorites',
  '/subscription',
  '/operations',
  '/config',
]

const viewports = [
  { name: 'mobile', width: 390, height: 844 },
  { name: 'desktop', width: 1440, height: 900 },
]

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForFrontend() {
  let lastError

  for (let attempt = 1; attempt <= 15; attempt += 1) {
    try {
      const response = await fetch(baseUrl)
      if (response.ok) return
    } catch (error) {
      lastError = error
    }
    await delay(1_000)
  }

  throw lastError || new Error(`Frontend did not become ready at ${baseUrl}`)
}

async function waitForShell(page) {
  await page.waitForSelector('.app-layout', { timeout: 10_000 })
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
}

async function gotoRoute(page, route) {
  const url = `${baseUrl}${route}`
  let lastError

  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      await waitForFrontend()
      await page.goto(url, { waitUntil: 'domcontentloaded' })
      return
    } catch (error) {
      lastError = error
      if (!/ERR_CONNECTION_REFUSED|fetch failed/.test(String(error)) || attempt === 5) break
      await delay(1_000)
    }
  }

  throw lastError
}

test('top-level app routes do not create viewport horizontal overflow', async () => {
  const browser = await chromium.launch()
  const failures = []

  try {
    for (const viewport of viewports) {
      const page = await browser.newPage({ viewport })

      for (const route of routes) {
        await gotoRoute(page, route)
        await waitForShell(page)

        const overflow = await page.evaluate(() => {
          const documentWidth = document.documentElement.scrollWidth
          const bodyWidth = document.body?.scrollWidth || 0
          const viewportWidth = window.innerWidth
          const offenders = Array.from(document.body.querySelectorAll('*'))
            .map((element) => {
              const rect = element.getBoundingClientRect()
              return {
                tag: element.tagName.toLowerCase(),
                className: typeof element.className === 'string' ? element.className : '',
                left: Math.round(rect.left),
                right: Math.round(rect.right),
                width: Math.round(rect.width),
              }
            })
            .filter((rect) => rect.width > 0 && (rect.left < -1 || rect.right > viewportWidth + 1))
            .slice(0, 8)

          return {
            bodyWidth,
            documentWidth,
            offenders,
            viewportWidth,
          }
        })

        const maxWidth = Math.max(overflow.documentWidth, overflow.bodyWidth)
        if (maxWidth > viewport.width + 1) {
          failures.push(`${viewport.name} ${route}: ${maxWidth}px > ${viewport.width}px ${JSON.stringify(overflow.offenders)}`)
        }
      }

      await page.close()
    }
  } finally {
    await browser.close()
  }

  assert.deepEqual(failures, [])
})
