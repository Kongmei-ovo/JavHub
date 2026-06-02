import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const vueSource = readFileSync(new URL('./Search.vue', import.meta.url), 'utf8')
const externalStyle = readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8')
const source = `${vueSource}\n${externalStyle}`

function sourceBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} should exist`)
  return match[1]
}

function backgroundIncludes(token) {
  return new RegExp(`background:[\\s\\S]*var\\(--${token}\\)`)
}

test('search page keeps large scoped styles in a feature stylesheet', () => {
  assert.match(vueSource, /<style scoped src="\.\.\/features\/search\/search\.css"><\/style>/)
  assert.ok(vueSource.split('\n').length < 800, 'Search.vue should stay below 800 lines')
  assert.ok(externalStyle.split('\n').length > 850, 'external stylesheet should contain the moved search styles')
})

test('search page requests grouped variants with explanations by default', () => {
  assert.match(source, /variant_mode:\s*'grouped'/)
  assert.match(source, /include_variant_explanations:\s*1/)
  assert.doesNotMatch(source, /variant_scope:\s*'indexed'/)
})

test('search page can expand backend-provided variant groups inline', () => {
  assert.match(source, /expandedVariantGroups/)
  assert.match(source, /variantGroupItems\(item\)/)
  assert.match(source, /另 \{\{ item\.variant_group_count - 1 \}\} 个版本/)
  assert.match(source, /toggleVariantGroup\(item\)/)
})

test('search page reuses shared video variant presentation helpers', () => {
  assert.match(source, /import \{ variantGroupKey, visibleVariantItems \} from '\.\.\/utils\/videoVariantPresentation\.js'/)
  assert.doesNotMatch(source, /variantGroupKey\(item\) \{\s*return item\.canonical_code/)
  assert.doesNotMatch(source, /const keyOf = \(value\) => value\?\.content_id/)
})

test('search cards pass backend display code and variant labels into MovieCard', () => {
  assert.match(source, /:contentId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:dvdId="item\.display_code \|\| item\.dvd_id \|\| item\.content_id"/)
  assert.match(source, /:variantLabels="item\.variant_labels \|\| \[\]"/)
  assert.match(source, /:variantExplanations="item\.variant_explanations \|\| \[\]"/)
})

test('search filter chrome uses shared liquid glass controls without uppercase microcopy', () => {
  const commandCapsuleBlock = sourceBlock('.command-capsule')
  const commandCapsuleFocusedBlock = sourceBlock('.command-capsule.focused')
  const capsuleDividerBlock = sourceBlock('.capsule-divider')
  const sortLabelBlock = sourceBlock('.sort-strip-label')
  const panelLabelBlock = sourceBlock('.panel-field label')
  const sortResultCountBlock = sourceBlock('.sort-result-count')
  const barDividerBlock = sourceBlock('.bar-divider')
  const sortPillBlock = sourceBlock('.sort-pill')
  const sortPillHoverBlock = sourceBlock('.sort-pill:hover')
  const sortPillActiveBlock = sourceBlock('.sort-pill.active')
  const sortPillActiveHoverBlock = sourceBlock('.sort-pill.active:hover')
  const randomPillActiveBlock = sourceBlock('.sort-pill.random.active')
  const sortClearButtonBlock = sourceBlock('.sort-clear-btn')
  const sortClearButtonHoverBlock = sourceBlock('.sort-clear-btn:hover')
  const filterItemBlock = sourceBlock('.filter-item')
  const filterItemHoverBlock = sourceBlock('.filter-item:hover')
  const filterItemActiveBlock = sourceBlock('.filter-item.toggle.active')
  const appliedChipBlock = sourceBlock('.applied-chip')
  const appliedChipHoverBlock = sourceBlock('.applied-chip:hover')
  const advancedPanelBlock = sourceBlock('.advanced-panel')
  const panelFooterBlock = sourceBlock('.panel-footer')
  const panelInputBlock = sourceBlock('.panel-input')
  const panelInputFocusBlock = sourceBlock('.panel-input:focus')
  const trayTagBlock = sourceBlock('.tray-tag')
  const mobileBlock = source.match(/@media \(max-width:\s*768px\)\s*\{[\s\S]*\n\}/)?.[0] || ''

  assert.match(sortLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(sortLabelBlock, /text-transform:\s*uppercase/)
  assert.match(panelLabelBlock, /letter-spacing:\s*0/)
  assert.doesNotMatch(panelLabelBlock, /text-transform:\s*uppercase/)
  assert.match(capsuleDividerBlock, /background:\s*var\(--glass-control-border\)/)
  assert.match(sortResultCountBlock, /border-right:\s*1px solid var\(--glass-control-border\)/)
  assert.match(barDividerBlock, /background:\s*var\(--glass-control-border\)/)
  for (const block of [capsuleDividerBlock, sortResultCountBlock, barDividerBlock]) {
    assert.doesNotMatch(block, /var\(--border\)/)
  }

  assert.match(commandCapsuleBlock, backgroundIncludes('material-glass-sheet'))
  assert.match(commandCapsuleBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(commandCapsuleBlock, /box-shadow:\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(commandCapsuleBlock, /var\(--shadow-floating\)/)
  assert.match(commandCapsuleFocusedBlock, backgroundIncludes('glass-active-material'))
  assert.match(commandCapsuleFocusedBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(commandCapsuleFocusedBlock, /box-shadow:\s*var\(--glass-active-shadow\),\s*var\(--glass-surface-shadow\)/)
  assert.doesNotMatch(commandCapsuleFocusedBlock, /var\(--shadow-floating\)/)

  assert.match(advancedPanelBlock, backgroundIncludes('material-glass-sheet'))
  assert.match(advancedPanelBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(advancedPanelBlock, /box-shadow:\s*var\(--shadow-sheet\)/)
  assert.match(panelFooterBlock, /border-top:\s*1px solid var\(--glass-edge\)/)
  assert.doesNotMatch(panelFooterBlock, /var\(--border\)/)

  assert.doesNotMatch(source, /\.sort-pill[\s\S]*?background:\s*var\(--surface-control\)|\.sort-pill[\s\S]*?background:\s*var\(--surface-control-hover\)|\.sort-pill[\s\S]*?var\(--active-border\)/)
  assert.doesNotMatch(source, /\.filter-item[\s\S]*?background:\s*var\(--surface-control\)|\.filter-item[\s\S]*?background:\s*var\(--surface-control-hover\)|\.filter-item[\s\S]*?var\(--active-border\)/)
  assert.doesNotMatch(source, /\.applied-chip[\s\S]*?background:\s*var\(--surface-control\)|\.applied-chip[\s\S]*?background:\s*var\(--surface-control-hover\)/)
  assert.doesNotMatch(source, /\.panel-input[\s\S]*?background:\s*var\(--surface-input\)|\.panel-input[\s\S]*?background:\s*var\(--surface-input-focus\)|\.panel-input[\s\S]*?border-color:\s*var\(--accent\)/)

  for (const [block, name] of [
    [sortPillBlock, 'sort pill'],
    [sortClearButtonBlock, 'sort clear'],
    [filterItemBlock, 'filter item'],
    [appliedChipBlock, 'applied chip'],
    [panelInputBlock, 'panel input'],
    [trayTagBlock, 'tray tag'],
  ]) {
    assert.match(block, backgroundIncludes('material-glass-control'), `${name} should use shared glass control`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
  }

  for (const [block, name] of [
    [sortPillHoverBlock, 'sort pill hover'],
    [filterItemHoverBlock, 'filter item hover'],
    [appliedChipHoverBlock, 'applied chip hover'],
  ]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
  }

  assert.match(sortClearButtonHoverBlock, /background:\s*var\(--badge-error-bg\)/)
  assert.match(sortClearButtonHoverBlock, /border-color:\s*var\(--badge-error-border\)/)
  assert.match(sortClearButtonHoverBlock, /color:\s*var\(--badge-error-text\)/)
  assert.doesNotMatch(sortClearButtonHoverBlock, /#FF375F|rgba\(255,\s*55,\s*95/i)

  for (const [block, name] of [
    [sortPillActiveBlock, 'sort pill active'],
    [randomPillActiveBlock, 'random pill active'],
    [filterItemActiveBlock, 'filter item active'],
  ]) {
    assert.match(block, backgroundIncludes('glass-active-material'), `${name} should use active glass material`)
    assert.match(block, /border-color:\s*var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
  }
  assert.match(sortPillActiveHoverBlock, backgroundIncludes('material-glass-control-hover'))
  assert.match(sortPillActiveHoverBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(panelInputFocusBlock, /border-color:\s*var\(--glass-active-border\)/)
  assert.match(panelInputFocusBlock, backgroundIncludes('glass-active-material'))
  assert.match(panelInputFocusBlock, /box-shadow:\s*var\(--glass-active-shadow\)/)

  assert.match(mobileBlock, /\.variant-inline-item\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.doesNotMatch(source, /\.variant-inline-item\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.04\)/)
})

test('search inline variant controls use shared glass materials and explicit motion', () => {
  const variantButtonBlock = sourceBlock('.variant-expand-btn')
  const variantButtonHoverBlock = sourceBlock('.variant-expand-btn:hover')
  const variantButtonActiveBlock = sourceBlock('.variant-expand-btn:active')
  const variantRowBlock = sourceBlock('.variant-inline-item')
  const variantRowHoverBlock = sourceBlock('.variant-inline-item:hover')

  for (const [block, name] of [[variantButtonBlock, 'variant button'], [variantRowBlock, 'variant row']]) {
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, backgroundIncludes('material-glass-control'), `${name} should use shared glass material`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /transition:\s*var\(--transition-pro\)|background:\s*var\(--surface-control\)/, `${name} should not keep legacy flat controls`)
  }

  for (const [block, name] of [[variantButtonHoverBlock, 'variant button hover'], [variantRowHoverBlock, 'variant row hover']]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lightly lift`)
  }

  assert.match(variantButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assert.doesNotMatch(source, /\.variant-expand-btn\s*\{[^}]*transition:\s*var\(--transition-pro\)/)
})

test('search pagination controls use shared glass materials and explicit motion', () => {
  const pageButtonBlock = sourceBlock('.page-btn')
  const pageButtonHoverBlock = sourceBlock('.page-btn:hover:not(:disabled)')
  const pageButtonActiveBlock = sourceBlock('.page-btn:active:not(:disabled)')
  const jumpInputBlock = sourceBlock('.jump-input')
  const jumpInputFocusBlock = sourceBlock('.jump-input:focus')
  const jumpButtonBlock = sourceBlock('.jump-btn')
  const jumpButtonHoverBlock = sourceBlock('.jump-btn:hover')
  const jumpButtonActiveBlock = sourceBlock('.jump-btn:active')

  for (const [block, name] of [[pageButtonBlock, 'page button'], [jumpButtonBlock, 'jump button']]) {
    assert.match(block, backgroundIncludes('material-glass-control'), `${name} should use shared glass material`)
    assert.match(block, /border:\s*1px solid var\(--glass-control-border\)/, `${name} should use shared glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow\)/, `${name} should use shared glass shadow`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /transition:\s*var\(--transition-pro\)|background:\s*var\(--surface-control\)/, `${name} should not keep legacy pagination material`)
  }

  for (const [block, name] of [[pageButtonHoverBlock, 'page button hover'], [jumpButtonHoverBlock, 'jump button hover']]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
    assert.match(block, /transform:\s*translateY\(-1px\)/, `${name} should lightly lift`)
  }

  assert.match(pageButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assert.match(jumpButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)

  assert.match(jumpInputBlock, backgroundIncludes('material-glass-control'))
  assert.match(jumpInputBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(jumpInputBlock, /transition:\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(jumpInputBlock, /transition:\s*var\(--transition-pro\)|background:\s*var\(--surface-input\)/)
  assert.match(jumpInputFocusBlock, /border-color:\s*var\(--glass-control-border-hover\)/)
  assert.match(jumpInputFocusBlock, backgroundIncludes('material-glass-control-hover'))
  assert.doesNotMatch(source, /\.page-btn\s*\{[^}]*transition:\s*var\(--transition-pro\)|\.jump-btn\s*\{[^}]*transition:\s*var\(--transition-pro\)|\.jump-input\s*\{[^}]*transition:\s*var\(--transition-pro\)/)
})

test('search primary action buttons use active glass instead of solid accent fills', () => {
  const capsuleButtonBlock = sourceBlock('.capsule-search-btn')
  const capsuleButtonHoverBlock = sourceBlock('.capsule-search-btn:hover')
  const capsuleButtonActiveBlock = sourceBlock('.capsule-search-btn:active')
  const clearButtonBlock = sourceBlock('.btn-clear')
  const clearButtonHoverBlock = sourceBlock('.btn-clear:hover')
  const clearButtonActiveBlock = sourceBlock('.btn-clear:active')
  const applyButtonBlock = sourceBlock('.btn-apply')
  const applyButtonHoverBlock = sourceBlock('.btn-apply:hover')
  const applyButtonActiveBlock = sourceBlock('.btn-apply:active')

  for (const [block, name] of [[capsuleButtonBlock, 'capsule search button'], [applyButtonBlock, 'apply button']]) {
    assert.match(block, backgroundIncludes('glass-active-material'), `${name} should use active glass material`)
    assert.match(block, /border:\s*1px solid var\(--glass-active-border\)/, `${name} should use active glass border`)
    assert.match(block, /box-shadow:\s*var\(--glass-active-shadow\)/, `${name} should use active glass shadow`)
    assert.match(block, /color:\s*var\(--text-primary\)/, `${name} should keep text on glass, not accent fill`)
    assert.match(block, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/, `${name} should use control blur`)
    assert.match(block, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/, `${name} should use explicit motion tokens`)
    assert.doesNotMatch(block, /background:\s*var\(--accent\)|color:\s*var\(--text-on-accent\)|border:\s*none|transition:\s*all\b|box-shadow:\s*none/, `${name} should not keep the legacy solid primary`)
  }

  assert.match(clearButtonBlock, backgroundIncludes('material-glass-control'))
  assert.match(clearButtonBlock, /border:\s*1px solid var\(--glass-control-border\)/)
  assert.match(clearButtonBlock, /box-shadow:\s*var\(--glass-control-shadow\)/)
  assert.match(clearButtonBlock, /backdrop-filter:\s*blur\(var\(--glass-blur-control\)\)\s*saturate\(var\(--glass-saturate-control\)\)/)
  assert.match(clearButtonBlock, /transition:\s*transform var\(--motion-standard\),\s*background var\(--motion-standard\),\s*border-color var\(--motion-standard\),\s*box-shadow var\(--motion-standard\),\s*color var\(--motion-fast\),\s*opacity var\(--motion-fast\)/)
  assert.doesNotMatch(clearButtonBlock, /background:\s*var\(--surface-control\)|transition:\s*all\b/)

  for (const [block, name] of [[capsuleButtonHoverBlock, 'capsule hover'], [clearButtonHoverBlock, 'clear hover'], [applyButtonHoverBlock, 'apply hover']]) {
    assert.match(block, backgroundIncludes('material-glass-control-hover'), `${name} should use shared hover material`)
    assert.match(block, /border-color:\s*var\(--glass-control-border-hover\)/, `${name} should use shared hover border`)
    assert.match(block, /box-shadow:\s*var\(--glass-control-shadow-hover\)/, `${name} should use shared hover shadow`)
  }

  assert.match(capsuleButtonHoverBlock, /transform:\s*translateY\(-1px\)\s*scale\(1\.02\)/)
  assert.match(clearButtonHoverBlock, /transform:\s*translateY\(-1px\)/)
  assert.match(applyButtonHoverBlock, /transform:\s*translateY\(-1px\)/)
  assert.match(capsuleButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.96\)/)
  assert.match(clearButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
  assert.match(applyButtonActiveBlock, /transform:\s*translateY\(0\)\s*scale\(0\.99\)/)
})

test('search loading spinner uses theme glass colors instead of white accent paint', () => {
  const spinnerBlock = sourceBlock('.spinner')

  assert.match(spinnerBlock, /border:\s*2px solid var\(--glass-control-border\)/)
  assert.match(spinnerBlock, /border-top-color:\s*var\(--text-primary\)/)
  assert.doesNotMatch(spinnerBlock, /rgba\(255,\s*255,\s*255|rgba\(255,255,255|#fff|#ffffff|var\(--text-on-accent\)/i)
})

test('search command and result controls use layered liquid glass backgrounds', () => {
  const layeredControl = /background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control\)/
  const layeredControlHover = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-control-hover\)/
  const layeredActive = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--glass-active-material\)/
  const layeredSheet = /background:\s*var\(--surface-specular-edge-strong\),\s*var\(--surface-noise\),\s*var\(--material-glass-sheet\)/

  assert.match(sourceBlock('.command-capsule'), layeredSheet)
  assert.match(sourceBlock('.command-capsule.focused'), layeredActive)
  assert.match(sourceBlock('.capsule-search-btn'), layeredActive)
  assert.match(sourceBlock('.capsule-search-btn:hover'), layeredControlHover)
  assert.match(sourceBlock('.sort-pill'), layeredControl)
  assert.match(sourceBlock('.sort-pill:hover'), layeredControlHover)
  assert.match(sourceBlock('.sort-pill.active'), layeredActive)
  assert.match(sourceBlock('.filter-item'), layeredControl)
  assert.match(sourceBlock('.filter-item:hover'), layeredControlHover)
  assert.match(sourceBlock('.filter-item.toggle.active'), layeredActive)
  assert.match(sourceBlock('.applied-chip'), layeredControl)
  assert.match(sourceBlock('.applied-chip:hover'), layeredControlHover)
  assert.match(sourceBlock('.advanced-panel'), layeredSheet)
  assert.match(sourceBlock('.panel-input'), layeredControl)
  assert.match(sourceBlock('.panel-input:focus'), layeredActive)
  assert.match(sourceBlock('.variant-expand-btn'), layeredControl)
  assert.match(sourceBlock('.variant-expand-btn:hover'), layeredControlHover)
  assert.match(sourceBlock('.variant-inline-item'), layeredControl)
  assert.match(sourceBlock('.variant-inline-item:hover'), layeredControlHover)
  assert.match(sourceBlock('.page-btn'), layeredControl)
  assert.match(sourceBlock('.page-btn:hover:not(:disabled)'), layeredControlHover)
  assert.match(sourceBlock('.jump-input'), layeredControl)
  assert.match(sourceBlock('.jump-input:focus'), layeredControlHover)
  assert.match(sourceBlock('.jump-btn'), layeredControl)
  assert.match(sourceBlock('.jump-btn:hover'), layeredControlHover)
})
