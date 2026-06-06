export function javinfoImportJobDetail(job, formatBytes) {
  const parts = []
  if (job.file_size) parts.push(formatBytes(job.file_size))
  if (job.created_at) parts.push(new Date(job.created_at).toLocaleString())
  return parts.length ? parts.join(' · ') : `任务 #${job.id}`
}

export const javinfoImportJobComputed = {
  javinfoImportJobSummary() {
    if (this.javinfoImportJobs.length) return `最近 ${this.javinfoImportJobs.length} 个导入任务`
    return '暂无导入任务'
  },
  javinfoImportJobsStateNote() {
    if (this.javinfoImportJobsLoading) return '正在读取最近导入任务。'
    if (this.javinfoImportJobsError) return this.javinfoImportJobsError
    if (this.javinfoImportJobs.length) return '最近任务已读取。'
    return '最近任务会在导入后显示。'
  },
  javinfoImportJobEmptyNote() {
    return this.javinfoImportUploading || this.isJavInfoImportActive(this.javinfoImportJob)
      ? '任务创建后会显示在这里。'
      : '完成一次导入后会在这里显示结果。'
  },
}

export const aiConnectionComputed = {
  currentAiProvider() {
    return this.aiProviderOptions.find(option => option.value === this.config.ai.provider) || this.aiProviderOptions[0]
  },
  currentAiProviderLabel() { return this.currentAiProvider.label },
  currentAiProviderHint() { return this.currentAiProvider.hint },
  currentAiProviderPlaceholder() { return this.currentAiProvider.placeholder },
  currentAiModelPlaceholder() { return this.currentAiProvider.model },
  currentAiConfig() {
    const provider = this.config.ai.provider || 'openai_compatible'
    return this.config.ai[provider] || this.config.ai.openai_compatible
  },
  aiConnectionBusy() {
    return Boolean(this.aiLoadingModels || this.aiTesting)
  },
}
