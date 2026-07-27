<script setup lang="ts">
import { Check, X } from "@lucide/vue";
import type { MemoryCandidate } from "../../types";
import UiButton from "../ui/UiButton.vue";

defineProps<{
  items: MemoryCandidate[];
  pending: boolean;
}>();
defineEmits<{
  action: [item: MemoryCandidate, action: "confirm" | "reject"];
}>();
</script>

<template>
  <section class="candidate-inbox" aria-labelledby="candidate-inbox-title">
    <header>
      <div>
        <small>Review queue</small>
        <h2 id="candidate-inbox-title">Pending review</h2>
      </div>
      <span>{{ items.length }}</span>
    </header>

    <div class="candidate-inbox__list">
      <article v-for="item in items" :key="item.candidate_id">
        <div>
          <small>{{ item.memory_type }} · {{ Math.round(item.confidence * 100) }}% confidence</small>
          <p>
            <span>{{ item.subject }} {{ item.predicate }}</span>
            <strong>{{ item.value }}</strong>
          </p>
        </div>
        <div class="candidate-inbox__actions">
          <UiButton
            variant="primary"
            size="sm"
            :disabled="pending"
            aria-label="Confirm"
            @click="$emit('action', item, 'confirm')"
          >
            <template #icon><Check /></template>
            Approve
          </UiButton>
          <UiButton variant="ghost" size="sm" :disabled="pending" @click="$emit('action', item, 'reject')">
            <template #icon><X /></template>
            Reject
          </UiButton>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.candidate-inbox {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.candidate-inbox > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.candidate-inbox header small,
.candidate-inbox article small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.candidate-inbox h2 {
  margin: 0.15rem 0 0;
  font-size: var(--font-size-md);
}
.candidate-inbox > header > span {
  display: grid;
  min-width: 1.7rem;
  height: 1.7rem;
  place-items: center;
  color: var(--accent-primary);
  background: var(--accent-subtle);
  border-radius: var(--radius-round);
  font: 600 var(--font-size-xs) var(--font-mono);
}
.candidate-inbox__list {
  display: grid;
  gap: var(--space-2);
}
.candidate-inbox article {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--surface-sidebar);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.candidate-inbox article > div:first-child {
  min-width: 0;
}
.candidate-inbox p {
  display: grid;
  gap: 0.15rem;
  margin: var(--space-1) 0 0;
  overflow-wrap: anywhere;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
}
.candidate-inbox p strong {
  color: var(--content-primary);
}
.candidate-inbox__actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--space-2);
}
@media (max-width: 640px) {
  .candidate-inbox article {
    align-items: stretch;
    flex-direction: column;
  }
  .candidate-inbox__actions > * {
    flex: 1;
  }
}
</style>
