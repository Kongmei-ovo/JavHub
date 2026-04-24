/**
 * DMM 图片 URL 映射工具
 *
 * 低清库：pics.dmm.co.jp/mono/movie/adult/{raw_id}/{raw_id}ps.jpg
 * 高清新库：awsimgsrc.dmm.co.jp/pics_dig/digital/video/{padded_id}/{padded_id}pl.jpg (竖版)
 *                                                    {padded_id}/{padded_id}ps.jpg (横版)
 * 高清旧库：awsimgsrc.dmm.co.jp/dig/mono/movie/{raw_id}/{raw_id}ps.jpg (TK等系列)
 *
 * 补零规则：部分系列需要将数字部分补到5位（miaa784→miaa00784）
 *          TK等字母偏长的系列不需要补零（tkekdv814→tkekdv814）
 */

/**
 * 将内容 ID 的数字部分补零到5位（仅当数字部分 < 10000 时）
 * miaa784     → miaa00784
 * tkekdv814   → tkekdv814   （不补，字母部分偏长）
 * 1stars540   → 1stars00540
 */
function padContentId(id) {
  return id.replace(/^([a-z]+)(\d+)$/i, (match, prefix, num) => {
    // 字母部分 ≥ 5 个字母：不补零（TK系列等）
    if (prefix.length >= 5) return id
    return prefix + num.padStart(5, '0')
  })
}

/**
 * 判断是否为 TK 系列（使用旧库 dig/mono/movie）
 */
function isTkSeries(id) {
  return /^[a-z]{5,}\d+$/i.test(id)
}

/**
 * 从低清 jacket_thumb_url 提取 content_id
 * 例: https://pics.dmm.co.jp/mono/movie/adult/miaa784/miaa784ps.jpg → miaa784
 */
function extractContentId(jacketUrl) {
  if (!jacketUrl) return null
  const m = jacketUrl.match(/\/([a-z]+\d+)(?:ps|pl)\.jpg$/i)
  return m ? m[1] : null
}

/**
 * 构建高清竖版大图 URL (pl.jpg)
 * awsimgsrc.dmm.co.jp/pics_dig/digital/video/{id}/{id}pl.jpg
 * 兜底：awsimgsrc.dmm.co.jp/dig/mono/movie/{raw_id}/{raw_id}pl.jpg
 */
export function jacketFullUrl(jacketUrl) {
  if (!jacketUrl) return null
  const id = extractContentId(jacketUrl)
  if (!id) return jacketUrl
  if (isTkSeries(id)) {
    // TK系列用旧库 dig/mono/movie
    return `https://awsimgsrc.dmm.co.jp/dig/mono/movie/${id}/${id}pl.jpg`
  }
  const padded = padContentId(id)
  if (padded !== id) {
    // 需要补零的系列（数字不足5位）：pics_dig/digital/video
    return `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/${padded}/${padded}pl.jpg`
  }
  // 不需要补零：优先 pics_dig/digital/video，兜底 dig/mono/movie
  return `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/${id}/${id}pl.jpg`
}

/**
 * 构建高清横版 URL (ps.jpg)
 * awsimgsrc.dmm.co.jp/pics_dig/digital/video/{id}/{id}ps.jpg
 * 兜底：awsimgsrc.dmm.co.jp/dig/mono/movie/{raw_id}/{raw_id}ps.jpg
 */
export function jacketHdUrl(jacketUrl) {
  if (!jacketUrl) return null
  const id = extractContentId(jacketUrl)
  if (!id) return jacketUrl
  if (isTkSeries(id)) {
    // TK系列用旧库 dig/mono/movie
    return `https://awsimgsrc.dmm.co.jp/dig/mono/movie/${id}/${id}ps.jpg`
  }
  const padded = padContentId(id)
  if (padded !== id) {
    // 需要补零的系列：pics_dig/digital/video
    return `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/${padded}/${padded}ps.jpg`
  }
  return `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/${id}/${id}ps.jpg`
}

/**
 * 低清横版缩略图 URL（直接从库取，不做转换）
 */
export function jacketThumbUrl(video) {
  return video?.jacket_thumb_url || video?.jacket_full_url || null
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
 * 演员头像 URL
 * awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/{filename}
 */
export function actressImgUrl(imageUrl) {
  if (!imageUrl) return null
  if (imageUrl.startsWith('http')) return imageUrl
  return `https://awsimgsrc.dmm.co.jp/pics_dig/mono/actjpgs/${imageUrl.replace(/^\//, '')}`
}
