import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'

const sources = new Map([
  ['actor.css', readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8')],
  ['entities.css', readFileSync(new URL('../features/entities/entities.css', import.meta.url), 'utf8')],
  ['favorites.css', readFileSync(new URL('../features/favorites/favorites.css', import.meta.url), 'utf8')],
  ['downloads.css', readFileSync(new URL('../features/downloads/downloads.css', import.meta.url), 'utf8')],
  ['downloadCandidatePanel.css', readFileSync(new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url), 'utf8')],
  ['search.css', readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8')],
  ['subscription.css', readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8')],
])

const repeatedSurfaces = [
  ['actor.css', '.movie-card-wrap'],
  ['entities.css', '.entity-list-card'],
  ['favorites.css', '.collection-row'],
  ['downloads.css', '.task-card'],
  ['downloadCandidatePanel.css', '.event-row'],
  ['search.css', '.result-card-group'],
  ['subscription.css', '.work-card-wrap'],
]

function collectStyleSources(rootUrl) {
  const collected = new Map()
  const rootPath = rootUrl.pathname

  function visit(directoryUrl) {
    for (const entry of readdirSync(directoryUrl, { withFileTypes: true })) {
      const entryUrl = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, directoryUrl)
      if (entry.isDirectory()) {
        visit(entryUrl)
        continue
      }

      if (!entry.name.endsWith('.css') && !entry.name.endsWith('.vue')) continue

      const sourceName = entryUrl.pathname.slice(rootPath.length).replace(/^\//, '')
      const fileSource = readFileSync(entryUrl, 'utf8')

      if (entry.name.endsWith('.css')) {
        collected.set(sourceName, fileSource)
        continue
      }

      const styleBlocks = [...fileSource.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)]
      if (styleBlocks.length > 0) {
        collected.set(sourceName, styleBlocks.map((match) => match[1]).join('\n'))
      }
    }
  }

  if (statSync(rootUrl).isDirectory()) visit(rootUrl)
  return collected
}

const pageStyleSources = collectStyleSources(new URL('../', import.meta.url))

function selectorMatches(ruleSelector, selector) {
  return ruleSelector
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split(',')
    .map((part) => part.trim())
    .some((part) => part === selector)
}

function ruleFor(source, selector) {
  for (const match of source.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (selectorMatches(match[1], selector)) return match[2]
  }
  return ''
}

function declarationsFor(source, property) {
  const declarations = []
  const propertyPattern = property.replace('-', '\\-')
  const declarationPattern = new RegExp(`(?:^|;)\\s*${propertyPattern}\\s*:\\s*([^;{}]+);`, 'g')

  for (const match of source.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selector = match[1].replace(/\/\*[\s\S]*?\*\//g, '').trim()
    const body = match[2]

    for (const declaration of body.matchAll(declarationPattern)) {
      declarations.push({
        selector,
        value: declaration[1].trim(),
      })
    }
  }

  return declarations
}

function splitTransitionItems(value) {
  const items = []
  let start = 0
  let depth = 0

  for (let index = 0; index < value.length; index += 1) {
    const char = value[index]
    if (char === '(') depth += 1
    if (char === ')') depth = Math.max(0, depth - 1)
    if (char === ',' && depth === 0) {
      items.push(value.slice(start, index).trim())
      start = index + 1
    }
  }

  items.push(value.slice(start).trim())
  return items.filter(Boolean)
}

function transitionPropertyFor(item) {
  if (item.startsWith('var(')) return item
  return item.split(/\s+/)[0]
}

function keyframesFor(source) {
  const keyframes = []
  const pattern = /@keyframes\s+([^{\s]+)\s*\{/g
  let match

  while ((match = pattern.exec(source))) {
    let depth = 1
    let index = pattern.lastIndex
    while (index < source.length && depth > 0) {
      if (source[index] === '{') depth += 1
      if (source[index] === '}') depth -= 1
      index += 1
    }

    keyframes.push({
      name: match[1],
      body: source.slice(pattern.lastIndex, index - 1),
    })
    pattern.lastIndex = index
  }

  return keyframes
}

function selectorHasState(selector, state) {
  return selector.split(',').some((part) => part.includes(state))
}

function scaleValues(transform) {
  return [...transform.matchAll(/scale\((\d*\.?\d+)/g)].map((match) => Number(match[1]))
}

function negativeTranslateYValues(transform) {
  return [...transform.matchAll(/translateY\((-?\d*\.?\d+)px\)/g)]
    .map((match) => Number(match[1]))
    .filter((value) => value < 0)
}

function translateYValues(transform) {
  return [...transform.matchAll(/translateY\((-?\d*\.?\d+)px\)/g)].map((match) => Number(match[1]))
}

function isEntryOrExitSelector(selector) {
  return /-(?:enter|leave)-(?:from|to)\b/.test(selector)
}

test('repeated long-list surfaces skip offscreen rendering work', () => {
  const offenders = []

  for (const [sourceName, selector] of repeatedSurfaces) {
    const source = sources.get(sourceName)
    const block = ruleFor(source, selector)
    if (!/content-visibility:\s*auto/.test(block) || !/contain-intrinsic-size:\s*1px\s+\d+px/.test(block)) {
      offenders.push(`${sourceName}:${selector}`)
    }
  }

  assert.deepEqual(offenders, [])
})

test('page motion transitions only animate transform and opacity', () => {
  const allowedProperties = new Set(['transform', 'opacity'])
  const offenders = []

  for (const [sourceName, source] of pageStyleSources) {
    for (const { selector, value } of declarationsFor(source, 'transition')) {
      const animatedProperties = splitTransitionItems(value).map(transitionPropertyFor)
      for (const property of animatedProperties) {
        if (!allowedProperties.has(property)) {
          offenders.push(`${sourceName}:${selector} -> transition ${property}`)
        }
      }
    }

    for (const { selector, value } of declarationsFor(source, 'transition-property')) {
      const animatedProperties = splitTransitionItems(value)
      for (const property of animatedProperties) {
        if (!allowedProperties.has(property)) {
          offenders.push(`${sourceName}:${selector} -> transition-property ${property}`)
        }
      }
    }
  }

  // 历史 token 债基线:ratchet 锁当前计数、挡新增;存量过渡非 transform/opacity 待专门精修轮。
  assert.equal(offenders.length, 9, offenders.join('\n'))
})

test('page motion transitions use shared motion tokens', () => {
  const offenders = []

  for (const [sourceName, source] of pageStyleSources) {
    for (const { selector, value } of declarationsFor(source, 'transition')) {
      for (const item of splitTransitionItems(value)) {
        if (!/var\(--motion-/.test(item)) {
          offenders.push(`${sourceName}:${selector} -> ${item}`)
        }
      }
    }
  }

  // 历史 token 债基线:ratchet 锁当前计数、挡新增;裸过渡时长待专门精修轮迁成 --motion-* token。
  assert.equal(offenders.length, 1, offenders.join('\n'))
})

test('interactive transforms stay light for hover focus and press', () => {
  const offenders = []

  for (const [sourceName, source] of pageStyleSources) {
    for (const { selector, value } of declarationsFor(source, 'transform')) {
      const isHoverOrFocus = selectorHasState(selector, ':hover') || selectorHasState(selector, ':focus-visible')
      const isPress = selectorHasState(selector, ':active')

      if (isHoverOrFocus) {
        for (const lift of negativeTranslateYValues(value)) {
          if (Math.abs(lift) > 2) offenders.push(`${sourceName}:${selector} -> lift ${lift}px`)
        }
        for (const scale of scaleValues(value)) {
          if (scale > 1.04) offenders.push(`${sourceName}:${selector} -> hover scale ${scale}`)
        }
      }

      if (isPress) {
        for (const scale of scaleValues(value)) {
          if (scale < 0.96 || scale > 1.01) offenders.push(`${sourceName}:${selector} -> press scale ${scale}`)
        }
      }
    }
  }

  assert.deepEqual(offenders, [])
})

test('entry and exit transforms stay light', () => {
  const offenders = []
  const exemptKeyframes = /(?:spin|shimmer|skeleton|pulse|progress|jiggle)/i

  function checkTransform(sourceName, context, transform) {
    for (const scale of scaleValues(transform)) {
      if (scale < 0.96 || scale > 1.01) offenders.push(`${sourceName}:${context} -> reveal scale ${scale}`)
    }

    for (const offset of translateYValues(transform)) {
      if (Math.abs(offset) > 20) offenders.push(`${sourceName}:${context} -> reveal offset ${offset}px`)
    }
  }

  for (const [sourceName, source] of pageStyleSources) {
    for (const { selector, value } of declarationsFor(source, 'transform')) {
      if (isEntryOrExitSelector(selector)) checkTransform(sourceName, selector, value)
    }

    for (const { name, body } of keyframesFor(source)) {
      if (exemptKeyframes.test(name)) continue

      for (const declaration of body.matchAll(/transform\s*:\s*([^;{}]+);/g)) {
        checkTransform(sourceName, `@keyframes ${name}`, declaration[1])
      }
    }
  }

  assert.deepEqual(offenders, [])
})

test('content entry keyframes animate only transform and opacity', () => {
  const allowedProperties = new Set(['transform', 'opacity'])
  const exemptKeyframes = /(?:spin|shimmer|skeleton|pulse|progress|jiggle)/i
  const offenders = []

  for (const [sourceName, source] of pageStyleSources) {
    for (const { name, body } of keyframesFor(source)) {
      if (exemptKeyframes.test(name)) continue

      for (const declaration of body.matchAll(/([a-z-]+)\s*:/g)) {
        const property = declaration[1]
        if (!allowedProperties.has(property)) {
          offenders.push(`${sourceName}:@keyframes ${name} -> ${property}`)
        }
      }
    }
  }

  assert.deepEqual(offenders, [])
})
