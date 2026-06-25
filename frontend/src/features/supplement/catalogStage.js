// Field-first funnel (一部片一个阶段): a metadata gap holds the film in 缺元数据
// until fields complete; then it surfaces by acquisition state. Backend emits
// `funnel_stage` directly — prefer it; this mirror is the fallback + test spec.
//
//   缺元数据 ──► (字段齐) ──► 待找源 ──► 可下载 ──► 获取中 ──► 已入库 ✓
export function catalogStage(film) {
  if (film && film.funnel_stage) return film.funnel_stage
  if (!film || !film.metadata_complete) return 'meta_gap'
  if (film.status === 'owned') return 'complete'
  if (film.status === 'in_progress') return 'fetching'
  if (film.status === 'available') return 'downloadable'
  return 'find_source'
}

// label = 人话状态；tone = 语义色键（映射 main.css 语义色）；action = 主操作文案
// （null 表示该阶段无主操作，列里放进度/对勾）；primary = 是否实心主按钮。
export const STAGE_META = {
  find_source: { label: '待找源', tone: 'find', action: '找源', primary: false },
  downloadable: { label: '可下载', tone: 'dl', action: '下载', primary: true },
  fetching: { label: '获取中', tone: 'prog', action: null, primary: false },
  meta_gap: { label: '缺元数据', tone: 'meta', action: '补元数据', primary: false },
  complete: { label: '齐全', tone: 'ok', action: null, primary: false },
}

export const STAGE_ORDER = ['find_source', 'downloadable', 'fetching', 'meta_gap', 'complete']

// completeness summary tier -> stage, for filter-chip counts.
export const STAGE_SUMMARY_KEY = {
  find_source: 'needs_magnet',
  downloadable: 'available',
  fetching: 'in_progress',
  meta_gap: 'owned_meta_gap',
  complete: 'owned_complete',
}

// Which lifecycle stages belong to each of the two action sub-tabs.
// ① 影片目录 is the full list (no stage filter); ② 字段 / ③ 下载源 below.
export const FUNNEL_TABS = {
  fields: ['meta_gap'],
  sources: ['find_source', 'downloadable', 'fetching'],
}
