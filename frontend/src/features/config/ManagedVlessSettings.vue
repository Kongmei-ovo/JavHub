<template>
  <template v-if="proxy.enabled && proxy.mode === 'vless'">
    <label class="settings-row proxy-uri-row">
      <span class="setting-copy">
        <span class="setting-title">VLESS 节点</span>
        <span class="setting-note">支持 XTLS Vision 与 REALITY，留空保存不会覆盖当前节点。</span>
      </span>
      <span class="settings-control">
        <input class="input" type="password" v-model="proxy.vless_uri" autocomplete="new-password" placeholder="vless://…" />
      </span>
    </label>
    <label class="settings-row proxy-uri-row">
      <span class="setting-copy">
        <span class="setting-title">节点订阅</span>
        <span class="setting-note">支持 Base64 编码的 VLESS 订阅；留空保存不会覆盖当前订阅。</span>
      </span>
      <span class="settings-control">
        <input class="input" type="password" v-model="proxy.subscription_url" autocomplete="new-password" placeholder="https://…/sub/…" />
      </span>
    </label>
    <div v-if="nodes.length" class="settings-row proxy-nodes-row">
      <span class="setting-copy">
        <span class="setting-title">节点池</span>
        <span class="setting-note">自动优选会定期切换至低延迟节点，也可以手动指定。</span>
      </span>
      <span class="settings-control proxy-node-list">
        <button class="proxy-node" :class="{ selected: autoSelected }" type="button" @click="selectNode('自动优选')">
          <span>⚡ 自动优选</span><small>故障自动切换</small>
        </button>
        <button v-for="node in nodes" :key="node.tag" class="proxy-node" :class="{ selected: node.selected }" type="button" @click="selectNode(node.tag)">
          <span>{{ node.name }}</span><small>{{ node.delay ? `${node.delay} ms` : '等待测速' }}</small>
        </button>
      </span>
    </div>
    <div class="settings-row proxy-check-row">
      <span class="setting-copy">
        <span class="setting-title">连接状态</span>
        <span class="setting-note">检查 sing-box 核心，并通过 Cloudflare 验证代理出口。</span>
      </span>
      <span class="settings-control proxy-check-control">
        <span class="proxy-status" :class="statusType" role="status">
          <span class="proxy-status-dot" aria-hidden="true"></span>
          {{ status }}
        </span>
        <button v-if="proxy.subscription_url" class="btn btn-ghost" type="button" @click="refreshSubscription" :disabled="testing">刷新订阅</button>
        <button class="btn btn-secondary" type="button" @click="test" :disabled="testing || (!proxy.vless_uri && !proxy.subscription_url)">
          {{ testing ? '检查中…' : '测速' }}
        </button>
      </span>
    </div>
  </template>
</template>
<script>
import api from '../../api'
export default { name: 'ManagedVlessSettings', props: { proxy: { type: Object, required: true } }, data: () => ({ testing: false, status: '保存后自动启动', statusType: 'idle', nodes: [], autoSelected: true }), mounted() { this.loadNodes() }, methods: {
  setNodes(nodes) { this.nodes = nodes || []; this.autoSelected = !this.nodes.some(node => node.selected) },
  async loadNodes() { try { const r = await api.getSingBoxNodes(); this.setNodes(r.data?.nodes) } catch (_) {} },
  async refreshSubscription() { this.testing = true; this.status = '正在更新订阅并启动节点池…'; this.statusType = 'testing'; try { const r = await api.refreshSingBoxSubscription(this.proxy); this.setNodes(r.data?.nodes); this.status = `已载入 ${this.nodes.length} 个节点`; this.statusType = 'success' } catch (e) { this.status = e.response?.data?.detail || e.message || '订阅刷新失败'; this.statusType = 'error' } finally { this.testing = false } },
  async selectNode(tag) { try { const r = await api.selectSingBoxNode(tag); this.setNodes(r.data?.nodes); this.autoSelected = tag === '自动优选'; this.status = tag === '自动优选' ? '已启用自动优选' : `已切换至 ${tag}`; this.statusType = 'success' } catch (e) { this.status = e.response?.data?.detail || '切换失败'; this.statusType = 'error' } },
  async test() { if (this.proxy.subscription_url) return this.refreshSubscription(); this.testing = true; this.status = '正在检查核心与代理出口…'; this.statusType = 'testing'; try { const r = await api.testSingBox(this.proxy); this.status = r.data?.running ? '代理可用，核心运行正常' : '出口检查完成，但核心未运行'; this.statusType = r.data?.running ? 'success' : 'error' } catch (e) { this.status = e.response?.data?.detail || e.message || '连接失败'; this.statusType = 'error' } finally { this.testing = false } },
} }
</script>
<style scoped src="./managedVlessSettings.css"></style>
