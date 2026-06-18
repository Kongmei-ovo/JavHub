export const pageSizeOptions = [15, 30, 50, 100]

export const displayLangOptions = [
  { value: 'ja', label: '日文' },
  { value: 'zh', label: '中文' },
  { value: 'en', label: '英文' },
]

export const searchSortOptions = [
  { value: 'random', label: '随机' },
  { value: 'none', label: '无排序' },
  { value: 'release_date_desc', label: '发行日新到旧' },
  { value: 'release_date_asc', label: '发行日旧到新' },
  { value: 'title_ja_asc', label: '标题 A-Z' },
  { value: 'title_ja_desc', label: '标题 Z-A' },
  { value: 'runtime_mins_desc', label: '时长长到短' },
  { value: 'runtime_mins_asc', label: '时长短到长' },
]

export const downloadPolicyOptions = [
  { value: 'manual', label: '人工批准', hint: '只生成候选，下载必须手动批准。' },
  { value: 'rules', label: '规则自动', hint: '自动处理允许来源中符合规则的候选。' },
  { value: 'auto', label: '全自动', hint: '自动补磁力并下发允许来源中的候选。' },
]

export const candidateSourceOptions = [
  { value: 'subscription', label: '订阅发现' },
  { value: 'inventory', label: '库存发现' },
  { value: 'supplement', label: '补全发现' },
  { value: 'manual', label: '手动加入' },
]
