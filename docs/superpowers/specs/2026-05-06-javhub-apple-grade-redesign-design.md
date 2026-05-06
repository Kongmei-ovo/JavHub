# JavHub Apple-Grade Redesign Design

**Date:** 2026-05-06

**Goal:** Make JavHub's highest-frequency experience feel Apple-grade: fast, calm, premium, progressive, and reliable.

**Selected scope:** Design System Foundation + Core Path Migration.

**Core paths for phase one:**
- Search flow: `影片检索 → 筛选/排序/分页 → 影片详情 → 收藏/下载`
- Recommendation flow: `个性推荐 → 标签/演员/系列 → 影片详情 → 收藏/下载`
- Shared video detail modal from all entry points

**Risk posture:** Stable rollout. Each behavior change should have tests and browser verification before being considered complete.

---

## 1. Product Goal and Boundaries

Phase one is not a whole-product rewrite. It establishes a durable Apple-grade product language and applies it to the highest-frequency paths.

The user should experience:

- Immediate response after clicking a card or changing a primary control.
- Progressive detail loading: base card data first, JavInfo detail next, MetaTube metadata and large media afterward.
- Quiet, graceful degradation for enhancement data such as metadata, stills, preview video, and image failures.
- Consistent card, loading, empty, error, and feedback patterns across search, recommendation, and shared detail.
- Premium dark Pro visual quality with restrained Liquid Glass in surfaces that benefit from depth: navigation, modal sheets, floating actions, and feedback.

Phase one explicitly excludes:

- Full navigation information architecture rewrite.
- Deep rewrites of subscription, inventory, download management, or actor merge flows.
- New feature expansion unrelated to perceived quality, performance, or maintainability.
- Large backend domain-model restructuring.

---

## 2. Current Foundations to Preserve

The current codebase already has several strong foundations:

- Global design tokens in `frontend/src/assets/main.css` for dark surfaces, motion, glass, typography, radii, and Element Plus overrides.
- Theme infrastructure in `frontend/src/assets/themes.js` for future visual consistency.
- Route-level dynamic imports in `frontend/src/router/index.js`.
- Shared global detail modal rendered from `frontend/src/App.vue`.
- Progressive detail loading direction in `frontend/src/utils/modalState.js` and `backend/modules/info_client.py`.
- Diskcache-based backend caching in `backend/services/cache.py`.
- Backend route modularity under `backend/routers/`.

These should be refined rather than discarded.

---

## 3. Frontend Architecture

### 3.1 Design Tokens

Extend `frontend/src/assets/main.css` so components express intent through semantic tokens instead of hardcoded visual constants.

Add or normalize tokens for:

- Materials: subtle glass, elevated glass, sheet glass, card surface, card hover surface.
- Motion: fast, standard, emphasized, reveal, press.
- Geometry: card radius, sheet radius, control radius, touch target size.
- Elevation: card, hover, floating, modal sheet.
- Status: success, warning, error, info, pending.
- Interaction states: hover, press, selected, disabled, loading.

The goal is not to invent a heavy design-system package. The goal is to make visual choices consistent and easy to audit.

### 3.2 Card Primitive

Create a single shared video-card primitive to replace duplicated behavior across:

- `frontend/src/components/MovieCard.vue`
- `frontend/src/components/VideoCard.vue`
- search/recommendation in-view card variants

The primitive should provide:

- Stable cover aspect ratio.
- Lazy image loading.
- High-quality fallback image state.
- Optional favorite action.
- Optional preview badge.
- Code/title/date/runtime/service badge slots or props.
- Hover, press, selected, and loading states.
- Matching skeleton dimensions to avoid layout shift.

Pages should pass normalized video data and callbacks. They should not reinvent cover fallback, favorite placement, hover physics, badge styling, or image-loading behavior.

### 3.3 State Primitives

Introduce shared state primitives for:

- Skeleton text, card, grid, and section states.
- Empty states with a single recommended action.
- Inline error states with retry for main-path failures.
- Progressive sections that can reveal content when data arrives or when the section approaches the viewport.

Error semantics:

- Main-path failures are visible and actionable.
- Enhancement-path failures are silent or inline-muted and never trigger noisy global toast.

Enhancement-path examples:

- MetaTube metadata.
- Gallery/still images.
- Preview video lookup.
- Optional high-resolution cover.

### 3.4 Video Modal Decomposition

Split the current monolithic detail modal into focused pieces:

- `VideoDetailSheet.vue`: modal shell, layout, close behavior, focus/scroll management, backdrop behavior.
- `VideoHeroMedia.vue`: cover, high-resolution cover upgrade, preview/play entry.
- `VideoMetadataPanel.vue`: title, code, release date, runtime, score, director, summary, metadata loading state.
- `VideoPeopleTags.vue`: actresses, categories, maker, series, navigation callbacks.
- `VideoGallery.vue`: still gallery lazy reveal and viewer.
- `VideoActions.vue`: favorite, download, copy, stream/play actions.

`frontend/src/utils/modalState.js` remains the single entry point for opening the modal, but its state model should clearly separate:

- Base card data.
- JavInfo detail data.
- MetaTube metadata.
- Media/gallery state.
- Request generation ID for stale response protection.
- Errors by lane: `javinfo`, `metatube`, `cover`, `gallery`, `stream`.

---

## 4. Data Flow and Performance

### 4.1 Request Semantics

The API layer should distinguish request intent:

- Main-path requests: visible error feedback on failure.
- Enhancement requests: `silentError` or equivalent, no global toast on failure.
- Cancelable or sequence-guarded requests: search, filters, sorting, pagination.

Search and recommendation pages should prevent older responses from overwriting newer state when users type quickly, change filters, or paginate rapidly.

### 4.2 Detail Loading Flow

Opening a video detail should follow this sequence:

1. Immediately show modal shell with normalized base card data.
2. Fetch JavInfo detail and merge into modal when available.
3. Fetch MetaTube metadata separately and merge when available.
4. Upgrade cover and reveal gallery progressively.
5. Load preview player/HLS only after explicit user intent.

No remote metadata or large image should block modal first paint.

### 4.3 Image and Media Strategy

For search and recommendation lists:

- Use lazy-loaded thumbnails.
- Reserve layout space with aspect-ratio boxes.
- Use skeletons with the same footprint as final cards.
- Avoid broken image icons.

For detail:

- Start with the card's existing cover.
- Upgrade to better image data after JavInfo detail arrives.
- Keep gallery collapsed/lazy until user intent or viewport proximity.
- Do not load HLS/player dependencies until playback is requested.

### 4.4 Bundle Strategy

Current risks include full Element Plus import, global icon registration, and media-heavy dependencies. Phase one should:

- Stop registering all Element Plus icons globally.
- Move test-only tooling such as Playwright to dev dependencies.
- Keep route-level dynamic imports.
- Add Vite manual chunking for Vue, Element Plus, media player libraries, and motion utilities.
- Record build chunk sizes after each phase.

### 4.5 Backend Hotspots

Only backend changes that directly affect perceived quality are in scope for phase one.

Priority backend improvements:

- Add bounded concurrency to `backend/routers/categories.py` category stats fan-out.
- Preserve diskcache TTLs and clarify stale fallback behavior for enum/stats/search endpoints.
- Keep metadata as an independent enhancement API.
- Treat stream proxy buffering as a follow-up unless it directly blocks first-stage UX verification.

---

## 5. UI and Interaction Language

### 5.1 Visual Direction

The approved direction is dark Pro with restrained Liquid Glass.

Use:

- Deep black/near-black page backgrounds.
- Low-noise card surfaces.
- Subtle borders and elevation.
- Liquid Glass for modal sheets, navigation, floating action areas, and feedback.
- White/neutral emphasis with low-saturation status colors.

Avoid:

- Full-screen decorative blur.
- Neon-heavy glow.
- Random translucent surfaces without hierarchy.
- Large motion or bouncy effects that feel game-like.

### 5.2 Cards

Cards should feel stable, quiet, and premium:

- Content-first hierarchy.
- Gentle lift on hover.
- Press feedback on click.
- Favorite action with small, tactile motion.
- Badges that support scanning without overpowering covers or titles.
- Mobile touch targets at least 44px where controls are interactive.

### 5.3 Detail Modal

The detail modal is the main carrier of premium feel.

It should:

- Open immediately.
- Use a focused dim/blur backdrop.
- Preserve context and support close/escape/backdrop behavior.
- Reveal sections progressively with short fade/translate/blur-removal motion.
- Separate main detail loading from enhancement loading.
- Keep gallery and video playback from competing with first paint.

### 5.4 Motion

Motion should be unified into three categories:

- Micro motion: button press, favorite pop, tag hover.
- Transition motion: page changes, modal open/close, sheet movement.
- Progressive reveal: content arrival, skeleton replacement, section reveal.

Motion should be short, calm, and consistent.

### 5.5 Feedback

Feedback hierarchy:

- User action success: toast capsule or local inline success.
- User action failure: small error feedback with clear text.
- Main data failure: inline state with retry.
- Enhancement failure: silent degradation.

Global toasts should not appear for background enrichment failures.

---

## 6. Implementation Phases

### Phase 1: Stabilize Current Progressive Detail

Finish and harden the current detail-loading work:

- Ensure metadata failures remain silent.
- Ensure stale responses cannot overwrite current video.
- Ensure missing IDs degrade cleanly.
- Ensure the backend metadata route is covered by tests.

### Phase 2: Design-System Primitives

Create the minimal primitives needed by search and recommendation:

- Semantic design tokens.
- Shared video card primitive.
- Skeleton/grid/empty/error/progressive section primitives.
- API request semantics for main vs enhancement errors.

### Phase 3: Search and Recommendation Migration

Migrate the selected core paths:

- Search page card grid, loading states, and stale-request behavior.
- Recommendation page card/list states and navigation to detail.
- Shared modal entry behavior from both paths.

### Phase 4: Performance Foundation

Apply the highest-leverage performance fixes:

- Vite chunking and dependency cleanup.
- Image lazy-loading and placeholder discipline.
- Category stats bounded concurrency.
- Bundle size tracking.

---

## 7. Verification Plan

Every phase should be verified with fresh evidence before completion.

Automated verification:

- Frontend node tests for modal state, API error semantics, and reusable state/card behavior.
- Backend unittest tests for metadata route, cache behavior, and category stats concurrency.
- `npm run build` for frontend production build.

Browser verification:

- Search keyword input.
- Rapid filter/sort/page changes.
- Opening detail from search.
- Opening detail from recommendation.
- Metadata success and failure.
- Image failure fallback.
- Gallery lazy reveal.
- Favorite feedback.
- Download action feedback.
- Tag/actress/series navigation from modal and return behavior.

Performance evidence:

- Build chunk size output before and after chunking.
- Confirmation that list images are lazy-loaded.
- Confirmation that modal first paint is not blocked by MetaTube or gallery.
- Confirmation that old search responses cannot overwrite new results.

---

## 8. Acceptance Criteria

Phase one is acceptable when:

- Search and recommendation flows use shared card/state primitives.
- The shared detail modal opens immediately and progressively fills content.
- Enhancement failures do not create noisy global errors.
- Search/filter/pagination interactions are protected from stale response overwrites.
- Large images and gallery content do not block first paint.
- Bundle and backend hot spots have at least first-pass safeguards.
- Tests and browser verification cover the selected core paths.
- The visual result feels dark, premium, calm, and unified rather than merely restyled.
