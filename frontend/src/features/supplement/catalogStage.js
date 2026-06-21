// Map a completeness film (status + metadata_complete) onto a single lifecycle
// stage. One canonical work carries one stage; the card action follows from it.
//
//   待找源 ──► 可下载 ──► 获取中 ──► 缺元数据 ──► 齐全 ✓
//   └──── 收藏阶段（鸡源 + 磁力 + 下载）────┘└── 元数据阶段（蛋源）──┘
export function catalogStage(film) {
  if (film.status === 'owned') return film.metadata_complete ? 'complete' : 'meta_gap'
  if (film.status === 'in_progress') return 'fetching'
  if (film.status === 'available') return 'downloadable'
  return 'find_source' // needs_magnet / unknown
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
