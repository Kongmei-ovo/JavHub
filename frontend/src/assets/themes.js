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
  '--radius-card': '22px',
  '--radius-sheet': '28px',
  '--radius-control': '999px',
  '--touch-target': '40px',

  '--motion-fast': '160ms var(--ease-pro)',
  '--motion-standard': '280ms var(--ease-pro)',
  '--motion-emphasized': '460ms var(--ease-pro)',
  '--motion-reveal': '420ms var(--ease-pro)',

  '--font-body': SYSTEM_FONT,
  '--font-display': SYSTEM_DISPLAY_FONT,
  '--font-mono': MONO_FONT,
  '--type-display': '50px',
  '--type-display-mobile': '32px',
  '--type-page-title': '28px',
  '--type-page-title-mobile': '26px',
  '--type-workbench-title': '24px',
  '--type-entity-title': '28px',
  '--type-section-title': '20px',
  '--type-panel-title': '18px',
  '--type-card-title': '15px',
  '--type-body': '14px',
  '--type-control': '13px',
  '--type-caption': '12px',
  '--type-micro': '11px',
  '--type-badge': '10px',
  '--page-title-size': '40px',
  '--page-title-size-mobile': 'var(--type-display-mobile)',
  '--page-title-line': '1.12',
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
  '--active-bg': 'var(--glass-active-material)',
  '--active-border': 'var(--glass-active-border)',
  '--active-indicator': 'var(--text-primary)',
  '--surface-nav': 'var(--glass-nav-material)',
  '--surface-nav-border': 'var(--glass-edge)',
  '--surface-control': 'var(--material-glass-control)',
  '--surface-control-hover': 'var(--material-glass-control-hover)',
  '--surface-input': 'var(--material-glass-control)',
  '--surface-input-focus': 'var(--glass-active-material)',
  '--surface-scrim': 'var(--scrim)',
  '--surface-card': 'var(--glass-card-material)',
  '--surface-card-hover': 'var(--glass-card-material-hover)',
  '--material-glass-subtle': 'var(--glass-subtle-material)',
  '--material-glass-control': 'var(--glass-control-material)',
  '--material-glass-control-hover': 'var(--glass-control-material-hover)',
  '--material-glass-elevated': 'var(--glass-card-material)',
  '--material-glass-sheet': 'var(--glass-sheet-material)',
  '--hero-background': 'radial-gradient(circle at 50% 0%, var(--ambient-hero), transparent 36%), var(--bg-primary)',
  '--skeleton-base': 'var(--skeleton-track)',
  '--skeleton-highlight': 'var(--skeleton-glint)',
  '--sidebar-width': '224px',
  '--app-chrome-inset': '12px',
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
      '--glass-lowlight': 'rgba(29, 29, 31, 0.050)',
      '--glass-nav-bg': 'rgba(246, 246, 248, 0.72)',
      '--glass-nav-material': 'linear-gradient(145deg, rgba(255,255,255,0.80), rgba(246,246,248,0.62) 46%, rgba(255,255,255,0.50))',
      '--glass-subtle-bg': 'rgba(255, 255, 255, 0.36)',
      '--glass-subtle-material': 'linear-gradient(145deg, rgba(255,255,255,0.44), rgba(255,255,255,0.25) 56%, rgba(255,255,255,0.38))',
      '--glass-card-bg': 'rgba(255, 255, 255, 0.54)',
      '--glass-card-bg-hover': 'rgba(255, 255, 255, 0.68)',
      '--glass-card-material': 'linear-gradient(145deg, rgba(255,255,255,0.64), rgba(255,255,255,0.38) 52%, rgba(255,255,255,0.50))',
      '--glass-card-material-hover': 'linear-gradient(145deg, rgba(255,255,255,0.76), rgba(255,255,255,0.48) 52%, rgba(255,255,255,0.60))',
      '--glass-sheet-bg': 'rgba(255, 255, 255, 0.70)',
      '--glass-sheet-material': 'linear-gradient(145deg, rgba(255,255,255,0.82), rgba(255,255,255,0.58) 50%, rgba(255,255,255,0.68))',
      '--glass-control-bg': 'rgba(255, 255, 255, 0.34)',
      '--glass-control-bg-hover': 'rgba(255, 255, 255, 0.50)',
      '--glass-control-material': 'linear-gradient(145deg, rgba(255,255,255,0.54), rgba(255,255,255,0.25) 48%, rgba(255,255,255,0.42))',
      '--glass-control-material-hover': 'linear-gradient(145deg, rgba(255,255,255,0.68), rgba(255,255,255,0.36) 48%, rgba(255,255,255,0.54))',
      '--glass-control-border': 'rgba(29, 29, 31, 0.10)',
      '--glass-control-border-hover': 'rgba(29, 29, 31, 0.20)',
      '--glass-active-bg': 'rgba(255, 255, 255, 0.74)',
      '--glass-active-material': 'linear-gradient(145deg, rgba(255,255,255,0.88), rgba(255,255,255,0.58) 48%, rgba(255,255,255,0.72))',
      '--glass-active-border': 'rgba(255, 255, 255, 0.96)',
      '--glass-inner-shadow': 'inset 0 1px 0 rgba(255,255,255,0.88), inset 0 -1px 0 rgba(29,29,31,0.055)',
      '--glass-control-shadow': 'inset 0 1px 0 rgba(255,255,255,0.88), inset 0 -1px 0 rgba(29,29,31,0.055), 0 10px 26px rgba(29,29,31,0.075)',
      '--glass-control-shadow-hover': 'inset 0 1px 0 rgba(255,255,255,0.96), inset 0 -1px 0 rgba(29,29,31,0.065), 0 14px 34px rgba(29,29,31,0.105)',
      '--glass-surface-shadow': 'var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.72), inset 0 -1px 0 rgba(29,29,31,0.045)',
      '--glass-active-shadow': '0 12px 28px rgba(29,29,31,0.13), inset 0 1px 0 rgba(255,255,255,0.95), inset 0 -1px 0 rgba(29,29,31,0.055)',
      '--glass-blur-control': '14px',
      '--glass-blur-surface': '22px',
      '--glass-blur-sheet': '28px',
      '--glass-saturate-control': '170%',
      '--glass-saturate-surface': '165%',
      '--app-backdrop-texture': 'linear-gradient(180deg, rgba(255,255,255,0.72), rgba(242,242,247,0.84)), repeating-linear-gradient(135deg, rgba(29,29,31,0.018) 0, rgba(29,29,31,0.018) 1px, transparent 1px, transparent 6px)',
      '--content-material': 'rgba(255, 255, 255, 0.66)',
      '--content-material-border': 'rgba(255, 255, 255, 0.82)',
      '--chrome-floating-shadow': '0 22px 58px rgba(29,29,31,0.12), inset 0 1px 0 rgba(255,255,255,0.78), inset 0 -1px 0 rgba(29,29,31,0.045)',
      '--shadow-card': '0 1px 2px rgba(29, 29, 31, 0.04), 0 18px 46px rgba(29, 29, 31, 0.08)',
      '--shadow-hover': '0 18px 48px rgba(29, 29, 31, 0.13)',
      '--shadow-floating': '0 20px 52px rgba(29, 29, 31, 0.13)',
      '--shadow-sheet': '0 30px 86px rgba(29, 29, 31, 0.18)',
      '--ambient-hero': 'rgba(29, 29, 31, 0.08)',
      '--scrim': 'rgba(29, 29, 31, 0.18)',
      '--media-blackout': '#030304',
      '--media-edge-mask-strong': 'color-mix(in srgb, var(--text-primary) 76%, transparent)',
      '--media-edge-mask-clear': 'transparent',
      '--media-caption-scrim-clear': 'transparent',
      '--media-caption-scrim-strong': 'color-mix(in srgb, var(--media-blackout) 82%, transparent)',
      '--media-caption-text': '#F5F5F7',
      '--skeleton-track': 'rgba(112,112,112,0.08)',
      '--skeleton-glint': 'rgba(255,255,255,0.92)',
      '--link-underline': 'rgba(29, 29, 31, 0.18)',
      '--link-underline-hover': 'rgba(29, 29, 31, 0.38)',
      '--nav-active-bg': 'var(--glass-active-material)',
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
      '--glass-highlight': 'rgba(255, 255, 255, 0.24)',
      '--glass-lowlight': 'rgba(0, 0, 0, 0.30)',
      '--glass-nav-bg': 'rgba(14, 15, 17, 0.70)',
      '--glass-nav-material': 'linear-gradient(145deg, rgba(34,35,38,0.64), rgba(12,13,15,0.46) 48%, rgba(28,29,32,0.54))',
      '--glass-subtle-bg': 'rgba(18, 19, 21, 0.28)',
      '--glass-subtle-material': 'linear-gradient(145deg, rgba(255,255,255,0.115), rgba(16,17,19,0.34) 50%, rgba(255,255,255,0.070))',
      '--glass-card-bg': 'rgba(18, 19, 21, 0.42)',
      '--glass-card-bg-hover': 'rgba(30, 31, 34, 0.50)',
      '--glass-card-material': 'linear-gradient(145deg, rgba(255,255,255,0.130), rgba(18,19,21,0.40) 48%, rgba(255,255,255,0.075))',
      '--glass-card-material-hover': 'linear-gradient(145deg, rgba(255,255,255,0.165), rgba(26,27,30,0.46) 48%, rgba(255,255,255,0.095))',
      '--glass-sheet-bg': 'rgba(18, 19, 21, 0.60)',
      '--glass-sheet-material': 'linear-gradient(145deg, rgba(255,255,255,0.155), rgba(18,19,21,0.62) 50%, rgba(255,255,255,0.090))',
      '--glass-control-bg': 'rgba(18, 19, 21, 0.36)',
      '--glass-control-bg-hover': 'rgba(30, 31, 34, 0.44)',
      '--glass-control-material': 'linear-gradient(145deg, rgba(255,255,255,0.145), rgba(18,19,21,0.31) 46%, rgba(255,255,255,0.080))',
      '--glass-control-material-hover': 'linear-gradient(145deg, rgba(255,255,255,0.190), rgba(26,27,30,0.39) 46%, rgba(255,255,255,0.110))',
      '--glass-control-border': 'rgba(255, 255, 255, 0.12)',
      '--glass-control-border-hover': 'rgba(255, 255, 255, 0.24)',
      '--glass-active-bg': 'rgba(42, 43, 46, 0.54)',
      '--glass-active-material': 'linear-gradient(145deg, rgba(255,255,255,0.245), rgba(36,37,40,0.52) 48%, rgba(255,255,255,0.140))',
      '--glass-active-border': 'rgba(255, 255, 255, 0.32)',
      '--glass-inner-shadow': 'inset 0 1px 0 rgba(255,255,255,0.18), inset 0 -1px 0 rgba(0,0,0,0.24)',
      '--glass-control-shadow': 'inset 0 1px 0 rgba(255,255,255,0.19), inset 0 -1px 0 rgba(0,0,0,0.24), 0 12px 30px rgba(0,0,0,0.22)',
      '--glass-control-shadow-hover': 'inset 0 1px 0 rgba(255,255,255,0.25), inset 0 -1px 0 rgba(0,0,0,0.24), 0 16px 38px rgba(0,0,0,0.30)',
      '--glass-surface-shadow': 'var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.14), inset 0 -1px 0 rgba(0,0,0,0.22)',
      '--glass-active-shadow': '0 16px 36px rgba(0,0,0,0.36), inset 0 1px 0 rgba(255,255,255,0.27), inset 0 -1px 0 rgba(0,0,0,0.24)',
      '--glass-blur-control': '12px',
      '--glass-blur-surface': '20px',
      '--glass-blur-sheet': '26px',
      '--glass-saturate-control': '145%',
      '--glass-saturate-surface': '140%',
      '--app-backdrop-texture': 'linear-gradient(180deg, rgba(18,18,20,0.96), rgba(5,5,6,1)), repeating-linear-gradient(135deg, rgba(255,255,255,0.026) 0, rgba(255,255,255,0.026) 1px, transparent 1px, transparent 6px)',
      '--content-material': 'rgba(10, 10, 12, 0.72)',
      '--content-material-border': 'rgba(255, 255, 255, 0.090)',
      '--chrome-floating-shadow': '0 26px 70px rgba(0,0,0,0.52), inset 0 1px 0 rgba(255,255,255,0.13), inset 0 -1px 0 rgba(0,0,0,0.24)',
      '--shadow-card': '0 1px 0 rgba(255, 255, 255, 0.03), 0 22px 54px rgba(0, 0, 0, 0.40)',
      '--shadow-hover': '0 24px 64px rgba(0, 0, 0, 0.52)',
      '--shadow-floating': '0 24px 68px rgba(0, 0, 0, 0.48)',
      '--shadow-sheet': '0 34px 92px rgba(0, 0, 0, 0.66)',
      '--ambient-hero': 'rgba(255, 255, 255, 0.13)',
      '--scrim': 'rgba(0, 0, 0, 0.58)',
      '--media-blackout': '#010102',
      '--media-edge-mask-strong': 'color-mix(in srgb, var(--text-primary) 72%, transparent)',
      '--media-edge-mask-clear': 'transparent',
      '--media-caption-scrim-clear': 'transparent',
      '--media-caption-scrim-strong': 'color-mix(in srgb, var(--media-blackout) 86%, transparent)',
      '--media-caption-text': '#F5F5F7',
      '--skeleton-track': 'rgba(255,255,255,0.055)',
      '--skeleton-glint': 'rgba(255,255,255,0.13)',
      '--link-underline': 'rgba(255,255,255,0.22)',
      '--link-underline-hover': 'rgba(255,255,255,0.48)',
      '--nav-active-bg': 'var(--glass-active-material)',
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
