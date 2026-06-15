import test from 'node:test'
import assert from 'node:assert/strict'
import { installAxiosAdapter } from '../testSupport/axiosAdapter.js'
import { ElMessage } from '../utils/message.js'
import { DEFAULT_CONFIG } from '../features/config/configDefaults.js'

function installRejectingAdapter(t, status = 404, detail = 'Not Found') {
  installAxiosAdapter(t, async (config) => Promise.reject({
    config,
    response: { status, data: { detail } },
    message: `Request failed with status code ${status}`,
    isAxiosError: true,
    toJSON: () => ({}),
  }))
}

test('metatube metadata API is no longer exposed', async () => {
  const { default: api } = await import(`./index.js?metadata-removed-${Date.now()}`)

  assert.equal(api.getVideoMetadata, undefined)
})

test('main path API failure still shows global error toast', async (t) => {
  installRejectingAdapter(t, 500, '服务器内部错误')
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?main-error-${Date.now()}`)

  await assert.rejects(() => api.getVideo('miaa405'))

  assert.equal(errorMock.mock.callCount(), 1)
  assert.equal(errorMock.mock.calls[0].arguments[0], '服务器内部错误')
})

test('duplicate API failures are rate limited globally', async (t) => {
  installRejectingAdapter(t, 500, '服务器内部错误')
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?error-dedupe-${Date.now()}`)

  await assert.rejects(() => api.getVideo('miaa405'))
  await assert.rejects(() => api.getVideo('miaa406'))

  assert.equal(errorMock.mock.callCount(), 1)
})

test('getVideo forwards selected service version as a query param', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { content_id: 'MIAA-784' } }
  })

  const { default: api } = await import(`./index.js?video-service-code-${Date.now()}`)
  await api.getVideo('MIAA-784', { service_code: 'mono' })

  assert.equal(capturedConfig.url, '/v1/videos/MIAA-784')
  assert.deepEqual(capturedConfig.params, { service_code: 'mono' })
})

test('category stats helper is not exposed from the frontend API', async () => {
  const { default: api } = await import(`./index.js?category-stats-removed-${Date.now()}`)

  assert.equal(api.getCategoryStats, undefined)
})

test('listMakers forwards pagination and query params', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`./index.js?makers-pagination-${Date.now()}`)
  await api.listMakers({ page: 2, page_size: 30, q: 'studio' })

  assert.equal(capturedConfig.url, '/v1/makers')
  assert.deepEqual(capturedConfig.params, { page: 2, page_size: 30, q: 'studio' })
})

test('listVideos defaults to skipping total count', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`./index.js?videos-no-total-${Date.now()}`)
  await api.listVideos()

  assert.equal(capturedConfig.url, '/v1/videos')
  assert.deepEqual(capturedConfig.params, { page: 1, page_size: 20, include_total: false })
})

test('config defaults and update payload include Torznab source settings', async (t) => {
  assert.deepEqual(DEFAULT_CONFIG.sources?.torznab, {
    enabled: false,
    name: 'torznab',
    base_url: '',
    api_key: '',
    indexer: 'all',
    categories: '',
    limit: 20,
    timeout: 15,
  })

  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { ok: true } }
  })

  const { default: api } = await import(`./index.js?config-sources-${Date.now()}`)
  await api.updateConfig({
    sources: {
      torznab: {
        ...DEFAULT_CONFIG.sources.torznab,
        enabled: true,
        base_url: 'http://localhost:9696',
      },
    },
  })

  assert.equal(capturedConfig.url, '/v1/config')
  assert.deepEqual(JSON.parse(capturedConfig.data).sources.torznab, {
    enabled: true,
    name: 'torznab',
    base_url: 'http://localhost:9696',
    api_key: '',
    indexer: 'all',
    categories: '',
    limit: 20,
    timeout: 15,
  })
})

test('AI helper APIs send provider-aware requests', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { success: true, models: [] } }
  })

  const { default: api } = await import(`./index.js?ai-provider-${Date.now()}`)
  const draft = {
    provider: 'gemini',
    gemini: {
      base_url: 'https://generativelanguage.googleapis.com/v1beta',
      api_key: '',
      model: 'gemini-2.0-flash',
      timeout: 30,
    },
  }
  await api.testAiModel(draft)
  await api.listAiModels(draft)

  assert.equal(calls[0].url, '/v1/ai/test')
  assert.deepEqual(calls[0].data && JSON.parse(calls[0].data), { provider: 'gemini', ai: draft })
  assert.equal(calls[1].url, '/v1/ai/models')
  assert.deepEqual(calls[1].data && JSON.parse(calls[1].data), { provider: 'gemini', ai: draft })
})

test('JavInfo import APIs use preflight, job creation, chunked upload, status, and cancel endpoints', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    if (config.url === '/v1/javinfo/imports/jobs/7') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 0 } }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/chunks/0') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 4 } }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/chunks/1') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 6 } }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: { ok: true, id: 7, uploaded_bytes: 6, data: [] } }
  })

  const { default: api } = await import(`./index.js?javinfo-import-${Date.now()}`)
  const importDb = { host: 'localhost', database: 'r18' }
  const file = new Blob(['abcdef'])
  file.name = 'r18.dump'
  const progressEvents = []
  const progress = (event) => progressEvents.push(event)

  await api.preflightJavInfoImport(importDb, 6)
  await api.createJavInfoImportJob({ filename: file.name, file_size: file.size, import_db: importDb, confirm_replace: true })
  await api.uploadJavInfoImportDump(7, file, progress, { chunkSize: 4 })
  await api.runJavInfoMigrations(true)
  await api.listJavInfoImportJobs(5)
  await api.cancelJavInfoImportJob(7)

  assert.equal(calls[0].url, '/v1/javinfo/imports/preflight')
  assert.deepEqual(JSON.parse(calls[0].data), { import_db: importDb, expected_size: 6 })
  assert.equal(calls[1].url, '/v1/javinfo/imports/jobs')
  assert.equal(calls[2].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[3].url, '/v1/javinfo/imports/jobs/7/upload/chunks/0')
  assert.equal(calls[3].method, 'put')
  assert.equal(calls[3].headers['Content-Type'], 'application/octet-stream')
  assert.equal(calls[3].headers['X-Chunk-Offset'], '0')
  assert.equal(calls[3].headers['X-Chunk-Size'], '4')
  assert.equal(calls[3].headers['X-Total-Size'], '6')
  assert.equal(calls[4].url, '/v1/javinfo/imports/jobs/7/upload/chunks/1')
  assert.equal(calls[4].headers['X-Chunk-Offset'], '4')
  assert.equal(calls[4].headers['X-Chunk-Size'], '2')
  assert.equal(calls[5].url, '/v1/javinfo/imports/jobs/7/upload/complete')
  assert.equal(calls[6].url, '/v1/javinfo/imports/migrations')
  assert.deepEqual(JSON.parse(calls[6].data), { dry_run: true })
  assert.equal(calls[7].url, '/v1/javinfo/imports/jobs')
  assert.deepEqual(calls[7].params, { limit: 5 })
  assert.equal(calls[8].url, '/v1/javinfo/imports/jobs/7/cancel')
  assert.deepEqual(progressEvents.at(-1), { loaded: 6, total: 6 })
})

test('JavInfo chunk upload resumes from server byte count after a lost chunk response', async (t) => {
  const calls = []
  let jobReads = 0
  let firstChunkAttempts = 0
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    if (config.url === '/v1/javinfo/imports/jobs/7') {
      jobReads += 1
      return {
        config,
        status: 200,
        statusText: 'OK',
        headers: {},
        data: { id: 7, uploaded_bytes: jobReads === 1 ? 0 : 4 },
      }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/chunks/0') {
      firstChunkAttempts += 1
      if (firstChunkAttempts === 1) {
        return Promise.reject({
          config,
          response: { status: 502, data: { detail: 'Bad Gateway' } },
          message: 'Bad Gateway',
          isAxiosError: true,
          toJSON: () => ({}),
        })
      }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 6 } }
  })

  const { default: api } = await import(`./index.js?javinfo-import-resume-${Date.now()}`)
  const file = new Blob(['abcdef'])
  file.name = 'r18.dump'

  await api.uploadJavInfoImportDump(7, file, null, { chunkSize: 4 })

  assert.equal(calls[0].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[1].url, '/v1/javinfo/imports/jobs/7/upload/chunks/0')
  assert.equal(calls[2].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[3].url, '/v1/javinfo/imports/jobs/7/upload/chunks/1')
  assert.equal(calls[3].headers['X-Chunk-Offset'], '4')
  assert.equal(calls[4].url, '/v1/javinfo/imports/jobs/7/upload/complete')
})

test('JavInfo plain sql gzip upload uses chunked upload so restore can be polled separately', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    if (config.url === '/v1/javinfo/imports/jobs/7') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 0 } }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/chunks/0') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, status: 'uploading', uploaded_bytes: 4 } }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/chunks/1') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, status: 'uploading', uploaded_bytes: 6 } }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: { ok: true } }
  })

  const { default: api } = await import(`./index.js?javinfo-import-stream-${Date.now()}`)
  const file = new Blob(['abcdef'])
  file.name = 'r18.sql.gz'
  const progressEvents = []

  await api.uploadJavInfoImportDump(7, file, (event) => progressEvents.push(event), { chunkSize: 4 })

  assert.equal(calls[0].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[1].url, '/v1/javinfo/imports/jobs/7/upload/chunks/0')
  assert.equal(calls[1].method, 'put')
  assert.equal(calls[1].headers['Content-Type'], 'application/octet-stream')
  assert.equal(calls[1].headers['X-Chunk-Offset'], '0')
  assert.equal(calls[2].url, '/v1/javinfo/imports/jobs/7/upload/chunks/1')
  assert.equal(calls[2].headers['X-Chunk-Offset'], '4')
  assert.equal(calls[3].url, '/v1/javinfo/imports/jobs/7/upload/complete')
  assert.notEqual(calls[1].url, '/v1/javinfo/imports/jobs/7/upload')
  assert.deepEqual(progressEvents.at(-1), { loaded: 6, total: 6 })
})

test('JavInfo upload treats a lost complete response as success when job is already restoring', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    if (config.url === '/v1/javinfo/imports/jobs/7/upload/complete') {
      return Promise.reject({
        config,
        response: { status: 502, data: { detail: 'Bad Gateway' } },
        message: 'Bad Gateway',
        isAxiosError: true,
        toJSON: () => ({}),
      })
    }
    if (config.url === '/v1/javinfo/imports/jobs/7' && calls.length > 3) {
      return {
        config,
        status: 200,
        statusText: 'OK',
        headers: {},
        data: { id: 7, status: 'restoring', uploaded_bytes: 6, file_size: 6 },
      }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 0 } }
  })

  const { default: api } = await import(`./index.js?javinfo-import-complete-resume-${Date.now()}`)
  const file = new Blob(['abcdef'])
  file.name = 'r18.dump'

  const response = await api.uploadJavInfoImportDump(7, file, null, { chunkSize: 6 })

  assert.equal(response.data.status, 'restoring')
  assert.equal(calls[0].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[1].url, '/v1/javinfo/imports/jobs/7/upload/chunks/0')
  assert.equal(calls[2].url, '/v1/javinfo/imports/jobs/7/upload/complete')
  assert.equal(calls[3].url, '/v1/javinfo/imports/jobs/7')
})

test('config export API downloads a blob from the config export endpoint', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: new Blob(['config']) }
  })

  const { default: api } = await import(`./index.js?config-export-${Date.now()}`)
  await api.exportConfig()

  assert.equal(calls[0].url, '/v1/config/export')
  assert.equal(calls[0].responseType, 'blob')
})

test('getActressVideos forwards include_supplement and extra params', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [], total_count: 0 } }
  })

  const { default: api } = await import(`./index.js?actress-videos-supplement-${Date.now()}`)
  await api.getActressVideos(123, 1, 20, { include_supplement: '1', service_code: 'digital', year: 2024 })

  assert.equal(capturedConfig.url, '/v1/actresses/123/videos')
  assert.equal(capturedConfig.params.include_supplement, '1')
  assert.equal(capturedConfig.params.service_code, 'digital')
  assert.equal(capturedConfig.params.year, 2024)
})

test('getActressVideos defaults to skipping total count', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [], total_count: -1 } }
  })

  const { default: api } = await import(`./index.js?actress-videos-no-total-${Date.now()}`)
  await api.getActressVideos(123)

  assert.equal(capturedConfig.url, '/v1/actresses/123/videos')
  assert.deepEqual(capturedConfig.params, { page: 1, page_size: 20, include_total: false })
})

test('subscription new movies API forwards compact batch params', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: {} } }
  })

  const { default: api } = await import(`./index.js?subscription-new-movies-${Date.now()}`)
  await api.getNewMovies({ limit_per_actress: 12, cache: '0' })

  assert.equal(capturedConfig.url, '/v1/subscriptions/new_movies')
  assert.deepEqual(capturedConfig.params, { limit_per_actress: 12, cache: '0' })
})

test('numeric path APIs reject path-like identifiers before sending requests', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  })

  const { default: api } = await import(`./index.js?numeric-path-safety-${Date.now()}`)

  assert.throws(() => api.getActress('../123'), /actressId/)
  assert.throws(() => api.getActressVideos('123/status'), /actressId/)

  assert.deepEqual(calls, [])
})

test('getCacheStats sends GET to cache stats path', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { backend: 'redis' } }
  })

  const { default: api } = await import(`./index.js?cache-stats-${Date.now()}`)
  await api.getCacheStats()

  assert.equal(capturedConfig.url, '/v1/cache/stats')
  assert.equal(capturedConfig.method, 'get')
})

test('purgeCache forwards the requested scope', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { success: true } }
  })

  const { default: api } = await import(`./index.js?cache-purge-all-${Date.now()}`)
  await api.purgeCache('all')

  assert.equal(capturedConfig.url, '/v1/cache/purge')
  assert.equal(capturedConfig.method, 'post')
  assert.deepEqual(capturedConfig.params, { scope: 'all' })
})

test('favorite collection APIs use collection management endpoints', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7 } }
  })

  const { default: api } = await import(`./index.js?favorite-collections-${Date.now()}`)
  await api.getCollections()
  await api.createCollection({ name: '待看' })
  await api.updateCollection(7, { name: '精选' })
  await api.deleteCollection(7)

  assert.equal(calls[0].url, '/v1/favorites/collections')
  assert.equal(calls[0].method, 'get')
  assert.equal(calls[1].url, '/v1/favorites/collections')
  assert.equal(calls[1].method, 'post')
  assert.deepEqual(JSON.parse(calls[1].data), { name: '待看' })
  assert.equal(calls[2].url, '/v1/favorites/collections/7')
  assert.equal(calls[2].method, 'put')
  assert.deepEqual(JSON.parse(calls[2].data), { name: '精选' })
  assert.equal(calls[3].url, '/v1/favorites/collections/7')
  assert.equal(calls[3].method, 'delete')
})

test('favorite list API forwards lightweight metadata preference', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: [] }
  })

  const { default: api } = await import(`./index.js?favorite-lightweight-${Date.now()}`)
  await api.getFavorites('actress', { include_metadata: false, cache: '0' })

  assert.equal(capturedConfig.url, '/v1/favorites')
  assert.equal(capturedConfig.method, 'get')
  assert.deepEqual(capturedConfig.params, { entity_type: 'actress', include_metadata: false, cache: '0' })
})

test('favorite videos page API forwards bounded paging params', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`./index.js?favorite-videos-page-${Date.now()}`)
  await api.getFavoriteVideosPage({ limit: 48, offset: 96, cache: '0' })

  assert.equal(capturedConfig.url, '/v1/favorites/videos/page')
  assert.equal(capturedConfig.method, 'get')
  assert.deepEqual(capturedConfig.params, { limit: 48, offset: 96, cache: '0' })
})

test('health check bypasses api prefix because backend exposes bare health path', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { status: 'ok' } }
  })

  const { default: api } = await import(`./index.js?health-path-${Date.now()}`)
  await api.health()

  assert.equal(capturedConfig.url, '/health')
  assert.equal(capturedConfig.baseURL, '')
  assert.equal(capturedConfig.method, 'get')
})

test('health check returns readiness summary fields used by operations', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return {
      config,
      status: 200,
      statusText: 'OK',
      headers: {},
      data: {
        status: 'degraded',
        config: { loaded: false },
        database: { connectable: true },
        javinfo: { api_url_configured: true },
        cache: { backend: 'redis', active_entries: 2, total_entries: 3 },
      },
    }
  })

  const { default: api } = await import(`./index.js?health-summary-${Date.now()}`)
  const response = await api.readiness()

  assert.equal(capturedConfig.url, '/health/readiness')
  assert.equal(capturedConfig.baseURL, '')
  assert.equal(response.data.status, 'degraded')
  assert.equal(response.data.config.loaded, false)
  assert.equal(response.data.database.connectable, true)
  assert.equal(response.data.javinfo.api_url_configured, true)
  assert.equal(response.data.cache.backend, 'redis')
})

test('download candidate APIs send expected requests', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`./index.js?download-candidates-${Date.now()}`)
  await api.listDownloadCandidates({ status: 'candidate', source: 'subscription', needs_magnet: true, latest_event_action: 'magnet_enrich_failed' })
  await api.getDownloadCandidateSummary({ status: 'candidate', actress_id: 101 })
  await api.getDownloadCandidate(7)
  await api.listDownloadCandidateRuns(10)
  await api.retryDownloadCandidateRunFailed(11, { enrich: true })
  await api.createDownloadCandidate({ content_id: 'SIVR-438', title: 'Title' })
  await api.updateDownloadCandidateMagnet(7, 'magnet:?xt=urn:btih:abc')
  await api.enrichDownloadCandidateMagnet(7)
  await api.processDownloadCandidate(7, { enrich: true })
  await api.processDownloadCandidates({ status: 'candidate', source: 'inventory', limit: 20 })
  await api.processDownloadCandidates({ status: 'candidate', dry_run: true, limit: 5 })
  await api.approveDownloadCandidate(7)
  await api.rejectDownloadCandidate(8)
  await api.bulkRejectDownloadCandidates([7, 8])
  await api.bulkRestoreDownloadCandidates([9])

  assert.equal(calls[0].url, '/v1/downloads/candidates')
  assert.deepEqual(calls[0].params, { status: 'candidate', source: 'subscription', needs_magnet: true, latest_event_action: 'magnet_enrich_failed' })
  assert.equal(calls[1].url, '/v1/downloads/candidates/summary')
  assert.deepEqual(calls[1].params, { status: 'candidate', actress_id: 101 })
  assert.equal(calls[2].url, '/v1/downloads/candidates/7')
  assert.equal(calls[3].url, '/v1/downloads/candidates/runs')
  assert.deepEqual(calls[3].params, { limit: 10 })
  assert.equal(calls[4].url, '/v1/downloads/candidates/runs/11/retry-failed')
  assert.deepEqual(JSON.parse(calls[4].data), { enrich: true })
  assert.equal(calls[5].method, 'post')
  assert.equal(calls[5].url, '/v1/downloads/candidates')
  assert.deepEqual(JSON.parse(calls[6].data), { magnet: 'magnet:?xt=urn:btih:abc', magnet_source: 'manual' })
  assert.equal(calls[7].url, '/v1/downloads/candidates/7/enrich-magnet')
  assert.equal(calls[8].url, '/v1/downloads/candidates/7/process')
  assert.deepEqual(JSON.parse(calls[8].data), { enrich: true })
  assert.equal(calls[9].url, '/v1/downloads/candidates/process')
  assert.deepEqual(JSON.parse(calls[9].data), { status: 'candidate', source: 'inventory', limit: 20 })
  assert.equal(calls[10].url, '/v1/downloads/candidates/process')
  assert.deepEqual(JSON.parse(calls[10].data), { status: 'candidate', dry_run: true, limit: 5 })
  assert.equal(calls[11].url, '/v1/downloads/candidates/7/approve')
  assert.equal(calls[12].url, '/v1/downloads/candidates/8/reject')
  assert.equal(calls[13].url, '/v1/downloads/candidates/bulk/reject')
  assert.deepEqual(JSON.parse(calls[13].data), { ids: [7, 8] })
  assert.equal(calls[14].url, '/v1/downloads/candidates/bulk/restore')
  assert.deepEqual(JSON.parse(calls[14].data), { ids: [9] })
})

test('downloader management APIs send expected requests', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { clients: [] } }
  })

  const { default: api } = await import(`./index.js?downloaders-${Date.now()}`)
  await api.listDownloaders()
  await api.updateDownloaders({ default_id: 'qb', clients: [{ id: 'qb', type: 'qbittorrent' }] })
  await api.testDownloader({ id: 'tr', type: 'transmission', address: 'http://tr' })

  assert.equal(calls[0].url, '/v1/downloads/downloaders')
  assert.equal(calls[0].method, 'get')
  assert.equal(calls[1].url, '/v1/downloads/downloaders')
  assert.equal(calls[1].method, 'put')
  assert.deepEqual(JSON.parse(calls[1].data), { default_id: 'qb', clients: [{ id: 'qb', type: 'qbittorrent' }] })
  assert.equal(calls[2].url, '/v1/downloads/downloaders/test')
  assert.deepEqual(JSON.parse(calls[2].data), { id: 'tr', type: 'transmission', address: 'http://tr' })
})

test('operations overview API sends GET to correct path', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { status: 'ok' } }
  })

  const { default: api } = await import(`./index.js?operations-overview-${Date.now()}`)
  await api.getOperationsOverview()
  await api.runCandidateProcessingNow()
  await api.getDataQualityOverview(12)
  await api.startVideoVariantIndexJob()
  await api.listVideoVariantIndexJobs(5)
  await api.getVideoVariantIndexStats()

  assert.equal(calls[0].url, '/v1/operations/overview')
  assert.equal(calls[0].method, 'get')
  assert.equal(calls[1].url, '/v1/operations/candidate-processing/run')
  assert.equal(calls[1].method, 'post')
  assert.equal(calls[2].url, '/v1/data-quality/overview')
  assert.deepEqual(calls[2].params, { limit: 12 })
  assert.equal(calls[3].url, '/v1/video-variants/index/jobs')
  assert.equal(calls[3].method, 'post')
  assert.equal(calls[4].url, '/v1/video-variants/index/jobs')
  assert.deepEqual(calls[4].params, { limit: 5 })
  assert.equal(calls[5].url, '/v1/video-variants/index/stats')
})

test('translation job APIs send expected requests', async (t) => {
  const calls = []
  installAxiosAdapter(t, async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  })

  const { default: api } = await import(`./index.js?translation-jobs-${Date.now()}`)
  await api.startTranslationJob({ job_type: 'library_titles', provider: 'baidu', mode: 'remaining' })
  await api.listTranslationJobs(10)
  await api.getTranslationJob(7)
  await api.pauseTranslationJob(7)
  await api.listTranslationItems({ type: 'actress', status: 'failed', q: '三上', page: 2, page_size: 30 })
  await api.updateTranslationItem('actress', '26225', { action: 'save', translated_text: '三上悠亚' })
  await api.getTranslationItemHistory('actress', '26225', 20)
  await api.retryTranslationItems({ type: 'actress', status: 'failed' })

  assert.equal(calls[0].url, '/v1/translations/jobs')
  assert.equal(calls[0].method, 'post')
  assert.deepEqual(JSON.parse(calls[0].data), { job_type: 'library_titles', provider: 'baidu', mode: 'remaining' })
  assert.equal(calls[1].url, '/v1/translations/jobs')
  assert.equal(calls[1].method, 'get')
  assert.deepEqual(calls[1].params, { limit: 10 })
  assert.equal(calls[2].url, '/v1/translations/jobs/7')
  assert.equal(calls[3].url, '/v1/translations/jobs/7/pause')
  assert.equal(calls[3].method, 'post')
  assert.equal(calls[4].url, '/v1/translations/items')
  assert.equal(calls[4].method, 'get')
  assert.deepEqual(calls[4].params, { type: 'actress', status: 'failed', q: '三上', page: 2, page_size: 30 })
  assert.equal(calls[5].url, '/v1/translations/items/actress/26225')
  assert.equal(calls[5].method, 'patch')
  assert.equal(calls[6].url, '/v1/translations/items/actress/26225/history')
  assert.deepEqual(calls[6].params, { limit: 20 })
  assert.equal(calls[7].url, '/v1/translations/items/retry')
  assert.equal(calls[7].method, 'post')
})

test('testTranslation sends selected provider', async (t) => {
  let capturedConfig = null
  installAxiosAdapter(t, async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { translated_text: '测试' } }
  })

  const { default: api } = await import(`./index.js?translation-test-provider-${Date.now()}`)
  await api.testTranslation('テスト', 'baidu')

  assert.equal(capturedConfig.url, '/v1/translations/test')
  assert.deepEqual(JSON.parse(capturedConfig.data), { text: 'テスト', provider: 'baidu' })
})
