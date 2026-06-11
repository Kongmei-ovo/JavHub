import test from 'node:test'
import assert from 'node:assert/strict'
import { hydrateSubscriptionActorMeta } from './subscriptionActorMeta.js'

test('hydrates missing subscription actor metadata for portrait cards', async () => {
  const calls = []
  const result = await hydrateSubscriptionActorMeta(
    [{ actress_id: 1060480, actress_name: '田中ねね' }],
    {},
    async (actressId) => {
      calls.push(actressId)
      return { data: { id: actressId, image_url: 'tanaka_nene.jpg', movie_count: 3084 } }
    },
  )

  assert.deepEqual(calls, [1060480])
  assert.equal(result[1060480].image_url, 'tanaka_nene.jpg')
  assert.equal(result[1060480].movie_count, 3084)
})

test('skips actor metadata that is already cached', async () => {
  const cached = { 1060480: { id: 1060480, image_url: 'tanaka_nene.jpg' } }
  const result = await hydrateSubscriptionActorMeta(
    [{ actress_id: 1060480, actress_name: '田中ねね' }],
    cached,
    async () => {
      throw new Error('already cached actor should not be fetched')
    },
  )

  assert.deepEqual(result, cached)
})
