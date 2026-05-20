import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('./App.vue', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('./router/index.js', import.meta.url), 'utf8')

test('App lazy loads the global video modal only when opened', () => {
  assert.match(source, /defineAsyncComponent/)
  assert.match(source, /const VideoModal = defineAsyncComponent\(\(\) => import\('\.\/components\/VideoModal\.vue'\)\)/)
  assert.doesNotMatch(source, /import VideoModal from '\.\/components\/VideoModal\.vue'/)
})

test('primary navigation follows the daily workflow order', () => {
  const navStart = source.indexOf('const navItems')
  const navEnd = source.indexOf('const bottomNavItems', navStart)
  const navBlock = source.slice(navStart, navEnd)
  const labels = [...navBlock.matchAll(/label: '([^']+)'/g)].map((match) => match[1])

  assert.deepEqual(labels, [
    '运营总览',
    '个性推荐',
    '影片检索',
    '下载管理',
    '磁链解析',
    '我的收藏',
    '订阅演员',
    '库存对比',
    '演员映射',
    '补全管理',
    '翻译作业',
    '设置',
  ])
})

test('root route redirects to recommendations so the sidebar highlights the entry page', () => {
  assert.match(routerSource, /\{\s*path:\s*'\/',\s*redirect:\s*'\/genres'\s*\}/)
  assert.doesNotMatch(routerSource, /\{\s*path:\s*'\/',\s*component:/)
})
