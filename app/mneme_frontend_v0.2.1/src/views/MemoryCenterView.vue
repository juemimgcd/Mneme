<script setup lang="ts">
import { Brain, RefreshCw, ShieldAlert, Trash2 } from "@lucide/vue";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import CandidateInbox from "../components/memory/CandidateInbox.vue";
import MemoryDetail from "../components/memory/MemoryDetail.vue";
import MemoryList from "../components/memory/MemoryList.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
import UiSkeleton from "../components/ui/UiSkeleton.vue";
import UiStatusPanel from "../components/ui/UiStatusPanel.vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useMemoryCenter } from "../composables/useMemoryCenter";
import type { CanonicalMemory, MemoryCandidate } from "../types";
import { useI18n } from "../composables/useI18n";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();
const center = useMemoryCenter(
  props.workspace.token,
  props.workspace.activeKnowledgeBaseId,
  props.workspace.memoryPendingCount,
);

const compactMedia = window.matchMedia("(max-width: 800px)");
const compact = ref(compactMedia.matches);
const mobilePane = ref<"list" | "detail">("list");
const feedback = ref("");
const feedbackTone = ref<"success" | "error">("success");
const saveState = ref<"idle" | "saving" | "success" | "error">("idle");
const saveMessage = ref("");
const purgeKnowledgeBaseOpen = ref(false);
const purgeAccountOpen = ref(false);

const onCompactChange = (event: MediaQueryListEvent) => {
  compact.value = event.matches;
  if (!event.matches) mobilePane.value = "list";
};
compactMedia.addEventListener("change", onCompactChange);
onBeforeUnmount(() => compactMedia.removeEventListener("change", onCompactChange));

watch(props.workspace.activeKnowledgeBaseId, async () => {
  mobilePane.value = "list";
  feedback.value = "";
  await center.load();
});
onMounted(() => center.load());

function reportSuccess(message: string) {
  feedback.value = message;
  feedbackTone.value = "success";
}

function reportError() {
  feedback.value = center.error.value || t("memory.requestFailed");
  feedbackTone.value = "error";
}

async function handleCandidateAction(item: MemoryCandidate, action: "confirm" | "reject") {
  await center.candidateAction(item, action);
  if (center.error.value) reportError();
  else reportSuccess(t(action === "confirm" ? "memory.candidateApproved" : "memory.candidateRejected"));
}

async function handleSelect(memory: CanonicalMemory) {
  await center.select(memory);
  if (!center.error.value && center.detail.value && compact.value) mobilePane.value = "detail";
  else if (center.error.value) reportError();
}

async function handleRevise(value: string) {
  if (!center.detail.value || saveState.value === "saving") return;
  saveState.value = "saving";
  saveMessage.value = "";
  await center.revise(center.detail.value.memory, value);
  if (center.error.value) {
    saveState.value = "error";
    saveMessage.value = center.error.value;
    return;
  }
  saveState.value = "success";
  saveMessage.value = t("memory.revisionSaved");
}

async function handleInvalidate() {
  if (!center.detail.value) return;
  await center.invalidate(center.detail.value.memory);
  if (center.error.value) reportError();
  else {
    mobilePane.value = "list";
    reportSuccess(t("memory.invalidated"));
  }
}

async function handleRemove() {
  if (!center.detail.value) return;
  await center.remove(center.detail.value.memory);
  if (center.error.value) reportError();
  else {
    mobilePane.value = "list";
    reportSuccess(t("memory.deleted"));
  }
}

async function handleSourcePurge(sourceId: string) {
  await center.purge("source", sourceId);
  if (center.error.value) reportError();
  else {
    mobilePane.value = "list";
    reportSuccess(t("memory.sourceCleared"));
  }
}

async function handleSettingsToggle() {
  await center.toggleSettings();
  if (center.error.value) reportError();
  else reportSuccess(
    center.automaticConversationMemory.value
      ? t("memory.learningEnabled")
      : t("memory.learningDisabled"),
  );
}

async function purgeKnowledgeBase() {
  await center.purge("knowledge_base");
  if (center.error.value) reportError();
  else {
    purgeKnowledgeBaseOpen.value = false;
    mobilePane.value = "list";
    reportSuccess(t("memory.knowledgeBaseCleared"));
  }
}

async function purgeAccount() {
  await center.purge("account");
  if (center.error.value) reportError();
  else {
    purgeAccountOpen.value = false;
    mobilePane.value = "list";
    reportSuccess(t("memory.accountCleared"));
  }
}
</script>

<template>
  <div class="memory-center">
    <header class="memory-center__header">
      <div>
        <small>{{ t("memory.kicker") }}</small>
        <div class="memory-center__title">
          <h1>{{ t("nav.memory") }}</h1>
          <span v-if="center.pendingCount.value">{{ t("memory.pendingCount", { count: center.pendingCount.value }) }}</span>
        </div>
      </div>
      <UiButton
        variant="secondary"
        :loading="center.loading.value"
        :disabled="center.pending.value"
        @click="center.load"
      >
        <template #icon><RefreshCw /></template>
        {{ t("memory.refresh") }}
      </UiButton>
    </header>

    <UiStatusPanel
      v-if="center.error.value && !feedback"
      :title="center.error.value"
      tone="error"
    />
    <UiStatusPanel
      v-if="feedback"
      :title="feedback"
      :tone="feedbackTone"
      dismissible
      @dismiss="feedback = ''"
    />

    <div v-if="center.loading.value && !center.detail.value" class="memory-center__loading">
      <UiSkeleton v-for="item in 3" :key="item" height="4rem" />
    </div>

    <template v-else>
      <section class="learning-setting">
        <div>
          <strong>{{ t("memory.automaticLearning") }}</strong>
          <small>{{ t("memory.automaticLearningDescription") }}</small>
        </div>
        <label class="learning-setting__switch">
          <input
            type="checkbox"
            :aria-label="t('memory.automaticLearning')"
            :checked="center.automaticConversationMemory.value"
            :disabled="center.pending.value || center.loading.value"
            @change="handleSettingsToggle"
          />
          <span aria-hidden="true"><i /></span>
        </label>
      </section>

      <CandidateInbox
        v-if="center.candidates.value.length"
        :items="center.candidates.value"
        :pending="center.loading.value || center.pending.value"
        @action="handleCandidateAction"
      />

      <div class="memory-workspace" :data-mobile-pane="mobilePane">
        <section class="memory-library">
          <header>
            <div>
              <small>{{ t("memory.library") }}</small>
              <h2>{{ t("memory.activeMemories") }}</h2>
            </div>
            <span>{{ center.memories.value.length }}</span>
          </header>
          <MemoryList
            v-if="center.memories.value.length"
            :items="center.memories.value"
            :pending="center.pending.value || center.loading.value"
            :selected-id="center.detail.value?.memory.memory_id"
            @select="handleSelect"
          />
          <!-- Canonical state: "No active memories"; localized through memory.emptyTitle. -->
          <UiEmptyState
            v-else
            :title="t('memory.emptyTitle')"
            :description="t('memory.emptyDescription')"
          >
            <template #icon><Brain /></template>
          </UiEmptyState>
        </section>

        <MemoryDetail
          v-if="center.detail.value"
          :detail="center.detail.value"
          :pending="center.loading.value || center.pending.value"
          :save-state="saveState"
          :save-message="saveMessage"
          :show-back="compact"
          @back="mobilePane = 'list'"
          @revise="handleRevise"
          @invalidate="handleInvalidate"
          @remove="handleRemove"
          @purge-source="handleSourcePurge"
        />
        <UiEmptyState
          v-else
          class="memory-workspace__placeholder"
          :title="t('memory.selectTitle')"
          :description="t('memory.selectDescription')"
        >
          <template #icon><Brain /></template>
        </UiEmptyState>
      </div>

      <section class="danger-zone">
        <header>
          <div>
            <small>{{ t("memory.destructiveControls") }}</small>
            <h2>{{ t("memory.dangerZone") }}</h2>
          </div>
          <ShieldAlert aria-hidden="true" />
        </header>
        <p>{{ t("memory.dangerDescription") }}</p>
        <div>
          <UiButton
            variant="danger"
            :disabled="center.pending.value || !workspace.activeKnowledgeBaseId.value"
            @click="purgeKnowledgeBaseOpen = true"
          >
            <template #icon><Trash2 /></template>
            {{ t("memory.clearKnowledgeBase") }}
          </UiButton>
          <UiButton variant="danger" :disabled="center.pending.value" @click="purgeAccountOpen = true">
            <template #icon><Trash2 /></template>
            {{ t("memory.clearAccount") }}
          </UiButton>
        </div>
      </section>
    </template>
  </div>

  <UiDialog
    v-model="purgeKnowledgeBaseOpen"
    :title="t('memory.clearKnowledgeBaseTitle')"
    :description="t('memory.clearKnowledgeBaseDescription')"
    :confirm-label="t('memory.clearKnowledgeBase')"
    confirm-variant="danger"
    :busy="center.pending.value"
    @confirm="purgeKnowledgeBase"
  />
  <UiDialog
    v-model="purgeAccountOpen"
    :title="t('memory.clearAccountTitle')"
    :description="t('memory.clearAccountDescription')"
    :confirm-label="t('memory.clearAccount')"
    confirm-variant="danger"
    :busy="center.pending.value"
    @confirm="purgeAccount"
  />
</template>

<style scoped>
.memory-center {
  display: grid;
  width: min(100%, 1200px);
  gap: var(--space-5);
  margin: 0 auto;
  padding: var(--space-5);
  color: var(--content-primary);
}
.memory-center__header,
.memory-center__title,
.learning-setting,
.memory-library > header,
.danger-zone > header {
  display: flex;
  align-items: center;
}
.memory-center__header,
.learning-setting,
.memory-library > header,
.danger-zone > header {
  justify-content: space-between;
  gap: var(--space-4);
}
.memory-center__header > div {
  min-width: 0;
}
.memory-center__header > div > small,
.memory-library header small,
.danger-zone header small {
  color: var(--content-tertiary);
  font: 600 var(--font-size-xs) var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.memory-center__title {
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: 0.15rem;
}
.memory-center h1 {
  margin: 0;
  font: 650 1.55rem var(--font-serif);
}
.memory-center__title span,
.memory-library header > span {
  padding: 0.2rem 0.5rem;
  color: var(--accent-primary);
  background: var(--accent-subtle);
  border-radius: var(--radius-round);
  font: 600 var(--font-size-xs) var(--font-mono);
}
.memory-center__loading {
  display: grid;
  gap: var(--space-3);
}
.learning-setting {
  padding: var(--space-4);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.learning-setting > div {
  display: grid;
  gap: var(--space-1);
}
.learning-setting strong {
  font-size: var(--font-size-sm);
}
.learning-setting small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.learning-setting__switch {
  position: relative;
  flex: 0 0 auto;
  cursor: pointer;
}
.learning-setting__switch input {
  position: absolute;
  width: 2.4rem;
  height: 1.35rem;
  margin: 0;
  opacity: 0;
}
.learning-setting__switch > span:first-of-type {
  position: relative;
  display: block;
  width: 2.4rem;
  height: 1.35rem;
  background: var(--surface-raised);
  border: 1px solid var(--stroke-default);
  border-radius: var(--radius-round);
}
.learning-setting__switch i {
  position: absolute;
  top: 0.17rem;
  left: 0.18rem;
  width: 0.85rem;
  height: 0.85rem;
  background: var(--content-tertiary);
  border-radius: 50%;
  transition: transform 140ms var(--ease-out-ui), background-color 140ms ease;
}
.learning-setting__switch input:checked + span i {
  background: var(--accent-primary);
  transform: translateX(1rem);
}
.learning-setting__switch input:focus-visible + span {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
.learning-setting__switch:has(input:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}
.memory-workspace {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(380px, 1.2fr);
  align-items: start;
  gap: var(--space-4);
}
.memory-library {
  display: grid;
  gap: var(--space-3);
}
.memory-library h2,
.danger-zone h2 {
  margin: 0.15rem 0 0;
  font-size: var(--font-size-md);
}
.memory-workspace__placeholder {
  min-height: 16rem;
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.danger-zone {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  background: color-mix(in srgb, var(--status-danger) 4%, var(--surface-panel));
  border: 1px solid color-mix(in srgb, var(--status-danger) 30%, var(--stroke-subtle));
  border-radius: var(--radius-panel);
}
.danger-zone header > svg {
  width: 1.2rem;
  height: 1.2rem;
  color: var(--status-danger);
}
.danger-zone p {
  margin: 0;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
}
.danger-zone > div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
@media (max-width: 800px) {
  .memory-center {
    padding: var(--space-4);
  }
  .memory-workspace {
    display: block;
  }
  .memory-workspace[data-mobile-pane="list"] > :not(.memory-library),
  .memory-workspace[data-mobile-pane="detail"] > .memory-library {
    display: none;
  }
}
@media (max-width: 560px) {
  .memory-center__header,
  .learning-setting {
    align-items: flex-start;
  }
  .memory-center__header {
    flex-wrap: wrap;
  }
  .danger-zone > div {
    display: grid;
  }
}
@media (prefers-reduced-motion: reduce) {
  .learning-setting__switch i {
    transition: background-color 100ms linear;
  }
}
</style>
