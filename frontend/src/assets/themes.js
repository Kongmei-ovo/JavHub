// Two-mode Apple Liquid Glass theme system.
// applyTheme() swaps CSS custom properties on :root so the whole app responds.

export const DEFAULT_THEME_KEY = 'apple-light'
export const DARK_THEME_KEY = 'apple-dark'

const SYSTEM_DISPLAY_FONT = "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
const SYSTEM_FONT = "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
const MONO_FONT = "'SF Mono', 'JetBrains Mono', monospace"

const SHARED_TOKENS = {
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

  '--motion-fast': '160ms var(--ease-pro)',
  '--motion-standard': '280ms var(--ease-pro)',
  '--motion-emphasized': '460ms var(--ease-pro)',
  '--motion-reveal': '420ms var(--ease-pro)',

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

  '--z-base': '0',
  '--z-raised': '10',
  '--z-nav': '100',
  '--z-sheet': '300',
  '--z-dropdown': '700',
  '--z-modal': '900',
  '--z-lightbox': '950',
  '--z-toast': '1000',
  '--z-confirm': '1100',

  '--link-text': 'var(--text-primary)',
  '--text-on-accent': 'var(--bg-primary)',
  '--active-bg': 'var(--glass-active-bg)',
  '--active-border': 'var(--glass-active-border)',
  '--active-indicator': 'var(--text-primary)',
  '--surface-nav': 'var(--glass-nav-bg)',
  '--surface-nav-border': 'var(--glass-edge)',
  '--surface-control': 'var(--glass-control-bg)',
  '--surface-control-hover': 'var(--glass-control-bg-hover)',
  '--surface-input': 'var(--glass-control-bg)',
  '--surface-input-focus': 'var(--glass-active-bg)',
  '--surface-scrim': 'var(--scrim)',
  '--surface-card': 'var(--glass-card-bg)',
  '--surface-card-hover': 'var(--glass-card-bg-hover)',
  '--material-glass-subtle': 'var(--glass-subtle-bg)',
  '--material-glass-elevated': 'var(--glass-card-bg)',
  '--material-glass-sheet': 'var(--glass-sheet-bg)',
  '--hero-background': 'radial-gradient(circle at 50% 0%, var(--ambient-hero), transparent 36%), var(--bg-primary)',
  '--skeleton-base': 'var(--skeleton-track)',
  '--skeleton-highlight': 'var(--skeleton-glint)',
}

const STATUS_TOKENS = {
  light: {
    '--badge-success-bg': 'rgba(52, 199, 89, 0.10)',
    '--badge-success-border': 'rgba(52, 199, 89, 0.24)',
    '--badge-success-text': '#248A3D',
    '--badge-warning-bg': 'rgba(255, 149, 0, 0.11)',
    '--badge-warning-border': 'rgba(255, 149, 0, 0.25)',
    '--badge-warning-text': '#B86E00',
    '--badge-error-bg': 'rgba(255, 59, 48, 0.10)',
    '--badge-error-border': 'rgba(255, 59, 48, 0.24)',
    '--badge-error-text': '#C5271F',
    '--badge-info-bg': 'rgba(29, 29, 31, 0.06)',
    '--badge-info-border': 'rgba(29, 29, 31, 0.12)',
    '--badge-info-text': '#3A3A3C',
    '--badge-pending-bg': 'rgba(110, 115, 122, 0.09)',
    '--badge-pending-border': 'rgba(110, 115, 122, 0.20)',
    '--badge-pending-text': '#69707A',
  },
  dark: {
    '--badge-success-bg': 'rgba(52, 199, 89, 0.12)',
    '--badge-success-border': 'rgba(52, 199, 89, 0.26)',
    '--badge-success-text': '#32D74B',
    '--badge-warning-bg': 'rgba(255, 159, 10, 0.12)',
    '--badge-warning-border': 'rgba(255, 159, 10, 0.26)',
    '--badge-warning-text': '#FF9F0A',
    '--badge-error-bg': 'rgba(255, 69, 58, 0.12)',
    '--badge-error-border': 'rgba(255, 69, 58, 0.26)',
    '--badge-error-text': '#FF453A',
    '--badge-info-bg': 'rgba(255, 255, 255, 0.07)',
    '--badge-info-border': 'rgba(255, 255, 255, 0.16)',
    '--badge-info-text': '#F2F2F7',
    '--badge-pending-bg': 'rgba(142, 142, 147, 0.11)',
    '--badge-pending-border': 'rgba(142, 142, 147, 0.24)',
    '--badge-pending-text': '#9A9AA2',
  },
}

function makeTheme(config) {
  return {
    label: config.label,
    labelEn: config.labelEn,
    icon: config.icon,
    mode: config.mode,
    vars: {
      ...SHARED_TOKENS,
      ...STATUS_TOKENS[config.mode],
      ...config.vars,
    },
  }
}

export const THEMES = {
  'apple-light': makeTheme({
    label: '开灯',
    labelEn: 'Apple Light',
    icon: '☼',
    mode: 'light',
    vars: {
      '--bg-primary': '#FBFBFD',
      '--bg-secondary': '#F2F2F7',
      '--bg-card': 'rgba(255, 255, 255, 0.72)',
      '--bg-card-hover': 'rgba(255, 255, 255, 0.86)',
      '--accent': '#1D1D1F',
      '--accent-rgb': '29, 29, 31',
      '--accent-light': '#000000',
      '--accent-glow': 'rgba(29, 29, 31, 0.12)',
      '--accent-bg': 'rgba(29, 29, 31, 0.07)',
      '--text-primary': '#1D1D1F',
      '--text-secondary': '#515154',
      '--text-muted': '#77777D',
      '--border': 'rgba(29, 29, 31, 0.10)',
      '--border-light': 'rgba(29, 29, 31, 0.15)',
      '--glass-edge': 'rgba(29, 29, 31, 0.10)',
      '--glass-edge-strong': 'rgba(29, 29, 31, 0.16)',
      '--glass-highlight': 'rgba(255, 255, 255, 0.92)',
      '--glass-nav-bg': 'rgba(246, 246, 248, 0.72)',
      '--glass-subtle-bg': 'rgba(255, 255, 255, 0.42)',
      '--glass-card-bg': 'rgba(255, 255, 255, 0.62)',
      '--glass-card-bg-hover': 'rgba(255, 255, 255, 0.78)',
      '--glass-sheet-bg': 'rgba(255, 255, 255, 0.78)',
      '--glass-control-bg': 'rgba(255, 255, 255, 0.40)',
      '--glass-control-bg-hover': 'rgba(255, 255, 255, 0.58)',
      '--glass-control-border': 'rgba(29, 29, 31, 0.10)',
      '--glass-control-border-hover': 'rgba(29, 29, 31, 0.17)',
      '--glass-active-bg': 'rgba(255, 255, 255, 0.82)',
      '--glass-active-border': 'rgba(255, 255, 255, 0.96)',
      '--glass-inner-shadow': 'inset 0 1px 0 rgba(255,255,255,0.85), inset 0 -1px 0 rgba(29,29,31,0.035)',
      '--glass-active-shadow': '0 12px 28px rgba(29,29,31,0.13), inset 0 1px 0 rgba(255,255,255,0.95)',
      '--shadow-card': '0 1px 2px rgba(29, 29, 31, 0.04), 0 18px 46px rgba(29, 29, 31, 0.08)',
      '--shadow-hover': '0 18px 48px rgba(29, 29, 31, 0.13)',
      '--shadow-floating': '0 20px 52px rgba(29, 29, 31, 0.13)',
      '--shadow-sheet': '0 30px 86px rgba(29, 29, 31, 0.18)',
      '--ambient-hero': 'rgba(29, 29, 31, 0.08)',
      '--scrim': 'rgba(29, 29, 31, 0.18)',
      '--skeleton-track': 'rgba(112,112,112,0.08)',
      '--skeleton-glint': 'rgba(255,255,255,0.92)',
      '--link-underline': 'rgba(29, 29, 31, 0.18)',
      '--link-underline-hover': 'rgba(29, 29, 31, 0.38)',
      '--nav-active-bg': 'var(--glass-active-bg)',
    },
  }),

  'apple-dark': makeTheme({
    label: '关灯',
    labelEn: 'Apple Dark',
    icon: '☾',
    mode: 'dark',
    vars: {
      '--bg-primary': '#050506',
      '--bg-secondary': '#101012',
      '--bg-card': 'rgba(28, 28, 30, 0.58)',
      '--bg-card-hover': 'rgba(44, 44, 46, 0.70)',
      '--accent': '#F5F5F7',
      '--accent-rgb': '245, 245, 247',
      '--accent-light': '#FFFFFF',
      '--accent-glow': 'rgba(245, 245, 247, 0.16)',
      '--accent-bg': 'rgba(245, 245, 247, 0.10)',
      '--text-primary': '#F5F5F7',
      '--text-secondary': '#D1D1D6',
      '--text-muted': '#8E8E93',
      '--border': 'rgba(255, 255, 255, 0.10)',
      '--border-light': 'rgba(255, 255, 255, 0.16)',
      '--glass-edge': 'rgba(255, 255, 255, 0.12)',
      '--glass-edge-strong': 'rgba(255, 255, 255, 0.22)',
      '--glass-highlight': 'rgba(255, 255, 255, 0.18)',
      '--glass-nav-bg': 'rgba(18, 18, 20, 0.76)',
      '--glass-subtle-bg': 'rgba(255, 255, 255, 0.045)',
      '--glass-card-bg': 'rgba(255, 255, 255, 0.070)',
      '--glass-card-bg-hover': 'rgba(255, 255, 255, 0.10)',
      '--glass-sheet-bg': 'rgba(22, 22, 24, 0.82)',
      '--glass-control-bg': 'rgba(255, 255, 255, 0.060)',
      '--glass-control-bg-hover': 'rgba(255, 255, 255, 0.095)',
      '--glass-control-border': 'rgba(255, 255, 255, 0.12)',
      '--glass-control-border-hover': 'rgba(255, 255, 255, 0.24)',
      '--glass-active-bg': 'rgba(255, 255, 255, 0.16)',
      '--glass-active-border': 'rgba(255, 255, 255, 0.24)',
      '--glass-inner-shadow': 'inset 0 1px 0 rgba(255,255,255,0.13), inset 0 -1px 0 rgba(0,0,0,0.30)',
      '--glass-active-shadow': '0 16px 36px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.20)',
      '--shadow-card': '0 1px 0 rgba(255, 255, 255, 0.03), 0 22px 54px rgba(0, 0, 0, 0.40)',
      '--shadow-hover': '0 24px 64px rgba(0, 0, 0, 0.52)',
      '--shadow-floating': '0 24px 68px rgba(0, 0, 0, 0.48)',
      '--shadow-sheet': '0 34px 92px rgba(0, 0, 0, 0.66)',
      '--ambient-hero': 'rgba(255, 255, 255, 0.13)',
      '--scrim': 'rgba(0, 0, 0, 0.58)',
      '--skeleton-track': 'rgba(255,255,255,0.055)',
      '--skeleton-glint': 'rgba(255,255,255,0.13)',
      '--link-underline': 'rgba(255,255,255,0.22)',
      '--link-underline-hover': 'rgba(255,255,255,0.48)',
      '--nav-active-bg': 'var(--glass-active-bg)',
    },
  }),
}

const LEGACY_THEME_MAP = {
  'apple-espana': 'apple-light',
  'studio-silver': 'apple-light',
  'apple-pro-dark': 'apple-dark',
  midnight: 'apple-dark',
  oled: 'apple-dark',
  'deep-space': 'apple-dark',
  'graphite-gold': 'apple-dark',
  forest: 'apple-dark',
  tokyo: 'apple-dark',
  aurora: 'apple-dark',
  rose: 'apple-dark',
}

export const THEME_KEYS = Object.keys(THEMES)

export function resolveThemeKey(themeKey) {
  if (themeKey && THEMES[themeKey]) return themeKey
  return LEGACY_THEME_MAP[themeKey] || DEFAULT_THEME_KEY
}

export function isDarkTheme(themeKey) {
  return resolveThemeKey(themeKey) === DARK_THEME_KEY
}

export function applyTheme(themeKey) {
  const resolvedKey = resolveThemeKey(themeKey)
  const theme = THEMES[resolvedKey]
  if (!theme) return resolvedKey

  if (typeof document !== 'undefined') {
    const root = document.documentElement
    Object.entries(theme.vars).forEach(([key, value]) => root.style.setProperty(key, value))
    root.dataset.theme = theme.mode
  }

  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('javhub_theme', resolvedKey)
  }

  return resolvedKey
}

export function toggleTheme(currentTheme) {
  return applyTheme(isDarkTheme(currentTheme) ? DEFAULT_THEME_KEY : DARK_THEME_KEY)
}

export function restoreTheme() {
  const saved = typeof localStorage !== 'undefined'
    ? localStorage.getItem('javhub_theme')
    : null
  return applyTheme(saved || DEFAULT_THEME_KEY)
}
