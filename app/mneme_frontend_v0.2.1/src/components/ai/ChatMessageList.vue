<script setup lang="ts">
import { Bot, ChevronDown, MessageSquare, RefreshCw } from "@lucide/vue";
import type { AnswerMode, ChatMessageData } from "../../types";
import UiButton from "../ui/UiButton.vue";
import UiEmptyState from "../ui/UiEmptyState.vue";

defineProps<{
  messages: ChatMessageData[];
  answerMode: AnswerMode;
  pending: boolean;
  formatDate: (value: string | number | Date) => string;
  modeLabel: (value?: string) => string;
}>();

defineEmits<{
  regenerate: [messageId: string, mode: AnswerMode];
}>();
</script>

<template>
  <section class="message-list" aria-label="Conversation">
    <template v-if="messages.length">
      <article
        v-for="(message, index) in messages"
        :key="message.id"
        class="message"
        :class="`message--${message.role}`"
      >
        <div class="message__avatar" aria-hidden="true">
          <component :is="message.role === 'user' ? MessageSquare : Bot" />
        </div>
        <div class="message__body">
          <header class="message__header">
            <span>{{ message.role === "user" ? "You" : "Mneme" }}</span>
            <time :datetime="message.created_at">{{ formatDate(message.created_at) }}</time>
            <span v-if="message.route" data-testid="answer-mode-badge" class="message__mode">
              {{ modeLabel(message.route.query_type) }}
            </span>
          </header>

          <p class="message__content">{{ message.content }}</p>

          <div v-if="message.role === 'assistant'" class="message__meta">
            <span v-if="message.agent_run_id">Run {{ message.agent_run_id }}</span>
            <span v-if="message.confidence !== null">Confidence {{ Math.round(message.confidence * 100) }}%</span>
            <span v-if="message.insufficient_evidence">Insufficient evidence</span>
            <span v-if="message.uncertainty">Uncertainty: {{ message.uncertainty }}</span>
            <UiButton
              v-if="messages[index - 1]?.id"
              variant="ghost"
              size="sm"
              :disabled="pending"
              @click="$emit('regenerate', messages[index - 1].id, answerMode)"
            >
              <template #icon><RefreshCw /></template>
              Regenerate in selected mode
            </UiButton>
          </div>

          <details v-if="message.sources.length" class="message__sources">
            <summary>
              <ChevronDown aria-hidden="true" />
              {{ message.sources.length }} {{ message.sources.length === 1 ? "source" : "sources" }}
            </summary>
            <ul>
              <li
                v-for="source in message.sources"
                :key="source.evidence_id || source.source_id || source.document_id || source.chunk_id"
              >
                <span>{{ source.source_type || "source" }}</span>
                <strong>{{ source.document_id || source.source_id || source.evidence_id }}</strong>
                <time v-if="source.source_time" :datetime="source.source_time">{{ formatDate(source.source_time) }}</time>
              </li>
            </ul>
          </details>
        </div>
      </article>
    </template>
    <UiEmptyState
      v-else
      title="Start a conversation"
      description="Choose an answer mode, then ask a question."
    >
      <template #icon><Bot /></template>
    </UiEmptyState>
  </section>
</template>

<style scoped>
.message-list {
  display: grid;
  width: min(100%, 760px);
  margin: 0 auto;
}
.message {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  gap: var(--space-3);
  padding: var(--space-5) 0;
}
.message + .message {
  border-top: 1px solid var(--stroke-subtle);
}
.message__avatar {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  color: var(--accent-primary);
  background: var(--accent-subtle);
  border-radius: var(--radius-control);
}
.message__avatar svg {
  width: 1rem;
  height: 1rem;
}
.message__body {
  min-width: 0;
}
.message--user .message__body {
  padding: var(--space-3) var(--space-4);
  background: var(--surface-sidebar);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.message__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.message__header > span:first-child {
  color: var(--content-secondary);
  font-weight: 650;
}
.message__mode {
  padding: 0.15rem 0.4rem;
  color: var(--content-secondary);
  background: var(--surface-raised);
  border-radius: var(--radius-round);
  font: 600 0.65rem var(--font-mono);
}
.message__content {
  margin: var(--space-2) 0 0;
  overflow-wrap: anywhere;
  color: var(--content-primary);
  line-height: 1.72;
  white-space: pre-wrap;
}
.message--assistant .message__content {
  font-size: 0.96rem;
}
.message__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
  margin-top: var(--space-3);
  color: var(--content-tertiary);
  font: var(--font-size-xs) var(--font-mono);
}
.message__sources {
  margin-top: var(--space-3);
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.message__sources summary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  cursor: pointer;
}
.message__sources summary svg {
  width: 0.9rem;
  transition: transform var(--duration-fast) var(--ease-out-ui);
}
.message__sources[open] summary svg {
  transform: rotate(180deg);
}
.message__sources ul {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}
.message__sources li {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-sidebar);
  border-left: 2px solid var(--stroke-default);
}
.message__sources li strong {
  color: var(--content-secondary);
  font-family: var(--font-mono);
  font-weight: 500;
}
@media (max-width: 560px) {
  .message {
    grid-template-columns: 1.65rem minmax(0, 1fr);
    padding: var(--space-4) 0;
  }
  .message__avatar {
    width: 1.65rem;
    height: 1.65rem;
  }
  .message--user .message__body {
    padding: var(--space-3);
  }
}
@media (prefers-reduced-motion: reduce) {
  .message__sources summary svg {
    transition: none;
  }
}
</style>
