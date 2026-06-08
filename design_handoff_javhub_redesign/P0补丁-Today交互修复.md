# P0 落地补丁 · `views/Today.vue`（点海报走全局弹窗 + "继续观看"诚实化）

> 采用规划里的**方案 A**：把"继续观看 + 假进度条 + 不播的播放键"诚实化成"最近查看 + 查看详情"，
> 并让点海报/hero 调用全站统一的 `openVideoModal()`。**只改 `views/Today.vue` 一个文件**，5 处。
> 每处都是精确 find/replace，逐字对齐当前源码。

---

## 改动 1 — 引入全局弹窗
`<script>` 顶部 import 区。

**Find：**
```js
import { normalizeVideo } from '../utils/videoNormalize.js'
```
**Replace：**
```js
import { normalizeVideo } from '../utils/videoNormalize.js'
import { openVideoModal } from '../utils/modalState.js'
```

---

## 改动 2 — hero 模板：去假进度条、文案与按钮诚实化
模板里的 `<section class="today-hero">` 整块替换。

**Find：**
```html
          <span class="today-hero__kicker">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="13" height="13" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            继续浏览
          </span>
          <h2 class="today-hero__title" :title="heroTitle">{{ heroTitle }}</h2>
          <p class="today-hero__meta">{{ heroMeta }}</p>
          <div v-if="heroProgress > 0" class="today-hero__progress" aria-hidden="true">
            <span :style="{ transform: `scaleX(${heroProgress / 100})` }"></span>
          </div>
          <div class="today-hero__actions">
            <button class="btn today-hero__btn-primary" type="button" @click.stop="openVideo(hero)">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" aria-hidden="true">
                <polygon points="6 4 20 12 6 20 6 4" />
              </svg>
              继续播放
            </button>
            <button class="btn today-hero__btn-ghost" type="button" @click.stop="openVideo(hero)">详情</button>
          </div>
```
**Replace：**
```html
          <span class="today-hero__kicker">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="13" height="13" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            最近查看
          </span>
          <h2 class="today-hero__title" :title="heroTitle">{{ heroTitle }}</h2>
          <p class="today-hero__meta">{{ heroMeta }}</p>
          <div class="today-hero__actions">
            <button class="btn today-hero__btn-primary" type="button" @click.stop="openVideo(hero)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="14" height="14" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
              查看详情
            </button>
          </div>
```
> 说明：删掉了永不填充的进度条 `div`；kicker "继续浏览"→"最近查看"；主按钮 "继续播放"(播放三角图标)→"查看详情"(右尖角图标)；
> 删掉与主按钮同动作的重复"详情"ghost 按钮。

---

## 改动 3 — `heroMeta` 计算属性：去掉 heroProgress 分支
**Find：**
```js
      if (this.heroProgress > 0) parts.push(`上次看到 ${this.heroProgress}%`)
      else if (n.release_date) parts.push(n.release_date)
```
**Replace：**
```js
      if (n.release_date) parts.push(n.release_date)
```

---

## 改动 4 — `data()`：删除 heroProgress 字段
**Find：**
```js
      hero: null,
      heroProgress: 0,
      activeDownloads: [],
```
**Replace：**
```js
      hero: null,
      activeDownloads: [],
```

---

## 改动 5 — `openVideo()`：改用全局弹窗，不再跳 /search
**Find：**
```js
    openVideo(video) {
      if (!video) return
      try {
        const safe = {
          ...video,
          content_id: video.content_id || video.dvd_id || video.code || video.id,
          display_code: video.display_code || video.dvd_id || video.content_id,
        }
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(HERO_STORAGE_KEY, JSON.stringify(safe))
        }
      } catch (err) {
        // localStorage may throw in private mode; non-fatal.
      }
      const code = video.display_code || video.dvd_id || video.content_id || video.code || video.id
      if (code) {
        this.$router.push({ path: '/search', query: { q: String(code) } })
      } else {
        this.$router.push('/search')
      }
    },
```
**Replace：**
```js
    openVideo(video) {
      if (!video) return
      try {
        const safe = {
          ...video,
          content_id: video.content_id || video.dvd_id || video.code || video.id,
          display_code: video.display_code || video.dvd_id || video.content_id,
        }
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(HERO_STORAGE_KEY, JSON.stringify(safe))
        }
      } catch (err) {
        // localStorage may throw in private mode; non-fatal.
      }
      // 与全站一致：打开全局详情弹窗，而不是把用户甩进搜索页
      openVideoModal(video, '/')
    },
```

---

## 验证清单
1. 起 dev server，进首页：
   - 点 hero、点"订阅更新"里的任意海报 → **弹出 VideoModal**（能看到磁力/收藏/演员），URL 停在 `/`，不再跳 `/search`。
   - hero 不再出现永不填充的进度条；kicker 显示"最近查看"；按钮是"查看详情"。
2. 与在 `/search` 点卡片对比，弹窗行为/外观一致（同一个全局弹窗）。
3. `grep heroProgress views/Today.vue` 应**零命中**（死代码清干净）。
4. 跑测试。若 `Today.test.js` 里断言了旧文案/旧跳转（如 "继续播放" / `push('/search')` / `heroProgress`），同步改成新行为：
   - 期望 `openVideoModal` 被调用（可 mock `utils/modalState.js`）；
   - 文案断言改 "最近查看" / "查看详情"。

## 备注
- 仅此一个文件；不动任何 CSS（`today.css` 里 `.today-hero__progress` 样式留着无妨，已无元素引用；想干净可顺手删该规则，非必须）。
- 这两处修完，首页"行为割裂"和"假进度"即消除。其余 P1–P3 见《功能逻辑完善规划.md》。
