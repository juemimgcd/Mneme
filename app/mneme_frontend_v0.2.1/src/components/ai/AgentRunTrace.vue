<script setup lang="ts">
import { AlertTriangle, CheckCircle2, Circle, LoaderCircle } from "@lucide/vue";
import { computed } from "vue";
import type { AgentRunTraceItem, AgentStreamConnectionState } from "../../types";

const props = defineProps<{
  items: AgentRunTraceItem[];
  progress: string;
  streamState: AgentStreamConnectionState;
}>();

const currentIndex = computed(() => {
  let active = -1;
  for (let index = props.items.length - 1; index >= 0; index -= 1) {
    if (props.items[index].state === "active") {
      active = index;
      break;
    }
  }
  return active >= 0 ? active : Math.max(0, props.items.length - 1);
});
const currentItem = computed(() => props.items[currentIndex.value]);
const completedCount = computed(() => props.items.filter((item) => item.state === "complete").length);
const iconFor = (state: AgentRunTraceItem["state"]) =>
  state === "complete" ? CheckCircle2 : state === "warning" ? AlertTriangle : LoaderCircle;
</script>

<template>
  <aside data-testid="agent-run-trace" class="run-trace" aria-live="polite">
    <header>
      <div class="run-trace__heading">
        <component :is="currentItem ? iconFor(currentItem.state) : Circle" aria-hidden="true" />
        <div>
          <strong>{{ currentItem?.label || progress || "Preparing run" }}</strong>
          <small>{{ completedCount }} of {{ items.length }} steps complete</small>
        </div>
      </div>
      <span :data-state="streamState">{{ streamState }}</span>
    </header>

    <div class="run-trace__meter" aria-hidden="true">
      <i :style="{ transform: `scaleX(${items.length ? Math.max(0.08, completedCount / items.length) : 0.08})` }" />
    </div>

    <details v-if="items.length > 1">
      <summary>Show run history</summary>
      <ol>
        <li v-for="item in items" :key="item.id" :data-state="item.state">
          <component :is="iconFor(item.state)" aria-hidden="true" />
          <span>{{ item.label }}</span>
          <small v-if="item.sequence">#{{ item.sequence }}</small>
        </li>
      </ol>
    </details>
  </aside>
</template>

<style scoped>
.run-trace {
  width: min(100%, 760px);
  margin: var(--space-3) auto var(--space-5);
  padding: var(--space-4);
  background: var(--surface-sidebar);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.run-trace header,
.run-trace__heading {
  display: flex;
  align-items: center;
}
.run-trace header {
  justify-content: space-between;
  gap: var(--space-3);
}
.run-trace__heading {
  min-width: 0;
  gap: var(--space-3);
}
.run-trace__heading > svg {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  color: var(--accent-primary);
}
.run-trace__heading > div {
  display: grid;
  min-width: 0;
  gap: 0.1rem;
}
.run-trace strong {
  overflow: hidden;
  color: var(--content-primary);
  font-size: var(--font-size-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-trace small {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.run-trace header > span {
  flex: 0 0 auto;
  padding: 0.18rem 0.45rem;
  color: var(--content-tertiary);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-round);
  font: 600 0.62rem var(--font-mono);
  text-transform: uppercase;
  transition: color var(--duration-fast) ease, border-color var(--duration-fast) ease, opacity var(--duration-fast) ease;
}
.run-trace header > span[data-state="streaming"],
.run-trace header > span[data-state="completed"] {
  color: var(--status-success);
  border-color: color-mix(in srgb, var(--status-success) 40%, var(--stroke-subtle));
}
.run-trace header > span[data-state="reconnecting"],
.run-trace header > span[data-state="failed"] {
  color: var(--status-danger);
}
.run-trace__meter {
  height: 2px;
  margin-top: var(--space-3);
  overflow: hidden;
  background: var(--stroke-subtle);
}
.run-trace__meter i {
  display: block;
  width: 100%;
  height: 100%;
  background: var(--accent-primary);
  transform-origin: left;
  transition: transform 180ms var(--ease-out-ui);
}
.run-trace details {
  margin-top: var(--space-3);
}
.run-trace summary {
  color: var(--content-secondary);
  font-size: var(--font-size-xs);
  cursor: pointer;
}
.run-trace ol {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
  padding: 0;
  list-style: none;
}
.run-trace li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-2);
  color: var(--content-secondary);
  font-size: var(--font-size-xs);
  transition: color var(--duration-fast) ease, opacity var(--duration-fast) ease;
}
.run-trace li > svg {
  width: 0.9rem;
  height: 0.9rem;
  color: var(--status-success);
}
.run-trace li[data-state="active"] > svg {
  color: var(--accent-primary);
}
.run-trace li[data-state="warning"] > svg {
  color: var(--status-warning);
}
@media (prefers-reduced-motion: reduce) {
  .run-trace__meter i {
    transition: none;
  }
}
</style>
