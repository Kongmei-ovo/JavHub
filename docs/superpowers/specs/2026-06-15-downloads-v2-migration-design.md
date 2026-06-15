# Downloads v2 独立迁移设计

## 背景

JavHub 的 v2 重设计已经完成 Today、候选确认、补全管理和内容材质等主要迁移，但 `/downloads` 仍由旧的 `views/Home.vue` 承载。该页面虽然使用了 v2 token，并已删除候选 tab，却仍请求候选汇总、展示候选指标，并在空态中引导用户处理候选。

候选确认已经有独立的 `/candidates` 页面和完整状态模型。下载页继续持有候选摘要会造成职责重复，并可能让 `/downloads` 与 `/candidates` 显示不同的候选数量。迁移的根因不是单个样式遗漏，而是早期规划中的“新建独立 Downloads 页面并退役 legacy Home”没有完成。

## 目标

- 让 `/downloads` 由职责明确的 `Downloads.vue` 承载。
- 保留现有真实下载任务、失败重试、删除和下载源配置能力。
- 使用 v2 的紧凑行式信息层级展示下载任务。
- 移除下载页对候选摘要和候选 UI 的依赖。
- 保留现有下载筛选、下载源 tab 和旧候选深链兼容。
- 增加测试约束，防止路由或页面重新依赖 `Home.vue` 和候选逻辑。

## 非目标

- 不修改后端 API 或数据库模型。
- 不伪造实时速度、下载百分比、剩余时间、peer 数或暂停/继续能力。
- 不重做 Candidates、Today 或其他已经迁移到 v2 的页面。
- 不改变下载器配置的数据结构或保存流程。
- 不引入新的全局状态管理方案。

## 页面结构

### 顶部

页面标题为“下载任务”，副标题只显示真实下载任务汇总，例如进行中和排队数量。右侧保留搜索影片、磁链解析和手动刷新入口。

### 状态摘要与筛选

页面展示四个真实状态：

- 待处理：`pending`
- 下载中：`downloading`
- 已完成：`completed`
- 失败：`failed`

状态摘要可点击，并通过 `task_status` 查询参数同步筛选。页面不再加载或展示候选数量、候选来源或可批准数量。

### 下载任务列表

任务列表由现有 `TaskList.vue` 承载，但视觉改为 v2 紧凑行：

- 左侧媒体占位和番号。
- 中间显示标题、创建时间、下载器和错误信息。
- 右侧显示真实状态。
- 失败任务提供重试操作。
- 所有任务提供确认后移除操作。

后端尚未提供进度、速度或暂停命令，因此任务行不显示假进度条或不可用按钮。

### 下载源

下载源继续使用现有 `DownloaderManagementPanel.vue`，并保持异步加载。`?tab=downloaders` 可直接打开下载源面板。

### 空态

无任务时只提供与下载职责一致的下一步：

- 有状态筛选时，主要操作为清除筛选。
- 无筛选时，主要操作为进入影库。
- 次要操作为进入磁链解析。

空态不再读取或引导候选确认。

## 路由与兼容

- `/downloads` 懒加载 `views/Downloads.vue`。
- `?tab=tasks`、`?tab=downloaders` 和 `?task_status=<status>` 保持有效。
- `/downloads?tab=candidates` 重定向到 `/candidates`。
- 重定向时删除 `tab=candidates`，保留其余查询参数。
- `/tasks` 继续重定向到 `/downloads`。

## 状态与数据流

`Downloads.vue` 继续使用页面局部状态：

- `tasks`
- `stats`
- `statsLoaded`
- `filterStatus`
- `activeTab`
- `retryingTasks`
- 下载器配置、编辑器和测试状态

页面挂载时加载任务；仅在下载源 tab 激活时加载下载器。任务每 30 秒刷新一次，卸载时清理 timer。

任务加载失败时保留当前数据并记录诊断信息，避免把网络失败伪装成空列表。失败重试使用任务级 in-flight guard，完成后重新加载任务。

## 文件边界

- 新增 `frontend/src/views/Downloads.vue`
- 新增 `frontend/src/views/Downloads.test.js`
- 新增 `frontend/src/features/downloads/downloads.css`
- 更新 `frontend/src/features/home/TaskList.vue`
- 更新 `frontend/src/features/home/DownloadStatsBar.vue`
- 更新 `frontend/src/router/index.js`
- 删除 `frontend/src/views/Home.vue`
- 删除或迁移 `frontend/src/views/Home.test.js`
- 更新引用旧页面名或候选耦合的视觉、排版和工作流测试

现有下载器配置逻辑优先原样迁移，避免在 UI 迁移中改变配置行为。

## 测试策略

实施遵循测试优先：

1. 新增失败测试，要求 `/downloads` 加载 `Downloads.vue` 且源码不再引用 `Home.vue`。
2. 新增失败测试，要求 Downloads 页面不包含 `candidateStats`、`getDownloadCandidateSummary`、`CandidateOverview` 或候选入口。
3. 新增失败测试，覆盖状态筛选、下载源 tab、旧候选深链和空态行为。
4. 更新 `TaskList` 和 `DownloadStatsBar` 的组件契约测试。
5. 更新 `App.test.js`、`WorkflowIntegration.test.js`、排版和视觉契约中的旧文件引用。
6. 运行前端全量测试与生产构建。
7. 使用本地浏览器检查桌面与移动断点下的 `/downloads`，并确认 `/candidates` 未回退。

## 验收标准

- `/downloads` 不再加载或引用 `Home.vue`。
- 下载页面源码和运行时均不请求候选 summary。
- 页面只展示下载任务与下载源配置。
- 状态筛选、重试、删除、刷新和下载源配置保持可用。
- `/downloads?tab=candidates` 正确转到 `/candidates` 并保留其他查询参数。
- 页面不展示后端没有提供的速度、百分比、暂停或继续能力。
- 前端测试和构建通过。
- 桌面与移动端浏览器验证通过。
