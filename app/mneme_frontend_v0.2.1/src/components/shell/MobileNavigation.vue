<script setup lang="ts">
import type { Component } from "vue";
import { Ellipsis } from "@lucide/vue";
import { useI18n } from "../../composables/useI18n";

type NavigationItem = { id: string; label: string; shortLabel?: string; icon: Component };
defineProps<{ items: NavigationItem[]; activeId: string; moreActive: boolean; moreOpen: boolean }>();
const emit = defineEmits<{ navigate: [id: string]; openMore: [] }>();
const { t } = useI18n();
</script>

<template>
  <nav data-testid="mobile-navigation" class="mobile-navigation" :aria-label="t('shell.mobileWorkspace')">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      :class="{ 'mobile-navigation__active': activeId === item.id }"
      :aria-label="item.label"
      :aria-pressed="activeId === item.id"
      @click="emit('navigate', item.id)"
    >
      <component :is="item.icon" class="size-[18px]" />
      <span>{{ item.shortLabel || item.label }}</span>
    </button>
    <button
      type="button"
      :class="{ 'mobile-navigation__active': moreActive || moreOpen }"
      :aria-label="t('shell.openMoreNavigation')"
      :aria-expanded="moreOpen"
      aria-controls="more-navigation-sheet"
      @click="emit('openMore')"
    ><Ellipsis class="size-[18px]" /><span>{{ t("shell.more") }}</span></button>
  </nav>
</template>

<style scoped>
.mobile-navigation { position: fixed; inset: auto 0 0; z-index: 35; display: none; min-height: calc(3.7rem + env(safe-area-inset-bottom)); grid-template-columns: repeat(5, minmax(0, 1fr)); padding: 0.3rem max(0.35rem, env(safe-area-inset-right)) max(0.35rem, env(safe-area-inset-bottom)) max(0.35rem, env(safe-area-inset-left)); background: color-mix(in srgb, var(--bg-sidebar) 96%, transparent); border-top: 1px solid var(--border-muted); }
.mobile-navigation button { display: grid; min-width: 0; place-items: center; gap: 0.12rem; padding: 0.3rem 0.15rem; color: var(--text-tertiary); background: transparent; border: 0; border-radius: 0.4rem; font-size: 0.6rem; }
.mobile-navigation button:active { transform: scale(0.97); }
.mobile-navigation__active { color: var(--accent); background: var(--accent-soft); }
.mobile-navigation span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (hover: hover) and (pointer: fine) { .mobile-navigation button:hover { color: var(--accent); background: var(--accent-soft); } }
@media (max-width: 767px) { .mobile-navigation { display: grid; } }
@media (prefers-reduced-motion: reduce) { .mobile-navigation button:active { transform: none; } }
</style>
