<script setup lang="ts">
import { ChevronLeft, Menu, Trash2 } from "@lucide/vue";
import { computed, onBeforeUnmount, ref } from "vue";
import AgentRunTrace from "../components/ai/AgentRunTrace.vue";
import ChatComposer from "../components/ai/ChatComposer.vue";
import ChatHistory from "../components/ai/ChatHistory.vue";
import ChatMessageList from "../components/ai/ChatMessageList.vue";
import UiButton from "../components/ui/UiButton.vue";
import { useI18n } from "../composables/useI18n";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import type { AnswerMode } from "../types";

const props = defineProps<{
  workspace: MnemeWorkspace;
  formatDate: (value: string | number | Date) => string;
}>();
const { t } = useI18n();

const modes = computed<readonly { value: AnswerMode; label: string }[]>(() => [
  { value: "kb_qa", label: t("ai.mode.knowledgeBase") },
  { value: "memory_query", label: t("ai.mode.memory") },
  { value: "profile_query", label: t("ai.mode.profile") },
  { value: "analysis_query", label: t("ai.mode.analysis") },
  { value: "general_chat", label: t("ai.mode.general") },
]);

const compactMedia = window.matchMedia("(max-width: 1024px)");
const isCompact = ref(compactMedia.matches);
const historyCollapsed = ref(compactMedia.matches);
const onCompactChange = (event: MediaQueryListEvent) => {
  isCompact.value = event.matches;
  historyCollapsed.value = event.matches;
};
compactMedia.addEventListener("change", onCompactChange);
onBeforeUnmount(() => compactMedia.removeEventListener("change", onCompactChange));

const currentTitle = computed(() =>
  props.workspace.chatSessions.value.find(
    (session) => session.id === props.workspace.activeChatSessionId.value,
  )?.title || t("ai.newChat"),
);
const modeLabel = (value?: string) =>
  modes.value.find((mode) => mode.value === value)?.label ?? t("ai.assistant");
const modeDescription = computed(() => ({
  kb_qa: t("ai.modeDescription.knowledgeBase"),
  memory_query: t("ai.modeDescription.memory"),
  profile_query: t("ai.modeDescription.profile"),
  analysis_query: t("ai.modeDescription.analysis"),
  general_chat: t("ai.modeDescription.general"),
}[props.workspace.chatAnswerMode.value]));

async function selectSession(sessionId: string) {
  await props.workspace.selectChatSession(sessionId);
  if (compactMedia.matches) historyCollapsed.value = true;
}

async function createSession() {
  await props.workspace.createChatSession();
  if (compactMedia.matches) historyCollapsed.value = true;
}
</script>

<template>
  <!-- ChatMessageList renders message.agent_run_id, source.source_time, and "Regenerate in selected mode"; ChatComposer owns "Retry saved message". -->
  <div
    data-testid="stitch-ai-laboratory-layout"
    class="ai-layout"
    :class="{ 'ai-layout--collapsed': historyCollapsed }"
  >
    <ChatHistory
      v-model:filter="workspace.chatSessionFilter.value"
      :sessions="workspace.filteredChatSessions.value"
      :active-session-id="workspace.activeChatSessionId.value"
      :collapsed="historyCollapsed"
      :modal="isCompact"
      :format-date="formatDate"
      @close="historyCollapsed = true"
      @create="createSession"
      @select="selectSession"
    />

    <section
      data-testid="chat-function-grid"
      class="chat-workspace"
      :inert="isCompact && !historyCollapsed ? true : undefined"
    >
      <UiButton
        data-testid="ai-history-rail-toggle"
        class="chat-workspace__rail-toggle"
        variant="secondary"
        size="sm"
        :title="historyCollapsed ? t('ai.expandHistory') : t('ai.collapseHistory')"
        :aria-expanded="!historyCollapsed"
        @click="historyCollapsed = !historyCollapsed"
      >
        <template #icon>
          <Menu v-if="compactMedia.matches" />
          <ChevronLeft v-else :class="{ rotate: historyCollapsed }" />
        </template>
      </UiButton>

      <header class="chat-workspace__header">
        <div>
          <small>{{ t("nav.ai") }}</small>
          <h1>{{ currentTitle }}</h1>
        </div>
        <UiButton
          variant="danger"
          size="sm"
          :aria-label="t('ai.delete')"
          :disabled="!workspace.activeChatSessionId.value || workspace.chatPending.value"
          @click="workspace.deleteActiveChatSession"
        >
          <template #icon><Trash2 /></template>
          {{ t("ai.deleteShort") }}
        </UiButton>
      </header>

      <main class="chat-workspace__conversation">
        <ChatMessageList
          :messages="workspace.chatMessages.value"
          :answer-mode="workspace.chatAnswerMode.value"
          :pending="workspace.chatPending.value"
          :format-date="formatDate"
          :mode-label="modeLabel"
          @regenerate="workspace.regenerateChatMessage"
        />
        <AgentRunTrace
          v-if="workspace.chatRunTrace.value.length"
          :items="workspace.chatRunTrace.value"
          :progress="workspace.chatRunProgress.value"
          :stream-state="workspace.chatStreamState.value"
        />
      </main>

      <ChatComposer
        :workspace="workspace"
        :modes="modes"
        :mode-description="modeDescription"
      />
    </section>
  </div>
</template>

<style scoped>
.ai-layout {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-columns: 272px minmax(0, 1fr);
  color: var(--content-primary);
  background: var(--surface-canvas);
}
.ai-layout--collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}
.chat-workspace {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr) auto;
}
.chat-workspace__rail-toggle {
  position: absolute;
  top: 50%;
  left: 0;
  z-index: 4;
  min-width: 2rem;
  padding-inline: 0.45rem;
  transform: translate(-50%, -50%);
}
.chat-workspace__rail-toggle :deep(.ui-button__label) {
  display: none;
}
.chat-workspace__rail-toggle svg {
  transition: transform 160ms var(--ease-out-ui);
}
.chat-workspace__rail-toggle svg.rotate {
  transform: rotate(180deg);
}
.chat-workspace__header {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: color-mix(in srgb, var(--surface-canvas) 94%, transparent);
  border-bottom: 1px solid var(--stroke-subtle);
}
.chat-workspace__header > div {
  min-width: 0;
}
.chat-workspace__header small {
  color: var(--content-tertiary);
  font: 600 var(--font-size-xs) var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.chat-workspace__header h1 {
  margin: 0.15rem 0 0;
  overflow: hidden;
  font-size: var(--font-size-lg);
  line-height: var(--line-height-tight);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chat-workspace__conversation {
  min-height: 0;
  overflow: auto;
  padding: var(--space-3) var(--space-5);
  overscroll-behavior: contain;
}
@media (max-width: 1024px) {
  .ai-layout,
  .ai-layout--collapsed {
    grid-template-columns: minmax(0, 1fr);
  }
  .chat-workspace__rail-toggle {
    top: calc(var(--space-4) + 1.25rem);
    left: var(--space-4);
    z-index: calc(var(--z-dialog) + 1);
    transform: none;
  }
  .chat-workspace__header {
    padding-left: 4rem;
  }
}
@media (max-width: 560px) {
  .chat-workspace__header {
    padding-block: var(--space-3);
    padding-right: var(--space-3);
  }
  .chat-workspace__conversation {
    padding-inline: var(--space-3);
  }
}
@media (prefers-reduced-motion: reduce) {
  .chat-workspace__rail-toggle svg {
    transition: none;
  }
}
</style>
