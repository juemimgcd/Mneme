<script setup lang="ts">
import { MessageSquare, Plus, Search, X } from "@lucide/vue";
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { ChatSessionData } from "../../types";
import { useI18n } from "../../composables/useI18n";
import UiButton from "../ui/UiButton.vue";
import UiEmptyState from "../ui/UiEmptyState.vue";

const props = defineProps<{
  sessions: ChatSessionData[];
  activeSessionId: string;
  collapsed: boolean;
  formatDate: (value: string | number | Date) => string;
  modal: boolean;
}>();

const filter = defineModel<string>("filter", { required: true });
const emit = defineEmits<{
  close: [];
  create: [];
  select: [sessionId: string];
}>();
const { t } = useI18n();
const panel = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
let previousOverflow = "";
let modalActive = false;

function onKeydown(event: KeyboardEvent) {
  if (!props.modal || props.collapsed) return;
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

function releaseModal(restoreFocus: boolean) {
  if (!modalActive) return;
  const returnFocus = previousFocus;
  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = previousOverflow;
  previousFocus = null;
  modalActive = false;
  if (restoreFocus) void nextTick(() => returnFocus?.focus());
}

watch(
  () => [props.collapsed, props.modal] as const,
  async ([collapsed, modal], previous) => {
    if (!collapsed && modal) {
      previousFocus = document.activeElement as HTMLElement | null;
      previousOverflow = document.body.style.overflow;
      modalActive = true;
      document.body.style.overflow = "hidden";
      document.addEventListener("keydown", onKeydown);
      await nextTick();
      panel.value?.querySelector<HTMLElement>("button, input")?.focus();
      return;
    }
    if (previous && !previous[0] && previous[1]) releaseModal(true);
  },
);

onBeforeUnmount(() => releaseModal(false));
</script>

<template>
  <aside
    ref="panel"
    data-testid="ai-history-rail"
    class="chat-history"
    :aria-hidden="collapsed"
    :inert="collapsed || undefined"
    :role="modal ? 'dialog' : undefined"
    :aria-modal="modal && !collapsed ? 'true' : undefined"
    :aria-label="t('ai.chatHistory')"
    tabindex="-1"
  >
    <header class="chat-history__header">
      <div>
        <small>{{ t("ai.workspace") }}</small>
        <h2>{{ t("ai.chats") }}</h2>
      </div>
      <UiButton class="chat-history__close" variant="ghost" size="sm" :aria-label="t('ai.closeHistory')" @click="$emit('close')">
        <template #icon><X /></template>
      </UiButton>
    </header>

    <UiButton class="chat-history__new" variant="primary" @click="$emit('create')">
      <template #icon><Plus /></template>
      {{ t("ai.newChat") }}
    </UiButton>

    <label class="chat-history__search">
      <Search aria-hidden="true" />
      <span class="sr-only">{{ t("ai.searchHistory") }}</span>
      <input v-model="filter" type="search" :placeholder="t('ai.search')" />
    </label>

    <nav :aria-label="t('ai.chatHistory')">
      <button
        v-for="session in sessions"
        :key="session.id"
        type="button"
        :class="{ active: session.id === activeSessionId }"
        :aria-current="session.id === activeSessionId ? 'page' : undefined"
        @click="$emit('select', session.id)"
      >
        <MessageSquare aria-hidden="true" />
        <span>
          <strong>{{ session.title || t("ai.untitledChat") }}</strong>
          <small>{{ session.last_message_at ? formatDate(session.last_message_at) : t("ai.noMessages") }}</small>
        </span>
      </button>
    </nav>

    <UiEmptyState
      v-if="!sessions.length"
      :title="t('ai.noChatsTitle')"
      :description="t('ai.noChatsDescription')"
    >
      <template #icon><MessageSquare /></template>
    </UiEmptyState>
  </aside>
</template>

<style scoped>
.chat-history {
  display: flex;
  min-width: 0;
  height: 100%;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--surface-sidebar);
  border-right: 1px solid var(--stroke-subtle);
  transition: opacity 160ms var(--ease-out-ui);
}
.chat-history[aria-hidden="true"] {
  visibility: hidden;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}
.chat-history__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.chat-history__header h2 {
  margin: 0.1rem 0 0;
  color: var(--content-primary);
  font-size: var(--font-size-lg);
}
.chat-history__header small {
  color: var(--content-tertiary);
  font: 600 var(--font-size-xs) var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.chat-history__close {
  display: none;
}
.chat-history__new {
  width: 100%;
}
.chat-history__search {
  display: flex;
  min-height: 2.4rem;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  color: var(--content-tertiary);
  background: var(--surface-canvas);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.chat-history__search:focus-within {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}
.chat-history__search svg {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
}
.chat-history__search input {
  min-width: 0;
  flex: 1;
  color: var(--content-primary);
  background: transparent;
  border: 0;
  outline: 0;
}
.chat-history nav {
  display: grid;
  gap: var(--space-1);
  overflow: auto;
}
.chat-history nav button {
  display: grid;
  min-width: 0;
  min-height: 3.4rem;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: var(--space-3);
  padding: var(--space-3);
  color: var(--content-secondary);
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-control);
  transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease;
}
.chat-history nav button > svg {
  width: 1rem;
  height: 1rem;
  margin-top: 0.15rem;
  color: var(--content-tertiary);
}
.chat-history nav button span {
  display: grid;
  min-width: 0;
  gap: 0.2rem;
}
.chat-history nav strong,
.chat-history nav small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-history nav strong {
  color: inherit;
  font-size: var(--font-size-sm);
  font-weight: 600;
}
.chat-history nav small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.chat-history nav button.active {
  color: var(--content-primary);
  background: var(--surface-selected);
  box-shadow: inset 2px 0 var(--accent-primary);
}
@media (hover: hover) and (pointer: fine) {
  .chat-history nav button:hover:not(.active) {
    color: var(--content-primary);
    background: var(--surface-raised);
  }
}
@media (max-width: 1024px) {
  .chat-history {
    position: fixed;
    inset: 0;
    z-index: var(--z-dialog);
    padding: max(var(--space-4), env(safe-area-inset-top)) var(--space-4) max(var(--space-4), env(safe-area-inset-bottom));
    border-right: 0;
  }
  .chat-history[aria-hidden="true"] {
    display: none;
  }
  .chat-history__close {
    display: inline-flex;
  }
}
@media (prefers-reduced-motion: reduce) {
  .chat-history {
    transition: opacity 100ms linear;
  }
}
</style>
