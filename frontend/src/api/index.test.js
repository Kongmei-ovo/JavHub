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

test('getVideoMetadata failure does not show global error toast', async (t) => {
  installRejectingAdapter(t)
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?metadata-suppress-${Date.now()}`)

  await assert.rejects(() => api.getVideoMetadata('miaa405'))

  assert.equal(errorMock.mock.callCount(), 0)
})

test('main path API failure still shows global error toast', async (t) => {
  installRejectingAdapter(t, 500, '服务器内部错误')
  const errorMock = t.mock.method(ElMessage, 'error', () => {})
  const { default: api } = await import(`./index.js?main-error-${Date.now()}`)

  await assert.rejects(() => api.getVideo('miaa405'))

  assert.equal(errorMock.mock.callCount(), 1)
  assert.equal(errorMock.mock.calls[0].arguments[0], '服务器内部错误')
})

test('concurrent getCategoryStats calls share one network request', async (t) => {
  const originalAdapter = axios.defaults.adapter
  const originalLocalStorage = globalThis.localStorage
  let requestCount = 0

  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
  }
  axios.defaults.adapter = async (config) => {
    requestCount += 1
    return {
      config,
      status: 200,
      statusText: 'OK',
      headers: {},
      data: [{ category_id: 1, count: 12 }],
    }
  }
  t.after(() => {
    axios.defaults.adapter = originalAdapter
    if (originalLocalStorage === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = originalLocalStorage
    }
  })

  const { default: api } = await import(`./index.js?category-stats-dedupe-${Date.now()}`)

  const [first, second] = await Promise.all([
    api.getCategoryStats(),
    api.getCategoryStats(),
  ])

  assert.deepEqual(first, [{ category_id: 1, count: 12 }])
  assert.deepEqual(second, [{ category_id: 1, count: 12 }])
  assert.equal(requestCount, 1)
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
  await api.createDownloadCandidate({ content_id: 'SIVR-438', title: 'Title' })
  await api.updateDownloadCandidateMagnet(7, 'magnet:?xt=urn:btih:abc')
  await api.approveDownloadCandidate(7)
  await api.rejectDownloadCandidate(8)

  assert.equal(calls[0].url, '/v1/downloads/candidates')
  assert.deepEqual(calls[0].params, { status: 'candidate', source: 'subscription', needs_magnet: true })
  assert.equal(calls[1].url, '/v1/downloads/candidates/7')
  assert.equal(calls[2].method, 'post')
  assert.equal(calls[2].url, '/v1/downloads/candidates')
  assert.deepEqual(JSON.parse(calls[3].data), { magnet: 'magnet:?xt=urn:btih:abc', magnet_source: 'manual' })
  assert.equal(calls[4].url, '/v1/downloads/candidates/7/approve')
  assert.equal(calls[5].url, '/v1/downloads/candidates/8/reject')
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
  await api.confirmActorMapping({ emby_actor_id: '1', javinfo_actress_id: 2 })
  await api.ignoreActorMapping({ emby_actor_id: '3', emby_actor_name: 'Ignored' })
  await api.deleteActorMapping(9)

  assert.equal(calls[0].url, '/inventory/actor-mappings')
  assert.deepEqual(calls[0].params, { status: 'confirmed' })
  assert.equal(calls[1].url, '/inventory/actor-mappings/summary')
  assert.equal(calls[2].url, '/inventory/actor-mappings/unmapped')
  assert.deepEqual(calls[2].params, { search: '瑠花' })
  assert.equal(calls[3].url, '/inventory/actor-mappings/confirm')
  assert.equal(calls[4].url, '/inventory/actor-mappings/ignore')
  assert.equal(calls[5].url, '/inventory/actor-mappings/9')
  assert.equal(calls[5].method, 'delete')
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
