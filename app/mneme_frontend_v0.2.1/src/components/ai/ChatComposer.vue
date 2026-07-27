<script setup lang="ts">
import { CornerDownLeft, Send, Square } from "@lucide/vue";
import { computed } from "vue";
import type { MnemeWorkspace } from "../../composables/useMnemeWorkspace";
import { useI18n } from "../../composables/useI18n";
import type { AnswerMode } from "../../types";
import UiButton from "../ui/UiButton.vue";
import UiSegmentedControl, { type UiSegmentedOption } from "../ui/UiSegmentedControl.vue";
import UiStatusPanel from "../ui/UiStatusPanel.vue";

const props = defineProps<{
  workspace: MnemeWorkspace;
  modes: readonly { value: AnswerMode; label: string }[];
  modeDescription: string;
}>();

const { t } = useI18n();
const options = computed<UiSegmentedOption[]>(() => props.modes.map((mode) => ({ ...mode })));
const selectedMode = computed({
  get: () => props.workspace.chatAnswerMode.value,
  set: (value: string) => void props.workspace.selectChatAnswerMode(value as AnswerMode),
});
const running = computed(() => props.workspace.chatPending.value || props.workspace.chatControlPending.value);
const retryable = computed(() => !running.value && props.workspace.chatError.value?.retryable);
const composerPlaceholder = computed(() =>
  running.value ? t("ai.runningPlaceholder") : t("ai.placeholder"),
);

function updateMultiAgent(event: Event) {
  void props.workspace.setChatMultiAgentEnabled((event.target as HTMLInputElement).checked);
}
</script>

<template>
  <form data-testid="workspace-chat-command" class="chat-composer" @submit.prevent="workspace.sendChatMessage()">
    <UiSegmentedControl
      v-model="selectedMode"
      data-testid="answer-mode-selector"
      class="chat-composer__modes"
      :ariaLabel="'Answer mode'"
      :options="options"
      :disabled="running"
      size="sm"
    />

    <label class="multi-agent" :class="{ 'multi-agent--active': workspace.chatMultiAgentEnabled.value }">
      <input
        data-testid="multi-agent-toggle"
        type="checkbox"
        :checked="workspace.chatMultiAgentEnabled.value"
        :disabled="running || !workspace.chatMultiAgentAvailable.value"
        @change="updateMultiAgent"
      />
      <span class="multi-agent__switch" aria-hidden="true"><i /></span>
      <span>
        <strong>Multi-Agent thinking</strong>
        <small>
          {{ workspace.chatMultiAgentAvailable.value
            ? "Parallel retrieval with a final evidence review."
            : "Available in Analysis mode." }}
        </small>
      </span>
    </label>

    <UiStatusPanel
      v-if="workspace.chatError.value"
      :title="workspace.chatError.value.message"
      tone="error"
    />

    <div class="chat-composer__input">
      <textarea
        v-model="workspace.chatQuestion.value"
        :placeholder="composerPlaceholder"
        aria-label="Message Mneme"
        rows="2"
      />

      <div v-if="running" class="chat-composer__run-control">
        <select
          v-model="workspace.chatControlMode.value"
          aria-label="Run control mode"
          :disabled="workspace.chatControlPending.value"
        >
          <option value="steer">Steer now</option>
          <option value="followup">Queue next</option>
        </select>
        <UiButton
          variant="secondary"
          size="sm"
          :disabled="workspace.chatControlPending.value || !workspace.chatQuestion.value.trim()"
          aria-label="Apply run control"
          @click="workspace.controlActiveChatRun"
        >
          <template #icon><CornerDownLeft /></template>
          Apply
        </UiButton>
      </div>

      <UiButton
        v-if="running"
        class="chat-composer__submit"
        variant="secondary"
        aria-label="Stop generating"
        @click="workspace.cancelActiveChatRun"
      >
        <template #icon><Square /></template>
        Stop
      </UiButton>
      <UiButton
        v-else-if="retryable"
        class="chat-composer__submit"
        variant="primary"
        aria-label="Retry saved message"
        @click="workspace.retryFailedChatMessage"
      >
        <template #icon><Send /></template>
        Retry
      </UiButton>
      <UiButton
        v-else
        class="chat-composer__submit"
        variant="primary"
        type="submit"
        aria-label="Send message"
        :disabled="!workspace.chatQuestion.value.trim()"
      >
        <template #icon><Send /></template>
        Send
      </UiButton>
    </div>

    <div class="chat-composer__footer">
      <small v-if="workspace.chatRunProgress.value" role="status">{{ workspace.chatRunProgress.value }}</small>
      <small data-testid="answer-mode-description">{{ modeDescription }}</small>
    </div>
  </form>
</template>

<style scoped>
.chat-composer {
  display: grid;
  width: min(100%, 820px);
  gap: var(--space-3);
  margin: 0 auto;
  padding: var(--space-3) var(--space-5) max(var(--space-4), env(safe-area-inset-bottom));
  background: var(--surface-canvas);
  border-top: 1px solid var(--stroke-subtle);
}
.chat-composer__modes {
  width: 100%;
  overflow-x: auto;
}
.chat-composer__modes :deep(.ui-segmented__option) {
  flex: 1 0 max-content;
}
.multi-agent {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  color: var(--content-secondary);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
  cursor: pointer;
  transition: color var(--duration-fast) ease, border-color var(--duration-fast) ease, background-color var(--duration-fast) ease;
}
.multi-agent--active {
  border-color: color-mix(in srgb, var(--accent-primary) 45%, var(--stroke-subtle));
  background: var(--accent-subtle);
}
.multi-agent:has(input:disabled) {
  opacity: 0.55;
  cursor: not-allowed;
}
.multi-agent input {
  position: absolute;
  width: 2.15rem;
  height: 1.2rem;
  margin: 0;
  opacity: 0;
  cursor: inherit;
}
.multi-agent > span:last-child {
  display: grid;
  gap: 0.1rem;
}
.multi-agent strong {
  color: var(--content-primary);
  font-size: var(--font-size-sm);
}
.multi-agent small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.multi-agent__switch {
  position: relative;
  width: 2.15rem;
  height: 1.2rem;
  flex: 0 0 auto;
  background: var(--surface-raised);
  border: 1px solid var(--stroke-default);
  border-radius: var(--radius-round);
  pointer-events: none;
}
.multi-agent__switch i {
  position: absolute;
  top: 0.15rem;
  left: 0.16rem;
  width: 0.76rem;
  height: 0.76rem;
  background: var(--content-tertiary);
  border-radius: 50%;
  transition: transform 140ms var(--ease-out-ui), background-color 140ms ease;
}
.multi-agent input:checked + .multi-agent__switch i {
  background: var(--accent-primary);
  transform: translateX(0.88rem);
}
.multi-agent input:focus-visible + .multi-agent__switch {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
.multi-agent > span:last-child {
  pointer-events: none;
}
.chat-composer__input {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.chat-composer__input:focus-within {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}
.chat-composer textarea {
  min-width: 0;
  min-height: 2.75rem;
  padding: var(--space-2);
  resize: none;
  color: var(--content-primary);
  background: transparent;
  border: 0;
  outline: 0;
  line-height: 1.5;
}
.chat-composer__run-control {
  display: flex;
  grid-column: 1 / -1;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--stroke-subtle);
}
.chat-composer__run-control select {
  min-height: 2rem;
  padding: 0 var(--space-3);
  color: var(--content-primary);
  background: var(--surface-canvas);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.chat-composer__footer {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  color: var(--content-tertiary);
}
.chat-composer__footer small {
  font-size: var(--font-size-xs);
}
.chat-composer__footer small:last-child {
  margin-left: auto;
  text-align: right;
}
@media (max-width: 640px) {
  .chat-composer {
    padding-inline: var(--space-3);
  }
  .chat-composer__input {
    grid-template-columns: minmax(0, 1fr);
  }
  .chat-composer__submit {
    width: 100%;
  }
  .chat-composer__run-control {
    flex-wrap: wrap;
  }
  .chat-composer__run-control select {
    flex: 1;
  }
  .chat-composer__footer {
    display: grid;
  }
  .chat-composer__footer small:last-child {
    margin-left: 0;
    text-align: left;
  }
}
@media (prefers-reduced-motion: reduce) {
  .multi-agent__switch i {
    transition: background-color 100ms linear;
  }
}
</style>
