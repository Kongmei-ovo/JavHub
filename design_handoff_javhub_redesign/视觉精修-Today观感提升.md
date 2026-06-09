# 视觉精修补丁 · Today 视图（观感提升）

> 基于对真实渲染的截图诊断。4 处精修,全部**只动样式**,不碰结构/逻辑/token 定义本身。
> 改动集中在 `features/today/today.css`;其中卡片提升用到的 `--card-elevated` 已存在于暗色 token,无需新增。
> 每处都是精确 find/replace。落地后对照截图验收。

---

## 精修 1 · 页面标题层级（"今日"立起来）
**问题**:页面标题 `今日` 与区块标题 `待处理/下载中/订阅更新` 同为 22px,层级塌平,页面标题太胆怯。
**改**:页面标题升到 30px(更自信),区块标题降到 20px(明确从属),topbar 给更多上下呼吸。

`features/today/today.css`:

**Find:**
```css
.today-topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--page-gutter);
```
**Replace:**（仅 padding 行：`--space-4` → `--space-5`）
```css
.today-topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5) var(--page-gutter);
```

**Find:**
```css
.today-topbar__title h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--type-title-1);
  font-weight: 700;
  letter-spacing: 0;
  color: var(--text-primary);
}
```
**Replace:**
```css
.today-topbar__title h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.4px;
  color: var(--text-primary);
}
```

**Find:**
```css
.today-section__head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--type-title-1);
  font-weight: 650;
  letter-spacing: 0;
  color: var(--text-primary);
}
```
**Replace:**
```css
.today-section__head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 680;
  letter-spacing: -0.2px;
  color: var(--text-primary);
}
```

---

## 精修 2 · chrome 卡片提升（统计/待处理/下载读成"表面"）
**问题**:统计卡、待处理卡用 `--card (#17171E)` + 0.075 发丝边,与 canvas `#0F0F14` 几乎贴平,沉在近黑里。
（海报卡有封面提供对比,chrome 卡没有,需要自己立起来。）
**改**:换用更亮的 `--card-elevated`、发丝边升到 `--hairline-strong`、加顶部内高光 + 轻投影。

`features/today/today.css`:

**Find:**
```css
.today-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-card);
  border: 1px solid var(--hairline);
  background: var(--card);
  text-align: left;
  color: var(--text-primary);
  text-decoration: none;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
  cursor: pointer;
}
```
**Replace:**
```css
.today-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-card);
  border: 1px solid var(--hairline-strong);
  background: var(--card-elevated);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 1px 2px rgba(0, 0, 0, 0.30);
  text-align: left;
  color: var(--text-primary);
  text-decoration: none;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
  cursor: pointer;
}
```

**Find:**
```css
.today-attn {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-card);
  border: 1px solid var(--hairline);
  background: var(--card);
}
```
**Replace:**
```css
.today-attn {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-card);
  border: 1px solid var(--hairline-strong);
  background: var(--card-elevated);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 1px 2px rgba(0, 0, 0, 0.30);
}
```

**Find:**
```css
.today-dl {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline);
  background: var(--card);
  transition: opacity var(--motion-fast);
}
```
**Replace:**
```css
.today-dl {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--hairline-strong);
  background: var(--card-elevated);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition: opacity var(--motion-fast);
}
```

> ⚠️ 浅色主题核对:`--card-elevated` 浅色为 `#FFFFFF`、`--hairline-strong` 0.13,提升在浅色下同样成立(白卡 + 轻边 + 微影),无需分主题处理。切到 apple-light 扫一眼确认即可。

---

## 精修 3 · Hero 放出色彩（封面是灵魂,别闷掉）
**问题**:左侧 scrim `--black-80`(80% 黑)压住封面,颜色只在右 1/3 露脸。
**改**:scrim 收一档并让右侧更通透;封面取景下移一点、饱和度微提,让主体/色彩更出。

`features/today/today.css`:

**Find:**
```css
.today-hero__art {
  position: absolute;
  inset: 0;
  background-color: var(--card-2);
  background-size: cover;
  background-position: center 22%;
  filter: saturate(1.06);
}
```
**Replace:**
```css
.today-hero__art {
  position: absolute;
  inset: 0;
  background-color: var(--card-2);
  background-size: cover;
  background-position: center 30%;
  filter: saturate(1.12);
}
```

**Find:**
```css
.today-hero__scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(105deg, var(--black-80) 0%, var(--black-40) 42%, var(--white-00) 78%);
}
```
**Replace:**
```css
.today-hero__scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(100deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.42) 38%, rgba(0,0,0,0.05) 72%, transparent 100%);
}
```
> 文字仍压在左侧(scrim 左端仍 0.78 黑),对比度不受影响;只是右侧从"硬切到全黑"改成"自然消隐",封面色透出来。

---

## 精修 4 · 干掉统计卡的数据废话(data-slop)
**问题**:`影库 2,418 → 2,418 部入库` 重复念数字;四个 delta 全绿(向上),颜色失义;"待处理"积压项标绿语义错。
**改**:delta 改成"补充信息",绿色只留给真正正向项,中性项用 flat(灰)。
这是 `views/Today.vue` 的 `statItems` computed 里的 `delta` / `deltaTone` 逻辑。

`views/Today.vue` `statItems()`:
- **library**:`delta` 不要回显总数。改为本周新增(若有该数据)或留空:
  ```js
  delta: this.libraryWeeklyAdded ? `+${this.formatNumber(this.libraryWeeklyAdded)} 本周` : '',
  deltaTone: 'up',
  ```
  （没有"本周新增"数据源就先 `delta: ''`,空着也比回显总数好。）
- **downloading**:`进行中` 改为带信息的中性文案:
  ```js
  delta: this.activeDownloads.length > 0
    ? `${Math.max(...this.activeDownloads.map(d => d.pct || 0))}% 最快`
    : '空闲',
  deltaTone: 'flat',
  ```
- **subs**:保留 `+N 新片`(这是真正向),`deltaTone: 'up'`。
- **pending**:积压项改**中性**,且把"候选 + 缺档"合并表述:
  ```js
  delta: this.candidateSummary.candidate > 0
    ? `${this.candidateSummary.candidate} 候选${this.candidateSummary.missing_magnet ? ` · ${this.candidateSummary.missing_magnet} 缺档` : ''}`
    : '已清空',
  deltaTone: 'flat',   // 积压不是好事,不标绿
  ```
> 原则:delta 要么给新信息,要么不给;颜色只在"确实是好消息"时才用绿。

---

## 验收对照
1. 页面标题"今日"明显大于、重于区块标题,一眼能分清"页面 vs 区块"。
2. 统计卡 / 待处理卡 / 下载行从背景里**浮起来**,有清晰的表面感(不再是贴平的暗块)。
3. Hero 右侧能看到封面色彩自然透出,左侧文字对比度不变。
4. 统计 delta 不再回显数字;只有真正正向项是绿色,积压/中性项是灰。
5. 切浅色主题扫一眼,卡片提升与标题层级同样成立。
6. `npm test` 全绿(若 today 相关测试断言了旧字号/旧 delta 文案,同步更新断言)。

> 这一轮是纯观感打磨,改完 Today 的"成品感"会明显上一个台阶。同样的手法(标题层级 + chrome 卡片提升 + 克制用色)可以接着推到候选页 / 下载页 / 运营总览,保持全站一致。
