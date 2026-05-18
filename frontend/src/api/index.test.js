import test from 'node:test'
import assert from 'node:assert/strict'
import axios from 'axios'
import { ElMessage } from 'element-plus'

function installRejectingAdapter(t, status = 404, detail = 'Not Found') {
  const originalAdapter = axios.defaults.adapter
  axios.defaults.adapter = async (config) => Promise.reject({
    config,
    response: { status, data: { detail } },
    message: `Request failed with status code ${status}`,
    isAxiosError: true,
    toJSON: () => ({}),
  })
  t.after(() => {
    axios.defaults.adapter = originalAdapter
  })
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

test('category stats helper is not exposed from the frontend API', async () => {
  const { default: api } = await import(`./index.js?category-stats-removed-${Date.now()}`)

  assert.equal(api.getCategoryStats, undefined)
})

test('AI helper APIs send provider-aware requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { success: true, models: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

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
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
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
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?javinfo-import-${Date.now()}`)
  const importDb = { host: 'localhost', database: 'r18' }
  const file = new Blob(['abcdef'])
  file.name = 'r18.dump'
  const progressEvents = []
  const progress = (event) => progressEvents.push(event)

  await api.preflightJavInfoImport(importDb, 6)
  await api.createJavInfoImportJob({ filename: file.name, file_size: file.size, import_db: importDb, confirm_replace: true })
  await api.uploadJavInfoImportDump(7, file, progress, { chunkSize: 4 })
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
  assert.equal(calls[6].url, '/v1/javinfo/imports/jobs')
  assert.deepEqual(calls[6].params, { limit: 5 })
  assert.equal(calls[7].url, '/v1/javinfo/imports/jobs/7/cancel')
  assert.deepEqual(progressEvents.at(-1), { loaded: 6, total: 6 })
})

test('JavInfo chunk upload resumes from server byte count after a lost chunk response', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  let jobReads = 0
  let firstChunkAttempts = 0
  axios.defaults.adapter = async (config) => {
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
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

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

test('JavInfo plain sql gzip upload streams in a single request', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    if (config.url === '/v1/javinfo/imports/jobs/7') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, uploaded_bytes: 0 } }
    }
    if (config.url === '/v1/javinfo/imports/jobs/7/upload') {
      return { config, status: 200, statusText: 'OK', headers: {}, data: { id: 7, status: 'restoring', uploaded_bytes: 6 } }
    }
    return { config, status: 200, statusText: 'OK', headers: {}, data: { ok: true } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?javinfo-import-stream-${Date.now()}`)
  const file = new Blob(['abcdef'])
  file.name = 'r18.sql.gz'
  const progressEvents = []

  await api.uploadJavInfoImportDump(7, file, (event) => progressEvents.push(event), { chunkSize: 4 })

  assert.equal(calls[0].url, '/v1/javinfo/imports/jobs/7')
  assert.equal(calls[1].url, '/v1/javinfo/imports/jobs/7/upload')
  assert.equal(calls[1].method, 'put')
  assert.equal(calls[1].headers['Content-Type'], 'application/octet-stream')
  assert.equal(calls[1].headers['X-Filename'], 'r18.sql.gz')
  assert.equal(calls[1].headers['X-File-Size'], '6')
  assert.equal(calls.length, 2)
  assert.deepEqual(progressEvents.at(-1), { loaded: 6, total: 6 })
})

test('JavInfo upload treats a lost complete response as success when job is already restoring', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
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
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

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
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: new Blob(['config']) }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?config-export-${Date.now()}`)
  await api.exportConfig()

  assert.equal(calls[0].url, '/v1/config/export')
  assert.equal(calls[0].responseType, 'blob')
})

test('getActressVideos forwards include_supplement and extra params', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [], total_count: 0 } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?actress-videos-supplement-${Date.now()}`)
  await api.getActressVideos(123, 1, 20, { include_supplement: '1', service_code: 'digital', year: 2024 })

  assert.equal(capturedConfig.url, '/v1/actresses/123/videos')
  assert.equal(capturedConfig.params.include_supplement, '1')
  assert.equal(capturedConfig.params.service_code, 'digital')
  assert.equal(capturedConfig.params.year, 2024)
})

test('numeric path APIs reject path-like identifiers before sending requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?numeric-path-safety-${Date.now()}`)

  assert.throws(() => api.getActress('../123'), /actressId/)
  assert.throws(() => api.getActressVideos('123/status'), /actressId/)
  assert.throws(() => api.getSupplementActressStatus('123?debug=1'), /actressId/)
  assert.throws(() => api.startSupplementFilmographyJob('123/filmography'), /actressId/)
  assert.throws(() => api.refreshSupplementActressResolved('abc'), /actressId/)
  assert.throws(() => api.getSupplementJob('7/retry'), /jobId/)
  assert.throws(() => api.retrySupplementJob('retry'), /jobId/)

  assert.deepEqual(calls, [])
})

test('getSupplementStats sends GET to correct path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-stats-${Date.now()}`)
  await api.getSupplementStats()

  assert.equal(capturedConfig.url, '/v1/supplement/stats')
  assert.equal(capturedConfig.method, 'get')
})

test('startSupplementFilmographyJob sends POST to correct path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 202, statusText: 'Accepted', headers: {}, data: { job_id: 1, status: 'queued' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-start-job-${Date.now()}`)
  await api.startSupplementFilmographyJob(456)

  assert.equal(capturedConfig.url, '/v1/supplement/actresses/456/filmography/jobs')
  assert.equal(capturedConfig.method, 'post')
})

test('listSupplementJobs forwards filter params', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-jobs-${Date.now()}`)
  await api.listSupplementJobs({ page: 2, status: 'failed', actress_id: 123 })

  assert.equal(capturedConfig.url, '/v1/supplement/jobs')
  assert.equal(capturedConfig.params.page, 2)
  assert.equal(capturedConfig.params.status, 'failed')
  assert.equal(capturedConfig.params.actress_id, 123)
})

test('listSupplementMovies forwards matched=false filter', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-movies-${Date.now()}`)
  await api.listSupplementMovies({ matched: false, actress_id: 456 })

  assert.equal(capturedConfig.url, '/v1/supplement/movies')
  assert.equal(capturedConfig.params.matched, false)
  assert.equal(capturedConfig.params.actress_id, 456)
})

test('enrichSupplementMovieDetail sends POST with source movie id', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { source: 'avbase' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-${Date.now()}`)
  await api.enrichSupplementMovieDetail('prestige:SIVR-438', 'avbase')

  assert.equal(capturedConfig.url, '/v1/supplement/movies/detail')
  assert.equal(capturedConfig.method, 'post')
  assert.equal(capturedConfig.params.source, 'avbase')
  assert.equal(capturedConfig.params.source_movie_id, 'prestige:SIVR-438')
})

test('startSupplementMovieDetailJob sends POST with source movie id', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 202, statusText: 'Accepted', headers: {}, data: { job_id: 3, status: 'queued' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-job-${Date.now()}`)
  await api.startSupplementMovieDetailJob('prestige:SIVR-438', 'avbase')

  assert.equal(capturedConfig.url, '/v1/supplement/movies/detail/jobs')
  assert.equal(capturedConfig.method, 'post')
  assert.equal(capturedConfig.params.source, 'avbase')
  assert.equal(capturedConfig.params.source_movie_id, 'prestige:SIVR-438')
})

test('startSupplementMovieDetailJob defaults to all sources', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 202, statusText: 'Accepted', headers: {}, data: { job_id: 3, status: 'queued' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-job-default-${Date.now()}`)
  await api.startSupplementMovieDetailJob('SIVR-397')

  assert.equal(capturedConfig.params.source, 'all')
  assert.equal(capturedConfig.params.source_movie_id, 'SIVR-397')
})

test('startSupplementMovieDetailJob forwards actress id when provided', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 202, statusText: 'Accepted', headers: {}, data: { job_id: 3, status: 'queued' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-job-actress-${Date.now()}`)
  await api.startSupplementMovieDetailJob('SIVR-397', 'all', 1098399)

  assert.equal(capturedConfig.params.source, 'all')
  assert.equal(capturedConfig.params.source_movie_id, 'SIVR-397')
  assert.equal(capturedConfig.params.actress_id, 1098399)
})

test('enrichSupplementMovieDetail defaults to all sources', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { source: 'all' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-default-${Date.now()}`)
  await api.enrichSupplementMovieDetail('SIVR-397')

  assert.equal(capturedConfig.params.source, 'all')
  assert.equal(capturedConfig.params.source_movie_id, 'SIVR-397')
})

test('getSupplementMovieSources sends GET to movie sources path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { movie: { id: 12 } } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-movie-sources-${Date.now()}`)
  await api.getSupplementMovieSources(12)

  assert.equal(capturedConfig.url, '/v1/supplement/movies/12/sources')
  assert.equal(capturedConfig.method, 'get')
})

test('createSupplementDownloadCandidates posts supplement movie filters', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { created: 2 } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-candidates-${Date.now()}`)
  await api.createSupplementDownloadCandidates({ actress_id: 123, q: 'SIVR' })

  assert.equal(capturedConfig.url, '/v1/supplement/movies/candidates')
  assert.equal(capturedConfig.method, 'post')
  assert.deepEqual(capturedConfig.params, { actress_id: 123, q: 'SIVR' })
})

test('listSupplementSources sends GET to sources path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: [] }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-sources-${Date.now()}`)
  await api.listSupplementSources()

  assert.equal(capturedConfig.url, '/v1/supplement/sources')
  assert.equal(capturedConfig.method, 'get')
})

test('listSupplementSourcesHealth sends GET to source health path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: [] }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-source-health-${Date.now()}`)
  await api.listSupplementSourcesHealth()

  assert.equal(capturedConfig.url, '/v1/supplement/sources/health')
  assert.equal(capturedConfig.method, 'get')
})

test('listSupplementSourcesBudgets sends GET to source budgets path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: [] }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-source-budgets-${Date.now()}`)
  await api.listSupplementSourcesBudgets()

  assert.equal(capturedConfig.url, '/v1/supplement/sources/budgets')
  assert.equal(capturedConfig.method, 'get')
})

test('runSupplementProviderSmoke posts payload to provider smoke path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { reports: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-provider-smoke-${Date.now()}`)
  await api.runSupplementProviderSmoke({ source: 'fc2', source_movie_id: 'FC2-PPV-4897640' })

  assert.equal(capturedConfig.url, '/v1/supplement/providers/smoke')
  assert.equal(capturedConfig.method, 'post')
  assert.deepEqual(JSON.parse(capturedConfig.data), { source: 'fc2', source_movie_id: 'FC2-PPV-4897640' })
})

test('listSupplementProviderSmokeRuns sends GET with limit and source', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: [] }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-provider-smoke-runs-${Date.now()}`)
  await api.listSupplementProviderSmokeRuns(3, 'fc2')

  assert.equal(capturedConfig.url, '/v1/supplement/providers/smoke/runs')
  assert.equal(capturedConfig.method, 'get')
  assert.deepEqual(capturedConfig.params, { limit: 3, source: 'fc2' })
})

test('source health actions post expected payloads', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-source-actions-${Date.now()}`)
  await api.pauseSupplementSource('javbus', 'maintenance', 60)
  await api.resumeSupplementSource('javbus')

  assert.equal(calls[0].url, '/v1/supplement/sources/javbus/pause')
  assert.deepEqual(JSON.parse(calls[0].data), { reason: 'maintenance', duration_minutes: 60 })
  assert.equal(calls[1].url, '/v1/supplement/sources/javbus/resume')
  assert.equal(calls[1].method, 'post')
})

test('manual supplement movie actions post expected payloads', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: {} }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-manual-actions-${Date.now()}`)
  await api.matchSupplementMovie(12, 'umd1010', '人工确认')
  await api.ignoreSupplementMovie(12, '跳过')
  await api.unmatchSupplementMovie(12, '解除')

  assert.equal(calls[0].url, '/v1/supplement/movies/12/match')
  assert.deepEqual(JSON.parse(calls[0].data), { content_id: 'umd1010', reason: '人工确认' })
  assert.equal(calls[1].url, '/v1/supplement/movies/12/ignore')
  assert.deepEqual(JSON.parse(calls[1].data), { reason: '跳过' })
  assert.equal(calls[2].url, '/v1/supplement/movies/12/unmatch')
  assert.deepEqual(JSON.parse(calls[2].data), { reason: '解除' })
})

test('startSupplementMovieDetailBatchJobs sends POST with filters', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 202, statusText: 'Accepted', headers: {}, data: { queued: 2 } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-detail-batch-${Date.now()}`)
  await api.startSupplementMovieDetailBatchJobs({ source: 'avbase', limit: 20, missing_cover: true })

  assert.equal(capturedConfig.url, '/v1/supplement/movies/detail/jobs/batch')
  assert.equal(capturedConfig.method, 'post')
  assert.equal(capturedConfig.params.source, 'avbase')
  assert.equal(capturedConfig.params.limit, 20)
  assert.equal(capturedConfig.params.missing_cover, true)
})

test('cancelSupplementJob sends POST to correct path', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { job_id: 1, status: 'failed' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-cancel-${Date.now()}`)
  await api.cancelSupplementJob(1)

  assert.equal(capturedConfig.url, '/v1/supplement/jobs/1/cancel')
  assert.equal(capturedConfig.method, 'post')
})

test('download candidate APIs send expected requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?download-candidates-${Date.now()}`)
  await api.listDownloadCandidates({ status: 'candidate', source: 'subscription', needs_magnet: true })
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
  assert.deepEqual(calls[0].params, { status: 'candidate', source: 'subscription', needs_magnet: true })
  assert.equal(calls[1].url, '/v1/downloads/candidates/7')
  assert.equal(calls[2].url, '/v1/downloads/candidates/runs')
  assert.deepEqual(calls[2].params, { limit: 10 })
  assert.equal(calls[3].url, '/v1/downloads/candidates/runs/11/retry-failed')
  assert.deepEqual(JSON.parse(calls[3].data), { enrich: true })
  assert.equal(calls[4].method, 'post')
  assert.equal(calls[4].url, '/v1/downloads/candidates')
  assert.deepEqual(JSON.parse(calls[5].data), { magnet: 'magnet:?xt=urn:btih:abc', magnet_source: 'manual' })
  assert.equal(calls[6].url, '/v1/downloads/candidates/7/enrich-magnet')
  assert.equal(calls[7].url, '/v1/downloads/candidates/7/process')
  assert.deepEqual(JSON.parse(calls[7].data), { enrich: true })
  assert.equal(calls[8].url, '/v1/downloads/candidates/process')
  assert.deepEqual(JSON.parse(calls[8].data), { status: 'candidate', source: 'inventory', limit: 20 })
  assert.equal(calls[9].url, '/v1/downloads/candidates/process')
  assert.deepEqual(JSON.parse(calls[9].data), { status: 'candidate', dry_run: true, limit: 5 })
  assert.equal(calls[10].url, '/v1/downloads/candidates/7/approve')
  assert.equal(calls[11].url, '/v1/downloads/candidates/8/reject')
  assert.equal(calls[12].url, '/v1/downloads/candidates/bulk/reject')
  assert.deepEqual(JSON.parse(calls[12].data), { ids: [7, 8] })
  assert.equal(calls[13].url, '/v1/downloads/candidates/bulk/restore')
  assert.deepEqual(JSON.parse(calls[13].data), { ids: [9] })
})

test('downloader management APIs send expected requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { clients: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

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
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { status: 'ok' } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?operations-overview-${Date.now()}`)
  await api.getOperationsOverview()
  await api.runCandidateProcessingNow()

  assert.equal(calls[0].url, '/v1/operations/overview')
  assert.equal(calls[0].method, 'get')
  assert.equal(calls[1].url, '/v1/operations/candidate-processing/run')
  assert.equal(calls[1].method, 'post')
})

test('actor mapping APIs send expected requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?actor-mappings-${Date.now()}`)
  await api.listActorMappings({ status: 'confirmed' })
  await api.getActorMappingSummary()
  await api.listUnmappedActors({ search: '瑠花' })
  await api.searchActorMappingCandidates({ emby_actor_id: '1', emby_actor_name: '瑠花', q: '瑠花' })
  await api.reviewActorMappingWithAi({ emby_actor_id: '1', emby_actor_name: '瑠花', javinfo_actress_id: 2 })
  await api.generateActorMappingCandidates({ search: '瑠花', limit: 10, per_actor: 2 })
  await api.autoMatchActorMappings({ dry_run: true, limit: 20 })
  await api.confirmActorMapping({ emby_actor_id: '1', javinfo_actress_id: 2 })
  await api.ignoreActorMapping({ emby_actor_id: '3', emby_actor_name: 'Ignored' })
  await api.deleteActorMapping(9)

  assert.equal(calls[0].url, '/inventory/actor-mappings')
  assert.deepEqual(calls[0].params, { status: 'confirmed' })
  await api.listActorMappings({ status: 'candidate', limit: 100000 })
  assert.deepEqual(calls.at(-1).params, { status: 'candidate', limit: 100000 })
  assert.equal(calls[1].url, '/inventory/actor-mappings/summary')
  assert.equal(calls[2].url, '/inventory/actor-mappings/unmapped')
  assert.deepEqual(calls[2].params, { search: '瑠花' })
  assert.equal(calls[3].url, '/inventory/actor-mappings/search')
  assert.deepEqual(calls[3].params, { emby_actor_id: '1', emby_actor_name: '瑠花', q: '瑠花' })
  assert.equal(calls[4].url, '/inventory/actor-mappings/ai-review')
  assert.equal(calls[4].method, 'post')
  assert.equal(calls[5].url, '/inventory/actor-mappings/candidates/generate')
  assert.equal(calls[5].method, 'post')
  assert.deepEqual(calls[5].params, { search: '瑠花', limit: 10, per_actor: 2 })
  assert.equal(calls[6].url, '/inventory/actor-mappings/auto-match')
  assert.equal(calls[6].method, 'post')
  assert.deepEqual(calls[6].params, { dry_run: true, limit: 20 })
  assert.equal(calls[7].url, '/inventory/actor-mappings/confirm')
  assert.equal(calls[8].url, '/inventory/actor-mappings/ignore')
  assert.equal(calls[9].url, '/inventory/actor-mappings/9')
  assert.equal(calls[9].method, 'delete')
})

test('translation job APIs send expected requests', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const calls = []
  axios.defaults.adapter = async (config) => {
    calls.push(config)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { data: [] } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?translation-jobs-${Date.now()}`)
  await api.startTranslationJob({ job_type: 'library_titles', provider_order: ['cache', 'google_free'], mode: 'remaining' })
  await api.listTranslationJobs(10)
  await api.getTranslationJob(7)
  await api.pauseTranslationJob(7)
  await api.listTranslationItems({ type: 'actress', status: 'failed', q: '三上', page: 2, page_size: 30 })
  await api.updateTranslationItem('actress', '26225', { action: 'save', translated_text: '三上悠亚' })
  await api.getTranslationItemHistory('actress', '26225', 20)
  await api.retryTranslationItems({ type: 'actress', status: 'failed' })

  assert.equal(calls[0].url, '/v1/translations/jobs')
  assert.equal(calls[0].method, 'post')
  assert.deepEqual(JSON.parse(calls[0].data), { job_type: 'library_titles', provider_order: ['cache', 'google_free'], mode: 'remaining' })
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

test('recoverStaleSupplementJobs sends POST with older_than_minutes', async (t) => {
  const originalAdapter = axios.defaults.adapter
  let capturedConfig = null
  axios.defaults.adapter = async (config) => {
    capturedConfig = config
    return { config, status: 200, statusText: 'OK', headers: {}, data: { recovered: 2 } }
  }
  t.after(() => { axios.defaults.adapter = originalAdapter })

  const { default: api } = await import(`./index.js?supplement-recover-${Date.now()}`)
  await api.recoverStaleSupplementJobs(60)

  assert.equal(capturedConfig.url, '/v1/supplement/jobs/recover_stale')
  assert.equal(capturedConfig.params.older_than_minutes, 60)
})
