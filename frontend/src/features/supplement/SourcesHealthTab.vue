<template>
  <SourceHealthPanel
    v-model:provider-smoke-form="providerSmokeForm"
    v-model:provider-smoke-report="providerSmokeReport"
    :provider-source-options="providerSourceOptions"
    :provider-smoke-loading="providerSmokeLoading"
    :provider-smoke-runs="providerSmokeRuns"
    :source-health-loading="sourceHealthLoading"
    :source-health-rows="sourceHealthRows"
    :source-action-loading="sourceActionLoading"
    :format-action-time="formatActionTime"
    :smoke-run-label="smokeRunLabel"
    :source-health-label="sourceHealthLabel"
    :source-budget-label="sourceBudgetLabel"
    :source-health-detail="sourceHealthDetail"
    @refresh-health="loadSourceHealth"
    @run-smoke="runProviderSmoke"
    @load-smoke-runs="loadProviderSmokeRuns"
    @pause-source="pauseSource"
    @resume-source="resumeSource"
  />
</template>

<script>
import { watch } from 'vue'
import SourceHealthPanel from './SourceHealthPanel.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'SourcesHealthTab',
  components: { SourceHealthPanel },
  props: {
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['summary-change'],
  setup(props, { emit }) {
    const supplement = useSupplementApi()

    function emitSummary() {
      emit('summary-change', {
        count: supplement.sourceHealthRows.value.length,
        degraded: supplement.sourceHealthRows.value.some(source => ['degraded', 'cooling_down', 'paused'].includes(source.runtime_status)),
      })
    }

    async function loadSourceHealth(options = {}) {
      await supplement.loadSourceHealth(options)
      emitSummary()
    }

    watch(
      () => props.refreshNonce,
      () => loadSourceHealth(),
      { immediate: true }
    )

    return {
      ...supplement,
      emit,
      loadSourceHealth,
    }
  },
}
</script>
