import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { createRequestSequence } from './requestSequence.js'

describe('createRequestSequence', () => {
  it('accepts only the latest token', () => {
    const seq = createRequestSequence()
    const t1 = seq.next()
    const t2 = seq.next()
    const t3 = seq.next()

    assert.equal(seq.isCurrent(t1), false)
    assert.equal(seq.isCurrent(t2), false)
    assert.equal(seq.isCurrent(t3), true)
  })

  it('can invalidate pending requests', () => {
    const seq = createRequestSequence()
    const t1 = seq.next()
    assert.equal(seq.isCurrent(t1), true)

    seq.invalidate()
    assert.equal(seq.isCurrent(t1), false)

    const t2 = seq.next()
    assert.equal(seq.isCurrent(t2), true)
  })
})
