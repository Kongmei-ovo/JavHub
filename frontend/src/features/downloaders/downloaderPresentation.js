export const DEFAULT_DOWNLOADER_TYPES = [
  { value: 'open115', label: '115 Open（原生）' },
  { value: 'qbittorrent', label: 'qBittorrent' },
  { value: 'transmission', label: 'Transmission' },
  { value: 'synology', label: 'Synology Download Station' },
  { value: 'aria2', label: 'Aria2' },
  { value: 'deluge', label: 'Deluge' },
  { value: 'flood', label: 'Flood' },
  { value: 'rutorrent', label: 'ruTorrent' },
  { value: 'utorrent', label: 'uTorrent' },
]

const DOWNLOADER_TYPE_MARKS = {
  open115: '115',
  qbittorrent: 'QB',
  transmission: 'TR',
  synology: 'SY',
  aria2: 'A2',
  deluge: 'DE',
  flood: 'FL',
  rutorrent: 'RU',
  utorrent: 'UT',
}

const DOWNLOADER_ADDRESS_PLACEHOLDERS = {
  open115: '',
  qbittorrent: 'http://localhost:8080',
  transmission: 'http://localhost:9091',
  synology: 'http://nas:5000',
  aria2: 'http://localhost:6800',
  deluge: 'http://localhost:8112',
  flood: 'http://localhost:3000',
  rutorrent: 'https://myrut.com/rutorrent',
  utorrent: 'http://127.0.0.1:8080/gui/',
}

const TAGGABLE_DOWNLOADER_TYPES = new Set([
  'qbittorrent',
  'transmission',
  'deluge',
  'flood',
  'rutorrent',
  'utorrent',
])

export function createDefaultDownloaderTypes() {
  return DEFAULT_DOWNLOADER_TYPES.map(type => ({ ...type }))
}

export function downloaderTypeMark(type) {
  return DOWNLOADER_TYPE_MARKS[type] || String(type || 'DL').slice(0, 2).toUpperCase()
}

export function downloaderAddressPlaceholder(type) {
  return DOWNLOADER_ADDRESS_PLACEHOLDERS[type] || 'http://localhost'
}

export function downloaderPathPlaceholder(type) {
  if (type === 'synology') return 'video/downloads'
  if (type === 'qbittorrent') return '/downloads 或 category:Movies'
  if (type === 'open115') return '/JavHub'
  if (type === 'utorrent') return 'movie\\ 或留空'
  return '/downloads'
}

export function supportsDownloaderTags(type) {
  return TAGGABLE_DOWNLOADER_TYPES.has(type)
}

export function tokenPlaceholder(type) {
  return type === 'aria2' ? 'rpc-secret，可选' : '可选'
}
