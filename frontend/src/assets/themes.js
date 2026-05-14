// 主题配置：每套主题是一组 CSS 变量
// 切换本质：applyTheme() 替换 document.documentElement 的变量集，全站自动响应

export const DEFAULT_THEME_KEY = 'apple-espana'

const SYSTEM_DISPLAY_FONT = "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
const SYSTEM_FONT = "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
const MONO_FONT = "'SF Mono', 'JetBrains Mono', monospace"

const SHARED_TOKENS = {
  // 圆角
  '--radius-xs': '6px',
  '--radius-sm': '8px',
  '--radius-md': '12px',
  '--radius-lg': '16px',
  '--radius-xl': '20px',
  '--radius-pro': 'var(--radius-xl)',
  '--radius-card': '28px',
  '--radius-sheet': '32px',
  '--radius-control': '999px',
  '--touch-target': '44px',
  // 动效
  '--motion-fast': '160ms var(--ease-pro)',
  '--motion-standard': '280ms var(--ease-pro)',
  '--motion-emphasized': '460ms var(--ease-pro)',
  '--motion-reveal': '420ms var(--ease-pro)',
  // 字体
  '--font-body': SYSTEM_FONT,
  '--font-display': SYSTEM_DISPLAY_FONT,
  '--font-mono': MONO_FONT,
  '--type-display': '56px',
  '--type-display-mobile': '32px',
  '--type-page-title': '30px',
  '--type-page-title-mobile': '26px',
  '--type-workbench-title': '24px',
  '--type-entity-title': '28px',
  '--type-section-title': '22px',
  '--type-panel-title': '18px',
  '--type-card-title': '15px',
  '--type-body': '14px',
  '--type-control': '13px',
  '--type-caption': '12px',
  '--type-micro': '11px',
  '--type-badge': '10px',
  '--page-title-size': 'var(--type-display)',
  '--page-title-size-mobile': 'var(--type-display-mobile)',
  '--page-title-line': '1.06',
  '--page-title-weight': '650',
  // 层级
  '--z-base': '0',
  '--z-raised': '10',
  '--z-nav': '100',
  '--z-sheet': '300',
  '--z-dropdown': '700',
  '--z-modal': '900',
  '--z-lightbox': '950',
  '--z-toast': '1000',
  '--z-confirm': '1100',
  // 语义材质
  '--text-on-accent': '#FFFFFF',
  '--surface-nav': 'var(--bg-secondary)',
  '--surface-nav-border': 'var(--border-light)',
  '--surface-control': 'var(--bg-secondary)',
  '--surface-control-hover': 'var(--bg-card-hover)',
  '--surface-input': 'var(--bg-secondary)',
  '--surface-input-focus': 'var(--bg-card)',
  '--surface-scrim': 'rgba(29, 29, 31, 0.18)',
  '--hero-background': 'var(--bg-primary)',
  '--skeleton-base': 'rgba(112, 112, 112, 0.08)',
  '--skeleton-highlight': 'rgba(255, 255, 255, 0.9)',
  '--active-bg': 'var(--surface-control-hover)',
  '--active-border': 'var(--border-light)',
  '--active-indicator': 'var(--text-primary)',
  '--link-text': 'var(--text-primary)',
  '--link-underline': 'var(--border-light)',
  '--link-underline-hover': 'rgba(var(--accent-rgb), 0.28)',
}

const DARK_OVERLAYS = {
  '--white-00': 'rgba(255,255,255,0)',
  '--white-06': 'rgba(255,255,255,0.06)',
  '--white-10': 'rgba(255,255,255,0.10)',
  '--white-15': 'rgba(255,255,255,0.15)',
  '--white-20': 'rgba(255,255,255,0.20)',
  '--black-10': 'rgba(0,0,0,0.10)',
  '--black-20': 'rgba(0,0,0,0.20)',
  '--black-40': 'rgba(0,0,0,0.40)',
  '--black-60': 'rgba(0,0,0,0.60)',
  '--black-80': 'rgba(0,0,0,0.80)',
  '--surface-nav': 'rgba(22, 22, 23, 0.86)',
  '--surface-nav-border': 'rgba(255,255,255,0.12)',
  '--surface-control': 'var(--bg-secondary)',
  '--surface-control-hover': 'var(--bg-card-hover)',
  '--surface-input': 'var(--bg-secondary)',
  '--surface-input-focus': 'var(--bg-card)',
  '--surface-scrim': 'rgba(0,0,0,0.58)',
  '--hero-background': 'radial-gradient(circle at 50% 0%, rgba(var(--accent-rgb), 0.14), transparent 34%), var(--bg-primary)',
  '--skeleton-base': 'rgba(255,255,255,0.055)',
  '--skeleton-highlight': 'rgba(255,255,255,0.13)',
  '--active-bg': 'rgba(255,255,255,0.08)',
  '--active-border': 'rgba(255,255,255,0.16)',
  '--active-indicator': '#FFFFFF',
  '--link-text': 'var(--text-primary)',
  '--link-underline': 'rgba(255,255,255,0.22)',
  '--link-underline-hover': 'rgba(255,255,255,0.48)',
}

const LIGHT_OVERLAYS = {
  '--white-00': 'rgba(255,255,255,0)',
  '--white-06': 'rgba(0,0,0,0.03)',
  '--white-10': 'rgba(0,0,0,0.06)',
  '--white-15': 'rgba(0,0,0,0.10)',
  '--white-20': 'rgba(0,0,0,0.15)',
  '--black-10': 'rgba(0,0,0,0.03)',
  '--black-20': 'rgba(0,0,0,0.06)',
  '--black-40': 'rgba(0,0,0,0.10)',
  '--black-60': 'rgba(0,0,0,0.15)',
  '--black-80': 'rgba(0,0,0,0.20)',
  '--surface-nav': 'rgba(245, 245, 247, 0.86)',
  '--surface-nav-border': '#E8E8ED',
  '--surface-control': 'var(--bg-secondary)',
  '--surface-control-hover': 'var(--bg-card)',
  '--surface-input': 'var(--bg-secondary)',
  '--surface-input-focus': 'var(--bg-card)',
  '--surface-scrim': 'rgba(29,29,31,0.18)',
  '--hero-background': 'radial-gradient(circle at 50% 0%, rgba(var(--accent-rgb), 0.08), transparent 34%), var(--bg-primary)',
  '--skeleton-base': 'rgba(112,112,112,0.08)',
  '--skeleton-highlight': 'rgba(255,255,255,0.9)',
  '--active-bg': '#FFFFFF',
  '--active-border': '#E8E8ED',
  '--active-indicator': '#1D1D1F',
  '--link-text': 'var(--text-primary)',
  '--link-underline': '#D6D6D6',
  '--link-underline-hover': 'rgba(29, 29, 31, 0.32)',
}

const DARK_STATUS = {
  '--badge-success-bg': 'rgba(52, 199, 89, 0.10)',
  '--badge-success-border': 'rgba(52, 199, 89, 0.24)',
  '--badge-success-text': '#32D74B',
  '--badge-warning-bg': 'rgba(255, 159, 10, 0.10)',
  '--badge-warning-border': 'rgba(255, 159, 10, 0.24)',
  '--badge-warning-text': '#FF9F0A',
  '--badge-error-bg': 'rgba(255, 69, 58, 0.10)',
  '--badge-error-border': 'rgba(255, 69, 58, 0.24)',
  '--badge-error-text': '#FF453A',
  '--badge-info-bg': 'rgba(255, 255, 255, 0.06)',
  '--badge-info-border': 'rgba(255, 255, 255, 0.16)',
  '--badge-info-text': '#F2F2F7',
  '--badge-pending-bg': 'rgba(142, 142, 147, 0.10)',
  '--badge-pending-border': 'rgba(142, 142, 147, 0.24)',
  '--badge-pending-text': '#9A9AA2',
}

const LIGHT_STATUS = {
  '--badge-success-bg': 'rgba(52, 199, 89, 0.09)',
  '--badge-success-border': 'rgba(52, 199, 89, 0.22)',
  '--badge-success-text': '#248A3D',
  '--badge-warning-bg': 'rgba(255, 149, 0, 0.10)',
  '--badge-warning-border': 'rgba(255, 149, 0, 0.24)',
  '--badge-warning-text': '#B86E00',
  '--badge-error-bg': 'rgba(255, 59, 48, 0.09)',
  '--badge-error-border': 'rgba(255, 59, 48, 0.22)',
  '--badge-error-text': '#C5271F',
  '--badge-info-bg': 'rgba(28, 31, 35, 0.06)',
  '--badge-info-border': 'rgba(28, 31, 35, 0.13)',
  '--badge-info-text': '#2F343B',
  '--badge-pending-bg': 'rgba(110, 115, 122, 0.09)',
  '--badge-pending-border': 'rgba(110, 115, 122, 0.20)',
  '--badge-pending-text': '#69707A',
}

function makeTheme(config) {
  return {
    label: config.label,
    labelEn: config.labelEn,
    icon: config.icon,
    vars: {
      ...SHARED_TOKENS,
      ...(config.light ? LIGHT_OVERLAYS : DARK_OVERLAYS),
      ...(config.light ? LIGHT_STATUS : DARK_STATUS),
      ...config.vars,
    },
  }
}

export const THEMES = {
  'apple-espana': makeTheme({
    label: '苹果白',
    labelEn: 'Apple Espana',
    icon: '○',
    light: true,
    vars: {
      '--bg-primary': '#FFFFFF',
      '--bg-secondary': '#F5F5F7',
      '--bg-card': '#FFFFFF',
      '--bg-card-hover': '#F5F5F7',
      '--accent': '#1D1D1F',
      '--accent-rgb': '29, 29, 31',
      '--accent-light': '#000000',
      '--text-on-accent': '#FFFFFF',
      '--accent-glow': 'rgba(29, 29, 31, 0.12)',
      '--accent-bg': 'rgba(29, 29, 31, 0.07)',
      '--text-primary': '#1D1D1F',
      '--text-secondary': '#474747',
      '--text-muted': '#707070',
      '--border': '#D6D6D6',
      '--border-light': '#E8E8ED',
      '--shadow-card': '0 1px 2px rgba(29, 29, 31, 0.04)',
      '--shadow-hover': '0 12px 30px rgba(29, 29, 31, 0.09)',
      '--material-glass-subtle': 'rgba(245, 245, 247, 0.78)',
      '--material-glass-elevated': 'rgba(255, 255, 255, 0.86)',
      '--material-glass-sheet': 'rgba(255, 255, 255, 0.92)',
      '--surface-card': '#FFFFFF',
      '--surface-card-hover': '#F5F5F7',
      '--shadow-floating': '0 16px 38px rgba(29, 29, 31, 0.10)',
      '--shadow-sheet': '0 28px 80px rgba(29, 29, 31, 0.16)',
      '--badge-info-bg': '#F5F5F7',
      '--badge-info-border': '#E8E8ED',
      '--badge-info-text': '#474747',
      '--nav-active-bg': 'rgba(255, 255, 255, 0.78)',
    },
  }),

  'apple-pro-dark': makeTheme({
    label: '苹果黑',
    labelEn: 'Apple Pro Dark',
    icon: '●',
    vars: {
      '--bg-primary': '#000000',
      '--bg-secondary': '#161617',
      '--bg-card': '#1D1D1F',
      '--bg-card-hover': '#333336',
      '--accent': '#F5F5F7',
      '--accent-rgb': '245, 245, 247',
      '--accent-light': '#FFFFFF',
      '--text-on-accent': '#000000',
      '--accent-glow': 'rgba(245, 245, 247, 0.16)',
      '--accent-bg': 'rgba(245, 245, 247, 0.10)',
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#F5F5F7',
      '--text-muted': '#86868B',
      '--border': '#333336',
      '--border-light': '#424245',
      '--shadow-card': 'none',
      '--shadow-hover': '0 18px 44px rgba(0, 0, 0, 0.38)',
      '--material-glass-subtle': 'rgba(22, 22, 23, 0.78)',
      '--material-glass-elevated': 'rgba(29, 29, 31, 0.88)',
      '--material-glass-sheet': 'rgba(22, 22, 23, 0.92)',
      '--surface-card': '#1D1D1F',
      '--surface-card-hover': '#333336',
      '--shadow-floating': '0 18px 44px rgba(0, 0, 0, 0.38)',
      '--shadow-sheet': '0 30px 86px rgba(0, 0, 0, 0.62)',
      '--badge-info-bg': 'rgba(245, 245, 247, 0.08)',
      '--badge-info-border': 'rgba(245, 245, 247, 0.16)',
      '--badge-info-text': '#F5F5F7',
      '--nav-active-bg': 'rgba(255, 255, 255, 0.08)',
    },
  }),

  midnight: makeTheme({
    label: '深空暗夜',
    labelEn: 'Midnight',
    icon: '◐',
    vars: {
      // 背景
      '--bg-primary': '#08080A',
      '--bg-secondary': '#101012',
      '--bg-card': 'rgba(255, 255, 255, 0.03)',
      '--bg-card-hover': 'rgba(255, 255, 255, 0.06)',
      // 强调色
      '--accent': '#FFFFFF',
      '--accent-rgb': '255, 255, 255',
      '--accent-light': '#F2F2F7',
      '--text-on-accent': '#1D1D1F',
      '--accent-glow': 'rgba(255, 255, 255, 0.12)',
      '--accent-bg': 'rgba(255, 255, 255, 0.05)',
      // 文字
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#A1A1AA',
      '--text-muted': '#71717A',
      // 边框
      '--border': 'rgba(255, 255, 255, 0.08)',
      '--border-light': 'rgba(255, 255, 255, 0.15)',
      // 阴影与材质
      '--shadow-card': '0 20px 40px rgba(0, 0, 0, 0.60)',
      '--shadow-hover': '0 30px 60px rgba(0, 0, 0, 0.80)',
      '--material-glass-subtle': 'rgba(255, 255, 255, 0.035)',
      '--material-glass-elevated': 'rgba(255, 255, 255, 0.065)',
      '--material-glass-sheet': 'rgba(18, 18, 22, 0.78)',
      '--surface-card': 'rgba(255, 255, 255, 0.035)',
      '--surface-card-hover': 'rgba(255, 255, 255, 0.065)',
      '--shadow-floating': '0 24px 60px rgba(0, 0, 0, 0.45)',
      '--shadow-sheet': '0 40px 100px rgba(0, 0, 0, 0.65)',
      '--nav-active-bg': 'rgba(255, 255, 255, 0.10)',
    },
  }),

  'studio-silver': makeTheme({
    label: '工作室银',
    labelEn: 'Studio Silver',
    icon: '◌',
    light: true,
    vars: {
      '--bg-primary': '#F3F4F6',
      '--bg-secondary': '#ECEEF2',
      '--bg-card': 'rgba(255, 255, 255, 0.58)',
      '--bg-card-hover': 'rgba(255, 255, 255, 0.78)',
      '--accent': '#1D1F23',
      '--accent-rgb': '29, 31, 35',
      '--accent-light': '#343841',
      '--text-on-accent': '#FFFFFF',
      '--accent-glow': 'rgba(29, 31, 35, 0.10)',
      '--accent-bg': 'rgba(29, 31, 35, 0.055)',
      '--text-primary': '#1D1D1F',
      '--text-secondary': '#61656D',
      '--text-muted': '#6F7680',
      '--border': 'rgba(29, 31, 35, 0.105)',
      '--border-light': 'rgba(29, 31, 35, 0.18)',
      '--shadow-card': '0 18px 45px rgba(34, 40, 49, 0.10)',
      '--shadow-hover': '0 24px 60px rgba(34, 40, 49, 0.16)',
      '--material-glass-subtle': 'rgba(255, 255, 255, 0.46)',
      '--material-glass-elevated': 'rgba(255, 255, 255, 0.68)',
      '--material-glass-sheet': 'rgba(246, 247, 250, 0.86)',
      '--surface-card': 'rgba(255, 255, 255, 0.58)',
      '--surface-card-hover': 'rgba(255, 255, 255, 0.82)',
      '--shadow-floating': '0 24px 55px rgba(34, 40, 49, 0.14)',
      '--shadow-sheet': '0 34px 90px rgba(34, 40, 49, 0.20)',
      '--nav-active-bg': 'rgba(29, 31, 35, 0.07)',
    },
  }),

  oled: makeTheme({
    label: '纯黑玻璃',
    labelEn: 'OLED Glass',
    icon: '●',
    vars: {
      '--bg-primary': '#030303',
      '--bg-secondary': '#050505',
      '--bg-card': 'rgba(255, 255, 255, 0.026)',
      '--bg-card-hover': 'rgba(255, 255, 255, 0.055)',
      '--accent': '#E7ECF2',
      '--accent-rgb': '231, 236, 242',
      '--accent-light': '#FFFFFF',
      '--text-on-accent': '#030303',
      '--accent-glow': 'rgba(231, 236, 242, 0.12)',
      '--accent-bg': 'rgba(231, 236, 242, 0.045)',
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#A4A7AD',
      '--text-muted': '#62666D',
      '--border': 'rgba(255, 255, 255, 0.075)',
      '--border-light': 'rgba(255, 255, 255, 0.14)',
      '--shadow-card': '0 20px 42px rgba(0, 0, 0, 0.72)',
      '--shadow-hover': '0 32px 70px rgba(0, 0, 0, 0.88)',
      '--material-glass-subtle': 'rgba(255, 255, 255, 0.028)',
      '--material-glass-elevated': 'rgba(255, 255, 255, 0.055)',
      '--material-glass-sheet': 'rgba(8, 8, 10, 0.84)',
      '--surface-card': 'rgba(255, 255, 255, 0.028)',
      '--surface-card-hover': 'rgba(255, 255, 255, 0.058)',
      '--shadow-floating': '0 24px 64px rgba(0, 0, 0, 0.58)',
      '--shadow-sheet': '0 42px 110px rgba(0, 0, 0, 0.78)',
      '--nav-active-bg': 'rgba(231, 236, 242, 0.08)',
    },
  }),

  'deep-space': makeTheme({
    label: '深空石墨',
    labelEn: 'Deep Graphite',
    icon: '◆',
    vars: {
      '--bg-primary': '#03060B',
      '--bg-secondary': '#080C12',
      '--bg-card': 'rgba(232, 238, 247, 0.032)',
      '--bg-card-hover': 'rgba(232, 238, 247, 0.064)',
      '--accent': '#D8D8DA',
      '--accent-rgb': '216, 216, 218',
      '--accent-light': '#F5F5F7',
      '--text-on-accent': '#03060B',
      '--accent-glow': 'rgba(216, 216, 218, 0.14)',
      '--accent-bg': 'rgba(216, 216, 218, 0.055)',
      '--text-primary': '#F8FAFC',
      '--text-secondary': '#A0A7B2',
      '--text-muted': '#646C78',
      '--border': 'rgba(214, 224, 238, 0.08)',
      '--border-light': 'rgba(214, 224, 238, 0.145)',
      '--shadow-card': '0 20px 44px rgba(0, 0, 0, 0.64)',
      '--shadow-hover': '0 32px 72px rgba(0, 0, 0, 0.82)',
      '--material-glass-subtle': 'rgba(232, 238, 247, 0.034)',
      '--material-glass-elevated': 'rgba(232, 238, 247, 0.066)',
      '--material-glass-sheet': 'rgba(12, 17, 25, 0.80)',
      '--surface-card': 'rgba(232, 238, 247, 0.034)',
      '--surface-card-hover': 'rgba(232, 238, 247, 0.068)',
      '--shadow-floating': '0 24px 64px rgba(0, 0, 0, 0.50)',
      '--shadow-sheet': '0 42px 108px rgba(0, 0, 0, 0.68)',
      '--badge-info-bg': 'rgba(216, 216, 218, 0.12)',
      '--badge-info-border': 'rgba(216, 216, 218, 0.25)',
      '--badge-info-text': '#D8D8DA',
      '--nav-active-bg': 'rgba(216, 216, 218, 0.10)',
    },
  }),

  'graphite-gold': makeTheme({
    label: '石墨金',
    labelEn: 'Graphite Gold',
    icon: '◒',
    vars: {
      '--bg-primary': '#090909',
      '--bg-secondary': '#111111',
      '--bg-card': 'rgba(255, 255, 255, 0.032)',
      '--bg-card-hover': 'rgba(255, 255, 255, 0.062)',
      '--accent': '#D6B66A',
      '--accent-rgb': '214, 182, 106',
      '--accent-light': '#E8D28E',
      '--text-on-accent': '#090909',
      '--accent-glow': 'rgba(214, 182, 106, 0.13)',
      '--accent-bg': 'rgba(214, 182, 106, 0.052)',
      '--text-primary': '#FFFFFF',
      '--text-secondary': '#A09C92',
      '--text-muted': '#6D695F',
      '--border': 'rgba(255, 255, 255, 0.08)',
      '--border-light': 'rgba(214, 182, 106, 0.18)',
      '--shadow-card': '0 20px 42px rgba(0, 0, 0, 0.62)',
      '--shadow-hover': '0 32px 68px rgba(0, 0, 0, 0.82)',
      '--material-glass-subtle': 'rgba(255, 255, 255, 0.034)',
      '--material-glass-elevated': 'rgba(255, 255, 255, 0.062)',
      '--material-glass-sheet': 'rgba(16, 15, 13, 0.80)',
      '--surface-card': 'rgba(255, 255, 255, 0.034)',
      '--surface-card-hover': 'rgba(255, 255, 255, 0.065)',
      '--shadow-floating': '0 24px 62px rgba(0, 0, 0, 0.50)',
      '--shadow-sheet': '0 42px 104px rgba(0, 0, 0, 0.68)',
      '--badge-warning-bg': 'rgba(214, 182, 106, 0.12)',
      '--badge-warning-border': 'rgba(214, 182, 106, 0.28)',
      '--badge-warning-text': '#E8D28E',
      '--nav-active-bg': 'rgba(214, 182, 106, 0.11)',
    },
  }),
}

const LEGACY_THEME_MAP = {
  forest: 'midnight',
  tokyo: 'deep-space',
  aurora: 'deep-space',
  rose: 'graphite-gold',
}

export const THEME_KEYS = Object.keys(THEMES)

export function resolveThemeKey(themeKey) {
  if (themeKey && THEMES[themeKey]) return themeKey
  return LEGACY_THEME_MAP[themeKey] || DEFAULT_THEME_KEY
}

export function applyTheme(themeKey) {
  const resolvedKey = resolveThemeKey(themeKey)
  const theme = THEMES[resolvedKey]
  if (!theme) return resolvedKey

  if (typeof document !== 'undefined') {
    const root = document.documentElement
    Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v))
  }

  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('javhub_theme', resolvedKey)
  }

  return resolvedKey
}

export function restoreTheme() {
  const saved = typeof localStorage !== 'undefined'
    ? localStorage.getItem('javhub_theme')
    : null
  return applyTheme(saved || DEFAULT_THEME_KEY)
}
