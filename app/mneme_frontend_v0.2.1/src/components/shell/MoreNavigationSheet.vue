<script setup lang="ts">
import type { Component } from "vue";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { BookOpen, LifeBuoy, LogOut, Monitor, Moon, Sun, X } from "@lucide/vue";
import { useI18n } from "../../composables/useI18n";
import { type ThemeMode, usePreferences } from "../../composables/usePreferences";
import UiIconButton from "../ui/UiIconButton.vue";
import UiSegmentedControl from "../ui/UiSegmentedControl.vue";

type NavigationItem = { id: string; label: string; icon: Component };

const props = defineProps<{ open: boolean; items: NavigationItem[]; activeId: string; userName: string }>();
const emit = defineEmits<{
  close: [];
  navigate: [id: string];
  documentation: [];
  support: [];
  logout: [];
}>();

const { t } = useI18n();
const { themeMode, setThemeMode } = usePreferences();
const panel = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
let previousOverflow = "";

const themeModel = computed({
  get: () => themeMode.value,
  set: (value: string) => setThemeMode(value as ThemeMode),
});
const themeOptions = computed(() => [
  { value: "system", label: t("settings.theme.system"), icon: Monitor },
  { value: "light", label: t("settings.theme.light"), icon: Sun },
  { value: "dark", label: t("settings.theme.dark"), icon: Moon },
]);

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab" || !panel.value) return;
  const focusable = [...panel.value.querySelectorAll<HTMLElement>(
    'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  )];
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function navigate(id: string) {
  emit("navigate", id);
  emit("close");
}

function runAction(action: "documentation" | "support" | "logout") {
  if (action === "documentation") emit("documentation");
  else if (action === "support") emit("support");
  else emit("logout");
  emit("close");
}

watch(() => props.open, async (open) => {
  if (open) {
    previousFocus = document.activeElement as HTMLElement | null;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeydown);
    await nextTick();
    panel.value?.querySelector<HTMLElement>("button")?.focus();
    return;
  }
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = previousOverflow;
  previousFocus?.focus();
  previousFocus = null;
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = previousOverflow;
});
</script>

<template>
  <Teleport to="body">
    <Transition name="more-sheet">
      <div v-if="open" class="more-sheet" role="presentation">
        <button class="more-sheet__scrim" type="button" aria-label="Close more navigation" @click="emit('close')" />
        <section
          ref="panel"
          id="more-navigation-sheet"
          data-testid="more-navigation-sheet"
          class="more-sheet__panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="more-sheet-title"
        >
          <header>
            <div><small>{{ userName }}</small><h2 id="more-sheet-title">More</h2></div>
            <UiIconButton label="Close" @click="emit('close')"><X /></UiIconButton>
          </header>

          <nav aria-label="Additional workspace views">
            <button
              v-for="item in items"
              :key="item.id"
              type="button"
              :class="{ active: activeId === item.id }"
              @click="navigate(item.id)"
            >
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </button>
          </nav>

          <section class="more-sheet__appearance">
            <span>{{ t("settings.theme") }}</span>
            <UiSegmentedControl v-model="themeModel" :options="themeOptions" :ariaLabel="t('settings.theme')" size="sm" />
          </section>

          <footer>
            <button type="button" @click="runAction('documentation')"><BookOpen />{{ t("shell.documentation") }}</button>
            <button type="button" @click="runAction('support')"><LifeBuoy />{{ t("shell.support") }}</button>
            <button type="button" class="more-sheet__logout" @click="runAction('logout')"><LogOut />Log out</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.more-sheet { position: fixed; inset: 0; z-index: 80; display: flex; align-items: end; }
.more-sheet__scrim { position: absolute; inset: 0; width: 100%; background: rgb(0 0 0 / 42%); border: 0; }
.more-sheet__panel {
  position: relative;
  width: 100%;
  max-height: min(82dvh, 40rem);
  overflow: auto;
  padding: 0.85rem max(0.85rem, env(safe-area-inset-right)) max(1rem, env(safe-area-inset-bottom)) max(0.85rem, env(safe-area-inset-left));
  color: var(--content-primary);
  background: var(--surface-panel);
  border-top: 1px solid var(--stroke-subtle);
  border-radius: 0.9rem 0.9rem 0 0;
  box-shadow: var(--shadow-popover);
}
.more-sheet__panel > header { display: flex; align-items: center; justify-content: space-between; padding: 0 0.15rem 0.75rem; }
.more-sheet__panel h2 { margin: 0.12rem 0 0; font-size: 1rem; }
.more-sheet__panel small { color: var(--content-tertiary); font-size: var(--font-size-xs); }
.more-sheet__panel nav { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
.more-sheet__panel nav button,
.more-sheet__panel footer button {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.75rem;
  color: var(--content-secondary);
  text-align: left;
  background: var(--surface-sidebar);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.more-sheet__panel nav button.active { color: var(--accent-primary); background: var(--accent-subtle); border-color: color-mix(in srgb, var(--accent-primary) 45%, var(--stroke-subtle)); }
.more-sheet__panel svg { width: 1rem; height: 1rem; }
.more-sheet__appearance { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; margin-top: 0.85rem; padding: 0.75rem; border: 1px solid var(--stroke-subtle); border-radius: var(--radius-control); }
.more-sheet__appearance > span { color: var(--content-secondary); font-size: var(--font-size-sm); font-weight: 600; }
.more-sheet__panel footer { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.5rem; margin-top: 0.85rem; padding-top: 0.85rem; border-top: 1px solid var(--stroke-subtle); }
.more-sheet__panel footer button { justify-content: center; background: transparent; font-size: var(--font-size-xs); }
.more-sheet__panel footer .more-sheet__logout { color: var(--danger); }
.more-sheet-enter-active { transition: opacity 220ms var(--ease-out-ui); }
.more-sheet-leave-active { transition: opacity 160ms var(--ease-out-ui); }
.more-sheet-enter-active .more-sheet__panel { transition: transform 220ms var(--ease-out-ui); }
.more-sheet-leave-active .more-sheet__panel { transition: transform 160ms var(--ease-out-ui); }
.more-sheet-enter-from,
.more-sheet-leave-to { opacity: 0; }
.more-sheet-enter-from .more-sheet__panel,
.more-sheet-leave-to .more-sheet__panel { transform: translateY(100%); }

@media (min-width: 768px) { .more-sheet { display: none; } }
@media (max-width: 420px) {
  .more-sheet__appearance { align-items: stretch; flex-direction: column; }
  .more-sheet__appearance :deep(.ui-segmented) { width: 100%; }
  .more-sheet__appearance :deep(.ui-segmented__option) { flex: 1; }
  .more-sheet__panel footer { grid-template-columns: 1fr; }
  .more-sheet__panel footer button { justify-content: flex-start; }
}
@media (prefers-reduced-motion: reduce) {
  .more-sheet-enter-active,
  .more-sheet-leave-active { transition-property: opacity; }
  .more-sheet-enter-active .more-sheet__panel,
  .more-sheet-leave-active .more-sheet__panel { transition: none; }
  .more-sheet-enter-from .more-sheet__panel,
  .more-sheet-leave-to .more-sheet__panel { transform: none; }
}
</style>
