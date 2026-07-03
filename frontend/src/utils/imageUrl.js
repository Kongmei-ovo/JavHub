/**
 * DMM 封面 URL 工具
 *
 * 封面的"身份"= 目录段 + 番号，这是库里 jacket_full_url 已经存好的相对路径
 * （如 `digital/video/achj00017/achj00017pl` 或 `mono/movie/adult/ebod093/ebod093pl`），
 * 不需要、也不应该再从低清 URL 反推番号（前导数字 / h_·n_ 前缀 / 素人 js·jp 后缀都会让
 * 正则静默失配，退回低清 —— 这正是过去封面不清晰的根因）。
 *
 * "高清"只是主机档位，不改路径：
 *   - 老库 pics.dmm.co.jp/{path}pl          → ~800px，全目录通用、体积轻（卡片够用）
 *   - 高清 CDN awsimgsrc.dmm.co.jp/pics_dig/… → 最高 2184px（仅数字版有；全屏时才值得）
 *
 * 2184px 只存在于 digital/video 目录（数字发行版）。一部 mono/movie/adult 的 DVD 片，
 * 若发过数字版，其高清藏在补零后的 digital/video 孪生路径里（ebod093→ebod00093）。
 */

const DMM_LEGACY = 'https://pics.dmm.co.jp'
const DMM_HD = 'https://awsimgsrc.dmm.co.jp/pics_dig'
// 后端会把相对路径拼成这些主机的绝对 URL；也有端点直接下发相对路径。两种都要能还原。
const DMM_HOST_PREFIX = /^https?:\/\/(?:pics\.dmm\.co\.jp|awsimgsrc\.dmm\.co\.jp\/pics_dig|awsimgsrc\.dmm\.co\.jp|awsimgsrc\.dmm\.com\/dig|awsimgsrc\.dmm\.com)\//i
const DMM_CATALOG_ROOT = /^(?:digital|mono)\//i

/**
 * 从任意封面引用还原 DMM 相对目录路径（无主机、无 .jpg）。
 * 兼容后端拼好的绝对 URL 与原始相对路径；非 DMM 引用（蛋源/鸡源/占位图）返回 ''。
 */
function dmmRelativePath(ref) {
  const s = String(ref || '').trim()
  if (!s) return ''
  const stripped = s.replace(DMM_HOST_PREFIX, '').replace(/^\/+/, '')
  if (/^https?:\/\//i.test(stripped)) return '' // 其它绝对主机（蛋源/鸡源）
  const path = stripped.replace(/\.jpg$/i, '')
  return DMM_CATALOG_ROOT.test(path) ? path : ''
}

/**
 * DMM 有两张不同比例的图，别混：
 *   ps（含素人 js）= 封面，竖版长方形（ratio≈0.70）→ 卡片用这张
 *   pl（含素人 jp）= 大图，横版 front+back 拼版（ratio≈1.49）→ 弹窗用这张
 * splitSuffix 把路径拆成 base(去后缀) + 后缀，好在两种变体间切换。
 */
function splitSuffix(path) {
  const m = String(path || '').match(/^(.*?)(ps|pl|js|jp)$/i)
  return m ? { base: m[1], suffix: m[2].toLowerCase() } : { base: String(path || ''), suffix: '' }
}

/** 把干净的 {字母}{数字} 番号补零到 5 位（digital 目录的写法）；其它形态原样返回 */
function padContentId(cid) {
  return cid.replace(/^([a-z]+)(\d+)$/i, (m, prefix, num) => (prefix.length >= 5 ? m : prefix + num.padStart(5, '0')))
}

/** DMM 相对路径 → 老库绝对 URL 供 <img> 直接使用；已是绝对 URL 或非 DMM 值原样返回 */
function dmmAbsolutize(ref) {
  const s = String(ref || '').trim()
  if (!s || /^https?:\/\//i.test(s)) return s
  const path = dmmRelativePath(s)
  return path ? `${DMM_LEGACY}/${path}.jpg` : s
}

/**
 * 某路径对应的 digital/video 数字孪生 base（不带后缀）——高清就藏在这里；无则返回 ''。
 * digital/video 本身即孪生；mono/movie 的 DVD 片（含无 adult 子目录、只下发 mono 番号的
 * catalog 端点）借补零后的数字发行版。番号需为干净的 {字母}{数字}——tk·前导数字·h_·n_
 * 无法可靠补零则返回 ''，交由 @error 降到给定路径。数字版竖封 ps 最高 1032px、横版 pl 最高 2184px。
 */
function digitalTwinBase(base, cid, cleanCid) {
  if (base.startsWith('digital/video/')) return base
  if (base.startsWith('mono/movie/') && cleanCid) {
    const padded = padContentId(cid)
    return `digital/video/${padded}/${padded}`
  }
  return ''
}

/** 卡片兜底用：把 DMM 引用的大图后缀 pl→ps / jp→js 翻成竖封（保留主机与路径）；非 DMM 原样透传 */
function toPortraitRef(ref) {
  const s = String(ref || '').trim()
  if (!s || !dmmRelativePath(s)) return s
  return s.replace(/pl(\.jpg)?$/i, 'ps$1').replace(/jp(\.jpg)?$/i, 'js$1')
}

/**
 * 封面 URL 候选，按"最优先"排序，供会在 @error 时逐级降级的 <img> 使用。
 *
 * hd=false（卡片=竖版封面 ps）：优先高清 CDN 上数字版竖封(最高 1032px)，再退回库里给的原始竖封缩略图。
 * hd=true （弹窗=横版大图 pl）：优先高清 CDN 数字版大图(最高 2184px)，再退老库 800px 大图。
 * ⚠ 卡片绝不返回 pl（横图塞竖卡会被裁成一团）；弹窗才用 pl。
 * 非 DMM 封面（蛋源/鸡源）原样透传。最后再挂上原始引用，保证任何情况都有图可显示。
 */
export function dmmCoverCandidates(video = {}, { hd = false, preferred = '' } = {}) {
  const refs = [preferred, video?.jacket_full_url, video?.jacket_thumb_url, video?.cover_url, video?.cover]
  const out = []
  const add = (value) => {
    const url = String(value || '').trim()
    if (url && !out.includes(url)) out.push(url)
  }

  let path = ''
  for (const ref of refs) {
    const found = dmmRelativePath(ref)
    if (found) { path = found; break }
  }

  if (path) {
    const { base } = splitSuffix(path)
    const cid = base.split('/').pop() || ''
    const cleanCid = /^[a-z]+\d+$/i.test(cid)
    const isAmateur = base.startsWith('digital/amateur/')
    const twinBase = digitalTwinBase(base, cid, cleanCid)
    if (hd) {
      // 弹窗大图 = 横版 pl（素人 jp）
      const large = isAmateur ? 'jp' : 'pl'
      if (twinBase) add(`${DMM_HD}/${twinBase}${large}.jpg`)
      add(`${DMM_LEGACY}/${base}${large}.jpg`)
    } else {
      // 卡片封面 = 竖版 ps（素人 js）
      const thumb = isAmateur ? 'js' : 'ps'
      if (twinBase) add(`${DMM_HD}/${twinBase}${thumb}.jpg`)
    }
  }

  // 兜底原始引用：弹窗按原样(大图)；卡片把 DMM pl→ps 翻成竖封(不换主机)，非 DMM 原样透传。
  for (const ref of refs) add(hd ? dmmAbsolutize(ref) : toPortraitRef(ref))
  return out
}

/**
 * 低清横版缩略图 URL（直接从库取，不做转换）
 */
export function jacketThumbUrl(video) {
  return video?.jacket_thumb_url || video?.jacket_full_url || null
}

export function videoCardCoverUrl(video) {
  return dmmCoverCandidates(video)[0] || ''
}

/**
 * 构建高清剧照 URL
 * 低清：https://pics.dmm.co.jp/digital/video/{id}/{id}-{n}.jpg
 * 高清：https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/{id}/{id}jp-{n}.jpg
 * 兜底：https://awsimgsrc.dmm.co.jp/dig/digital/video/{id}/{id}jp-{n}.jpg
 */
export function galleryFullUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  // path 格式: digital/video/miaa00784/miaa00784-3
  const lastDotIdx = path.lastIndexOf('.')
  const base = lastDotIdx >= 0 ? path.substring(0, lastDotIdx) : path
  const lastDashIdx = base.lastIndexOf('-')
  if (lastDashIdx < 0) return `https://awsimgsrc.dmm.co.jp/pics_dig/${base}jp.jpg`
  const galleryId = base.substring(0, lastDashIdx) // e.g. digital/video/miaa00784/miaa00784
  const num = base.substring(lastDashIdx + 1)       // e.g. 3
  // 先试 pics_dig 高清路径
  return `https://awsimgsrc.dmm.co.jp/pics_dig/${galleryId}jp-${num}.jpg`
}

/**
 * 低清剧照 URL（兜底）
 */
export function galleryThumbUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `https://pics.dmm.co.jp/${path}.jpg`
}

/**
 * gfriends 头像走的是 jsdelivr 的 GitHub 镜像，主入口 cdn.jsdelivr.net 已对该超大仓库
 * 返回 503（连 README 都拒），但 gcore POP 仍在服务。把主机名换成可用的 POP，路径与
 * ?t= 缓存戳原样保留，避免重新同步整库。其余主机的 http(s) URL 原样放行。
 */
function rewriteDeadCdnHost(url) {
  return url.replace(
    /^https?:\/\/cdn\.jsdelivr\.net\/gh\/gfriends\/gfriends@/i,
    'https://gcore.jsdelivr.net/gh/gfriends/gfriends@',
  )
}

/**
 * 演员头像 URL
 * awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/{filename}
 */
export function actressImgUrl(imageUrl) {
  if (!imageUrl) return null
  const url = String(imageUrl).trim()
  if (!url) return null
  if (/^https?:\/\//i.test(url)) return rewriteDeadCdnHost(url)
  const normalized = url.replace(/^\/+/, '')
  if (normalized.startsWith('pics_dig/')) {
    return `https://awsimgsrc.dmm.co.jp/${normalized}`
  }
  if (normalized.startsWith('mono/actjpgs/')) {
    return `https://awsimgsrc.dmm.co.jp/pics_dig/${normalized}`
  }
  return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${normalized}`
}
