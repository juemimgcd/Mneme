<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();
const sidebar = ref<HTMLElement | null>(null);
const overlayQuery = window.matchMedia("(max-width: 1023px)");
let previousFocus: HTMLElement | null = null;

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape" || !props.open || !overlayQuery.matches) return;
  event.preventDefault();
  emit("close");
}

watch(() => props.open, async (open) => {
  if (open && overlayQuery.matches) {
    previousFocus = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", onKeydown);
    await nextTick();
    sidebar.value?.querySelector<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])")?.focus();
    return;
  }
  document.removeEventListener("keydown", onKeydown);
  if (overlayQuery.matches) previousFocus?.focus();
  previousFocus = null;
});

onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Transition name="resource-scrim">
    <button v-if="open" class="resource-sidebar__scrim" type="button" aria-label="Close resources" @click="emit('close')" />
  </Transition>
  <aside
    id="workspace-resource-sidebar"
    ref="sidebar"
    data-testid="resource-sidebar"
    class="resource-sidebar stitch-sidebar"
    :class="{ 'resource-sidebar--open': open }"
    :aria-hidden="!open"
    :inert="open ? undefined : true"
  >
    <slot />
  </aside>
</template>

<style scoped>
.resource-sidebar { display: flex; width: 264px; min-width: 0; height: 100vh; flex-direction: column; overflow: hidden; border-right: 1px solid var(--border-muted); }
.resource-sidebar__scrim { display: none; }
@media (min-width: 1024px) { .resource-sidebar[aria-hidden="true"] { width: 0; visibility: hidden; border: 0; } }
@media (max-width: 1023px) {
  .resource-sidebar { position: fixed; inset: 0 auto 0 0; z-index: 50; width: min(84vw, 320px); padding-bottom: env(safe-area-inset-bottom); box-shadow: var(--shadow-float); transform: translateX(-102%); transition: transform 160ms var(--ease-out-ui); }
  .resource-sidebar--open { transform: translateX(0); }
  .resource-sidebar--open { transition-duration: 220ms; }
  .resource-sidebar__scrim { position: fixed; inset: 0; z-index: 40; display: block; width: 100%; background: rgb(0 0 0 / 42%); border: 0; }
  .resource-scrim-enter-active { transition: opacity 220ms var(--ease-out-ui); }
  .resource-scrim-leave-active { transition: opacity 160ms var(--ease-out-ui); }
  .resource-scrim-enter-from, .resource-scrim-leave-to { opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .resource-sidebar { transition: none; }
  .resource-scrim-enter-active, .resource-scrim-leave-active { transition-property: opacity; }
}
</style>
