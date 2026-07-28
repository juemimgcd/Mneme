<script setup lang="ts">
import type { Component } from "vue";
import { BookOpen, BrainCircuit, LifeBuoy, PanelLeft, Plus } from "@lucide/vue";
import { useI18n } from "../../composables/useI18n";
import UiIconButton from "../ui/UiIconButton.vue";

export type ActivityItem = { id: string; label: string; icon: Component };

defineProps<{ items: ActivityItem[]; activeId: string; resourceOpen: boolean; resourceToggleVisible: boolean }>();
const emit = defineEmits<{ navigate: [id: string]; create: []; documentation: []; support: []; toggleResource: [] }>();
const { t } = useI18n();
</script>

<template>
  <aside data-testid="activity-bar" class="activity-bar" :aria-label="t('shell.primaryWorkspace')">
    <div class="activity-bar__brand" aria-label="Mneme"><BrainCircuit class="size-5" /></div>
    <nav class="activity-bar__nav">
      <UiIconButton
        v-if="resourceToggleVisible"
        :label="t('shell.toggleResources')"
        :tooltip="t('shell.resources')"
        tooltip-side="right"
        :active="resourceOpen"
        :aria-expanded="resourceOpen"
        aria-controls="workspace-resource-sidebar"
        @click="emit('toggleResource')"
      ><PanelLeft class="size-4" /></UiIconButton>
      <UiIconButton
        v-for="item in items"
        :key="item.id"
        :label="item.label"
        :tooltip="item.label"
        tooltip-side="right"
        :active="activeId === item.id"
        @click="emit('navigate', item.id)"
      >
        <component :is="item.icon" class="size-[18px]" />
      </UiIconButton>
    </nav>
    <div class="activity-bar__utilities">
      <UiIconButton :label="t('shell.documentation')" :tooltip="t('shell.documentation')" tooltip-side="right" @click="emit('documentation')"><BookOpen class="size-4" /></UiIconButton>
      <UiIconButton :label="t('shell.support')" :tooltip="t('shell.support')" tooltip-side="right" @click="emit('support')"><LifeBuoy class="size-4" /></UiIconButton>
      <UiIconButton :label="t('shell.newResearch')" :tooltip="t('shell.newResearch')" tooltip-side="right" @click="emit('create')"><Plus class="size-4" /></UiIconButton>
    </div>
  </aside>
</template>

<style scoped>
.activity-bar { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; min-height: 100vh; padding: 0.7rem 0.45rem; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.activity-bar__brand { display: grid; place-items: center; width: 2.35rem; height: 2.35rem; margin-bottom: 0.45rem; color: var(--accent); background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 32%, var(--border-muted)); border-radius: 0.55rem; }
.activity-bar__nav { display: grid; flex: 1; align-content: start; gap: 0.3rem; }
.activity-bar__utilities { display: grid; gap: 0.3rem; }
</style>
