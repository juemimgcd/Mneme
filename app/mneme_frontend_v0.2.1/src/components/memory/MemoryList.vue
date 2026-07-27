<script setup lang="ts">
import { ChevronRight } from "@lucide/vue";
import type { CanonicalMemory } from "../../types";

defineProps<{
  items: CanonicalMemory[];
  selectedId?: string;
  pending: boolean;
}>();
defineEmits<{ select: [memory: CanonicalMemory] }>();
</script>

<template>
  <div class="memory-list" aria-label="Active memories">
    <button
      v-for="item in items"
      :key="item.memory_id"
      type="button"
      :class="{ active: item.memory_id === selectedId }"
      :aria-current="item.memory_id === selectedId ? 'true' : undefined"
      :disabled="pending"
      @click="$emit('select', item)"
    >
      <span class="memory-list__copy">
        <small>{{ item.memory_type }} · {{ Math.round(item.confidence * 100) }}%</small>
        <strong>{{ item.subject }} {{ item.predicate }}</strong>
        <span>{{ item.value }}</span>
      </span>
      <ChevronRight aria-hidden="true" />
    </button>
  </div>
</template>

<style scoped>
.memory-list {
  display: grid;
  gap: var(--space-2);
}
.memory-list button {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  color: var(--content-primary);
  text-align: left;
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
  transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, border-color var(--duration-fast) ease;
}
.memory-list__copy {
  display: grid;
  min-width: 0;
  gap: 0.25rem;
}
.memory-list small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.memory-list strong {
  overflow: hidden;
  font-size: var(--font-size-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.memory-list__copy > span {
  display: -webkit-box;
  overflow: hidden;
  color: var(--content-secondary);
  font-size: var(--font-size-xs);
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.memory-list svg {
  width: 1rem;
  height: 1rem;
  color: var(--content-tertiary);
}
.memory-list button.active {
  border-color: color-mix(in srgb, var(--accent-primary) 48%, var(--stroke-subtle));
  background: var(--surface-selected);
  box-shadow: inset 2px 0 var(--accent-primary);
}
.memory-list button:disabled {
  opacity: 0.55;
}
@media (hover: hover) and (pointer: fine) {
  .memory-list button:hover:not(:disabled):not(.active) {
    background: var(--surface-raised);
    border-color: var(--stroke-default);
  }
}
</style>
