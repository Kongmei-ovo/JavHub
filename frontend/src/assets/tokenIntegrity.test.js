import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative } from 'node:path'

// Guard against a silent failure mode: `var(--token)` with no fallback where
// `--token` is never defined. CSS does not warn on this — the property quietly
// falls back to its inherited/initial value (wrong font-size, missing colour,
// dropped gradient). Renaming/collapsing design tokens (the v2 token waves)
// leaves exactly these dangling references behind. See memory:
// project_legacy_type_token_debt.

const SRC = join(dirname(fileURLToPath(import.meta.url)), '..')

// Tokens injected at runtime via :style / element.style.setProperty, so they
// have no static definition. Add here ONLY when a token is genuinely set in JS.
const RUNTIME_INJECTED = new Set([
  '--skeleton-grid-columns', // AppleSkeleton.vue — computed gridVars
  '--skeleton-aspect-ratio', // AppleSkeleton.vue — computed styleVars
])

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules') continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, files)
    else if (/\.(css|vue|js|ts)$/.test(entry) && !/\.test\.js$/.test(entry)) files.push(full)
  }
  return files
}

const files = walk(SRC)

// 1) Collect every DEFINED custom property. Strip `var(--x` first so the inner
//    token of a usage is never mistaken for a definition.
const defined = new Set()
for (const file of files) {
  const noVar = readFileSync(file, 'utf8').replace(/var\(\s*--[\w-]+/g, 'var(__')
  for (const match of noVar.matchAll(/(--[\w-]+)\s*:/g)) defined.add(match[1])
}

// 2) Flag usages of an undefined token that have no fallback.
const offenders = []
for (const file of files) {
  readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
    for (const match of line.matchAll(/var\(\s*(--[\w-]+)\s*(,?)/g)) {
      const name = match[1]
      const hasFallback = match[2] === ','
      if (hasFallback || defined.has(name) || RUNTIME_INJECTED.has(name)) continue
      offenders.push(`${relative(SRC, file)}:${i + 1}  var(${name})`)
    }
  })
}

test('no var(--token) references an undefined token without a fallback', () => {
  assert.deepEqual(
    offenders,
    [],
    `\nDangling design-token references (define the token, add a fallback, or — if set in JS — add to RUNTIME_INJECTED):\n  ${offenders.join('\n  ')}\n`,
  )
})
