import { reactive, computed } from 'vue'
import api from '../api/index.js'

export const state = reactive({
    registry: new Set(),
    items: [],
    initialized: false
})

export const subscriptionState = {
    async init() {
        if (state.initialized) return
        const resp = await api.getSubscriptions()
        const items = resp.data?.data || resp.data || []
        state.items = items
        state.registry = new Set()
        items.forEach(item => {
            if (item.actress_id && item.enabled !== 0 && item.enabled !== false) {
                state.registry.add(String(item.actress_id))
            }
        })
        state.initialized = true
    },

    async refresh() {
        state.initialized = false
        await this.init()
    },

    isSubscribed(actressId) {
        return state.registry.has(String(actressId))
    },

    async toggle(actressId, actressName) {
        if (!actressId) return false
        const existing = state.items.find(item => (
            String(item.actress_id) === String(actressId)
            && item.enabled !== 0
            && item.enabled !== false
        ))
        if (existing?.id) {
            await api.deleteSubscription(existing.id)
            state.registry.delete(String(actressId))
            state.items = state.items.filter(item => item.id !== existing.id)
            await this.refresh()
            for (const listener of this.listeners) {
                listener({ actressId, subscribed: false })
            }
            return false
        }
        const resp = await api.toggleSubscription({
            actress_id: Number(actressId),
            actress_name: actressName || ''
        })
        const subscribed = resp.data?.subscribed
        if (subscribed) {
            state.registry.add(String(actressId))
        } else {
            state.registry.delete(String(actressId))
        }
        await this.refresh()
        for (const listener of this.listeners) {
            listener({ actressId, subscribed })
        }
        return subscribed
    },

    listener: null,
    listeners: new Set(),
    subscribe(callback) {
        this.listeners.add(callback)
        return () => {
            this.listeners.delete(callback)
        }
    },

    count: computed(() => state.registry.size),

    state
}

export default subscriptionState
