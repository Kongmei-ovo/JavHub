<template>
  <!-- 补全工作台统一 hero —— 待补全演员 / 待补全作品 / 任务队列 三个 tab 共用，保证切换时
       高度一致。选中演员时头像/名字「露出」在顶部(head)；未选演员时只剩底部的胶囊(#meters)，
       结构不变、不割裂。胶囊样式(.hero-meter / .job-stat / .cmp-bar)由本组件经 :slotted 统一供给。 -->
  <div class="sup-hero" :class="{ 'sup-hero--bare': !hasActor }">
    <div v-if="hasActor" class="sup-hero-head">
      <div class="sup-hero-av" :style="avatarUrl ? null : avatarStyle">
        <img v-if="avatarUrl" :src="avatarUrl" :alt="name" loading="eager" decoding="async" @error="onAvatarError" />
        <span v-else>{{ avatarLetter }}</span>
      </div>
      <div class="sup-hero-id">
        <h2>{{ name }}</h2>
        <div class="sh-sub">
          <template v-if="original">{{ original }} · </template>{{ subtitle }}
        </div>
      </div>
      <slot name="aside" />
    </div>
    <div class="sup-hero-meters">
      <slot name="meters" />
    </div>
  </div>
</template>

<script>
import { actressImgUrl } from '../../utils/imageUrl.js'
import { applyImageFallback } from '../../utils/imageFallback.js'
import { displayName } from '../../utils/displayLang.js'

export default {
  name: 'SupplementActorHero',
  props: {
    actor: { type: Object, default: null },
    subtitle: { type: String, default: '' },
  },
  computed: {
    hasActor() {
      const a = this.actor
      return !!(a && (a.id || a.name_kanji || a.name_romaji || a.name))
    },
    name() {
      return displayName(this.actor, 'name_kanji', 'name_romaji')
        || this.actor?.name_kanji || this.actor?.name_romaji || this.actor?.name || '未知演员'
    },
    original() { const o = this.actor?.name_kanji || this.actor?.name_romaji || ''; return o && o !== this.name ? o : '' },
    avatarUrl() { return this.actor?.image_url ? (actressImgUrl(this.actor.image_url) || '') : '' },
    avatarLetter() { return (this.name || '?').slice(0, 1) },
    avatarStyle() {
      const seed = String(this.actor?.id || this.name || 'jh'); let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${(hue + 38) % 360} 55% 46%))` }
    },
  },
  methods: {
    onAvatarError(e) { applyImageFallback(e, { label: this.avatarLetter }) },
  },
}
</script>

<style scoped>
.sup-hero {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5);
  border-radius: var(--radius-sheet);
  background: linear-gradient(120deg, rgba(var(--accent-rgb), 0.12), var(--card) 50%);
  border: 1px solid var(--hairline-strong);
  margin-bottom: var(--space-5);
  overflow: hidden;
}

/* 未选演员(只剩胶囊)时进一步收紧上下内边距，卡片更矮。 */
.sup-hero--bare { padding: var(--space-3) var(--space-4); }

.sup-hero-head {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
}

.sup-hero-av {
  width: 92px;
  height: 92px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 38px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.sup-hero-av img { width: 100%; height: 100%; object-fit: cover; display: block; }

.sup-hero-id { flex: 1; min-width: 0; }

.sup-hero-id h2 {
  margin: 0;
  font-size: var(--type-title-1);
  font-weight: var(--type-title-1-weight);
  letter-spacing: var(--type-title-1-tracking);
  color: var(--text-primary);
}

.sh-sub { margin-top: 4px; font-size: var(--type-caption); color: var(--text-secondary); }

/* 胶囊网格 —— auto-fit 自适应列数(2~4)，所有 tab 共用，高度一致。 */
.sup-hero-meters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
}

/* 有头像时胶囊与上方 head 之间加一条分隔线；纯胶囊态不需要。 */
.sup-hero:not(.sup-hero--bare) .sup-hero-meters {
  padding-top: var(--space-3);
  border-top: 1px solid var(--hairline-strong);
}

/* 胶囊本体(.hero-meter / .job-stat / .cmp-bar)是各 tab 经 #meters 槽传入的内容，归父级
   scope 所有，故样式放共享的 supplementHero.css(由各父级 scoped 引入)，此处不重复。 */
</style>
