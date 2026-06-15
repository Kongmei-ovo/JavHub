import test from 'node:test'
import assert from 'node:assert/strict'

import {
  supplementJobFailureDiagnostics,
  supplementJobFailureSummary,
  supplementJobProviderSummary,
} from './supplementJobDiagnostics.js'

test('supplement job diagnostics summarize compound provider failures', () => {
  const error = 'partial retryable detail failures: avbase: avbase request failed: 404 Not Found; fanza: no high-confidence fanza candidate for 2-026; fc2: no high-confidence fc2 candidate for 2-026; javlibrary: javlibrary cloudflare challenge returned; mgstage: mgstage request failed: 403 Forbidden'

  const diagnostics = supplementJobFailureDiagnostics({ last_error: error })

  assert.equal(diagnostics.reasonKey, 'source_unavailable')
  assert.equal(diagnostics.reasonLabel, '来源暂不可用')
  assert.equal(diagnostics.summary, '来源暂不可用')
  assert.equal(diagnostics.nextActionLabel, '检查来源')
  assert.deepEqual(diagnostics.providers, ['javlibrary', 'mgstage', 'avbase', 'fanza', 'fc2'])
  assert.equal(supplementJobProviderSummary(diagnostics.providers), 'javlibrary · mgstage · avbase · fanza · 另 1 个来源')
  assert.equal(
    supplementJobFailureSummary({ last_error: error }),
    '来源暂不可用 · javlibrary · mgstage · avbase · fanza · 另 1 个来源',
  )
})

test('supplement job diagnostics expose concurrency and low-confidence next actions', () => {
  assert.deepEqual(
    supplementJobFailureDiagnostics({ last_error: 'source health control concurrency limit reached for javbus' }),
    {
      hasError: true,
      reasonKey: 'concurrency_limit',
      reasonLabel: '并发限制',
      summary: '并发限制',
      providers: ['javbus'],
      providerSummary: 'javbus',
      nextActionLabel: '等待冷却',
      nextActionDetail: 'javbus',
    },
  )

  const lowConfidence = supplementJobFailureDiagnostics({ last_error: 'no high-confidence fc2 candidate for ABC-001' })

  assert.equal(lowConfidence.reasonKey, 'low_confidence')
  assert.equal(lowConfidence.reasonLabel, '低置信匹配')
  assert.equal(lowConfidence.nextActionLabel, '人工匹配')
  assert.equal(lowConfidence.providerSummary, 'fc2')
})

test('supplement job diagnostics preserve a no-error state', () => {
  assert.deepEqual(supplementJobFailureDiagnostics({}), {
    hasError: false,
    reasonKey: '',
    reasonLabel: '无',
    summary: '无',
    providers: [],
    providerSummary: '',
    nextActionLabel: '刷新队列',
    nextActionDetail: '同步最新状态',
  })
})
