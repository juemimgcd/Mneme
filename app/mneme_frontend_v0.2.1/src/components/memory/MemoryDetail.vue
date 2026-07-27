<script setup lang="ts">
import { ArrowLeft, Ban, Save, ShieldAlert, Trash2 } from "@lucide/vue";
import { ref, watch } from "vue";
import type { MemoryDetail } from "../../types";
import UiButton from "../ui/UiButton.vue";
import UiDialog from "../ui/UiDialog.vue";
import UiStatusPanel from "../ui/UiStatusPanel.vue";

const props = withDefaults(defineProps<{
  detail: MemoryDetail;
  pending: boolean;
  saveState: "idle" | "saving" | "success" | "error";
  saveMessage?: string;
  showBack?: boolean;
}>(), {
  saveMessage: "",
  showBack: false,
});
const emit = defineEmits<{
  back: [];
  revise: [value: string];
  invalidate: [];
  remove: [];
  purgeSource: [id: string];
}>();

const value = ref(props.detail.memory.value);
const invalidateOpen = ref(false);
const removeOpen = ref(false);
const purgeSourceOpen = ref(false);
const pendingSourceId = ref("");

watch(
  () => props.detail.memory.value,
  (nextValue) => {
    value.value = nextValue;
  },
);

function requestSourcePurge(sourceId: string) {
  pendingSourceId.value = sourceId;
  purgeSourceOpen.value = true;
}

function confirmSourcePurge() {
  if (!pendingSourceId.value) return;
  emit("purgeSource", pendingSourceId.value);
}
</script>

<template>
  <article class="memory-detail">
    <header class="memory-detail__header">
      <div>
        <UiButton v-if="showBack" variant="ghost" size="sm" @click="emit('back')">
          <template #icon><ArrowLeft /></template>
          All memories
        </UiButton>
        <small>{{ detail.memory.memory_type }} · {{ detail.memory.status }}</small>
        <h2>{{ detail.memory.subject }} {{ detail.memory.predicate }}</h2>
      </div>
      <strong>{{ Math.round(detail.memory.confidence * 100) }}%</strong>
    </header>

    <section class="memory-detail__editor">
      <div>
        <h3>Memory value</h3>
        <small>Editing creates a new audited revision.</small>
      </div>
      <textarea v-model="value" aria-label="Memory value" />
      <UiStatusPanel
        v-if="saveState === 'success' || saveState === 'error'"
        :title="saveMessage"
        :tone="saveState === 'success' ? 'success' : 'error'"
      />
      <div class="memory-detail__actions">
        <UiButton
          variant="primary"
          :loading="saveState === 'saving'"
          :disabled="pending || !value.trim() || value === detail.memory.value"
          @click="emit('revise', value)"
        >
          <template #icon><Save /></template>
          Save revision
        </UiButton>
        <UiButton variant="secondary" :disabled="pending" @click="invalidateOpen = true">
          <template #icon><Ban /></template>
          Invalidate
        </UiButton>
        <UiButton variant="danger" :disabled="pending" @click="removeOpen = true">
          <template #icon><Trash2 /></template>
          Hard delete
        </UiButton>
      </div>
    </section>

    <section class="memory-detail__section">
      <h3>Revision history</h3>
      <ol class="revision-list">
        <li v-for="revision in detail.revisions" :key="revision.revision_id">
          <strong>{{ revision.value }}</strong>
          <small>
            {{ new Date(revision.valid_from).toLocaleString() }}
            <template v-if="revision.valid_to"> – {{ new Date(revision.valid_to).toLocaleString() }}</template>
            · {{ revision.reason }}
          </small>
        </li>
      </ol>
    </section>

    <section class="memory-detail__section">
      <h3>Evidence</h3>
      <ul class="evidence-list">
        <li v-for="evidence in detail.evidence" :key="evidence.evidence_id">
          <small>{{ evidence.source_type }} · {{ new Date(evidence.source_time).toLocaleString() }}</small>
          <p>{{ evidence.excerpt }}</p>
          <UiButton
            variant="danger"
            size="sm"
            :disabled="pending"
            @click="requestSourcePurge(evidence.source_document_id || evidence.source_id)"
          >
            <template #icon><ShieldAlert /></template>
            Clear this source
          </UiButton>
        </li>
      </ul>
    </section>
  </article>

  <UiDialog
    v-model="invalidateOpen"
    title="Invalidate this memory?"
    description="The memory will stop influencing future answers, while its revision and evidence history remain available for audit."
    confirm-label="Invalidate memory"
    confirm-variant="secondary"
    :busy="pending"
    @confirm="emit('invalidate')"
  />
  <UiDialog
    v-model="removeOpen"
    title="Hard delete this memory?"
    description="This permanently removes the memory and every revision. This action cannot be undone."
    confirm-label="Hard delete"
    confirm-variant="danger"
    :busy="pending"
    @confirm="emit('remove')"
  />
  <UiDialog
    v-model="purgeSourceOpen"
    title="Clear memories from this source?"
    description="All governed memories backed by this owned source will be permanently removed. This action cannot be undone."
    confirm-label="Clear source"
    confirm-variant="danger"
    :busy="pending"
    @confirm="confirmSourcePurge"
  />
</template>

<style scoped>
.memory-detail {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.memory-detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.memory-detail__header > div {
  min-width: 0;
}
.memory-detail__header small,
.memory-detail__section small,
.memory-detail__editor small {
  display: block;
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.memory-detail__header h2 {
  margin: var(--space-2) 0 0;
  overflow-wrap: anywhere;
  font-size: var(--font-size-lg);
}
.memory-detail__header > strong {
  color: var(--accent-primary);
  font: 650 var(--font-size-md) var(--font-mono);
}
.memory-detail__editor {
  display: grid;
  gap: var(--space-3);
}
.memory-detail h3 {
  margin: 0;
  color: var(--content-primary);
  font-size: var(--font-size-sm);
}
.memory-detail__editor textarea {
  width: 100%;
  min-height: 6rem;
  padding: var(--space-3);
  resize: vertical;
  color: var(--content-primary);
  background: var(--surface-canvas);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
  line-height: 1.6;
}
.memory-detail__editor textarea:focus-visible {
  border-color: var(--accent-primary);
  outline: 0;
  box-shadow: 0 0 0 3px var(--accent-subtle);
}
.memory-detail__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.memory-detail__section {
  display: grid;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--stroke-subtle);
}
.revision-list,
.evidence-list {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}
.revision-list li,
.evidence-list li {
  padding: var(--space-3);
  background: var(--surface-sidebar);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.revision-list strong {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--content-primary);
  font-size: var(--font-size-sm);
}
.evidence-list p {
  margin: var(--space-2) 0 var(--space-3);
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}
@media (max-width: 640px) {
  .memory-detail {
    padding: var(--space-4);
  }
  .memory-detail__actions {
    display: grid;
  }
}
</style>
