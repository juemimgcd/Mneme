<script setup lang="ts">
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Database,
  Globe2,
  Moon,
  RefreshCw,
  Sun,
  Workflow,
} from "@lucide/vue";
import { computed, ref, watch } from "vue";
import ChannelGatewayPanel from "../components/channels/ChannelGatewayPanel.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiSegmentedControl, { type UiSegmentedOption } from "../components/ui/UiSegmentedControl.vue";
import UiStatusPanel from "../components/ui/UiStatusPanel.vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";
import { usePreferences, type Locale, type ThemeMode } from "../composables/usePreferences";

const props = defineProps<{
  workspace: MnemeWorkspace;
  healthLabel: string;
  formatDate: (value: string | number | Date) => string;
}>();

const preferences = usePreferences();
const { t } = useI18n();
const contextWindow = ref(32);
const activeSection = ref("appearance");
const modelPendingTarget = ref("");
const modelFeedback = ref<{ target: string; message: string; tone: "success" | "error" } | null>(null);
const syncFeedback = ref<{ target: "graph" | "memory"; message: string; tone: "success" | "error" } | null>(null);

const sections = computed(() => [
  { id: "appearance", label: t("settings.appearance") },
  { id: "channels", label: t("settings.channels") },
  { id: "models", label: t("settings.models") },
  { id: "sync", label: t("settings.sync") },
  { id: "health", label: t("settings.health") },
]);
const themeOptions = computed<UiSegmentedOption[]>(() => [
  { value: "system", label: t("settings.theme.system"), ariaLabel: t("settings.theme.systemLabel"), icon: Globe2 },
  { value: "light", label: t("settings.theme.light"), ariaLabel: t("settings.theme.lightLabel"), icon: Sun },
  { value: "dark", label: t("settings.theme.dark"), ariaLabel: t("settings.theme.darkLabel"), icon: Moon },
]);
const localeOptions = computed<UiSegmentedOption[]>(() => [
  { value: "en-US", label: t("settings.language.english") },
  { value: "zh-CN", label: t("settings.language.chinese") },
]);
const themeModel = computed({
  get: () => preferences.themeMode.value,
  set: (value: string) => preferences.setThemeMode(value as ThemeMode),
});
const localeModel = computed({
  get: () => preferences.locale.value,
  set: (value: string) => preferences.setLocale(value as Locale),
});
const activeConfig = computed(() =>
  props.workspace.aiModelConfigs.value.find((config) => config.id === props.workspace.activeAiModelConfigId.value)
  ?? props.workspace.aiModelConfigs.value.find((config) => config.is_default),
);
const healthTone = computed(() =>
  ["ready", "healthy", "ok", "preview"].includes(props.healthLabel.toLowerCase()) ? "ready" : "degraded",
);

watch(
  () => activeConfig.value?.context_window,
  (value) => {
    if (value) contextWindow.value = Math.round(value / 1000);
  },
  { immediate: true },
);

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

async function runModelAction(target: string, action: () => Promise<void>) {
  if (modelPendingTarget.value) return;
  modelPendingTarget.value = target;
  modelFeedback.value = null;
  try {
    await action();
    modelFeedback.value = {
      target,
      message: props.workspace.aiModelActionStatus.value,
      tone: "success",
    };
  } catch (error) {
    modelFeedback.value = { target, message: errorMessage(error), tone: "error" };
  } finally {
    modelPendingTarget.value = "";
  }
}

async function runSyncAction(target: "graph" | "memory", action: () => Promise<void>) {
  if (props.workspace.syncBusyTarget.value) return;
  syncFeedback.value = null;
  try {
    await action();
    syncFeedback.value = {
      target,
      message: props.workspace.syncStatus.value,
      tone: "success",
    };
  } catch (error) {
    syncFeedback.value = { target, message: errorMessage(error), tone: "error" };
  }
}

function jumpToSection(sectionId: string) {
  activeSection.value = sectionId;
  document.getElementById(sectionId)?.scrollIntoView({ block: "start" });
}
</script>

<template>
  <div data-testid="stitch-settings-layout" class="settings-layout">
    <aside class="settings-section-nav">
      <small>{{ t("settings.preferences") }}</small>
      <nav :aria-label="t('settings.navigation')">
        <a v-for="section in sections" :key="section.id" :href="`#${section.id}`">
          {{ section.label }}
        </a>
      </nav>
      <label class="settings-section-select">
        <span>{{ t("settings.navigation") }}</span>
        <select v-model="activeSection" @change="jumpToSection(activeSection)">
          <option v-for="section in sections" :key="section.id" :value="section.id">
            {{ section.label }}
          </option>
        </select>
      </label>
    </aside>

    <main class="settings-content">
      <section id="appearance" class="settings-section">
        <header class="settings-section__header">
          <small>{{ t("settings.appearance") }}</small>
          <h2>{{ t("settings.appearanceDescription") }}</h2>
        </header>
        <div class="settings-rows">
          <div class="setting-row">
            <div>
              <strong>{{ t("settings.theme") }}</strong>
              <p>{{ t("settings.themeDescription") }}</p>
            </div>
            <UiSegmentedControl
              v-model="themeModel"
              class="setting-row__control"
              :options="themeOptions"
              :ariaLabel="t('settings.theme')"
              size="sm"
            />
          </div>
          <div class="setting-row">
            <div>
              <strong>{{ t("settings.language") }}</strong>
              <p>{{ t("settings.languageDescription") }}</p>
            </div>
            <UiSegmentedControl
              v-model="localeModel"
              class="setting-row__control"
              :options="localeOptions"
              :ariaLabel="t('settings.language')"
              size="sm"
            />
          </div>
        </div>
      </section>

      <ChannelGatewayPanel :workspace="workspace" :format-date="formatDate" />

      <section id="models" class="settings-section">
        <header class="settings-section__header">
          <small>{{ t("settings.intelligence") }}</small>
          <h2>{{ t("settings.modelConfiguration") }}</h2>
          <p>{{ t("settings.modelsDescription") }}</p>
        </header>

        <div class="model-grid">
          <article
            v-for="config in workspace.aiModelConfigs.value"
            :key="config.id"
            class="model-card"
            :class="{ 'model-card--selected': config.is_default }"
          >
            <header>
              <div>
                <strong>{{ config.label }}</strong>
                <span v-if="config.is_default"><CheckCircle2 />{{ t("settings.default") }}</span>
              </div>
              <BrainCircuit aria-hidden="true" />
            </header>
            <p>{{ config.provider }} / {{ config.model_name }}</p>
            <code>{{ config.base_url }}</code>
            <footer>
              <UiButton
                size="sm"
                :loading="modelPendingTarget === `model:${config.id}`"
                :disabled="!!modelPendingTarget"
                :aria-label="t('settings.testModel', { name: config.label })"
                @click="runModelAction(`model:${config.id}`, () => workspace.testAiModelConfig(config.id))"
              >
                {{ t("settings.test") }}
              </UiButton>
              <UiButton
                v-if="!config.is_default"
                variant="ghost"
                size="sm"
                :disabled="!!modelPendingTarget"
                :aria-label="t('settings.setModelDefault', { name: config.label })"
                @click="runModelAction(`model:${config.id}`, () => workspace.setDefaultAiModelConfig(config.id))"
              >
                {{ t("settings.setDefault") }}
              </UiButton>
            </footer>
            <UiStatusPanel
              v-if="modelFeedback?.target === `model:${config.id}`"
              :title="modelFeedback.message"
              :tone="modelFeedback.tone"
            />
          </article>
        </div>

        <div class="settings-rows settings-rows--spaced">
          <div class="setting-row">
            <div>
              <strong>{{ t("settings.contextWindow") }}</strong>
              <p>{{ t("settings.contextWindowDescription") }}</p>
            </div>
            <div class="context-control">
              <output>{{ (contextWindow * 1000).toLocaleString() }}</output>
              <input v-model.number="contextWindow" type="range" min="8" max="128" />
              <UiButton
                size="sm"
                :loading="modelPendingTarget === 'context'"
                :disabled="!!modelPendingTarget"
                @click="runModelAction('context', () => workspace.updateActiveModelContextWindow(contextWindow * 1000))"
              >
                {{ t("settings.saveContextWindow") }}
              </UiButton>
              <UiStatusPanel
                v-if="modelFeedback?.target === 'context'"
                :title="modelFeedback.message"
                :tone="modelFeedback.tone"
              />
            </div>
          </div>
        </div>
      </section>

      <section id="sync" class="settings-section">
        <header class="settings-section__header">
          <small>{{ t("settings.storage") }}</small>
          <h2>{{ t("settings.sync") }}</h2>
          <p>{{ t("settings.syncDescription") }}</p>
        </header>
        <div class="settings-rows">
          <div class="setting-row">
            <div>
              <strong>{{ t("settings.graphSync") }}</strong>
              <p>{{ t("settings.graphSyncDescription") }}</p>
            </div>
            <div class="setting-action">
              <UiButton
                :loading="workspace.syncBusyTarget.value === 'graph'"
                :disabled="!!workspace.syncBusyTarget.value"
                @click="runSyncAction('graph', workspace.rebuildActiveGraph)"
              >
                <template #icon><RefreshCw /></template>
                {{ t("settings.rebuildGraph") }}
              </UiButton>
              <UiStatusPanel
                v-if="syncFeedback?.target === 'graph'"
                :title="syncFeedback.message"
                :tone="syncFeedback.tone"
              />
            </div>
          </div>
          <div class="setting-row">
            <div>
              <strong>{{ t("settings.memorySync") }}</strong>
              <p>{{ t("settings.memorySyncDescription") }}</p>
            </div>
            <div class="setting-action">
              <UiButton
                :loading="workspace.syncBusyTarget.value === 'memory'"
                :disabled="!!workspace.syncBusyTarget.value"
                @click="runSyncAction('memory', workspace.rebuildActiveMemory)"
              >
                <template #icon><Database /></template>
                {{ t("settings.rebuildMemory") }}
              </UiButton>
              <UiStatusPanel
                v-if="syncFeedback?.target === 'memory'"
                :title="syncFeedback.message"
                :tone="syncFeedback.tone"
              />
            </div>
          </div>
        </div>
      </section>

      <section id="health" class="settings-section" data-testid="insights-function-grid">
        <header class="settings-section__header settings-section__header--status">
          <div>
            <small>{{ t("settings.system") }}</small>
            <h2>{{ t("settings.graphHealth") }}</h2>
            <p>{{ t("settings.healthDescription") }}</p>
          </div>
          <span class="health-state" :data-tone="healthTone">
            <CheckCircle2 v-if="healthTone === 'ready'" />
            <AlertTriangle v-else />
            {{ healthLabel }}
          </span>
        </header>
        <div data-testid="insights-output-workspace" class="health-rows">
          <div><span>{{ t("settings.nodes") }}</span><strong>{{ workspace.graphData.value?.nodes.length ?? 0 }}</strong></div>
          <div><span>{{ t("settings.edges") }}</span><strong>{{ workspace.graphData.value?.edges.length ?? 0 }}</strong></div>
          <div><span>{{ t("settings.backend") }}</span><strong>{{ workspace.neo4jHealth.value?.backend ?? "pending" }}</strong></div>
          <div><span>{{ t("settings.readiness") }}</span><strong>{{ workspace.readiness.value?.overall_status ?? "loading" }}</strong></div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.settings-layout {
  display: grid;
  width: min(100%, 1120px);
  min-width: 0;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: clamp(1.5rem, 4vw, 3rem);
  margin: 0 auto;
  padding: var(--space-6);
  color: var(--content-primary);
}
.settings-section-nav {
  position: sticky;
  top: var(--space-4);
  min-width: 0;
  height: fit-content;
}
.settings-section-nav > small,
.settings-section__header > small,
.settings-section__header > div > small {
  color: var(--content-tertiary);
  font: 600 var(--font-size-xs) var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.settings-section-nav nav {
  display: grid;
  gap: var(--space-1);
  margin-top: var(--space-3);
}
.settings-section-nav a {
  padding: var(--space-2) var(--space-3);
  color: var(--content-secondary);
  border-radius: var(--radius-control);
  text-decoration: none;
}
.settings-section-select {
  display: none;
}
.settings-content {
  display: grid;
  min-width: 0;
  gap: clamp(2.5rem, 6vw, 4.5rem);
}
.settings-section {
  min-width: 0;
  scroll-margin-top: var(--space-5);
}
.settings-section__header {
  margin-bottom: var(--space-4);
}
.settings-section__header h2 {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-lg);
  line-height: var(--line-height-tight);
}
.settings-section__header p {
  max-width: 42rem;
  margin: var(--space-2) 0 0;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-body);
}
.settings-rows {
  border-top: 1px solid var(--stroke-subtle);
}
.settings-rows--spaced {
  margin-top: var(--space-5);
}
.setting-row {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(10rem, 0.8fr) minmax(18rem, 1.2fr);
  align-items: start;
  gap: var(--space-5);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--stroke-subtle);
}
.setting-row > div:first-child {
  min-width: 0;
}
.setting-row strong {
  font-size: var(--font-size-sm);
}
.setting-row p {
  margin: var(--space-1) 0 0;
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
  line-height: 1.55;
}
.setting-row__control {
  width: 100%;
}
.setting-row__control :deep(.ui-segmented__option) {
  flex: 1;
}
.model-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}
.model-card {
  display: grid;
  min-width: 0;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-panel);
}
.model-card--selected {
  border-color: color-mix(in srgb, var(--accent-primary) 48%, var(--stroke-subtle));
}
.model-card > header,
.model-card > header > div,
.model-card footer {
  display: flex;
  align-items: center;
}
.model-card > header {
  justify-content: space-between;
  gap: var(--space-3);
}
.model-card > header > div {
  min-width: 0;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.model-card > header > svg {
  width: 1rem;
  color: var(--content-tertiary);
}
.model-card header span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--accent-primary);
  font-size: var(--font-size-xs);
}
.model-card header span svg {
  width: 0.85rem;
}
.model-card > p {
  margin: 0;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
}
.model-card > code {
  overflow-wrap: anywhere;
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.model-card footer {
  gap: var(--space-2);
}
.context-control,
.setting-action {
  display: grid;
  gap: var(--space-3);
}
.context-control {
  grid-template-columns: auto minmax(8rem, 1fr) auto;
  align-items: center;
}
.context-control output {
  min-width: 4.5rem;
  color: var(--content-secondary);
  font: 600 var(--font-size-sm) var(--font-mono);
}
.context-control input {
  accent-color: var(--accent-primary);
}
.context-control :deep(.ui-status),
.setting-action :deep(.ui-status) {
  grid-column: 1 / -1;
}
.setting-action {
  justify-items: start;
}
.settings-section__header--status {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
.health-state {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  color: var(--status-warning);
  background: color-mix(in srgb, var(--status-warning) 8%, var(--surface-sidebar));
  border: 1px solid color-mix(in srgb, var(--status-warning) 30%, var(--stroke-subtle));
  border-radius: var(--radius-round);
  font: 600 var(--font-size-xs) var(--font-mono);
}
.health-state[data-tone="ready"] {
  color: var(--status-success);
  background: color-mix(in srgb, var(--status-success) 8%, var(--surface-sidebar));
  border-color: color-mix(in srgb, var(--status-success) 30%, var(--stroke-subtle));
}
.health-state svg {
  width: 0.9rem;
  height: 0.9rem;
}
.health-rows {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-block: 1px solid var(--stroke-subtle);
}
.health-rows > div {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border-right: 1px solid var(--stroke-subtle);
}
.health-rows > div:last-child {
  border-right: 0;
}
.health-rows span {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.health-rows strong {
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (hover: hover) and (pointer: fine) {
  .settings-section-nav a:hover {
    color: var(--content-primary);
    background: var(--surface-raised);
  }
}
@media (max-width: 900px) {
  .settings-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-5);
    padding: var(--space-4);
  }
  .settings-section-nav {
    top: 0;
    z-index: 8;
    padding: var(--space-2);
    background: color-mix(in srgb, var(--surface-canvas) 94%, transparent);
    border-bottom: 1px solid var(--stroke-subtle);
    backdrop-filter: blur(12px);
  }
  .settings-section-nav > small {
    display: none;
  }
  .settings-section-nav nav {
    display: flex;
    gap: var(--space-1);
    margin: 0;
    overflow-x: auto;
  }
  .settings-section-nav a {
    flex: 0 0 auto;
    white-space: nowrap;
  }
}
@media (max-width: 640px) {
  .settings-section-nav nav {
    display: none;
  }
  .settings-section-select {
    display: grid;
    gap: var(--space-1);
  }
  .settings-section-select span {
    color: var(--content-tertiary);
    font-size: var(--font-size-xs);
  }
  .settings-section-select select {
    width: 100%;
  }
  .settings-content {
    gap: var(--space-6);
  }
  .setting-row,
  .model-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .setting-row {
    gap: var(--space-3);
  }
  .context-control {
    grid-template-columns: minmax(0, 1fr);
  }
  .context-control :deep(.ui-button),
  .setting-action :deep(.ui-button) {
    width: 100%;
  }
  .health-rows {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .health-rows > div:nth-child(2) {
    border-right: 0;
  }
  .health-rows > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--stroke-subtle);
  }
}
@media (max-width: 420px) {
  .settings-section__header--status {
    flex-direction: column;
  }
  .health-rows {
    grid-template-columns: minmax(0, 1fr);
  }
  .health-rows > div,
  .health-rows > div:nth-child(2) {
    border-right: 0;
    border-bottom: 1px solid var(--stroke-subtle);
  }
  .health-rows > div:last-child {
    border-bottom: 0;
  }
}
</style>
