import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import packageJson from '../../package.json' with { type: 'json' }
import { THEMES, THEME_KEYS, applyTheme, resolveThemeKey, toggleTheme, isDarkTheme } from '../assets/themes.js'

const subscription = [
  readFileSync(new URL('./Subscription.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/subscription/subscription.css', import.meta.url), 'utf8'),
].join('\n')
const normalize = [
  readFileSync(new URL('./Normalize.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/normalize/normalize.css', import.meta.url), 'utf8'),
].join('\n')
const inventory = [
  readFileSync(new URL('./Inventory.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/inventory/inventory.css', import.meta.url), 'utf8'),
].join('\n')
const inventoryActor = readFileSync(new URL('./InventoryActor.vue', import.meta.url), 'utf8')
const libraryOrganizeVue = readFileSync(new URL('./LibraryOrganize.vue', import.meta.url), 'utf8')
const libraryOrganize = [
  libraryOrganizeVue,
  readFileSync(new URL('../features/library/libraryOrganize.css', import.meta.url), 'utf8'),
].join('\n')
const homeVue = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')
const downloadCandidatePanel = readFileSync(new URL('../features/candidates/DownloadCandidatePanel.vue', import.meta.url), 'utf8')
const home = [
  homeVue,
  downloadCandidatePanel,
  readFileSync(new URL('../features/home/CandidateOverview.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/home/DownloadStatsBar.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/home/TaskList.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/home/home.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/candidates/downloadCandidatePanel.css', import.meta.url), 'utf8'),
].join('\n')
const operations = [
  readFileSync(new URL('./Operations.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/SchedulerCard.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/DataQualityCard.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/CandidateAutoCard.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/SnapshotCard.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/MappingCard.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/operations/operations.css', import.meta.url), 'utf8'),
].join('\n')
const favorites = [
  readFileSync(new URL('./Favorites.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/favorites/favorites.css', import.meta.url), 'utf8'),
].join('\n')
const entities = [
  readFileSync(new URL('./Entities.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/entities/entities.css', import.meta.url), 'utf8'),
].join('\n')
const actor = [
  readFileSync(new URL('./Actor.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/actor/actor.css', import.meta.url), 'utf8'),
].join('\n')
const configVue = readFileSync(new URL('./Config.vue', import.meta.url), 'utf8')
const advancedSettingsPanel = readFileSync(new URL('../features/config/AdvancedSettingsPanel.vue', import.meta.url), 'utf8')
const configOptions = readFileSync(new URL('../features/config/configOptions.js', import.meta.url), 'utf8')
const configStyles = [
  readFileSync(new URL('../features/config/config.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/configAppearance.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/advancedSettingsPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/config/advancedSettingsPanelResponsive.css', import.meta.url), 'utf8'),
].join('\n')
const config = [configVue, advancedSettingsPanel, configOptions, configStyles].join('\n')
const configDefaults = readFileSync(new URL('../features/config/configDefaults.js', import.meta.url), 'utf8')
const genres = readFileSync(new URL('./Genres.vue', import.meta.url), 'utf8')
const search = [
  readFileSync(new URL('./Search.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/search/search.css', import.meta.url), 'utf8'),
].join('\n')
const discoveryDetail = readFileSync(new URL('./DiscoveryDetail.vue', import.meta.url), 'utf8')
const supplement = [
  readFileSync(new URL('./SupplementManagement.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/JobsTab.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/MoviesTab.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/SourcesHealthTab.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/RepairLaneTab.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/supplement/useSupplementApi.js', import.meta.url), 'utf8'),
].join('\n')
const supplementActorPicker = readFileSync(new URL('../features/supplement/ActorPickerView.vue', import.meta.url), 'utf8')
const supplementSourceHealth = readFileSync(new URL('../features/supplement/SourceHealthPanel.vue', import.meta.url), 'utf8')
const supplementMoviesPanel = readFileSync(new URL('../features/supplement/SupplementMoviesPanel.vue', import.meta.url), 'utf8')
const supplementDiagnosticsDialog = readFileSync(new URL('../features/supplement/SupplementSourceDiagnosticsDialog.vue', import.meta.url), 'utf8')
const candidateRunPanel = readFileSync(new URL('../features/candidates/CandidateRunPanel.vue', import.meta.url), 'utf8')
const configFeatureSource = [config, configDefaults].join('\n')
const supplementFeatureSource = [
  supplement,
  supplementActorPicker,
  supplementSourceHealth,
  supplementMoviesPanel,
  supplementDiagnosticsDialog,
].join('\n')
const logs = readFileSync(new URL('./Logs.vue', import.meta.url), 'utf8')
const library = readFileSync(new URL('./Library.vue', import.meta.url), 'utf8')
const duplicates = readFileSync(new URL('./Duplicates.vue', import.meta.url), 'utf8')
const glassSelect = readFileSync(new URL('../components/GlassSelect.vue', import.meta.url), 'utf8')
const videoModal = [
  readFileSync(new URL('../components/VideoModal.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/videoModal/videoModal.css', import.meta.url), 'utf8'),
].join('\n')
const actorPortraitCard = readFileSync(new URL('../components/ActorPortraitCard.vue', import.meta.url), 'utf8')
const mainCss = readFileSync(new URL('../assets/main.css', import.meta.url), 'utf8')

function layeredBackground(token) {
  return new RegExp(`background:\\s*var\\(--surface-specular-edge(?:-strong)?\\),\\s*var\\(--surface-noise\\),\\s*var\\(--${token}\\)`)
}
const searchPreferences = readFileSync(new URL('../utils/searchPreferences.js', import.meta.url), 'utf8')
const displayLangSource = readFileSync(new URL('../utils/displayLang.js', import.meta.url), 'utf8')
const translationProviders = readFileSync(new URL('../utils/translationProviders.js', import.meta.url), 'utf8')
const magnetParse = readFileSync(new URL('./MagnetParse.vue', import.meta.url), 'utf8')
const apiSource = readFileSync(new URL('../api/index.js', import.meta.url), 'utf8')
const app = readFileSync(new URL('../App.vue', import.meta.url), 'utf8')
const appNavigation = readFileSync(new URL('../appNavigation.js', import.meta.url), 'utf8')
const appChrome = [app, appNavigation].join('\n')
const viteConfig = readFileSync(new URL('../../vite.config.js', import.meta.url), 'utf8')
const router = readFileSync(new URL('../router/index.js', import.meta.url), 'utf8')
const translationJobs = [
  readFileSync(new URL('./TranslationJobs.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/TranslationSourcesPanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/TranslationReviewPanel.vue', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationJobs.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationPanelControls.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationSourcesPanel.css', import.meta.url), 'utf8'),
  readFileSync(new URL('../features/translations/translationReviewPanel.css', import.meta.url), 'utf8'),
].join('\n')
const dockerCompose = readFileSync(new URL('../../../docker-compose.yml', import.meta.url), 'utf8')
const dockerBuildWorkflow = readFileSync(new URL('../../../.github/workflows/docker-build.yml', import.meta.url), 'utf8')
const dockerSmokeWorkflow = readFileSync(new URL('../../../.github/workflows/docker-smoke.yml', import.meta.url), 'utf8')
const backupRestoreDoc = readFileSync(new URL('../../../docs/backup-restore.md', import.meta.url), 'utf8')
const dockerfile = readFileSync(new URL('../../../Dockerfile', import.meta.url), 'utf8')
const gitignore = readFileSync(new URL('../../../.gitignore', import.meta.url), 'utf8')

function loadConfigOptions() {
  const match = configVue.match(/<script>([\s\S]*?)<\/script>/)
  assert.ok(match, 'Config.vue should have an options script block')
  const script = match[1]
    .replace(/^import\s+.*$/gm, '')
    .replace('export default', 'return')
  return new Function(
    'api',
    'requestConfirm',
    'displayLang',
    'defineAsyncComponent',
    'DEFAULT_SEARCH_PREFERENCES',
    'loadSearchPreferences',
    'saveSearchPreferences',
    'AppleErrorState',
    'AppleSkeleton',
    'GlassSelect',
    'AdvancedSettingsPanel',
    'DEFAULT_BUBBLE_CFG',
    'DEFAULT_CONFIG',
    `${script}`
  )({}, async () => {}, { value: 'ja' }, () => ({}), {}, () => {}, () => {}, {}, {}, {}, {}, {}, {})
}

test('sidebar displays the package version without a hardcoded release string', () => {
  assert.match(app, /v\{\{ appVersion \}\}/)
  assert.match(app, /const appVersion = import\.meta\.env\.VITE_APP_VERSION \|\| 'dev'/)
  assert.doesNotMatch(app, /v1\.2\.0-beta\.\d+/)
  assert.match(viteConfig, /package\.json/)
  assert.match(viteConfig, /VITE_APP_VERSION/)
  assert.match(viteConfig, /process\.env\.VITE_APP_VERSION \|\| packageJson\.version/)
  assert.doesNotMatch(viteConfig, /1\.2\.0-beta\.\d+/)
  assert.match(packageJson.version, /^\d+\.\d+\.\d+-beta\.\d+$/)
})

test('docker deployment defaults to stable images and CI injects automatic versions', () => {
  assert.match(dockerCompose, /ghcr\.io\/kongmei-ovo\/javhub:stable/)
  assert.match(dockerCompose, /ghcr\.io\/kongmei-ovo\/javinfoapi:stable/)
  assert.doesNotMatch(dockerCompose, /v1\.2\.0-beta\.4/)
  assert.match(dockerCompose, /JAVINFO_API_URL:\s*\$\{JAVINFO_API_URL:-http:\/\/javinfoapi:18080\}/)
  assert.match(dockerCompose, /JAVHUB_CONFIG_PATH:\s*\/app\/config\.yaml/)
  assert.match(dockerBuildWorkflow, /RELEASE_VERSION: v1\.2\.0-beta\.\$\{\{ github\.run_number \}\}/)
  assert.match(dockerBuildWorkflow, /\$\{IMAGE_NAME\}:stable/)
  assert.match(dockerBuildWorkflow, /\$\{IMAGE_NAME\}:\$\{RELEASE_VERSION\}/)
  assert.match(dockerBuildWorkflow, /VITE_APP_VERSION: \$\{\{ env\.RELEASE_VERSION \}\}/)
  assert.match(dockerBuildWorkflow, /org\.opencontainers\.image\.version=\$\{\{ env\.RELEASE_VERSION \}\}/)
  assert.match(dockerBuildWorkflow, /runner: ubuntu-24\.04-arm/)
  assert.match(dockerBuildWorkflow, /platform: linux\/arm64/)
  assert.match(dockerBuildWorkflow, /docker buildx imagetools create/)
  assert.match(dockerfile, /ARG VITE_APP_VERSION=dev/)
  assert.match(dockerfile, /ENV VITE_APP_VERSION=\$\{VITE_APP_VERSION\}/)
})

test('settings page warns when Docker uses a localhost JavInfo URL', () => {
  assert.match(config, /dockerJavInfoApiUrl\(\)[\s\S]*return 'http:\/\/javinfoapi:18080'/)
  assert.match(config, /javinfoRuntimeWarning\(\)[\s\S]*localhost:18080[\s\S]*Docker/)
  assert.match(config, /applyDockerJavInfoUrl\(\)[\s\S]*this\.config\.javinfo\.api_url = this\.dockerJavInfoApiUrl/)
  assert.match(config, /v-if="javinfoRuntimeWarning"/)
  assert.match(config, /修正为 Docker 服务地址/)
})

test('settings page exposes bounded Torznab source configuration', () => {
  assert.match(configFeatureSource, /sources:\s*\{[\s\S]*torznab:\s*\{[\s\S]*enabled: false/)
  assert.match(config, /磁力索引源 \/ Torznab/)
  assert.match(config, /v-model="config\.sources\.torznab\.base_url"/)
  assert.match(config, /v-model="config\.sources\.torznab\.api_key"/)
  assert.match(config, /v-model\.number="config\.sources\.torznab\.limit"[\s\S]*max="100"/)
  assert.match(config, /v-model\.number="config\.sources\.torznab\.timeout"[\s\S]*max="60"/)
  assert.match(config, /mergeSourceConfig\(data\.sources \|\| \{\}\)/)
})

test('navigation and actor page use actor mapping language', () => {
  assert.match(app, /appVersion/)
  assert.match(app, /import\.meta\.env\.VITE_APP_VERSION/)
  assert.doesNotMatch(app, /v1\.2\.0-beta\.\d+/)
  assert.match(packageJson.version, /^\d+\.\d+\.\d+-beta\.\d+$/)
  assert.match(appChrome, /片库整理/)
  assert.match(libraryOrganize, /演员映射/)
  assert.doesNotMatch(app, /演员合并/)
  assert.match(normalize, /演员映射/)
  assert.match(normalize, /listUnmappedActors/)
  assert.match(normalize, /confirmActorMapping/)
  assert.match(normalize, /ignoreActorMapping/)
  assert.match(normalize, /getActorMappingSummary/)
  assert.match(normalize, /待映射审核/)
  assert.doesNotMatch(normalize, />建议候选</)
  assert.match(normalize, /JavInfo 库/)
  assert.match(normalize, /Emby 库/)
  assert.match(normalize, /candidate-compare/)
  assert.match(normalize, /searchActorMappingCandidates/)
  assert.match(normalize, /reviewActorMappingWithAi/)
  assert.match(normalize, /candidateAvatar/)
  assert.match(normalize, /智能判断/)
  assert.match(normalize, /待智能判断/)
  assert.match(normalize, /aiDecisionLabel/)
  assert.match(normalize, /reviewFilterOptions/)
  assert.match(normalize, /置信/)
  assert.match(normalize, /autoMatchActorMappings/)
  assert.match(normalize, /自动匹配预演/)
  assert.doesNotMatch(normalize, /limit:\s*100000/)
  assert.match(normalize, /import \{ requestConfirm \} from '\.\.\/utils\/confirmDialog'/)
  assert.match(normalize, /requestConfirm\(\{[\s\S]*title: '执行自动匹配\?'/)
  assert.match(normalize, /精确但歧义/)
  assert.match(normalize, /statuses = \['confirmed', 'ignored'\]/)
  assert.match(normalize, /actor\.candidates/)
  assert.match(normalize, /loadingMappings/)
})

test('favorites video cards display dvd numbers instead of internal ids', () => {
  assert.match(favorites, /v-bind="movieCardVariantProps\(item\.metadata \|\| \{\}\)"/)
  assert.match(favorites, /import \{ movieCardVariantProps, variantGroupKey, visibleVariantItems \} from '\.\.\/utils\/videoVariantPresentation\.js'/)
  assert.doesNotMatch(favorites, /movieDisplayCode/)
})

test('actor portrait cards unify favorites subscriptions and supplement actor picking', () => {
  assert.match(actorPortraitCard, /actor-portrait-card/)
  assert.match(favorites, /ActorPortraitCard/)
  assert.match(favorites, /subscriptionState/)
  assert.match(entities, /ActorPortraitCard/)
  assert.match(subscription, /ActorPortraitCard/)
  assert.match(supplementActorPicker, /ActorPortraitCard/)
  assert.match(favorites, /class="actor-favorites-grid"/)
  assert.match(entities, /:show-favorite="canFavoriteEntity"/)
  assert.match(entities, /label: '资料库演员'/)
  assert.match(entities, /label: 'Emby演员'/)
  assert.match(favorites, /otherEntityItems/)
  assert.match(favorites, /favoriteActorFromItem/)
  assert.doesNotMatch(favorites, /:show-favorite="true"/)
  assert.doesNotMatch(favorites, /:show-subscribe="actorCardCanSubscribe\(item\)"/)
  assert.doesNotMatch(favorites, /@subscribe="toggleActorSubscription\(item\)"/)
  assert.match(subscription, /density="standard"/)
  assert.match(supplementActorPicker, /density="compact"/)
  assert.match(supplementActorPicker, /action-label="选择"/)
})

test('supplement actor picker distinguishes empty recent jobs from load failures', () => {
  assert.match(supplement, /actorPickerError:\s*''/)
  assert.match(supplement, /actorPickerLoadFailed\(\)/)
  assert.match(supplementActorPicker, /actorEmptyState\(\)[\s\S]*title: '补全队列不可用'[\s\S]*title: '暂无可选演员'/)
  assert.match(supplementActorPicker, /:title="actorEmptyState\.title"/)
  assert.match(supplement, /:error="actorPickerLoadFailed\(\)"/)
  assert.doesNotMatch(supplement, /:error="actorPickerError"/)
})

test('library organize inventory actors reuse the shared portrait card', () => {
  assert.match(libraryOrganize, /import ActorPortraitCard from '\.\.\/components\/ActorPortraitCard\.vue'/)
  assert.match(libraryOrganize, /<ActorPortraitCard[\s\S]*v-for="actor in inventoryActors"/)
  assert.match(libraryOrganize, /:name="inventoryActorName\(actor\)"/)
  assert.match(libraryOrganize, /:avatar-url="inventoryActorAvatar\(actor\)"/)
  assert.match(libraryOrganize, /:meta="inventoryActorMeta\(actor\)"/)
  assert.match(libraryOrganize, /function inventoryActorMissingText\(actor\)/)
  assert.match(libraryOrganize, /missing < 0 \? '待对比'/)
  assert.match(libraryOrganize, /@open="goActorDetail\(actor\.actress_id\)"/)
  assert.doesNotMatch(libraryOrganize, /class="actor-tile"/)
})

test('favorites actor cards show subscription badges and route to the unified actor page', () => {
  assert.match(favorites, /subscriptionState\.refresh\(\)/)
  assert.match(favorites, /subscriptionState\.isSubscribed\(actorCardSubscriptionId\(item\)\)/)
  assert.match(favorites, /path: `\/actor\/\$\{encodeURIComponent\(name\)\}`/)
  assert.match(favorites, /query: id \? \{ name, actress_id: id \} : \{ name \}/)
  assert.doesNotMatch(favorites, /params: \{ type: 'actress'/)
})

test('actor detail owns actor favorite and subscribe actions', () => {
  assert.match(actor, /favoriteState/)
  assert.match(actor, /subscriptionState/)
  assert.match(actor, /toggleActorFavorite/)
  assert.match(actor, /toggleActorSubscription/)
  assert.match(actor, /isActorFavorited/)
  assert.match(actor, /isActorSubscribed/)
})

test('favorites page exposes edit mode for batch unfavorite', () => {
  const movieCardBlock = favorites.match(/<MovieCard[\s\S]*?\/>/)?.[0] || ''

  assert.match(favorites, /editMode/)
  assert.match(favorites, /selectedFavoriteKeys/)
  assert.match(favorites, /toggleEditMode/)
  assert.match(favorites, /toggleFavoriteSelection/)
  assert.match(favorites, /removeSelectedFavorites/)
  assert.match(favorites, /编辑/)
  assert.match(favorites, /取消收藏/)
  assert.doesNotMatch(movieCardBlock, /@click="handleFavoriteItemClick\(item\)"/)
  assert.match(favorites, /class="curate-header-main"[\s\S]*class="curate-toolbar"/)
  assert.match(favorites, /<div\s+v-for="item in actorFavoriteItems"[\s\S]*<ActorPortraitCard[\s\S]*<button[\s\S]*select-check/)
})

test('favorites page pages video details and loads full metadata only for non-video favorites', () => {
  assert.match(favorites, /FAVORITE_VIDEO_PAGE_SIZE/)
  assert.match(favorites, /api\.getFavoriteVideosPage/)
  assert.match(favorites, /loadMoreVideos/)
  assert.match(favorites, /loadNonVideoFavoriteMetadata/)
  assert.match(favorites, /favoriteState\.loadMetadataForTypes\(types\)/)
  assert.doesNotMatch(favorites, /favoriteState\.refresh\(\{ includeMetadata: true \}\)/)
})

test('favorites page avoids actor detail fanout on initial render', () => {
  assert.match(favorites, /actorSourceItems/)
  assert.match(favorites, /item\.metadata \|\| \{\}/)
  assert.doesNotMatch(favorites, /api\.getActress\(/)
  assert.doesNotMatch(favorites, /api\.searchActors\(/)
  assert.doesNotMatch(favorites, /enrichFavoriteActor/)
  assert.doesNotMatch(favorites, /watch\(\s*actorSourceItems/)
})

test('subscription management keeps shared subscription state in sync', () => {
  assert.match(subscription, /import subscriptionState from '..\/utils\/subscriptionState'/)
  assert.match(subscription, /await subscriptionState\.refresh\(\)/)
  assert.match(subscription, /api\.addSubscription[\s\S]*await syncSubscriptionState\(\)/)
  assert.match(subscription, /api\.deleteSubscription[\s\S]*await syncSubscriptionState\(\)/)
})

test('subscription routes missing movies into download candidates', () => {
  assert.match(subscription, /checkSubscription/)
  assert.match(subscription, /查看候选/)
  assert.match(subscription, /candidate_count/)
  assert.match(subscription, /待补磁力/)
  assert.match(subscription, /新增/)
  assert.match(subscription, /existing/)
  assert.match(subscription, /include_supplement: '1'/)
  assert.doesNotMatch(subscription, /api\.createDownload\(\{ code:/)
})

test('subscription page defers actor metadata loading until a subscription is opened', () => {
  const loadSubsBlock = subscription.match(/async function loadSubs\(\) \{[\s\S]*?\n\}/)?.[0] || ''
  const openSubSheetBlock = subscription.match(/async function openSubSheet\(sub\) \{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(loadSubsBlock, /api\.getSubscriptions\(\)/)
  assert.doesNotMatch(loadSubsBlock, /enrichActressMeta|api\.getActress/)
  assert.doesNotMatch(subscription, /Promise\.all\(ids\.map\(fetchOne\)\)/)

  assert.match(subscription, /async function loadSubscriptionActorMeta\(sub\)/)
  assert.match(subscription, /api\.getActress\(sub\.actress_id\)/)
  assert.match(openSubSheetBlock, /loadSubscriptionActorMeta\(sub\)/)
})

test('subscription page uses list-level candidate counts instead of loading full new movie payloads', () => {
  // Tolerate either a block-form computed(() => { ... }) or a single-expression
  // computed(() => subs.value.reduce(...)).
  assert.match(subscription, /const totalNewMovies = computed\([\s\S]{0,400}?subs\.value\.reduce/)
  assert.match(subscription, /sub\.candidate_count/)
  const loadSubsBlock = subscription.match(/async function loadSubs\(\)[\s\S]*?\n\}/)?.[0] || ''
  assert.doesNotMatch(loadSubsBlock, /loadNewMovieBadges|api\.getNewMovies/)
  assert.doesNotMatch(subscription, /api\.getNewMovies\(|function loadNewMovieBadges|newMovieMap/)
})

test('movie cards keep cover media free of quick actions', () => {
  assert.doesNotMatch(search, /@toggle-favorite="toggleFavorite\(item\)"/)
  assert.doesNotMatch(discoveryDetail, /@toggle-favorite="toggleVideoFavorite\(item\)"/)
  assert.doesNotMatch(favorites, /@toggle-favorite="toggleFavorite\('video', item\.entity_id\)"/)
  assert.doesNotMatch(subscription, /class="work-dl-btn"/)
  assert.doesNotMatch(subscription, /async function downloadMovie/)
})

test('movie detail entry points keep the user on the current page with the modal', () => {
  const movieEntrySources = [search, discoveryDetail, actor, favorites, subscription, inventoryActor]
  for (const source of movieEntrySources) {
    assert.match(source, /openVideoModal/)
    assert.doesNotMatch(source, /openVideoDetail/)
    assert.doesNotMatch(source, /name: 'VideoDetail'/)
  }
})

test('subscription page defaults to subscribed management and opens discovery from an action', () => {
  assert.doesNotMatch(subscription, /activeTab = ref\('discover'\)/)
  assert.doesNotMatch(subscription, /v-show="activeTab === 'discover'"/)
  assert.match(subscription, /添加演员/)
  assert.match(subscription, /discoverOpen/)
  assert.match(subscription, /api\.searchActors\(q\)/)
  assert.match(subscription, /getSubscriptions/)
  assert.match(subscription, /ActorPortraitCard/)
})

test('subscription discovery sheet keeps the management page legible behind it', () => {
  const sheetOverlayBlock = subscription.match(/\.sheet-overlay\s*\{[^}]*\}/)?.[0] || ''

  assert.match(sheetOverlayBlock, /backdrop-filter:\s*none/)
  assert.match(sheetOverlayBlock, /-webkit-backdrop-filter:\s*none/)
  assert.doesNotMatch(sheetOverlayBlock, /backdrop-filter:\s*blur/)
  assert.match(subscription, /class="[^"]*\bdiscover-overlay\b[^"]*"/)
  assert.match(subscription, /\.discover-overlay\s*\{[\s\S]*backdrop-filter: none/)
  assert.match(subscription, /\.discover-overlay\s*\{[\s\S]*-webkit-backdrop-filter: none/)
})

test('actor discovery surfaces route to the canonical actor page', () => {
  const goActressBlock = genres.match(/goActress\(actress\)\s*\{[\s\S]*?\n    \},\n    goSeries/)?.[0] || ''
  assert.match(goActressBlock, /path:\s*`\/actor\/\$\{encodeURIComponent\(name\)\}`/)
  assert.match(goActressBlock, /query\.actress_id = actress\.id/)
  assert.doesNotMatch(goActressBlock, /name:\s*'DiscoveryDetail'/)
  assert.doesNotMatch(goActressBlock, /type:\s*'actress'/)

  assert.match(discoveryDetail, /redirectActorRoute\(\)/)
  assert.match(discoveryDetail, /this\.type !== 'actress'/)
  assert.match(discoveryDetail, /path:\s*`\/actor\/\$\{encodeURIComponent\(name\)\}`/)
  assert.match(discoveryDetail, /query\.actress_id = Number\(this\.value\)/)
  assert.match(discoveryDetail, /category_id/)
  assert.match(discoveryDetail, /maker_id/)
  assert.match(discoveryDetail, /series_id/)
  assert.match(discoveryDetail, /label_id/)

  const viewAllVideosBlock = subscription.match(/function viewAllVideos\(\)\s*\{[\s\S]*?\n\}/)?.[0] || ''
  assert.match(viewAllVideosBlock, /const actressId = sheetActor\.value\.actress_id \|\| sheetActor\.value\.id/)
  assert.match(viewAllVideosBlock, /closeSheet\(\)/)
  assert.match(viewAllVideosBlock, /path:\s*`\/actor\/\$\{encodeURIComponent\(name\)\}`/)
  assert.match(viewAllVideosBlock, /query\.actress_id = actressId/)
})

test('inventory page shows mapping coverage and candidate handoff', () => {
  assert.match(inventory, /映射覆盖率/)
  assert.match(inventory, /处理未映射演员/)
  assert.match(inventory, /映射建议/)
  assert.match(inventory, /source: 'inventory'/)
  assert.match(inventory, /getActorMappingSummary/)
  assert.match(inventory, /job\.result\.unmapped/)
  assert.match(inventory, /候选/)
  assert.match(inventoryActor, /转为候选/)
  assert.match(inventoryActor, /createDownloadCandidate/)
  assert.match(inventoryActor, /查看库存下载候选/)
  assert.match(inventoryActor, /已映射到 JavInfo/)
  assert.match(inventoryActor, /未映射到 JavInfo/)
})

test('library organizer unifies inventory check duplicates and actor mapping', () => {
  assert.match(libraryOrganize, /片库整理/)
  assert.match(libraryOrganize, /const activeTab = ref\('queue'\)/)
  assert.match(libraryOrganize, /activeTab === 'inventory'/)
  assert.match(libraryOrganize, /activeTab === 'check'/)
  assert.match(libraryOrganize, /activeTab === 'mapping'/)
  assert.match(libraryOrganize, /activeTab === 'duplicates'/)
  assert.match(libraryOrganize, /source:\s*'inventory'/)
  assert.match(libraryOrganize, /listDownloadCandidates/)
  assert.match(libraryOrganize, /getDuplicates/)
  assert.match(libraryOrganize, /checkLibrary/)
  assert.match(libraryOrganize, /listUnmappedActors/)
  assert.match(libraryOrganize, /triggerInventoryJob/)
  assert.match(libraryOrganize, /getLibraryOrganizeOverview/)
  assert.match(libraryOrganize, /goActorDetail/)
  assert.match(libraryOrganize, /actor_id/)
  assert.doesNotMatch(libraryOrganize, /limit:\s*100000/)
})

test('downloads page summary uses the lightweight candidate summary endpoint', () => {
  const summaryBlock = home.match(/async loadCandidateSummary\(\) \{[\s\S]*?\n    \},/)?.[0] || ''
  const listBlock = home.match(/async loadCandidates\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

  assert.match(summaryBlock, /api\.getDownloadCandidateSummary\(\{ status: 'candidate', include_sources: true \}\)/)
  assert.match(summaryBlock, /this\.candidateStats = resp\.data \|\| this\.candidateStats/)
  assert.doesNotMatch(summaryBlock, /api\.listDownloadCandidates/)
  assert.doesNotMatch(listBlock, /resp\.data\.stats/)
  assert.match(listBlock, /params\.include_stats = false/)
})

test('inventory page summary uses lightweight candidate counts instead of candidate rows', () => {
  const summaryBlock = inventory.match(/const fetchMappingSummary = async \(\) => \{[\s\S]*?\n\}/)?.[0] || ''

  assert.match(summaryBlock, /api\.getDownloadCandidateSummary\(\{ status: 'candidate', source: 'inventory' \}\)/)
  assert.doesNotMatch(summaryBlock, /api\.listDownloadCandidates/)
})

test('duplicates page renders duplicate groups from Emby snapshots', () => {
  assert.match(duplicates, /duplicateItems\(item\)/)
  assert.match(duplicates, /v-for="duplicate in duplicateItems\(item\)"/)
  assert.match(duplicates, /deleteItem\(duplicate\)/)
  assert.match(duplicates, /ignoreItem\(duplicate\)/)
  assert.match(duplicates, /duplicate_count/)
})

test('default theme controls avoid white-on-white primary buttons', () => {
  assert.doesNotMatch(inventory, /\.btn-primary\s*\{[^}]*color:\s*#fff/s)
  assert.doesNotMatch(normalize, /\.btn-primary\s*\{[^}]*color:\s*#fff/s)
  assert.doesNotMatch(search, /\.btn-primary\s*\{/)
  assert.match(inventory, /class="btn btn-primary"/)
  assert.match(normalize, /class="btn btn-primary"/)
  assert.match(inventory, /var\(--badge-warning-bg\)/)
  assert.match(inventory, /var\(--badge-success-bg\)/)
})

test('mobile navigation and settings tabs stay compact', () => {
  const bottomNavStart = appNavigation.indexOf('export const bottomNavItems')
  const bottomNavEnd = appNavigation.indexOf(']', bottomNavStart)
  const bottomNavBlock = appNavigation.slice(bottomNavStart, bottomNavEnd)
  assert.equal((bottomNavBlock.match(/\{ path:/g) || []).length, 4)
  assert.doesNotMatch(bottomNavBlock, /label: '订阅'/)
  assert.doesNotMatch(bottomNavBlock, /label: '库存'/)
  assert.match(appNavigation, /export const mobileMoreItems/)
  assert.match(appNavigation, /label: '磁链解析'/)
  assert.match(appNavigation, /label: '实体目录'/)
  assert.match(appNavigation, /label: '补全管理'/)
  assert.match(appNavigation, /label: '片库整理'/)
  assert.doesNotMatch(appNavigation, /label: '库检测'/)
  assert.doesNotMatch(appNavigation, /label: '去重管理'/)
  assert.match(appNavigation, /label: '运行日志'/)
  assert.match(app, /bottom-nav-more/)
  assert.match(config, /scroll-snap-type: x proximity/)
  assert.match(config, /settings-footer[\s\S]*left: var\(--sidebar-width\)/)
  assert.match(config, /footer-content \.btn[\s\S]*width: 100%/)
})

test('primary pages use unified breathing rails', () => {
  assert.match(mainCss, /--page-gutter:\s*clamp\(18px, 2\.4vw, 36px\)/)
  assert.match(mainCss, /--page-max-standard:\s*1180px/)
  assert.match(mainCss, /--page-max-workspace:\s*1360px/)
  assert.match(mainCss, /--page-max-gallery:\s*1600px/)
  assert.match(mainCss, /\.page-shell\s*\{[\s\S]*width: min\(var\(--page-max\), calc\(100% - var\(--page-gutter\) - var\(--page-gutter\)\)\)/)
  assert.match(mainCss, /\.page-rail\s*\{[\s\S]*width: min\(var\(--page-max\), calc\(100% - var\(--page-gutter\) - var\(--page-gutter\)\)\)/)

  const mainContentBlock = app.match(/\.main-content\s*\{[^}]*\}/)?.[0] || ''
  assert.doesNotMatch(mainContentBlock, /(?:^|[;\s])padding(?:-inline|-block)?\s*:/)
  assert.match(app, /--mobile-bottom-nav-reserve:\s*calc\(var\(--mobile-bottom-nav-height\) \+ var\(--mobile-bottom-nav-offset\) \+ 12px\)/)
  assert.match(app, /@media \(max-width: 768px\)\s*\{[\s\S]*\.main-content\s*\{[\s\S]*padding-bottom:\s*var\(--mobile-bottom-nav-reserve\)/)

  for (const [name, source] of Object.entries({
    home,
    operations,
    inventory,
    normalize,
    supplement,
    translationJobs,
    inventoryActor,
    entities,
  })) {
    assert.match(source, /page-shell page-shell--workspace/, `${name} should use the workspace page shell`)
  }

  for (const [name, source] of Object.entries({
    config,
    magnetParse,
    logs,
    library,
    duplicates,
    subscription,
  })) {
    assert.match(source, /page-shell page-shell--standard/, `${name} should use the standard page shell`)
  }

  assert.match(favorites, /page-shell page-shell--gallery/)
  assert.match(search, /class="search-page page-bleed"/)
  assert.match(search, /page-rail page-rail--gallery/)
  assert.match(genres, /class="genres-page page-bleed"/)
  assert.match(genres, /page-rail page-rail--standard/)
  assert.match(discoveryDetail, /class="genre-detail-page page-bleed"/)
  assert.match(discoveryDetail, /page-rail page-rail--gallery/)
  assert.match(actor, /class="actor-page page-bleed"/)
  assert.match(actor, /page-rail page-rail--gallery/)

  for (const [name, source] of Object.entries({
    home,
    operations,
    inventory,
    normalize,
    supplement,
    translationJobs,
    config,
    magnetParse,
    logs,
    duplicates,
  })) {
    const topWrapper = source.match(/\.(home|operations-page|inventory-page|mapping-page|supplement-page|translation-page|settings|parse-page|logs|duplicates-page)\s*\{[^}]*\}/)?.[0] || ''
    assert.doesNotMatch(topWrapper, /max-width|margin:\s*0 auto|padding:\s*(?:\d|0)/, `${name} should not own page-level rail spacing`)
  }
})

test('mobile video surfaces share compact gallery density', () => {
  assert.match(mainCss, /--video-grid-min-mobile:\s*clamp\(126px, 42vw, 168px\)/)
  assert.match(mainCss, /--video-grid-gap-mobile:\s*clamp\(9px, 2\.8vw, 13px\)/)
  assert.match(mainCss, /--video-card-radius-mobile:\s*18px/)
  assert.match(mainCss, /--video-card-body-padding-mobile:\s*9px 10px 11px/)
  assert.match(mainCss, /--compact-toolbar-height:\s*44px/)

  const appleVideoCard = readFileSync(new URL('../components/AppleVideoCard.vue', import.meta.url), 'utf8')
  assert.match(appleVideoCard, /container-type:\s*inline-size/)
  assert.match(appleVideoCard, /@container\s*\(max-width:\s*180px\)/)
  assert.match(appleVideoCard, /padding:\s*var\(--video-card-body-padding-mobile\)/)

  assert.match(search, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(discoveryDetail, /\.results-grid,\s*\.skeleton-grid[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(discoveryDetail, /\.results-grid,\s*\.skeleton-grid[\s\S]*padding-inline:\s*0/)
  assert.match(actor, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(favorites, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(subscription, /--video-grid-min-mobile:\s*clamp\(104px, 31vw, 148px\)/)
  assert.match(subscription, /grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
  assert.match(inventoryActor, /\.videos-grid\s*\{[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(var\(--video-grid-min-mobile\),\s*1fr\)\)/)
})

test('video modal and recommendation page use mobile-specific proportions', () => {
  assert.match(videoModal, /@media\s*\(max-width:\s*768px\)[\s\S]*\.modal-overlay\s*\{[\s\S]*padding:\s*0/)
  assert.match(videoModal, /\.modal-container\s*\{[\s\S]*width:\s*100vw[\s\S]*height:\s*calc\(100dvh - 24px - env\(safe-area-inset-bottom, 0px\)\)/)
  assert.match(videoModal, /\.modal-content\s*\{[\s\S]*padding:\s*18px max\(14px, env\(safe-area-inset-right, 0px\)\) 28px max\(14px, env\(safe-area-inset-left, 0px\)\)[\s\S]*gap:\s*20px/)
  assert.match(videoModal, /\.modal-code-block\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/)
  assert.match(videoModal, /\.modal-actions\s*\{[\s\S]*display:\s*grid[\s\S]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/)
  assert.match(videoModal, /\.modal-meta\s*\{[\s\S]*grid-template-columns:\s*1fr/)
  assert.match(videoModal, /\.modal-meta::before\s*\{[\s\S]*display:\s*none/)
  assert.match(videoModal, /overflow-wrap:\s*anywhere/)

  assert.match(genres, /mobileDisplayedTags\(\)/)
  assert.match(genres, /isMobileViewport/)
  assert.match(genres, /fontSize:\s*`clamp\(/)
  assert.match(genres, /gridTemplateColumns:[\s\S]*`repeat\(auto-fit, minmax\(clamp\(/)
})

test('external data failures render page-level retry states', () => {
  assert.match(genres, /AppleErrorState/)
  assert.match(genres, /categoryError/)
  assert.match(genres, /reloadGenreData/)
  assert.match(search, /import AppleErrorState from '\.\.\/components\/AppleErrorState\.vue'/)
  assert.match(search, /components:\s*\{[^}]*AppleErrorState/)
  assert.match(search, /searchError/)
  assert.match(search, /formatApiError/)
  assert.match(apiSource, /silentError: true/)
  assert.match(appNavigation, /label: '配置中心'/)
})

test('inline style cleanup keeps only dynamic previews in settings and genres', () => {
  assert.doesNotMatch(magnetParse, /(^|[\s<])style="/)
  assert.doesNotMatch(home, /(^|[\s<])style="/)
  assert.doesNotMatch(config, /(^|[\s<])style="/)
  assert.match(config, /preview-bubble[\s\S]*:style="previewBubbleStyle\(index\)"/)
  assert.doesNotMatch(config, /legendary-dot|rarity-color-input|rarity-thresholds/)
  assert.match(genres, /:style="cloudStyle"/)
  assert.match(genres, /:style="bubbleStyle\(tag, index\)"/)
})

test('appearance controls keep compact state without discovery material parsing', () => {
  assert.match(config, /class="segmented-mini"[\s\S]*:aria-pressed="config\.javinfo\.page_size === size"/)
  assert.doesNotMatch(config, /class="theme-option"/)
  assert.doesNotMatch(config, /<span class="setting-title">全局主题<\/span>/)
  assert.doesNotMatch(config, /class="preference-section apple-surface"/)
  assert.match(config, /\.preference-stack\s*\{[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-subtle\)/)
  assert.match(config, /\.preference-stack\s*\{[\s\S]*border: 1px solid var\(--glass-control-border\)/)
  assert.doesNotMatch(config, /\.preference-stack\s*\{[\s\S]*background: var\(--bg-secondary\)/)
  assert.doesNotMatch(config, /\.preference-stack\s*\{[\s\S]*border: 1px solid var\(--border-light\)/)
  assert.doesNotMatch(configDefaults, /parseGradientList|customGradients|colorMode|rarityThresholds|rarityColors/)
  assert.doesNotMatch(config, /parseGradientList|customGradients|自定义材质|灵动金传说|按稀有度分层/)
})

test('theme presets are reduced to Apple light and dark glass modes', () => {
  assert.deepEqual(THEME_KEYS, ['apple-light', 'apple-dark'])

  const baselineTokens = Object.keys(THEMES['apple-light'].vars).sort()
  for (const [key, theme] of Object.entries(THEMES)) {
    assert.deepEqual(Object.keys(theme.vars).sort(), baselineTokens, `${key} token coverage should match apple-light`)
    assert.match(theme.vars['--font-body'], /SF Pro Text/)
    assert.match(theme.vars['--font-body'], /-apple-system/)
    assert.ok(theme.vars['--surface-nav'], `${key} should define semantic navigation material`)
    assert.ok(theme.vars['--glass-control-bg'], `${key} should define default glass controls`)
    assert.ok(theme.vars['--glass-active-bg'], `${key} should define active glass controls`)
  }

  assert.equal(THEMES['apple-light'].vars['--bg-primary'], '#FBFBFD')
  assert.equal(THEMES['apple-dark'].vars['--bg-primary'], '#050506')
  assert.match(app, /theme-toggle/)
  assert.match(app, /toggleAppTheme/)
  assert.match(mainCss, /--glass-control-bg/)
  assert.match(mainCss, /--glass-active-bg/)
  assert.match(mainCss, /--glass-active-shadow/)
  assert.match(mainCss, /\.btn-ghost[\s\S]*border: 1px solid var\(--glass-control-border/)
  assert.match(app, /background: var\(--surface-nav\)/)
  assert.match(app, /\.theme-toggle[\s\S]*backdrop-filter: blur/)
  assert.match(mainCss, /\.el-input__wrapper, \.input\s*\{[\s\S]*?background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--surface-input\) !important/)
  assert.match(mainCss, /\.el-input__wrapper, \.input\s*\{[\s\S]*?border: 1px solid var\(--glass-control-border\) !important/)
  assert.doesNotMatch(mainCss, /\.el-input__wrapper, \.input\s*\{[\s\S]*?border: 1px solid transparent !important/)

  const genresTabBaseBlock = genres.match(/\.tab-btn\s*\{[^}]*\}/)?.[0] || ''
  assert.match(genresTabBaseBlock, layeredBackground('material-glass-subtle'))
  assert.match(genresTabBaseBlock, /border: 1px solid var\(--glass-control-border\)/)

  const genresTabBlock = genres.match(/\.tab-btn\.active\s*\{[^}]*\}/)?.[0] || ''
  assert.doesNotMatch(genresTabBlock, /inset 0 -2px/)
  assert.match(genresTabBlock, /var\(--glass-active-shadow\)/)

  const segmentedBaseBlock = config.match(/\.segmented-mini button\s*\{[^}]*\}/)?.[0] || ''
  assert.match(segmentedBaseBlock, layeredBackground('material-glass-subtle'))
  assert.match(segmentedBaseBlock, /border: 1px solid var\(--glass-control-border\)/)

  const segmentedActiveBlock = config.match(/\.segmented-mini button\.active\s*\{[^}]*\}/)?.[0] || ''
  assert.doesNotMatch(segmentedActiveBlock, /inset 0 -2px/)
  assert.match(segmentedActiveBlock, /var\(--glass-active-shadow\)/)

  const settingsTabBaseBlock = config.match(/\.tab-item\s*\{[^}]*\}/)?.[0] || ''
  assert.match(settingsTabBaseBlock, layeredBackground('material-glass-subtle'))
  assert.match(settingsTabBaseBlock, /border: 1px solid var\(--glass-control-border\)/)

  const settingsTabActiveBlock = config.match(/\.tab-item\.active\s*\{[^}]*\}/)?.[0] || ''
  assert.match(settingsTabActiveBlock, /var\(--glass-active-shadow\)/)
  assert.doesNotMatch(config, /\.tab-item\.active::after/)

  for (const removed of ['apple-espana', 'apple-pro-dark', 'midnight', 'studio-silver', 'oled', 'deep-space', 'graphite-gold']) {
    assert.equal(THEMES[removed], undefined)
  }
})

test('legacy saved theme values resolve to Apple light and dark modes', () => {
  for (const key of ['apple-espana', 'studio-silver']) {
    assert.equal(resolveThemeKey(key), 'apple-light')
  }
  for (const key of ['apple-pro-dark', 'midnight', 'oled', 'deep-space', 'graphite-gold', 'forest', 'tokyo', 'aurora', 'rose']) {
    assert.equal(resolveThemeKey(key), 'apple-dark')
  }
  assert.equal(resolveThemeKey('missing-theme'), 'apple-light')
  assert.equal(isDarkTheme('apple-dark'), true)
  assert.equal(isDarkTheme('apple-light'), false)

  const writes = []
  const originalDocument = globalThis.document
  const originalLocalStorage = globalThis.localStorage
  globalThis.document = {
    documentElement: {
      style: {
        setProperty: () => {},
      },
      dataset: {},
    },
  }
  globalThis.localStorage = {
    setItem: (key, value) => writes.push([key, value]),
  }

  try {
    assert.equal(applyTheme('tokyo'), 'apple-dark')
    assert.deepEqual(writes.at(-1), ['javhub_theme', 'apple-dark'])
    assert.equal(globalThis.document.documentElement.dataset.theme, 'dark')
    assert.equal(toggleTheme('apple-dark'), 'apple-light')
    assert.deepEqual(writes.at(-1), ['javhub_theme', 'apple-light'])
  } finally {
    if (originalDocument === undefined) {
      delete globalThis.document
    } else {
      globalThis.document = originalDocument
    }
    if (originalLocalStorage === undefined) {
      delete globalThis.localStorage
    } else {
      globalThis.localStorage = originalLocalStorage
    }
  }
})

test('magnet parser regex is stateless across multiple lines', () => {
  assert.match(magnetParse, /const magnetRE = .*\/i/)
  assert.doesNotMatch(magnetParse, /const magnetRE = .*\/g[i]?/)
  assert.match(magnetParse, /magnet:\\\?xt=urn:btih:\(\[A-Fa-f0-9\]\+\)/)
})

test('download page exposes candidate approval workflow', () => {
  assert.match(home, /下载候选/)
  assert.match(home, /待补磁力/)
  assert.match(home, /approveDownloadCandidate/)
  assert.match(home, /rejectDownloadCandidate/)
  assert.match(home, /updateDownloadCandidateMagnet/)
  assert.match(home, /bulkRejectDownloadCandidates/)
  assert.match(home, /批量恢复/)
  assert.match(home, /搜索番号、标题、演员/)
  assert.match(home, /syncCandidateRoute/)
  assert.match(home, /by_source/)
  assert.match(home, /全部来源/)
  assert.match(home, /candidateFilter\.source === 'supplement'/)
  assert.match(home, /candidateSourceLabel/)
  assert.match(home, /补全/)
  assert.match(home, /candidate-overview/)
  assert.match(home, /candidateFilterLedger/)
  assert.match(home, /candidate-filter-ledger/)
  assert.match(home, /v-for="filter in candidateFilterLedger"/)
  assert.match(home, /latest_event_action/)
  assert.match(home, /candidateEventActionLabel/)
  assert.match(home, /待确认候选/)
  assert.match(home, /订阅发现/)
  assert.match(home, /库存发现/)
  assert.match(home, /补全发现/)
  assert.match(home, /candidate_by_source/)
  assert.match(home, /readyCandidateCount/)
  assert.match(home, /openCandidatePreset/)
  assert.match(home, /candidatePage: Number\(this\.\$route\.query\.page \|\| 1\) \|\| 1/)
  assert.match(home, /candidateTotalPages: 1/)
  assert.match(home, /page: tab === 'candidates' \? \(Number\(query\.page \|\| 1\) \|\| 1\) : this\.candidatePage/)
  assert.match(home, /if \(filter\.page && Number\(filter\.page\) > 1\) query\.page = String\(Number\(filter\.page\)\)/)
  assert.match(home, /params\.page = this\.candidatePage/)
  assert.match(home, /params\.page_size = this\.candidatePageSize/)
  assert.match(home, /params\.latest_event_action = this\.candidateFilter\.latest_event_action/)
  assert.match(home, /this\.candidateTotalPages = Number\(resp\.data\.total_pages \|\| 1\) \|\| 1/)
  assert.match(home, /pushDownloadRoute\(this\.candidateRouteQuery\(\{ status, needs_magnet: null, page: 1 \}\)\)/)
  assert.match(home, /candidateFilter\.needs_magnet === true/)
  assert.match(home, /goCandidatePage\(page\)/)
  assert.match(home, /pushDownloadRoute\(this\.candidateRouteQuery\(\{ page: nextPage \}\)\)/)
  assert.match(home, /candidateTotalPages > 1/)
  assert.match(home, /goCandidateActor/)
  assert.match(home, /goCandidateSupplement/)
  assert.match(home, /最近动作/)
  assert.match(candidateRunPanel, /最近处理/)
  assert.match(home, /loadCandidateRuns/)
  assert.match(home, /applyCandidateRunFilters/)
  assert.match(home, /retryFailedCandidateRun/)
  assert.match(home, /retryDownloadCandidateRunFailed/)
  assert.match(home, /listDownloadCandidateRuns/)
  assert.match(candidateRunPanel, /失败队列/)
  assert.match(candidateRunPanel, /重试失败/)
  assert.match(home, /dry_run: true/)
  assert.match(home, /processPreviewMessage/)
  assert.match(home, /processPreviewDetails/)
  assert.match(home, /预演中/)
  assert.match(home, /error_msg/)
  assert.match(home, /已关联任务/)
  assert.match(home, /重试/)
})

test('entity catalog unifies entity directories behind a route and nav entry', () => {
  assert.match(router, /path: '\/entities'/)
  assert.match(router, /Entities/)
  assert.match(appNavigation, /path: '\/entities'/)
  assert.match(appNavigation, /label: '实体目录'/)
  assert.match(entities, /name: 'Entities'/)
  for (const label of ['资料库演员', 'Emby演员', '题材', '系列', '厂商', '厂牌', '导演', '作者']) {
    assert.match(entities, new RegExp(label))
  }
  for (const method of ['listActresses', 'listInventoryActors', 'listCategories', 'listSeries', 'listMakers', 'listLabels', 'listDirectors', 'listAuthors']) {
    assert.match(entities, new RegExp(`api\\.${method}`))
  }
  assert.match(entities, /searchKeyword/)
  assert.match(entities, /openEntity\(item\)/)
  assert.match(entities, /favoriteState\.toggle/)
  assert.match(discoveryDetail, /\['actor', 'director', 'author'\]\.includes\(this\.type\)/)
  assert.match(discoveryDetail, /params\.q = this\.displayNameValue \|\| v/)
})

test('operations overview exposes candidate automation controls', () => {
  assert.match(operations, /立即运行/)
  assert.match(operations, /runCandidateProcessingNow/)
  assert.match(operations, /candidateSchedule/)
  assert.match(operations, /scheduleStatusLabel/)
  assert.match(operations, /effective_enabled/)
  assert.match(operations, /disabled_reason/)
  assert.match(operations, /下一次/)
  assert.match(operations, /候选处理正在运行/)
  assert.match(operations, /采集后自动匹配/)
  assert.match(operations, /保守唯一/)
  assert.match(operations, /自动化工作台/)
  assert.match(operations, /工作台路径/)
  assert.match(operations, /goWorkbenchAction/)
  assert.match(operations, /refreshMissingCache/)
})

test('operations overview surfaces prioritized data quality issues', () => {
  assert.match(operations, /数据质量优先级/)
  assert.match(operations, /topDataQualityIssues/)
  assert.match(operations, /dataQualitySummary/)
  assert.match(operations, /openDataQualityIssue\(issue\)/)
  assert.match(operations, /overview\?\.data_quality/)
  assert.match(operations, /issue\.score/)
  assert.match(operations, /issue\?\.action\?\.route/)
  assert.match(operations, /quality:\s*'missing_cover'/)
  assert.match(operations, /issueRepairProgressLabel\(issue\)/)
  assert.match(operations, /repair_progress\?\.label/)
  assert.match(operations, /issueRepairActions\(issue\)/)
  assert.match(operations, /seen\.has\(key\)/)
  assert.match(operations, /seen\.add\(key\)/)
  assert.match(operations, /openDataQualityRepairAction\(action, \$event\)/)
  assert.match(operations, /issueRepairReasonLabel\(issue\)/)
  assert.match(operations, /repair_progress\?\.reason_label/)
  assert.match(operations, /openDataQualityRoute\(action\?\.route\)/)
  assert.match(operations, /issueRepairReasonActions\(issue\)/)
  assert.match(operations, /issueRepairEventLabel\(issue\)/)
  assert.match(operations, /issueRepairEventActions\(issue\)/)
  assert.match(operations, /issueRepairLocalLabel\(issue\)/)
  assert.match(operations, /issueRepairLocalSourceLabel\(issue\)/)
  assert.match(operations, /issueRepairLocalActions\(issue\)/)
  assert.match(operations, /openDataQualityRepairAction\(action, \$event\)/)
  assert.match(operations, /openDataQualityRoute\(action\?\.route\)/)
  assert.match(operations, /repair_progress\?\.event_label/)
  assert.match(operations, /repair_progress\?\.event_actions/)
  assert.match(operations, /repair_progress\?\.reason_actions/)
  assert.match(config, /navGroups[\s\S]*id:\s*'automation'/)
  assert.match(config, /routeGroupMap[\s\S]*const group = routeGroupMap\[tab\] \|\| tab/)
  assert.match(operations, /issueRepairProviderLabel\(issue\)/)
  assert.match(operations, /issueRepairProviderActions\(issue\)/)
  assert.match(operations, /openDataQualityRepairAction\(action, \$event\)/)
  assert.match(operations, /openDataQualityRoute\(action\?\.route\)/)
  assert.match(operations, /:key="action\.route \|\| action\.label"/)
  assert.match(operations, /repair_progress\?\.provider_label/)
  assert.match(operations, /repair_progress\?\.provider_actions/)
  assert.match(operations, /repair_progress\?\.local_label/)
  assert.match(operations, /repair_progress\?\.local_source_label/)
  assert.match(operations, /repair_progress\?\.local_actions/)
})

test('operations overview uses a restrained Apple operations layout', () => {
  assert.match(operations, /operations-hero/)
  assert.match(operations, /priority-board/)
  assert.match(operations, /operations-segments/)
  assert.match(operations, /activeSegment/)
  assert.match(operations, /segmentFromRoute\(\)/)
  assert.match(operations, /setActiveSegment\(segment\)/)
  assert.match(operations, /diagnostic-grid/)
  assert.match(operations, /hero-stat-grid/)
  assert.match(operations, /--operations-panel-gap:\s*clamp\(12px,\s*1\.4vw,\s*18px\)/)
  assert.match(operations, /\.workbench-panel[\s\S]*background:[\s\S]*var\(--material-glass-sheet\)/)
  assert.match(operations, /\.hero-stat-grid[\s\S]*grid-template-columns:\s*repeat\(auto-fit,\s*minmax\(108px,\s*1fr\)\)/)
  assert.doesNotMatch(operations, /status-cell\.urgent/)
  assert.doesNotMatch(operations, /title:\s*'活动中心'/)
})

test('operations overview splits daily work, system status, and diagnostics into internal views', () => {
  assert.match(operations, /operationsSegments/)
  assert.match(operations, /key:\s*'workbench'[\s\S]*label:\s*'处理'/)
  assert.match(operations, /key:\s*'system'[\s\S]*label:\s*'系统状态'/)
  assert.match(operations, /key:\s*'diagnostics'[\s\S]*label:\s*'诊断记录'/)
  assert.match(operations, /<section v-if="activeSegment === 'workbench'" class="operations-workbench priority-board"/)
  assert.match(operations, /<section v-else-if="activeSegment === 'system'" class="system-layout"/)
  assert.match(operations, /<section v-else-if="activeSegment === 'diagnostics'" class="diagnostic-grid"/)
  assert.match(operations, /query: \{ \.\.\.this\.\$route\.query, tab: segment \}/)
  assert.match(operations, /this\.activeSegment = this\.segmentFromRoute\(\)/)
})

test('operations overview surfaces initialization health and setup entry points', () => {
  assert.match(operations, /<section v-else-if="activeSegment === 'system'" class="system-layout"[\s\S]*<SchedulerCard/)
  assert.match(operations, /初始化与健康检查/)
  assert.match(operations, /api\.readiness\(\)/)
  assert.match(operations, /healthStatusLabel/)
  assert.match(operations, /health\.status/)
  assert.match(operations, /配置已加载/)
  assert.match(operations, /数据库/)
  assert.match(operations, /JavInfo/)
  assert.match(operations, /缓存/)
  assert.match(operations, /healthCacheSummary/)
  assert.match(operations, /healthJavInfoUrlSummary/)
  assert.match(operations, /downloaders/)
  assert.match(operations, /sources/)
  assert.match(operations, /healthSourceAttemptSummary/)
  assert.match(operations, /最近源检索/)
  assert.match(operations, /scheduler/)
  assert.match(operations, /goJavInfoImport/)
  assert.match(operations, /\$router\.push\('\/settings'\)/)
  assert.match(operations, /\$router\.push\('\/logs'\)/)
  assert.match(operations, /query: \{ tab: 'javinfo-import' \}/)
  assert.match(operations, /<section v-else-if="activeSegment === 'diagnostics'" class="diagnostic-grid"[\s\S]*<SnapshotCard/)
  assert.match(operations, /缓存诊断/)
  assert.match(operations, /响应命中率/)
  assert.match(operations, /热门响应命名空间/)
  assert.doesNotMatch(operations, /Cache Stats/)
  assert.doesNotMatch(operations, /Response hit rate/)
  assert.doesNotMatch(operations, /Top response namespaces/)
})

test('operations exposes cache cleanup UI backed by purge API', () => {
  assert.match(operations, /缓存清理/)
  assert.match(operations, /cachePurgeScopes/)
  assert.match(operations, /selectedCachePurgeScope/)
  assert.match(operations, /requestConfirm/)
  assert.match(operations, /api\.purgeCache\(this\.selectedCachePurgeScope\)/)
  assert.match(operations, /await this\.loadCacheStats\(\)/)
  assert.match(apiSource, /purgeCache\(scope = 'video'\)/)
})

test('run logs page exposes search pagination and level summary', () => {
  assert.match(appNavigation, /label: '运行日志'/)
  assert.match(logs, /运行日志/)
  assert.match(logs, /logSummary/)
  assert.match(logs, /可按等级和关键词筛选/)
  assert.match(logs, /aria-label="日志等级汇总"/)
  assert.match(logs, /searchText/)
  assert.match(logs, /api\.getLogs\(this\.limit, this\.filterLevel, \{ q: this\.searchText, offset:/)
  assert.match(logs, /hasMoreLogs/)
  assert.match(apiSource, /getLogs\(limit = 100, level = '', options = \{\}\)/)
})

test('favorites exposes collection management controls', () => {
  assert.match(favorites, /收藏集合/)
  assert.match(favorites, /loadCollections/)
  assert.match(favorites, /api\.getCollections/)
  assert.match(favorites, /api\.createCollection/)
  assert.match(favorites, /api\.updateCollection/)
  assert.match(favorites, /api\.deleteCollection/)
  assert.match(favorites, /collectionForm/)
  assert.match(favorites, /editingCollectionId/)
  assert.match(apiSource, /createCollection\(data\)/)
  assert.match(apiSource, /updateCollection\(collectionId, data\)/)
  assert.match(apiSource, /deleteCollection\(collectionId\)/)
})

test('docker smoke and backup restore docs cover deploy validation', () => {
  assert.match(dockerSmokeWorkflow, /Docker Smoke/)
  assert.match(dockerSmokeWorkflow, /docker compose config/)
  assert.match(dockerSmokeWorkflow, /\/health/)
  assert.match(dockerSmokeWorkflow, /\/health\/readiness/)
  assert.match(dockerSmokeWorkflow, /payload\.get\("status"\) == "ok"/)
  assert.match(dockerSmokeWorkflow, /\/api\/v1\/cache\/stats/)
  assert.match(dockerSmokeWorkflow, /docker compose down -v/)
  assert.match(backupRestoreDoc, /config\.yaml/)
  assert.match(backupRestoreDoc, /data\//)
  assert.match(backupRestoreDoc, /javhub-local\.tgz/)
  assert.match(backupRestoreDoc, /tar -xzf backups\/<stamp>\/javhub-local\.tgz/)
  assert.match(backupRestoreDoc, /pg_dump/)
  assert.match(backupRestoreDoc, /pg_restore/)
  assert.match(backupRestoreDoc, /\/health/)
  assert.match(backupRestoreDoc, /\/health\/readiness/)
  assert.match(backupRestoreDoc, /\/api\/v1\/cache\/stats/)
  assert.match(gitignore, /backups\//)
  assert.match(gitignore, /\*\.dump/)
  assert.match(gitignore, /redis-dump\.rdb/)
})

test('translation jobs has a standalone navigation page and settings no longer owns translation UI', () => {
  assert.match(appNavigation, /label: '翻译作业'/)
  assert.match(appNavigation, /path: '\/translations'/)
  assert.match(router, /path: '\/translations'/)
  assert.match(router, /TranslationJobs/)
  assert.doesNotMatch(config, /<h2>翻译映射<\/h2>/)
  assert.doesNotMatch(config, /<h2>翻译源<\/h2>/)
  assert.match(translationJobs, /name: 'TranslationJobs'/)
  assert.match(translationJobs, /class="segmented-control apple-surface"/)
  assert.doesNotMatch(translationJobs, /summary-strip/)
  assert.match(translationJobs, /标题覆盖/)
  assert.match(translationJobs, /元数据覆盖/)
  assert.match(translationJobs, /待处理工作台/)
  assert.match(translationJobs, /任务状态/)
  assert.match(translationJobs, /继续翻译/)
  assert.match(translationJobs, /job-control-card/)
  assert.match(translationJobs, /--donut-hole-bg/)
  assert.match(translationJobs, /--translation-donut-hole-bg/)
  assert.match(translationJobs, /:global\(:root\[data-theme='dark'\]\)/)
  assert.doesNotMatch(translationJobs, /\.coverage-donut div[\s\S]{0,220}background: var\(--surface-card\)/)
  assert.match(translationJobs, /@click="refreshOverview"/)
  assert.doesNotMatch(translationJobs, /@click="reloadAll"/)
  assert.doesNotMatch(translationJobs, /overviewRecentJobs/)
  assert.doesNotMatch(translationJobs, /overview-recent/)
  assert.doesNotMatch(translationJobs, /最近作业/)
  assert.doesNotMatch(translationJobs, /await Promise\.all\(\[this\.loadConfig\(\), this\.loadStats\(\), this\.loadJobs\(\)\]\)/)
  assert.match(translationJobs, /await Promise\.all\(\[this\.loadConfig\(\), this\.loadJobs\(\)\]\)/)
  assert.doesNotMatch(translationJobs, /async reloadAll\(\)[\s\S]{0,160}this\.loadStats\(\)/)
  assert.match(translationJobs, /async refreshOverview\(\)[\s\S]*await this\.loadStats\(\)/)
  assert.match(translationJobs, /statsLoading/)
  assert.match(translationJobs, /TRANSLATION_STATS_CACHE_KEY/)
  assert.match(translationJobs, /cachedTranslationStats/)
  assert.match(translationJobs, /loadCachedStats\(\)/)
  assert.match(translationJobs, /translationStatsStorage\(\)/)
  assert.match(translationJobs, /window\.localStorage/)
  assert.match(translationJobs, /storage\?\.setItem\(TRANSLATION_STATS_CACHE_KEY/)
  assert.match(translationJobs, /storage\?\.getItem\(TRANSLATION_STATS_CACHE_KEY\)/)
  for (const label of ['总览', '创建作业', '翻译源', '校对台', '映射导入', '历史记录']) {
    assert.match(translationJobs, new RegExp(`label: '${label}'`))
  }
  assert.match(translationJobs, /reviewType: 'actress'/)
  assert.match(translationJobs, /listTranslationItems/)
  assert.match(translationJobs, /updateTranslationItem/)
  assert.match(translationJobs, /retryTranslationItems/)
  assert.match(translationJobs, /manual_edited/)
  assert.match(translationJobs, /只看|审核工作台|重试当前筛选/)
  assert.match(translationJobs, /低成本批量源/)
  assert.match(translationJobs, /实时兜底/)
  assert.match(translationJobs, /公共智能翻译参数在设置页维护/)
  assert.match(translationJobs, /批量作业默认不使用智能兜底/)
  assert.match(translationJobs, /translationProviders\.js/)
  assert.match(translationProviders, /ai: \{ label: '智能兜底'/)
  assert.match(translationProviders, /providerOrderLabel/)
  assert.match(translationJobs, /batch_concurrency/)
  assert.match(translationJobs, /batch_size/)
  assert.match(translationJobs, /batch_char_limit/)
  assert.match(translationJobs, /source_page_size/)
  assert.match(translationJobs, /scan_pages_per_batch/)
  assert.match(translationJobs, /job_type/)
  assert.match(translationJobs, /jobForm\.mode/)
  assert.match(translationJobs, /补剩余/)
  assert.match(translationJobs, /全量重翻/)
  assert.doesNotMatch(translationJobs, /数量上限/)
  assert.doesNotMatch(translationJobs, /jobForm\.limit/)
  assert.match(translationJobs, /library_titles/)
  assert.match(translationJobs, /metadata_names/)
  for (const jobType of ['metadata_categories', 'metadata_series', 'metadata_makers', 'metadata_labels', 'metadata_actresses']) {
    assert.match(translationJobs, new RegExp(jobType))
  }
  for (const label of ['题材名称', '系列名称', '厂商名称', '厂牌名称', '演员名称', '全部元数据名称']) {
    assert.match(translationJobs, new RegExp(label))
  }
  assert.match(translationJobs, /progress_percent/)
  assert.match(translationJobs, /startTranslationJob/)
  const startJobBlock = translationJobs.slice(
    translationJobs.indexOf('async startJob()'),
    translationJobs.indexOf('async continueJobFromLatest()')
  )
  assert.match(startJobBlock, /const confirmed = await requestConfirm\(/)
  assert.match(startJobBlock, /title: this\.jobForm\.mode === 'refresh_all' \? '开始全量重翻' : '开始翻译作业'/)
  assert.match(startJobBlock, /if \(!confirmed\) return[\s\S]*this\.startingJob = true[\s\S]*api\.startTranslationJob/)
  assert.match(translationJobs, /listTranslationJobs/)
  assert.match(translationJobs, /getTranslationJob/)
  assert.match(translationJobs, /pauseTranslationJob/)
  assert.match(translationJobs, /paused/)
  assert.match(translationJobs, /selectedProvider/)
  assert.match(translationJobs, /providerOptions/)
  assert.match(translationJobs, /name="translation-provider"/)
  assert.match(translationProviders, /baidu: \{ label: '百度翻译'/)
  assert.match(translationJobs, /provider: this\.selectedProvider/)
  assert.doesNotMatch(translationJobs, /moveProvider/)
  assert.doesNotMatch(translationJobs, /上移/)
  assert.doesNotMatch(translationJobs, /下移/)
  assert.match(translationJobs, /setInterval\(\(\) => this\.refreshCurrentJob\(jobId\), 2000\)/)
  assert.match(translationJobs, /\['cache', 'mapping'\]/)
  assert.doesNotMatch(translationJobs, /openai_compatible[\s\S]{0,120}selectedProviderOrder/)
})

test('settings page blocks saving until remote config has loaded', () => {
  assert.match(config, /configLoading: true/)
  assert.match(config, /configLoaded: false/)
  assert.match(config, /configLoadError: ''/)
  assert.match(config, /configMeta:/)
  assert.match(config, /async loadConfig\(\)/)
  assert.match(config, /canSaveConfig\(\)/)
  assert.match(config, /configStatusDescription\(\)/)
  assert.match(config, /v-else-if="configLoadError"/)
  assert.match(config, /v-if="canSaveConfig" class="settings-footer"/)
  assert.match(config, /配置文件未挂载或不可读取/)
  assert.match(config, /保存已暂停以避免覆盖现有设置/)
  assert.match(config, /if \(!this\.canSaveConfig\)[\s\S]*已阻止保存/)
  assert.match(config, /:disabled="testingTelegram \|\| !canSaveConfig \|\| !config\.telegram\.bot_token"/)
  assert.match(config, /@retry="loadConfig"/)
  assert.match(configFeatureSource, /max_auto_downloads_per_run/)
  assert.match(configFeatureSource, /max_auto_downloads_per_24h/)
  assert.match(configFeatureSource, /actor_mapping/)
  assert.match(configFeatureSource, /auto_match_after_collect/)
  assert.match(configFeatureSource, /ai/)
  assert.match(advancedSettingsPanel, /<h2>公共智能模型<\/h2>/)
  assert.match(advancedSettingsPanel, /aiProviderOptions/)
  assert.match(advancedSettingsPanel, /config\.ai\.provider/)
  assert.match(configFeatureSource, /gemini/)
  assert.match(configFeatureSource, /ollama/)
  assert.match(advancedSettingsPanel, /currentAiConfig/)
  assert.match(advancedSettingsPanel, /获取模型列表/)
  assert.match(advancedSettingsPanel, /loadAiModels/)
  assert.match(advancedSettingsPanel, /测试模型调用/)
  assert.match(advancedSettingsPanel, /testAIModel/)
  assert.match(apiSource, /listAiModels/)
  assert.match(apiSource, /testAiModel/)
})

test('settings page keeps downloaders out and gives Telegram its own section', () => {
  assert.match(config, /activeGroup === 'telegram'/)
  assert.match(config, /label: 'Telegram 通知'/)
  assert.match(config, /<h2>Bot 连接<\/h2>/)
  assert.match(config, /<h2>通知事件<\/h2>/)
  assert.match(config, /const \{ downloaders, openlist, server, rate_limit, \.\.\.configPayload \} = this\.config/)
  assert.doesNotMatch(config, /OpenList \/ 115云盘/)
  assert.doesNotMatch(config, /管理下载源/)
  assert.doesNotMatch(config, /config\.openlist/)
  assert.doesNotMatch(config, /系统通知/)
})

test('settings page does not expose startup-only server controls', () => {
  assert.doesNotMatch(advancedSettingsPanel, /服务端设置/)
  assert.doesNotMatch(advancedSettingsPanel, /前端 Origin/)
  assert.doesNotMatch(advancedSettingsPanel, /启用速率限制/)
  assert.doesNotMatch(config, /config\.server\.frontend_origin/)
  assert.doesNotMatch(config, /config\.rate_limit/)
  assert.doesNotMatch(configDefaults, /server: \{ frontend_origin/)
  assert.doesNotMatch(configDefaults, /rate_limit:/)
})

test('settings page exposes JavInfo database import workflow', () => {
  const servicesSection = config.slice(config.indexOf("activeGroup === 'services'"), config.indexOf("activeGroup === 'telegram'"))

  assert.match(configFeatureSource, /import_db/)
  assert.match(advancedSettingsPanel, /JavInfo 数据库导入/)
  assert.match(advancedSettingsPanel, /危险操作：全量替换/)
  assert.match(advancedSettingsPanel, /type="file"/)
  assert.doesNotMatch(servicesSection, /JavInfo 数据库导入/)
  assert.match(advancedSettingsPanel, /preflightJavInfoImport/)
  assert.match(advancedSettingsPanel, /runJavInfoMigrations/)
  assert.match(advancedSettingsPanel, /运行 JavInfo 迁移/)
  assert.match(advancedSettingsPanel, /createJavInfoImportJob/)
  assert.match(advancedSettingsPanel, /uploadJavInfoImportDump/)
  assert.match(advancedSettingsPanel, /listJavInfoImportJobs/)
  assert.match(advancedSettingsPanel, /javinfoImportConfirm/)
  assert.match(advancedSettingsPanel, /javinfoImportDirectConfirm/)
  assert.match(advancedSettingsPanel, /javinfoImportCanStart/)
  assert.match(advancedSettingsPanel, /import-progress/)
  assert.match(advancedSettingsPanel, /@drop\.prevent="onJavInfoImportFileDrop"/)
  assert.match(advancedSettingsPanel, /import-log-tail/)
  assert.match(advancedSettingsPanel, /失败不能自动回滚/)
  assert.match(apiSource, /runJavInfoMigrations\(dryRun = false\)/)
  assert.match(apiSource, /\/v1\/javinfo\/imports\/migrations/)
  assert.match(configDefaults, /maintenance_database: 'postgres'/)
  assert.match(configDefaults, /keep_previous_databases: 1/)
  assert.match(configDefaults, /user: 'javhub'/)
  assert.doesNotMatch(advancedSettingsPanel, /并行恢复/)
  assert.doesNotMatch(advancedSettingsPanel, /保留旧库/)
  assert.doesNotMatch(advancedSettingsPanel, /max_parallel_jobs/)
  assert.doesNotMatch(advancedSettingsPanel, /keep_previous_databases/)
})

test('settings route query opens JavInfo import workflow in advanced settings', () => {
  const component = loadConfigOptions()
  const vm = {
    activeGroup: 'services',
    navGroups: [
      { id: 'services' },
      { id: 'advanced' },
    ],
    $route: { query: { tab: 'javinfo-import' } },
  }
  vm.syncActiveGroupFromRoute = component.methods.syncActiveGroupFromRoute

  component.created.call(vm)

  assert.equal(vm.activeGroup, 'advanced')
  assert.equal(component.watch?.['$route.query.tab'], 'syncActiveGroupFromRoute')
})

test('JavInfo import preflight is tied to current settings and file', () => {
  assert.match(advancedSettingsPanel, /javinfoImportPreflightSignature: ''/)
  assert.match(advancedSettingsPanel, /javinfoImportRequestSignature\(\)[\s\S]*JSON\.stringify\(\{[\s\S]*import_db: this\.config\.javinfo\.import_db[\s\S]*file_size: this\.javinfoImportFile\?\.size \|\| 0[\s\S]*\}\)/)
  assert.match(advancedSettingsPanel, /javinfoImportPreflightCurrent\(\)[\s\S]*this\.javinfoImportPreflightSignature !== this\.javinfoImportRequestSignature\(\)[\s\S]*return null/)
  assert.match(advancedSettingsPanel, /&& this\.javinfoImportPreflightCurrent\(\)\?\.ok/)
  assert.match(advancedSettingsPanel, /const signature = this\.javinfoImportRequestSignature\(\)[\s\S]*this\.javinfoImportPreflightSignature = signature/)
})

test('JavInfo import cancel keeps polling while cancellation is still active', () => {
  assert.match(advancedSettingsPanel, /const stillActive = this\.isJavInfoImportActive\(resp\.data\)/)
  assert.match(advancedSettingsPanel, /if \(!stillActive\) \{[\s\S]*this\.stopJavInfoImportPolling\(\)/)
  assert.match(advancedSettingsPanel, /else \{[\s\S]*this\.startJavInfoImportPolling\(this\.javinfoImportJob\.id\)/)
})

test('settings page exposes sanitized config export from advanced settings', () => {
  assert.match(advancedSettingsPanel, /导出用户配置/)
  assert.match(advancedSettingsPanel, /exportUserConfig/)
  assert.match(advancedSettingsPanel, /exportingConfig/)
  assert.match(apiSource, /exportConfig/)
})

test('interactive filters avoid stale actions and stale pagination', () => {
  assert.match(search, /this\.applySearchPreferences\(\)/)
  assert.match(search, /clearSort\(\{ search = true \} = \{\}\)/)
  assert.match(search, /async activated\(\)[\s\S]*this\.applySearchPreferences\(\)[\s\S]*await this\.loadConfiguredPageSize\(\)[\s\S]*this\.syncRouteQuery\(this\.\$route\.query\)[\s\S]*this\.doSearch\(\)/)
  assert.match(genres, /this\.categoryError = ''[\s\S]*this\.displayedTags = this\.shuffledTags/)
  assert.doesNotMatch(genres, /stats_failed|loadCategoryStats|getCategoryStats|computeRarity/)
})

test('appearance settings are grouped by scope and persist discovery preferences', () => {
  const globalSection = config.slice(config.indexOf('<h2>全局偏好</h2>'), config.indexOf('<h2>影片检索</h2>'))
  const searchSection = config.slice(config.indexOf('<h2>影片检索</h2>'), config.indexOf('<h2>随机探索</h2>'))
  const discoverySection = config.slice(config.indexOf('<h2>随机探索</h2>'), config.indexOf('</template>'))
  assert.match(globalSection, /<span class="setting-title">显示语言<\/span>/)
  assert.match(searchSection, /<span class="setting-title">检索页数量<\/span>/)
  assert.match(searchSection, /<span class="setting-title">默认排序<\/span>/)
  assert.match(searchSection, /<span class="setting-title">默认版本筛选<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">演员头像<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">演员每批数量<\/span>/)
  assert.match(discoverySection, /<span class="setting-title">系列每批数量<\/span>/)
  assert.match(config, /<h2>题材 \/ 系列气泡<\/h2>/)
  assert.doesNotMatch(discoverySection, /材质|金传说|稀有度|色系预设/)
  assert.doesNotMatch(searchSection, /演员头像/)
  assert.doesNotMatch(discoverySection, /检索页数量/)
  assert.match(configDefaults, /defaultTab: 'genre'/)
  assert.match(configDefaults, /actressPageSize: 36/)
  assert.match(configDefaults, /seriesPageSize: 24/)
  assert.doesNotMatch(configDefaults, /colorMode|palette|customGradients|rarityThresholds|rarityColors/)
  assert.match(config, /seriesPageSizeOptions\s*=\s*\[12, 24, 36, 48\]/)
  assert.match(config, /localStorage\.setItem\('genres_bubble_cfg', JSON\.stringify\(this\.bubbleCfg\)\)/)
})

test('global dropdowns use the unified glass select control', () => {
  for (const [name, source] of Object.entries({
    config,
    inventory,
    supplementFeatureSource,
    translationJobs,
    logs,
    search,
    discoveryDetail,
  })) {
    assert.doesNotMatch(source, /<select\b/, `${name} should not use native select controls`)
  }

  const searchSection = config.slice(config.indexOf('<h2>影片检索</h2>'), config.indexOf('<h2>随机探索</h2>'))
  assert.match(searchSection, /<GlassSelect[\s\S]*v-model="searchPrefs\.defaultSort"/)
  assert.match(searchSection, /<GlassSelect[\s\S]*v-model="searchPrefs\.defaultServiceCode"/)
  assert.doesNotMatch(config, /v-model="bubbleCfg\.palette"/)

  assert.match(inventory, /import GlassSelect/)
  assert.match(inventory, /v-model="sortBy"[\s\S]*@change="doSearch"/)
  assert.match(inventory, /v-model="pageSize"[\s\S]*@change="onPageSizeChange"/)
  assert.match(supplementFeatureSource, /v-model="movieFilters\.matched"[\s\S]*matchFilterOptions/)
  assert.match(supplement, /value: false, label: '未匹配'/)
  // After the SupplementManagement split this lives in useSupplementApi as a
  // computed; accept either the legacy `providerSourceOptions()` call form or
  // the composable export form.
  assert.match(supplement, /providerSourceOptions/)
  assert.match(logs, /v-model="filterLevel"[\s\S]*levelOptions/)
  assert.match(search, /<GlassSelect[\s\S]*class="version-filter"[\s\S]*@change="doSearch"/)
  assert.match(discoveryDetail, /<GlassSelect[\s\S]*class="version-filter"[\s\S]*@change="doSearch"/)
  assert.match(search, /\.sort-strip[\s\S]*--filter-control-height: 32px/)
  assert.match(search, /\.version-filter[\s\S]*--glass-select-height: var\(--filter-control-height\)/)
  assert.match(search, /\.sort-strip[\s\S]*--filter-control-height: 44px/)
  assert.match(discoveryDetail, /\.chronicle-btn[\s\S]*width: var\(--filter-control-width\)/)

  assert.match(glassSelect, /aria-haspopup="listbox"/)
  assert.match(glassSelect, /event\.key === 'ArrowDown'/)
  assert.match(glassSelect, /event\.key === 'Escape'/)
  assert.match(glassSelect, /emit\('update:modelValue', option\.value\)/)
  assert.match(glassSelect, /<Teleport to="body">/)
  assert.match(glassSelect, /window\.visualViewport\?\.addEventListener\('resize', requestMenuPlacement\)/)
  assert.match(glassSelect, /menuNaturalHeight\(\)/)
  assert.doesNotMatch(glassSelect, /Math\.min\(menuRef\.value\.scrollHeight[\s\S]*360\)/)
  assert.match(mainCss, /\.glass-select--compact[\s\S]*--glass-select-height: 38px/)
  assert.match(mainCss, /\.glass-select__button[\s\S]*min-height: var\(--glass-select-height\)/)
  assert.match(mainCss, /\.glass-select__button[\s\S]*background:\s*var\(--surface-specular-edge\),\s*var\(--surface-noise\),\s*var\(--material-glass-control, var\(--glass-control-bg, rgba\(255, 255, 255, 0\.05\)\)\)/)
  assert.match(mainCss, /\.glass-select__menu[\s\S]*border-radius: var\(--glass-select-menu-radius, var\(--radius-lg\)\)/)
  assert.match(mainCss, /\.glass-select__menu[\s\S]*backdrop-filter: blur/)
})

test('search preferences drive initial search params', () => {
  assert.match(searchPreferences, /SEARCH_PREFERENCES_KEY = 'javhub_search_preferences'/)
  assert.match(searchPreferences, /defaultSort: 'random'/)
  assert.match(searchPreferences, /defaultServiceCode: ''/)
  assert.match(searchPreferences, /normalizeSearchPreferences/)
  assert.match(config, /loadSearchPreferences/)
  assert.match(config, /saveSearchPreferences/)
  assert.match(search, /import\s+\{[\s\S]*loadSearchPreferences[\s\S]*\}\s+from '\.\.\/utils\/searchPreferences\.js'/)
  assert.match(search, /buildSearchApiParams/)
  assert.match(search, /parseSearchQuery/)
  assert.match(search, /searchHasUserConditions/)
  assert.match(search, /searchQueryFromState/)
  assert.match(search, /function sortStateFromPreference\(defaultSort = 'random'\)/)
  assert.match(search, /async mounted\(\)[\s\S]*this\.applySearchPreferences\(\{ force: true \}\)[\s\S]*await this\.loadConfiguredPageSize\(\)/)
  assert.match(search, /async loadConfiguredPageSize\(\)[\s\S]*await api\.getConfig\(\)/)
  assert.match(search, /buildSearchParams\(page\) \{[\s\S]*buildSearchApiParams\(\{ \.\.\.this\.searchState, page \}, \{ pageSize: this\.pageSize \}\)/)
  assert.match(search, /buildSearchParams\(page\) \{[\s\S]*variant_mode: 'grouped'/)
  assert.match(search, /buildSearchParams\(page\) \{[\s\S]*include_variant_explanations: 1/)
  assert.doesNotMatch(search, /params\.service_code = this\.serviceCode/)
  assert.match(search, /replaceSearchRoute\(patch = \{\}, \{ replace = false \} = \{\}\)[\s\S]*searchQueryFromState\(\{ \.\.\.this\.searchState, \.\.\.patch \}\)/)
  assert.match(search, /doSearch\(\) \{[\s\S]*sortValueFromSortState\(this\.sortState\) === 'random'[\s\S]*searchHasUserConditions\(\{ \.\.\.this\.searchState, page: 1 \}\)[\s\S]*patch\.sort = 'release_date_desc'/)
  assert.match(discoveryDetail, /if \(this\.sortState\.random\)[\s\S]*params\.random = '1'[\s\S]*params\.include_total = false/)
  assert.match(search, /totalLabel\(\)[\s\S]*this\.sortState\.random[\s\S]*'随机探索结果'[\s\S]*this\.total < 0[\s\S]*'结果'/)
  assert.match(discoveryDetail, /totalLabel\(\)[\s\S]*this\.total < 0[\s\S]*'结果'/)
  assert.match(search, /cycleSort\(key\)[\s\S]*cycleSearchSort\(sortValueFromSortState\(this\.sortState\), key\)/)
  assert.match(search, /active: pill\.key === 'random' \? sortState\.random : sortState\[pill\.key\] !== null/)
  assert.doesNotMatch(search, /active: sortState\[pill\.key\] !== null/)
})

test('genres page applies series and actor preference settings separately', () => {
  assert.match(genres, /defaultTab: 'genre'/)
  assert.match(genres, /actressAvatarSize: 'medium'/)
  assert.match(genres, /actressPageSize: 36/)
  assert.match(genres, /seriesPageSize: 24/)
  assert.match(genres, /this\.activeTab = this\.tabFromRoute\(\) \|\| \(this\.tabs\.some\(tab => tab\.key === this\.cfg\.defaultTab\) \? this\.cfg\.defaultTab : 'genre'\)/)
  assert.match(genres, /'\$route\.query\.tab'\(\) \{[\s\S]*this\.applyRouteTab\(\)/)
  assert.match(genres, /actressPageSize\(\)[\s\S]*this\.cfg\.actressPageSize/)
  assert.match(genres, /seriesPageSize\(\)[\s\S]*this\.cfg\.seriesPageSize/)
  assert.match(genres, /const pageSize = this\.seriesPageSize[\s\S]*api\.listSeries\(page, pageSize\)/)
  assert.doesNotMatch(genres, /legendaryBubbleClass|rarity-|golden-shimmer/)
  assert.match(genres, /v-if="activeTab === 'series'" class="tag-cloud-wrap page-rail page-rail--standard"/)
  assert.match(genres, /api\.listActresses\(page, pageSize, \{ has_valid_avatar: 1 \}\)/)
  assert.match(genres, /actress\?\.image_url/)
  assert.match(genres, /actress\?\.avatar_url/)
  assert.match(genres, /actress\?\.javinfo_avatar_url/)
  assert.match(genres, /v-for="actress in displayedActresses"/)
  assert.doesNotMatch(genres, /visibleActresses\(\)/)
  assert.doesNotMatch(genres, /hasActressAvatar\(actress\)/)
  assert.doesNotMatch(genres, /第 \{\{ actressPage \}\}/)
  assert.doesNotMatch(genres, /第 \{\{ seriesPage \}\}/)
  assert.doesNotMatch(genres, /共 \{\{ categories\.length \}\}/)
})

test('genres page removes discovery material and category stats work', () => {
  assert.doesNotMatch(genres, /getCategoryStats|loadCategoryStats|categoryStats|statsLoading|computeRarity|rarityMap/)
  assert.doesNotMatch(genres, /legendary|goldLegend|golden-shimmer|rarity-|colorMode|palette|customGradients/)
  assert.doesNotMatch(apiSource, /getCategoryStats|categories\/stats|javhub_category_stats/)
})

test('genres actor loading uses portrait-shaped skeletons', () => {
  assert.match(genres, /v-if="actressesLoading" class="actress-grid" :style="actressGridStyle"/)
  assert.match(genres, /class="actress-skeleton-card"/)
  assert.match(genres, /class="actress-skeleton-avatar"/)
  assert.match(genres, /class="actress-skeleton-line"/)
  assert.match(genres, /\.actress-skeleton-avatar/)
  assert.doesNotMatch(genres, /<AppleSkeleton v-for="n in 12" :key="n" variant="card" \/>/)
})

test('display names prefer translations when source names are masked', () => {
  assert.match(displayLangSource, /String\(ja \|\| en \|\| ''\)\.includes\('\*'\)/)
  assert.match(displayLangSource, /return jaTrans \|\| enTrans \|\| ja \|\| en \|\| ''/)
})

test('genres page lazily loads series tab data', () => {
  assert.doesNotMatch(genres, /Promise\.all\(\[[\s\S]*this\.loadSeries\(\)/)
  assert.match(genres, /activateTab\(tab\)[\s\S]*if \(tab === 'series' && !this\.seriesRawPage\.length && !this\.seriesLoading\)[\s\S]*this\.loadSeries\(this\.seriesPage\)/)
  assert.match(genres, /switchTab\(tab\)[\s\S]*this\.\$router\.push\(\{ path: this\.\$route\.path, query: \{ \.\.\.this\.\$route\.query, tab \} \}\)/)
})

test('discovery navigation prefers ids for precise filtering', () => {
  assert.match(genres, /const filterValue = tag\.id \|\| tag\.name_ja \|\| tag\.name_en \|\| tag\.name \|\| name/)
  assert.match(genres, /params: \{ type: 'category', value: String\(filterValue\) \}/)
  assert.match(genres, /path:\s*`\/actor\/\$\{encodeURIComponent\(name\)\}`/)
  assert.match(genres, /query\.actress_id = actress\.id/)
  assert.match(genres, /params: \{ type: 'series', value: String\(item\.id \|\| name\) \}/)
  assert.match(app, /const value = item\.id \|\| item\.actress_id \|\| name/)
  assert.match(app, /params: \{ type: 'maker', value: String\(value\) \}/)
  assert.match(app, /params: \{ type: 'label', value: String\(value\) \}/)
  assert.match(app, /params: \{ type: 'series', value: String\(value\) \}/)
  assert.match(videoModal, /type: 'label', item: video\.label/)
  assert.match(discoveryDetail, /label: '厂牌'/)
  assert.match(discoveryDetail, /params\.label_id = parseInt\(v\); else params\.label_name = v/)
})

test('discovery video cards leave video favorites to the detail modal', () => {
  assert.doesNotMatch(discoveryDetail, /:isFavorited="isFavorited\('video', item\.content_id \|\| item\.dvd_id\)"/)
  assert.doesNotMatch(discoveryDetail, /@toggle-favorite="toggleVideoFavorite\(item\)"/)
  assert.doesNotMatch(discoveryDetail, /async toggleVideoFavorite\(item\)[\s\S]*favoriteState\.toggle\('video', id\)/)
  assert.match(videoModal, /class="favorite-btn"/)
})

test('search reset clears stale pagination state', () => {
  assert.match(search, /clearFilters\(\)[\s\S]*this\.results = \[\][\s\S]*this\.total = 0[\s\S]*this\.totalPages = 1[\s\S]*this\.page = 1[\s\S]*this\.jumpPage = null[\s\S]*this\.searched = false/)
})

test('discovery chronicle grouping follows the active release date direction', () => {
  assert.doesNotMatch(discoveryDetail, /this\.sortValue/)
  assert.match(discoveryDetail, /const releaseDateDirection = this\.sortState\.release_date === 'asc' \? 'asc' : 'desc'/)
  assert.match(discoveryDetail, /return releaseDateDirection === 'asc' \? a\.localeCompare\(b\) : b\.localeCompare\(a\)/)
})

test('discovery actress subscription is only enabled for numeric actress ids', () => {
  assert.match(discoveryDetail, /hasNumericActressId\(\)[\s\S]*this\.type === 'actress'[\s\S]*\/\^\\d\+\$\/\.test\(String\(this\.value \|\| ''\)\)/)
  assert.match(discoveryDetail, /v-if="hasNumericActressId"/)
  assert.match(discoveryDetail, /subscriptionState\.toggle\(Number\(this\.value\), this\.displayNameValue \|\| this\.value\)/)
})

test('actor page lazy-loads full filmography pagination', () => {
  assert.match(actor, /async mounted\(\)[\s\S]*await this\.loadActressInfo\(\)[\s\S]*this\.loadActorMovies\(\)/)
  assert.match(actor, /hasMoreMovies\(\)[\s\S]*this\.moviePage < this\.movieTotalPages/)
  assert.match(actor, /async loadMoreMovies\(\)[\s\S]*this\.moviePage \+ 1/)
  assert.match(actor, /@click="loadMoreMovies"/)
  assert.match(actor, /api\.getDownloadCandidateSummary/)
  assert.doesNotMatch(actor, /fetchRemainingMoviePages/)
  assert.doesNotMatch(actor, /MOVIE_PAGE_FETCH_CONCURRENCY/)
  assert.doesNotMatch(actor, /Promise\.all\(pagePromises\)/)
  assert.doesNotMatch(actor, /api\.listDownloadCandidates/)
  assert.doesNotMatch(actor, /limit:\s*100000/)
})

test('vite dev server proxies bare health checks to the backend', () => {
  assert.match(apiSource, /api\.get\('\/health', \{ baseURL: '' \}\)/)
  assert.match(viteConfig, /'\/health': \{[\s\S]*target: 'http:\/\/127\.0\.0\.1:18090'[\s\S]*\}/)
})

test('download mutations are guarded by in-flight state', () => {
  assert.match(home, /bulkCandidateLoading: false/)
  assert.match(home, /candidateMutations: \{\}/)
  assert.match(home, /retryingTasks: \{\}/)
  assert.match(home, /isCandidateMutating\(id\)/)
  assert.match(home, /this\.setCandidateMutation\(candidate\.id, 'approve'\)/)
  assert.match(home, /this\.clearCandidateMutation\(candidate\.id\)/)
  assert.match(home, /if \(this\.selectedCandidateIds\.length === 0 \|\| this\.bulkCandidateLoading\) return/)
  assert.match(home, /async retry\(task\)/)
  assert.match(home, /await api\.createDownload/)
  assert.match(home, /await this\.loadTasks\(\)/)
  const enrichVisibleBlock = home.slice(
    home.indexOf('async enrichVisibleCandidateMagnets()'),
    home.indexOf('async processVisibleCandidates()')
  )
  assert.match(enrichVisibleBlock, /const confirmed = await requestConfirm\(/)
  assert.match(enrichVisibleBlock, /title: '批量补充磁力'/)
  assert.match(enrichVisibleBlock, /message: `确认为当前列表中的 \$\{targets\.length\} 个下载候选查找并写入磁力？当前筛选总量 \$\{this\.candidateTotal\} 个。`/)
  assert.match(enrichVisibleBlock, /if \(!confirmed\) return[\s\S]*this\.candidateBatchProcessing = 'enrich'/)
})
