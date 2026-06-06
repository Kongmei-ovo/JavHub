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
    :gfriends-avatar-job="gfriendsAvatarJob"
    :gfriends-avatar-syncing="gfriendsAvatarSyncing"
    :format-action-time="formatActionTime"
    :smoke-run-label="smokeRunLabel"
    :source-health-label="sourceHealthLabel"
    :source-budget-label="sourceBudgetLabel"
    :source-health-detail="sourceHealthDetail"
    @refresh-health="loadSourceHealth"
    @run-smoke="runProviderSmoke"
    @sync-gfriends-avatars="confirmGfriendsAvatarSync"
    @view-avatar-jobs="emit('view-avatar-jobs')"
    @load-smoke-runs="loadProviderSmokeRuns"
    @pause-source="pauseSource"
    @resume-source="resumeSource"
  />
</template>

<script>
import { watch } from 'vue'
import { requestConfirm } from '../../utils/confirmDialog'
import SourceHealthPanel from './SourceHealthPanel.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'SourcesHealthTab',
  components: { SourceHealthPanel },
  props: {
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['view-avatar-jobs', 'summary-change'],
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

    async function confirmGfriendsAvatarSync() {
      const confirmed = await requestConfirm({
        title: '同步演员头像？',
        message: '会拉取 gfriends Filetree、匹配本地演员、写入头像覆盖，并校验图片可访问性。',
        details: '这是全局维护任务，不绑定具体演员。已有运行中的头像同步任务时会复用该任务。',
        confirmText: '开始同步',
      })
      if (!confirmed) return
      await supplement.syncGfriendsAvatars()
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
      confirmGfriendsAvatarSync,
      syncGfriendsAvatars: supplement.syncGfriendsAvatars,
      requestConfirm,
    }
  },
}
</script>
