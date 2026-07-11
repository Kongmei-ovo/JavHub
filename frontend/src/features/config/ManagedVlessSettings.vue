<template><template v-if="proxy.enabled && proxy.mode === 'vless'">
  <label class="settings-row settings-row--stacked"><span class="setting-copy"><span class="setting-title">VLESS 分享链接</span><span class="setting-note">支持 VLESS + XTLS Vision + REALITY；留空保存不会覆盖现有节点。</span></span><span class="settings-control settings-control--wide"><input class="input" type="password" v-model="proxy.vless_uri" autocomplete="new-password" placeholder="vless://…" /></span></label>
  <div class="settings-row settings-row--actions"><span class="setting-copy"><span class="setting-title">核心与出口检查</span><span class="setting-note" role="status">{{ status }}</span></span><span class="settings-control settings-control--wide"><button class="btn btn-secondary" type="button" @click="test" :disabled="testing || !proxy.vless_uri">{{ testing ? '测试中…' : '测试 VLESS 连接' }}</button></span></div>
</template></template>
<script>
import api from '../../api'
export default { name: 'ManagedVlessSettings', props: { proxy: { type: Object, required: true } }, data: () => ({ testing: false, status: '保存后将自动启动核心。' }), methods: {
  async test() { this.testing = true; this.status = '正在启动核心并检查 Cloudflare 出口…'; try { const r = await api.testSingBox(this.proxy); this.status = r.data?.running ? '连接成功，sing-box 核心正在运行。' : '测试完成，但核心未运行。' } catch (e) { this.status = e.response?.data?.detail || e.message || '连接失败' } finally { this.testing = false } },
} }
</script>
