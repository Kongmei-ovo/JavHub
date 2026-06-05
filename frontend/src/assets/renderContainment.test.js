import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const sources = new Map([
  ['actor.css', readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8')],
  ['entities.css', readFileSync(new URL('../features/entities/entities.css', import.meta.url), 'utf8')],
  ['favorites.css', readFileSync(new URL('../features/favorites/favorites.css', import.meta.url), 'utf8')],
  ['home.css', readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8')],
  ['inventory.css', readFileSync(new URL('../features/inventory/inventory.css', import.meta.url), 'utf8')],
  ['libraryOrganize.css', readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8')],
  ['normalize.css', readFileSync(new URL('../features/normalize/normalize.css', import.meta.url), 'utf8')],
  ['operations.css', readFileSync(new URL('../features/operations/operations.css', import.meta.url), 'utf8')],
  ['search.css', readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8')],
  ['subscription.css', readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8')],
  ['supplementManagement.css', readFileSync(new URL('../features/supplement/supplementManagement.css', import.meta.url), 'utf8')],
  ['SupplementJobList.vue', readFileSync(new URL('../features/supplement/SupplementJobList.vue', import.meta.url), 'utf8')],
])

const repeatedSurfaces = [
  ['actor.css', '.movie-card-wrap'],
  ['entities.css', '.entity-list-card'],
  ['favorites.css', '.collection-row'],
  ['home.css', '.task-card'],
  ['home.css', '.event-row'],
  ['inventory.css', '.actor-card'],
  ['libraryOrganize.css', '.missing-video'],
  ['libraryOrganize.css', '.mapping-item'],
  ['libraryOrganize.css', '.inventory-candidate'],
  ['libraryOrganize.css', '.duplicate-group'],
  ['libraryOrganize.css', '.job-row'],
  ['normalize.css', '.mapping-card'],
  ['normalize.css', '.mapping-row'],
  ['operations.css', '.compact-row'],
  ['operations.css', '.run-row'],
  ['search.css', '.result-card-group'],
  ['subscription.css', '.work-card-wrap'],
  ['supplementManagement.css', '.ios-row'],
  ['supplementManagement.css', '.diagnostics-row'],
  ['supplementManagement.css', '.detail-source-item'],
  ['supplementManagement.css', '.manual-action-item'],
  ['SupplementJobList.vue', '.ios-row'],
]

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
