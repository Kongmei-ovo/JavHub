# Handoff: JavHub UI 重设计（v2 设计语言）

## Overview
这是 JavHub（自托管影片目录面板）前端的一次 **UI/UX 重设计**。目标不是推翻现有的 Liquid Glass 体系，而是修正它的方向：让**内容（封面/肖像）成为主角**，把玻璃材质收回到"chrome"上，引入克制的彩色 accent，并补齐信息架构（真正的首页仪表盘、行动中心、批量操作、移动端导航）。

本包内含一套用 **React + 原生 CSS** 写成的高保真可点击原型（10 屏 + 双主题 + 设计文档），作为视觉与交互参考。

## About the Design Files
本包里的文件是**用 HTML/React 制作的设计参考**——展示预期外观与行为的原型，**不是要直接照搬进生产环境的代码**。

JavHub 现有前端是 **Vue 3 + 原生 CSS（设计 token 在 `frontend/src/assets/main.css`）**。任务是把这些原型设计**用现有 Vue 代码库的既有模式重新实现**（复用现有的 Apple-prefixed 组件、token 体系、guard 测试），而不是引入 React。原型里的 React 只是表达媒介。

## Fidelity
**高保真（hifi）**。颜色、字阶、间距、圆角、动效、交互都是最终意图，请按原型像素级还原，但落地时用 Vue 代码库现有的组件与 token。

## 设计语言：四条核心修正
1. **玻璃只给 chrome，内容区改实底。** 侧栏 / 顶栏 / 浮动工具栏 = 玻璃（`backdrop-filter: blur(40px) saturate(1.6)` + 1px specular 高光边）。内容画布 / 卡片 = **实底**（`--canvas` / `--card`）。这是让海报跳出来的关键。
2. **Poster-first，色彩从内容来。** 卡片 3:4 大封面、edge-to-edge，UI 的彩色由封面提供，深色底让色彩张力最大化。
3. **引入克制的 accent。** 现有 `--accent: #1D1D1F`（纯黑）导致全站灰阶像线框。改为真正的强调色（默认靛蓝 `#7C8CFF`），仅用于主按钮、激活态、进度、关键数字。
4. **用起 display 字阶。** hero 40px、区块标题 22–30px，层级靠"字号 × 字重 × 色阶"三轴拉开，不靠 border。

## Screens / Views

> 共 10 屏。导航分三组：**浏览**（今日/影库/私人策展/随机探索）、**自动化**（下载任务/演员订阅/候选确认/片库整理）、**系统**（运营总览/配置中心）。

### 1. 今日（Today，新落地页）
- **Purpose**：替代原"下载管理"作为首页，给出全局态势与待办。
- **Layout**：sticky 玻璃顶栏（标题 + 搜索 + 通知）→ 内容区 `max-width: 1400px` 居中，竖向分区，区块间距 `--s8`(44px)。
- **Components**：
  - **Hero 继续观看**：圆角 18px、min-height 280px、全幅封面 + 左→右黑色 scrim 渐变；内含 kicker（11px 大写）、40px display 标题、进度条（白、max-width 360px）、白底主按钮 + 玻璃副按钮。
  - **统计条**：4 列卡片，数字 `--t-h1`(30/700)、标签 `--t-cap`、delta（绿=up/灰=flat）。
  - **待处理（行动中心）**：把"候选/缺磁力/翻译"散页收口成卡片网格，每卡 = 着色图标 + 标题 + 描述 + 主/副按钮。
  - **下载中**：紧凑行（缩略图 + 名称 + meta + 进度条 + 右侧 %/速度）。
  - **订阅更新**：poster 网格。

### 2. 影库（Library）
- **Purpose**：检索 + 浏览全片库。
- **Layout**：`.topbar.solid`（玻璃实化、底部 hairline）含标题 + 搜索 + 「多选」按钮；内容 `max-width: 1640px`。
- **Components**：类型分段控件（全部/数字/DVD/流媒体/租赁，带计数）+ 排序分段（最新/时长）；poster 网格 `repeat(auto-fill, minmax(var(--grid-min), 1fr))`，`--grid-min` 随密度 168/200/244px。
- **批量多选**：顶栏切换 → 海报出现勾选态（2px accent 边框 + 左上角圆形勾选）→ 底部**浮动玻璃工具栏**（已选 N 项 + 下载/收藏/翻译/移除 + 完成）。

### 3. 私人策展（Curation / Favorites）
- **Purpose**：收藏分类浏览，且**每张影片卡下方挂演员订阅条**。
- **Layout**：分段 tab（全部/影片/演员/题材/系列，带计数）+ accent 提示横幅 + poster 网格（`showActs`）。
- **ActRow（演员订阅条）**：圆头像（首字、演员色）+ 翻译名（主）/罗马字（辅）+ 订阅按钮（**绿=已订阅 / 灰=可订阅**）。无演员时显示"暂无演员数据 · 收藏保持轻量"。对齐 `docs/favorite-subscription-card-mockup.png` 的方向。

### 4. 随机探索（Explore）
- **Purpose**：从片库翻出被遗忘的片。
- **Components**：题材 chip 过滤（点亮 = accent 实底）；大 shuffle hero（280px 封面 + 信息 + 「查看详情」「换一个」骰子按钮，旋转动画）；「再看看这些」随机网格。
- **逻辑**：用带种子的逐项哈希排序保证每次重抽顺序真的不同：`rnd(code)=(seed+1)*2654435761 →逐字符 (h^c)*16777619 >>>0`，`sort((a,b)=>rnd(a.code)-rnd(b.code))`。**不要用常量比较器**（会不重排）。

### 5. 候选确认（Candidates，真交互重点）
- **Purpose**：审核订阅自动抓取的候选。
- **Layout**：状态分段（待确认/已通过/已拒绝/缺磁力，带计数）+ 候选行列表。
- **行**：勾选框 + 缩略图 + 标题 + meta（番号/演员/来源 chip/种子 badge 或"缺磁力" badge）+ 操作（补磁力/编辑/✗拒绝/✓通过）。
- **逻辑**：✓/✗ 改状态并从待确认移除；**缺磁力的候选 ✓ 通过按钮禁用**（opacity 0.4 + not-allowed）；批量多选 → 浮动工具栏「全部通过/拒绝」；计数实时联动。

### 6. 演员订阅（Subscriptions）
- **Purpose**：管理演员订阅（Apple Music artist 风格）。
- **Layout**：3 列 KPI（已订阅/本期新片/累计收录）+ tab（全部/已订阅/推荐）+ artist 网格 `minmax(180px,1fr)`。
- **Artist 卡**：96px 圆头像（演员色 + 已订阅且有新片时右上 `+N` 红角标）+ 名/罗马字 + 数量/节奏 chip + 整宽订阅按钮（绿/灰切换，联动 KPI）。

### 7. 下载任务（Downloads）
- **Purpose**：下载队列管理。
- **Layout**：顶栏聚合速度 pill（↓总速 · ↑）；下载器源 pill（状态点 + 名称）；状态分段（下载中/排队/已完成/失败）+ 任务行。
- **行**：缩略图 + 名称 + meta（番号/体积/peers/eta）+ 进度条（active=accent / paused=灰 / done=绿）+ 右侧 %速度或完成/失败 badge + 操作。
- **逻辑**：暂停/继续切换（图标 + 速度/eta 变）；移除（出列 + 计数更新）；失败行显示错误原因 + 重试（移回 active）；完成行可"在片库整理"。

### 8. 片库整理（Library Organize）
- **Components**：scan 进度环（conic-gradient `--p`）+ 信息 + 暂停/应用全部建议；分段（重复/命名规范/孤立文件）。
- **重复组**：番号头 + 文件列表，每项单选「保留」圆钮（其余进回收站）+ 路径(mono)/体积/分辨率/入库日期。
- **命名规范**：旧名（删除线灰）→ 箭头 → 新名（绿 mono）+ 原因 + 跳过/应用。
- **孤立文件**：空态引导。

### 9. 运营总览（Operations）
- **Components**：4 KPI；数据源健康面板（脉冲状态点 ok/warn/bad + 名称/描述 + 延迟）；下载吞吐 CSS 柱状图（今日列 accent）；存储分布堆叠条 + 图例；近期任务时间线（着色图标 + 标题 + 时间）。

### 10. 配置中心（Settings）
- **Layout**：左侧 sticky 分类 tab（通用/数据源/下载/整理/通知）+ 右侧表单卡。
- **Components**：设置行（标题 nowrap + 描述 wrap + 控件）；iOS 风格开关（46×28 轨道，thumb `translateX(18px)`，spring）；分段控件；文本/mono/password 输入；底部 恢复默认/保存。

## Interactions & Behavior
- **导航**：桌面侧栏（可折叠，spring width 过渡）；移动端（≤820px）侧栏隐藏，出现 **Liquid Glass 浮动 tab bar**（距底边 `max(16px, safe-area)`、左右 12px、圆角 26px、强模糊）；主 tab = 今日/影库/策展/下载，其余进「更多」底部 sheet（spring 上滑、grabber、3 列网格、点击跳转并关闭、点 scrim 关闭）。
- **VideoModal**（影片详情，沉浸式）：全屏 backdrop（模糊）+ 大封面头图 + ESC 关闭 + ←/→ 翻片 + 关闭/上一/下一浮钮；body = 操作按钮（播放/下载/收藏）+ 元信息 grid + 演员订阅条 + 题材 chip 云 + 磁力列表（FHD/字幕/HD + 推荐 badge）+ **相关推荐横向轨道**（同制作商/同演员，可点进）。入场 `pop` spring。
- **动效**：标准 `--ease: cubic-bezier(0.22,1,0.36,1)`；微弹 `--spring: cubic-bezier(0.34,1.4,0.5,1)` 仅给浮岛/弹窗/开关；`fast 150 / std 260 / slow 420`。全局 `prefers-reduced-motion` 兜底。
- **悬停/按压**：海报 hover 上抬 4px + 阴影增强、收藏钮浮现；卡片 active 微缩。

## State Management
- 全局：`screen`(当前屏)、`modal`(选中影片)、`collapsed`(侧栏)、`moreOpen`(移动端 sheet)、Tweaks(`accent`/`theme`/`density`/`glassChrome`)。
- 各屏局部：筛选/排序/分段 tab、选择集（批量）、候选/下载/订阅的可变状态数组、shuffle seed。
- 落地 Vue 时：屏切换走 vue-router；这些局部状态用各 view 的 `setup()` ref/reactive 即可，与现有结构一致。

## Design Tokens
全部定义在 `JavHub Redesign/styles.css` 的 `:root` 与 `[data-theme]`。要点：

**颜色（深色，默认）**：`--bg #08080B` · `--canvas #0F0F14` · `--card #17171E` · `--card-2 #1C1C25` · `--hairline rgba(255,255,255,.075)` · 文本 `#F4F4F7 / #9D9DA7 / #66666F`。
**颜色（浅色）**：`--bg #ECECEF` · `--canvas #FBFBFD` · `--card #FFF` · 文本 `#16161B / #57575F / #8C8C95`。
**Accent**：默认 `#7C8CFF`（rgb 124,140,255）；Tweaks 备选 珊瑚 `#FF7A66` / 翡翠 `#46CE96` / 品红 `#FF6FA5` / 纯白 `#EDEDF2`。
**语义**：ok `#54D596` · warn `#FFC24B` · bad `#FF6F6F` · info `#62B6FF`（均配 0.16 alpha 底）。
**间距**：4/8 阶梯 `--s1..--s10` = 4·8·12·16·20·24·32·44·56·72。
**圆角**：海报 14 · 卡片 18 · 大面板/玻璃 24 · 胶囊 999 · chip 10。
**字阶**：display 40/700/-0.8 · h1 30/700/-0.5 · h2 22/650/-0.3 · h3 17/600 · body 15/450 · callout 14/500 · caption 12/550 · micro 11/600。
**字体**：系统栈 `-apple-system, BlinkMacSystemFont, "SF Pro Display"…`（与现有一致）。
**玻璃**：chrome 用 `backdrop-filter: blur(40px) saturate(1.6)` + `--glass-border` + specular 高光边；阴影 `--shadow-card` / `--shadow-pop`。

## Assets
- **无外部图片**：所有封面/头图都是程序化 `radial-gradient` 占位（模拟"色彩从内容来"）。落地时替换为真实封面（现有 `imageUrl.js` 体系）。占位生成函数见 `data.js` 的 `grad()`。
- **图标**：内联 SVG（24×24，stroke 1.7），路径表在 `components.jsx` 的 `PATHS`。可映射到现有 `appNavigation.js` 的图标组件。
- 参考稿：仓库内 `docs/favorite-subscription-card-mockup.png`（策展卡方向）。

## 映射回现有 Vue 代码
| 原型 | 你的代码 | 动作 |
|---|---|---|
| token | `assets/main.css :root` | 合并 `--canvas`/`--card` 实底层；`--accent` 改非黑 |
| 玻璃只给 chrome | `App.vue` 内容区 | `--content-material` 提到接近实底 |
| PosterCard | `AppleVideoCard.vue` | 放大封面占比、角标化番号/类型、hover 抬升 |
| 今日仪表盘 | 新建 `Today.vue` + 改首页路由 | 把现 Home(下载) 降级为 `/downloads` |
| 批量工具栏 | `Search.vue`/列表页 | 新增多选态 + 浮动 batch-bar |
| 移动浮岛 + 更多 sheet | `App.vue` bottom-nav | 对齐现有 C2 浮岛意图实现 |

## Files
原型源码（设计参考）：
- `JavHub Redesign/JavHub Redesign.html` — 入口
- `JavHub Redesign/styles.css` — **全部设计 token 与组件样式（最重要）**
- `JavHub Redesign/data.js` — mock 数据 + 封面渐变生成
- `JavHub Redesign/components.jsx` — Icon / PosterCard / ActRow / SectionHead
- `JavHub Redesign/screens.jsx` — 今日 / 影库 / 私人策展 / VideoModal
- `JavHub Redesign/screens2.jsx` — 运营总览 / 片库整理 / 配置中心
- `JavHub Redesign/screens3.jsx` — 随机探索 / 候选确认 / 演员订阅
- `JavHub Redesign/screens4.jsx` — 下载任务
- `JavHub Redesign/app.jsx` — App 壳 / 侧栏 / 移动导航 / Tweaks 接入
- `JavHub Redesign/tweaks-panel.jsx` — Tweaks 面板（演示用，落地可忽略）
- `JavHub Redesign/设计语言.html` — 人类可读的设计语言文档
