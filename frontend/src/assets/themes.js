// 主题配置：每套主题是一组 CSS 变量
// 主题切换通过替换 document.documentElement 的变量集实现

export const THEMES = {
  midnight: {
    label: '深空暗夜',
    labelEn: 'Midnight',
    icon: '🌌',
    vars: {
      '--bg-primary': '#1a1a2e',
      '--bg-secondary': '#16213e',
      '--bg-card': '#252542',
      '--bg-card-hover': '#2d2d4a',
      '--accent': '#4CAF50',
      '--accent-light': '#00E676',
      '--accent-glow': 'rgba(76, 175, 80, 0.3)',
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#9E9E9E',
      '--text-muted': '#6B6B8A',
      '--border': '#333355',
      '--border-light': '#3D3D6B',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.4)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.6)',
    },
  },

  catppuccin: {
    label: '奶油棉花',
    labelEn: 'Catppuccin',
    icon: '🍮',
    vars: {
      '--bg-primary': '#F5F0E8',
      '--bg-secondary': '#EAE4DF',
      '--bg-card': '#FFFFFF',
      '--bg-card-hover': '#F0E8E0',
      '--accent': '#DF8E9A',
      '--accent-light': '#E5A0AA',
      '--accent-glow': 'rgba(223, 142, 154, 0.25)',
      '--text-primary': '#4A3F35',
      '--text-secondary': '#7D6E63',
      '--text-muted': '#A89888',
      '--border': '#DDD5CA',
      '--border-light': '#EAE0D5',
      '--shadow-card': '0 2px 12px rgba(90, 70, 50, 0.1)',
      '--shadow-hover': '0 8px 32px rgba(90, 70, 50, 0.18)',
    },
  },

  oled: {
    label: '纯黑极限',
    labelEn: 'OLED Black',
    icon: '⚫',
    vars: {
      '--bg-primary': '#000000',
      '--bg-secondary': '#0A0A0A',
      '--bg-card': '#111111',
      '--bg-card-hover': '#1A1A1A',
      '--accent': '#00E5FF',
      '--accent-light': '#6EFFFF',
      '--accent-glow': 'rgba(0, 229, 255, 0.25)',
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#888888',
      '--text-muted': '#444444',
      '--border': '#222222',
      '--border-light': '#2A2A2A',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.8)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.9)',
    },
  },

  forest: {
    label: '森林苔藓',
    labelEn: 'Forest',
    icon: '🌿',
    vars: {
      '--bg-primary': '#1A2018',
      '--bg-secondary': '#222C20',
      '--bg-card': '#2A3628',
      '--bg-card-hover': '#324030',
      '--accent': '#7CB342',
      '--accent-light': '#AED581',
      '--accent-glow': 'rgba(124, 179, 66, 0.3)',
      '--text-primary': '#E8F0E0',
      '--text-secondary': '#9CAF88',
      '--text-muted': '#6B7D60',
      '--border': '#3A4838',
      '--border-light': '#445040',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.5)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.7)',
    },
  },

  nord: {
    label: '极地之蓝',
    labelEn: 'Nord',
    icon: '❄️',
    vars: {
      '--bg-primary': '#2E3440',
      '--bg-secondary': '#3B4252',
      '--bg-card': '#434C5E',
      '--bg-card-hover': '#4C566A',
      '--accent': '#88C0D0',
      '--accent-light': '#A3BE8C',
      '--accent-glow': 'rgba(136, 192, 208, 0.25)',
      '--text-primary': '#ECEFF4',
      '--text-secondary': '#D8DEE9',
      '--text-muted': '#4C566A',
      '--border': '#4C566A',
      '--border-light': '#5E81AC',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.3)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.5)',
    },
  },

  tokyo: {
    label: '霓虹东京',
    labelEn: 'Tokyo Night',
    icon: '🌃',
    vars: {
      '--bg-primary': '#1A1B2E',
      '--bg-secondary': '#1F2335',
      '--bg-card': '#24283B',
      '--bg-card-hover': '#2A2F45',
      '--accent': '#7AA2F7',
      '--accent-light': '#BB9AF7',
      '--accent-glow': 'rgba(122, 162, 247, 0.3)',
      '--text-primary': '#C0CAF5',
      '--text-secondary': '#9AA5CE',
      '--text-muted': '#565F89',
      '--border': '#3B4261',
      '--border-light': '#414868',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.4)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.6)',
    },
  },

  aurora: {
    label: '极光绿意',
    labelEn: 'Aurora',
    icon: '🌌',
    vars: {
      '--bg-primary': '#0F111A',
      '--bg-secondary': '#141824',
      '--bg-card': '#1C2030',
      '--bg-card-hover': '#242840',
      '--accent': '#4ADE80',
      '--accent-light': '#22D3EE',
      '--accent-glow': 'rgba(74, 222, 128, 0.25)',
      '--text-primary': '#F0F4F0',
      '--text-secondary': '#94A3B8',
      '--text-muted': '#475569',
      '--border': '#2A3348',
      '--border-light': '#334155',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.5)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.7)',
    },
  },

  rose: {
    label: '玫瑰灰粉',
    labelEn: 'Rose Quartz',
    icon: '🌸',
    vars: {
      '--bg-primary': '#1E1920',
      '--bg-secondary': '#27202A',
      '--bg-card': '#302830',
      '--bg-card-hover': '#3A3040',
      '--accent': '#E879A0',
      '--accent-light': '#F0A0C0',
      '--accent-glow': 'rgba(232, 121, 160, 0.25)',
      '--text-primary': '#F5E8F0',
      '--text-secondary': '#C0A0B0',
      '--text-muted': '#806870',
      '--border': '#403040',
      '--border-light': '#504050',
      '--shadow-card': '0 2px 12px rgba(0, 0, 0, 0.4)',
      '--shadow-hover': '0 8px 32px rgba(0, 0, 0, 0.6)',
    },
  },
}

export const THEME_KEYS = Object.keys(THEMES)

/**
 * 应用主题到根元素
 * @param {string} themeKey - THEMES 里的 key
 */
export function applyTheme(themeKey) {
  const theme = THEMES[themeKey]
  if (!theme) return
  const root = document.documentElement
  Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v))
  // 同步存 localStorage
  localStorage.setItem('javhub_theme', themeKey)
}

/**
 * 恢复上次保存的主题（启动时调用）
 */
export function restoreTheme() {
  const saved = localStorage.getItem('javhub_theme')
  if (saved && THEMES[saved]) {
    applyTheme(saved)
  } else {
    applyTheme('midnight')
  }
}
