import { defineAsyncComponent } from 'vue'
import AppleErrorState from '../../components/AppleErrorState.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'

const AdvancedSettingsSkeleton = {
  name: 'AdvancedSettingsSkeleton',
  components: { AppleSkeleton },
  template: '<AppleSkeleton class="advanced-settings-skeleton apple-surface" variant="list" :items="4" label="高级设置加载中" />',
}

const AdvancedSettingsError = {
  name: 'AdvancedSettingsError',
  components: { AppleErrorState },
  methods: {
    reloadPage() {
      window.location.reload()
    },
  },
  template: '<AppleErrorState class="advanced-settings-error apple-surface" title="高级设置加载失败" description="无法载入高级设置模块，刷新页面会重新请求这个模块。" retry-label="刷新页面" @retry="reloadPage" />',
}

export const AdvancedSettingsPanel = defineAsyncComponent({
  loader: () => import('./AdvancedSettingsPanel.vue'),
  loadingComponent: AdvancedSettingsSkeleton,
  errorComponent: AdvancedSettingsError,
  delay: 120,
  timeout: 15000,
  suspensible: false,
})
