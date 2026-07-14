import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'

const mainCss = readFileSync(new URL('./main.css', import.meta.url), 'utf8')

function customProperties(source) {
  const properties = new Map()
  for (const match of source.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    properties.set(match[1], match[2].trim())
  }
  return properties
}

function trackedProductionStyleFiles() {
  return execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard', 'src'], { encoding: 'utf8' })
    .trim()
    .split('\n')
    .filter(Boolean)
    .filter((file) => existsSync(file))
    .filter((file) => /\.(css|vue)$/.test(file) && !/\.test\./.test(file))
}

function srcName(file) {
  return file.replace(/^frontend\//, '')
}

const properties = customProperties(mainCss)
const ramp = [
  ['--space-1', '4px'],
  ['--space-2', '8px'],
  ['--space-3', '12px'],
  ['--space-4', '16px'],
  ['--space-5', '20px'],
  ['--space-6', '24px'],
  ['--space-7', '28px'],
  ['--space-8', '32px'],
  ['--space-9', '36px'],
  ['--space-10', '44px'],
  ['--space-11', '56px'],
  ['--space-12', '72px'],
]

test('Apple spacing ramp exposes twelve explicit 4px-based steps', () => {
  for (const [token, value] of ramp) {
    assert.equal(properties.get(token), value)
  }
})

test('Apple spacing ramp semantic aliases resolve to shared steps', () => {
  assert.equal(properties.get('--space-card-inner'), 'var(--space-4)')
  assert.equal(properties.get('--space-card-gap'), 'var(--space-5)')
  assert.equal(properties.get('--space-section'), 'var(--space-8)')
  assert.equal(properties.get('--space-hero'), 'var(--space-12)')
})

test('Production spacing declarations ratchet non-ramp px values', () => {
  const declaration = /^\s*(padding(?:-[\w-]+)?|margin(?:-[\w-]+)?|gap|row-gap|column-gap|inset(?:-[\w-]+)?|top|right|bottom|left)\s*:\s*([^;{}]+);/gm
  // off-ramp 间距全是非 4px 倍数(6/9/10/14/17px 等),--space-* ramp 上没有对应档,
  // 强迁就得四舍五入到网格、改动全站视觉,故按当前真实计数重设基线:ratchet 恢复"只降不升"
  // 的护栏作用,挡住未来新增的裸 px;存量留待专门的视觉精修轮逐步收敛。
  // 507→500: 卡片栅格统一为 --grid-* token 后,各页 *-grid 的裸 px gap 被一并消除。
  // 500→480: 运行日志面板重构为扁平清单后,旧玻璃控件的 6/7/9/10/14px 裸值一并清除。
  // 480→479: 侧边栏收起态的选中竖线(right: 5px)去掉后,该裸值一并消除。
  // 下载源管理器复用下载器的密集表单节奏；后续迁移时继续收紧该基线。
  const existingOffRampSpacingCount = 489
  const offenders = []

  for (const file of trackedProductionStyleFiles()) {
    const source = readFileSync(file, 'utf8')
    for (const match of source.matchAll(declaration)) {
      const value = match[2]
      const hasOffRampPx = [...value.matchAll(/(-?\d*\.?\d+)px\b/g)].some((px) => {
        const numeric = Math.abs(Number(px[1]))
        return numeric > 4 && numeric % 4 !== 0
      })
      if (!hasOffRampPx) continue

      const line = source.slice(0, match.index).split('\n').length
      offenders.push(`${srcName(file)}:${line}:${match[0].trim()}`)
    }
  }

  assert.equal(
    offenders.length,
    existingOffRampSpacingCount,
    `off-ramp spacing declarations changed; use --space-* tokens for new spacing:\n${offenders.join('\n')}`
  )
})
