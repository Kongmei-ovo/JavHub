<template>
  <SourceHealthPanel
    :global-check-loading="globalCheckLoading"
    :source-health-loading="sourceHealthLoading"
    :source-health-rows="sourceHealthRows"
    :source-action-loading="sourceActionLoading"
    :source-health-label="sourceHealthLabel"
    :source-budget-label="sourceBudgetLabel"
    @refresh-health="loadSourceHealth"
    @check-all="checkAllSourcesAction"
    @pause-source="pauseSource"
    @resume-source="resumeSource"
    @check-source="recheckSource"
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

    async function checkAllSourcesAction() {
      await supplement.checkAllSources()
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
      checkAllSourcesAction,
    }
  },
}
</script>
