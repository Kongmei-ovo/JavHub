export const AI_PROVIDER_OPTIONS = [
  { value: 'openai_compatible', label: 'OpenAI 兼容', hint: '适合 OpenAI、One API、LiteLLM、OpenRouter 等兼容接口。', placeholder: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  { value: 'gemini', label: 'Gemini', hint: '使用 Google Gemini 原生 generateContent 接口。', placeholder: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-2.0-flash' },
  { value: 'ollama', label: 'Ollama', hint: '连接本机或局域网 Ollama 服务。', placeholder: 'http://localhost:11434', model: 'qwen2.5:7b' },
]
