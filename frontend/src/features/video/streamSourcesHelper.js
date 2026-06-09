// SSE 流式拉 m3u8 播放源 + 错误摘要。给 VideoModal 当 helper 用,
// 把 EventSource 生命周期 / 事件解析 / 失败聚合从组件里搬出去。

export function createStreamSession({ code, onItem, onFirstOk, onDone, onAllError }) {
  const sources = []
  let firstOkFired = false
  const es = new EventSource(`/api/v1/stream/sources/${encodeURIComponent(code)}`)
  const close = () => { try { es.close() } catch {} }

  es.onmessage = (ev) => {
    let item
    try { item = JSON.parse(ev.data) } catch { return }
    if (item.source === '_done') {
      close()
      if (!firstOkFired) onAllError?.(sources)
      onDone?.(sources)
      return
    }
    sources.push(item)
    onItem?.(item)
    if (item.status === 'ok' && !firstOkFired) {
      firstOkFired = true
      onFirstOk?.(item)
    }
  }
  es.onerror = () => {
    // 服务端正常 close 也会触发 onerror;以 _done 是否到过判断
    if (es.readyState === EventSource.CLOSED && !firstOkFired) onAllError?.(sources)
    close()
  }
  return { close, sources }
}

export function triggerM3u8Download(m3u8Url, code) {
  const a = document.createElement('a')
  a.href = m3u8Url
  a.download = `${code}.m3u8`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export function formatStreamFailure(sources) {
  const real = sources.filter(s => s.source !== '_done')
  if (!real.length) return '获取播放地址失败'
  const counts = { no_result: 0, error: 0, ok: 0 }
  for (const s of real) counts[s.status] = (counts[s.status] || 0) + 1
  const names = real.map(s => s.source).join('/')
  if (counts.no_result === real.length) return `所有源都未收录该番号(${names})`
  if (counts.error === real.length) return `所有源都请求失败,请检查 FlareSolverr/网络(${names})`
  const errs = real.filter(s => s.status === 'error').map(s => s.source)
  return `未找到播放地址。失败源: ${errs.join('/') || '无'};其余未收录`
}
