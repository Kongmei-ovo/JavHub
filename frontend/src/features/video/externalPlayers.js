// 外连播放器表 + scheme 占位符替换。
// 抄自 OpenList(OpenList-Frontend):
//   - players[]        ← src/pages/home/previews/video_box.tsx
//   - convertURL()     ← src/utils/str.ts
// 占位符:$durl=直链(302), $edurl=encodeURIComponent, $bdurl=base64, $name=文件名;
// $url/$eurl/$burl 同理但取 raw_url(我们这里 raw_url 默认等于直链)。
// 直链走后端 302:浏览器/外部播放器跟随重定向,带各自 UA 直连网盘 CDN(见 backend open115 stream)。

export const EXTERNAL_PLAYERS = [
  { name: 'IINA', scheme: 'iina://weblink?url=$edurl', platforms: ['MacOS'] },
  { name: 'PotPlayer', scheme: 'potplayer://$durl', platforms: ['Windows'] },
  { name: 'VLC', scheme: 'vlc://$durl', platforms: ['Windows', 'MacOS', 'Linux', 'Android', 'iOS'] },
  { name: 'Android', scheme: 'intent:$durl#Intent;type=video/*;S.title=$name;end', platforms: ['Android'] },
  { name: 'nPlayer', scheme: 'nplayer-$durl', platforms: ['Android', 'iOS'] },
  { name: 'OmniPlayer', scheme: 'omniplayer://weblink?url=$durl', platforms: ['MacOS'] },
  { name: 'Fig Player', scheme: 'figplayer://weblink?url=$durl', platforms: ['MacOS'] },
  { name: 'Infuse', scheme: 'infuse://x-callback-url/play?url=$durl', platforms: ['MacOS', 'iOS'] },
  { name: 'SenPlayer', scheme: 'senplayer://x-callback-url/play?url=$edurl', platforms: ['MacOS', 'iOS'] },
  { name: 'Fileball', scheme: 'filebox://play?url=$durl', platforms: ['MacOS', 'iOS'] },
  { name: 'MX Player', scheme: 'intent:$durl#Intent;package=com.mxtech.videoplayer.ad;S.title=$name;end', platforms: ['Android'] },
  { name: 'MX Player Pro', scheme: 'intent:$durl#Intent;package=com.mxtech.videoplayer.pro;S.title=$name;end', platforms: ['Android'] },
  { name: 'iPlay', scheme: 'iplay://play/any?type=url&url=$bdurl', platforms: ['iOS'] },
  { name: 'mpv', scheme: 'mpv://$edurl', platforms: ['Windows', 'MacOS', 'Linux', 'Android'] },
]

function applyOps(token, value) {
  // token 形如 $edurl / $burl,取其中的 e/b 字母按出现的逆序套用 encode / base64。
  const ops = token.match(/[eb]/g)
  let u = value
  if (ops) {
    for (const o of ops.reverse()) {
      if (o === 'e') u = encodeURIComponent(u)
      else if (o === 'b') u = btoa(u)
    }
  }
  return u
}

export function convertURL(scheme, { rawUrl = '', name = '', dUrl = '' } = {}) {
  let ans = scheme.replace('$name', name)
  ans = ans.replace(/\$[eb_]*url/, (old) => applyOps(old, rawUrl))
  ans = ans.replace(/\$[eb_]*durl/, (old) => applyOps(old, dUrl))
  return ans
}

export function detectPlatform(ua = (typeof navigator !== 'undefined' ? navigator.userAgent : '')) {
  if (/Android/i.test(ua)) return 'Android'
  if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS'
  if (/Macintosh|Mac OS X/i.test(ua)) return 'MacOS'
  if (/Windows/i.test(ua)) return 'Windows'
  if (/Linux/i.test(ua)) return 'Linux'
  return 'MacOS'
}

export function playersForPlatform(platform = detectPlatform()) {
  return EXTERNAL_PLAYERS.filter((p) => p.platforms.includes(platform))
}
