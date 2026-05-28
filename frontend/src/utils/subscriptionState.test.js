import test from 'node:test'
import assert from 'node:assert/strict'

import api from '../api/index.js'
import subscriptionState, { state } from './subscriptionState.js'

function resetState() {
  state.registry = new Set()
  state.items = []
  state.initialized = false
  subscriptionState.listener = null
  subscriptionState.listeners?.clear?.()
}

test('subscription registry only treats enabled rows as subscribed', async (t) => {
  const originalGetSubscriptions = api.getSubscriptions
  t.after(() => {
    api.getSubscriptions = originalGetSubscriptions
    resetState()
  })

  api.getSubscriptions = async () => ({
    data: {
      data: [
        { id: 1, actress_id: 101, actress_name: 'Enabled', enabled: 1 },
        { id: 2, actress_id: 202, actress_name: 'Disabled', enabled: 0 },
      ],
    },
  })

  resetState()

  await subscriptionState.init()

  assert.equal(subscriptionState.isSubscribed(101), true)
  assert.equal(subscriptionState.isSubscribed(202), false)
})

test('subscription toggle deletes an existing subscribed row', async (t) => {
  const originalDeleteSubscription = api.deleteSubscription
  const originalGetSubscriptions = api.getSubscriptions
  const originalToggleSubscription = api.toggleSubscription
  const calls = []
  t.after(() => {
    api.deleteSubscription = originalDeleteSubscription
    api.getSubscriptions = originalGetSubscriptions
    api.toggleSubscription = originalToggleSubscription
    resetState()
  })

  api.getSubscriptions = async () => ({ data: { data: [] } })
  api.deleteSubscription = async (id) => {
    calls.push(['delete', id])
    return { data: { status: 'ok' } }
  }
  api.toggleSubscription = async () => {
    throw new Error('toggle endpoint should not be used for unsubscribe')
  }

  resetState()
  state.items = [{ id: 7, actress_id: 101, actress_name: 'Enabled', enabled: 1 }]
  state.registry = new Set(['101'])
  state.initialized = true

  const subscribed = await subscriptionState.toggle(101, 'Enabled')

  assert.equal(subscribed, false)
  assert.deepEqual(calls, [['delete', 7]])
})

test('subscription state notifies listeners in order and can unsubscribe one listener', async (t) => {
  const originalGetSubscriptions = api.getSubscriptions
  const originalToggleSubscription = api.toggleSubscription
  const events = []
  t.after(() => {
    api.getSubscriptions = originalGetSubscriptions
    api.toggleSubscription = originalToggleSubscription
    resetState()
  })

  api.getSubscriptions = async () => ({ data: { data: [] } })
  api.toggleSubscription = async () => ({ data: { subscribed: true } })

  resetState()
  state.initialized = true

  const unsubscribeFirst = subscriptionState.subscribe((event) => events.push(['first', event.actressId, event.subscribed]))
  subscriptionState.subscribe((event) => events.push(['second', event.actressId, event.subscribed]))

  assert.equal(typeof unsubscribeFirst, 'function')

  await subscriptionState.toggle(101, 'Enabled')
  unsubscribeFirst()
  await subscriptionState.toggle(202, 'Another')

  assert.deepEqual(events, [
    ['first', 101, true],
    ['second', 101, true],
    ['second', 202, true],
  ])
})
