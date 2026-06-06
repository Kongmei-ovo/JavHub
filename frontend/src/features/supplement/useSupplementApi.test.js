import test from 'node:test'
import assert from 'node:assert/strict'

const moduleUrl = new URL('./useSupplementApi.js', import.meta.url)

function createApi(overrides = {}) {
  return {
    listSupplementJobs: async () => ({ data: [], total_count: 0, total_pages: 1 }),
    retrySupplementJob: async () => ({}),
    cancelSupplementJob: async () => ({}),
    recoverStaleSupplementJobs: async () => ({}),
    listSupplementMovies: async () => ({ data: [], total_count: 0, total_pages: 1 }),
    startSupplementMovieDetailJob: async () => ({}),
    startSupplementMovieDetailBatchJobs: async () => ({}),
    createSupplementDownloadCandidates: async () => ({ created: 0, existing: 0 }),
    getSupplementMovieSources: async () => ({ movie: {} }),
    matchSupplementMovie: async () => ({}),
    ignoreSupplementMovie: async () => ({}),
    unmatchSupplementMovie: async () => ({}),
    listSupplementSourcesHealth: async () => [],
    listSupplementSourcesBudgets: async () => [],
    listSupplementProviderSmokeRuns: async () => [],
    runSupplementProviderSmoke: async () => ({}),
    pauseSupplementSource: async () => ({}),
    resumeSupplementSource: async () => ({}),
    startGfriendsAvatarSyncJob: async () => ({}),
    ...overrides,
  }
}

test('useSupplementApi loads jobs with filters and tracks loading state', async () => {
  const calls = []
  const { useSupplementApi } = await import(moduleUrl.href)
  const supplement = useSupplementApi({
    api: createApi({
      listSupplementJobs: async (params) => {
        calls.push(params)
        assert.equal(supplement.jobsLoading.value, true)
        return { data: { data: [{ id: 1, status: 'queued' }], total_count: 12, total_pages: 3 } }
      },
    }),
  })

  await supplement.loadJobs({
    page: 2,
    pageSize: 10,
    filters: { status: 'queued', actress_id: '7', source: '', error_provider: 'javbus' },
  })

  assert.deepEqual(calls, [{ page: 2, page_size: 10, status: 'queued', actress_id: '7', error_provider: 'javbus' }])
  assert.deepEqual(supplement.jobs.value, [{ id: 1, status: 'queued' }])
  assert.equal(supplement.jobsTotalCount.value, 12)
  assert.equal(supplement.jobsTotalPages.value, 3)
  assert.equal(supplement.jobsLoading.value, false)
  assert.equal(supplement.jobsError.value, '')
})

test('useSupplementApi captures job errors and always clears loading', async () => {
  const { useSupplementApi } = await import(moduleUrl.href)
  const supplement = useSupplementApi({
    api: createApi({
      listSupplementJobs: async () => {
        throw new Error('queue unavailable')
      },
    }),
  })
  const originalError = console.error
  console.error = () => {}

  try {
    await supplement.loadJobs()
  } finally {
    console.error = originalError
  }

  assert.equal(supplement.jobsLoading.value, false)
  assert.equal(supplement.jobsError.value, 'queue unavailable')
})

test('useSupplementApi loads movies with quality filters and exposes movie helpers', async () => {
  const calls = []
  const { useSupplementApi } = await import(moduleUrl.href)
  const supplement = useSupplementApi({
    api: createApi({
      listSupplementMovies: async (params) => {
        calls.push(params)
        return {
          data: [
            {
              id: 2,
              source_movie_id: 'src-2',
              matched_content_id: '',
              match_candidate_count: 1,
              cover_url: 'cover.jpg',
              runtime_mins: 120,
              maker_name: 'Maker',
              label_name: '',
              series_name: '',
              category_names: '["Drama","VR","HD"]',
            },
          ],
          total_count: 1,
          total_pages: 1,
        }
      },
    }),
  })

  await supplement.loadMovies({
    page: 3,
    filters: { matched: false, actress_id: '8', quality: 'low_completeness', q: 'abc' },
  })

  assert.deepEqual(calls, [{ page: 3, page_size: 20, matched: false, actress_id: '8', q: 'abc', max_completeness: 2 }])
  const [movie] = supplement.supplementMovies.value
  assert.equal(supplement.movieMatchClass(movie), 'candidate')
  assert.equal(supplement.movieMatchLabel(movie), '待确认 1')
  assert.equal(supplement.movieCategories(movie), 'Drama · VR · HD')
  assert.equal(supplement.movieFieldChips(movie).filter(chip => !chip.value).length, 2)
  assert.equal(supplement.moviesLoading.value, false)
})

test('useSupplementApi performs shared job operations and refreshes the queue', async () => {
  const calls = []
  const { useSupplementApi } = await import(moduleUrl.href)
  const supplement = useSupplementApi({
    api: createApi({
      retrySupplementJob: async (jobId) => calls.push(['retry', jobId]),
      cancelSupplementJob: async (jobId) => calls.push(['cancel', jobId]),
      recoverStaleSupplementJobs: async (minutes) => calls.push(['recover', minutes]),
      listSupplementJobs: async () => {
        calls.push(['load'])
        return { data: [], total_count: 0, total_pages: 1 }
      },
    }),
  })

  await supplement.retryJob(10)
  await supplement.cancelJob(11)
  await supplement.recoverStale(45)

  assert.deepEqual(calls, [
    ['retry', 10],
    ['load'],
    ['cancel', 11],
    ['load'],
    ['recover', 45],
    ['load'],
  ])
  assert.equal(supplement.recovering.value, false)
})

test('useSupplementApi loads source health with budgets and provider smoke runs', async () => {
  const { useSupplementApi } = await import(moduleUrl.href)
  const supplement = useSupplementApi({
    api: createApi({
      listSupplementSourcesHealth: async () => ({ data: [{ source: 'javbus', runtime_status: 'degraded' }] }),
      listSupplementSourcesBudgets: async () => ({ data: [{ source: 'javbus', local_active: 1 }] }),
      listSupplementProviderSmokeRuns: async (limit, source) => ({ data: [{ id: 1, request: { source } }] }),
      listSupplementJobs: async (params) => ({ data: { data: [{ id: 3, source: params.source, status: 'running' }] } }),
    }),
  })
  supplement.providerSmokeForm.value.source = 'javbus'

  await supplement.loadSourceHealth()

  assert.equal(supplement.sourceHealthRows.value[0].budget.local_active, 1)
  assert.equal(supplement.providerSmokeRuns.value[0].id, 1)
  assert.equal(supplement.gfriendsAvatarJob.value.source, 'gfriends')
  assert.equal(supplement.sourceHealthLoading.value, false)
})
