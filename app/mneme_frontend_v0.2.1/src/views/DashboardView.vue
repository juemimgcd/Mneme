<script setup lang="ts">
import { computed, ref } from "vue";
import { ArrowRight, Bot, Database, File, FolderPlus, Network, Search, Upload } from "@lucide/vue";
import type { MnemeWorkspace, WorkspaceCommandTab } from "../composables/useMnemeWorkspace";
import { useI18n } from "../composables/useI18n";
import UiButton from "../components/ui/UiButton.vue";
import UiField from "../components/ui/UiField.vue";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { formatDate, t } = useI18n();
const activeSubmission = ref<WorkspaceCommandTab | null>(null);

const commands = computed<Array<{ id: WorkspaceCommandTab; label: string; hint: string; icon: unknown; group: "create" | "query" }>>(() => [
  { id: "create", label: t("dashboard.command.create"), hint: t("dashboard.command.createHint"), icon: FolderPlus, group: "create" },
  { id: "upload", label: t("dashboard.command.upload"), hint: t("dashboard.command.uploadHint"), icon: Upload, group: "create" },
  { id: "ask", label: t("dashboard.command.ask"), hint: t("dashboard.command.askHint"), icon: Search, group: "query" },
  { id: "companion", label: t("dashboard.command.companion"), hint: t("dashboard.command.companionHint"), icon: Bot, group: "query" },
]);
const recentDocuments = computed(() => props.workspace.selectedDocuments.value.slice(0, 4));
const recentDocument = computed(() => recentDocuments.value[0] ?? null);
const metrics = computed(() => [
  {
    label: t("dashboard.documents"),
    value: props.workspace.selectedDocuments.value.length,
    detail: t("dashboard.indexed", { count: props.workspace.indexedDocumentCount.value }),
    icon: File,
  },
  {
    label: t("dashboard.memories"),
    value: props.workspace.memoryLibrary.value?.timeline.length ?? 0,
    detail: t("dashboard.canonical", { count: props.workspace.memoryGovernance.value?.canonical_memory_count ?? 0 }),
    icon: Database,
  },
  {
    label: t("dashboard.graph"),
    value: props.workspace.graphData.value?.nodes.length ?? 0,
    detail: t("dashboard.relations", { count: props.workspace.graphData.value?.edges.length ?? 0 }),
    icon: Network,
  },
]);

function continueWork() {
  if (recentDocument.value) {
    void props.workspace.openDocument(recentDocument.value.id);
    return;
  }
  props.workspace.workspaceCommandTab.value = "upload";
}

async function submitCommand(command: WorkspaceCommandTab, action: () => Promise<unknown>) {
  if (activeSubmission.value) return;
  activeSubmission.value = command;
  try {
    await action();
  } finally {
    activeSubmission.value = null;
  }
}

async function uploadFile(file: File | null | undefined) {
  if (!file || activeSubmission.value) return;
  await submitCommand("upload", () => props.workspace.uploadFile(file));
}
</script>

<template>
  <section data-testid="dashboard-overview" class="view-page">
    <section class="continue-work">
      <div class="continue-work__copy">
        <p>{{ t("dashboard.kicker") }}</p>
        <h1>{{ workspace.selectedKnowledgeBase.value?.name ?? t("dashboard.title") }}</h1>
        <span>{{ t("dashboard.description") }}</span>
      </div>
      <div class="continue-work__primary">
        <div class="continue-work__eyebrow">{{ t("dashboard.continue") }}</div>
        <strong>{{ recentDocument?.file_name ?? t("dashboard.noRecentTitle") }}</strong>
        <small v-if="recentDocument">{{ recentDocument.status }} · {{ formatDate(recentDocument.created_at) }}</small>
        <small v-else>{{ t("dashboard.noRecentDescription") }}</small>
        <UiButton variant="primary" @click="continueWork">
          <template #icon><component :is="recentDocument ? ArrowRight : Upload" /></template>
          {{ recentDocument ? t("dashboard.continueAction") : t("dashboard.uploadAction") }}
        </UiButton>
      </div>
    </section>

    <div data-testid="stitch-dashboard-grid" class="dashboard-stats" :aria-label="t('dashboard.overview')">
      <article v-for="metric in metrics" :key="metric.label">
        <component :is="metric.icon" />
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.detail }}</small>
      </article>
    </div>

    <section class="dashboard-body">
      <section class="recent-work" aria-labelledby="recent-work-title">
        <header>
          <div><p>{{ t("dashboard.activity") }}</p><h2 id="recent-work-title">{{ t("dashboard.recentFiles") }}</h2></div>
          <span>{{ workspace.selectedKnowledgeBase.value?.name }}</span>
        </header>
        <button
          v-for="document in recentDocuments"
          :key="document.id"
          type="button"
          @click="workspace.openDocument(document.id)"
        >
          <File />
          <span><strong>{{ document.file_name }}</strong><small>{{ document.status }} · {{ formatDate(document.created_at) }}</small></span>
          <ArrowRight />
        </button>
        <p v-if="!recentDocuments.length" class="recent-work__empty">{{ t("dashboard.noRecentDescription") }}</p>
      </section>

      <section data-testid="unified-command-module" class="command-module">
        <nav data-testid="workspace-command-tabs" :aria-label="t('dashboard.commands')">
          <div class="command-group">
            <span>{{ t("dashboard.command.createGroup") }}</span>
            <button
              v-for="command in commands.filter((item) => item.group === 'create')"
              :key="command.id"
              type="button"
              :class="{ active: workspace.workspaceCommandTab.value === command.id }"
              :aria-pressed="workspace.workspaceCommandTab.value === command.id"
              @click="workspace.workspaceCommandTab.value = command.id"
            >
              <component :is="command.icon" />
              <span><strong>{{ command.label }}</strong><small>{{ command.hint }}</small></span>
            </button>
          </div>
          <div class="command-group">
            <span>{{ t("dashboard.command.queryGroup") }}</span>
            <button
              v-for="command in commands.filter((item) => item.group === 'query')"
              :key="command.id"
              type="button"
              :class="{ active: workspace.workspaceCommandTab.value === command.id }"
              :aria-pressed="workspace.workspaceCommandTab.value === command.id"
              @click="workspace.workspaceCommandTab.value = command.id"
            >
              <component :is="command.icon" />
              <span><strong>{{ command.label }}</strong><small>{{ command.hint }}</small></span>
            </button>
          </div>
        </nav>

        <div data-testid="workspace-command-panel" class="command-panel">
          <form
            v-if="workspace.workspaceCommandTab.value === 'create'"
            data-testid="workspace-create-kb-command"
            @submit.prevent="submitCommand('create', workspace.createKnowledgeBase)"
          >
            <header><h2>{{ t("dashboard.command.create") }}</h2><p>{{ t("dashboard.command.createHint") }}</p></header>
            <UiField :label="t('dashboard.vaultName')" required>
              <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.knowledgeBaseForm.value.name" :placeholder="t('dashboard.vaultNamePlaceholder')" /></template>
            </UiField>
            <UiField :label="t('dashboard.vaultDescription')">
              <template #default="{ props: fieldProps }"><textarea v-bind="fieldProps" v-model="workspace.knowledgeBaseForm.value.description" :placeholder="t('dashboard.vaultDescriptionPlaceholder')" /></template>
            </UiField>
            <UiButton type="submit" variant="primary" :loading="activeSubmission === 'create'" :disabled="!workspace.knowledgeBaseForm.value.name.trim()">
              <template #icon><FolderPlus /></template>{{ t("dashboard.command.create") }}
            </UiButton>
          </form>

          <div v-else-if="workspace.workspaceCommandTab.value === 'upload'" data-testid="workspace-upload-command">
            <header><h2>{{ t("dashboard.command.upload") }}</h2><p>{{ t("dashboard.command.uploadHint") }}</p></header>
            <label class="drop-zone" :class="{ 'drop-zone--pending': activeSubmission === 'upload' }">
              <Upload />
              <strong>{{ activeSubmission === "upload" ? t("dashboard.uploading") : t("dashboard.chooseDocument") }}</strong>
              <small>{{ t("dashboard.uploadDescription") }}</small>
              <input :key="workspace.uploadInputKey.value" type="file" :disabled="Boolean(activeSubmission)" @change="uploadFile(($event.target as HTMLInputElement).files?.[0])" />
            </label>
          </div>

          <form
            v-else-if="workspace.workspaceCommandTab.value === 'ask'"
            data-testid="workspace-chat-command"
            @submit.prevent="submitCommand('ask', workspace.askVault)"
          >
            <header><h2>{{ t("dashboard.command.ask") }}</h2><p>{{ t("dashboard.command.askHint") }}</p></header>
            <UiField :label="t('dashboard.question')">
              <template #default="{ props: fieldProps }"><textarea v-bind="fieldProps" v-model="workspace.chatQuestion.value" :placeholder="t('dashboard.askPlaceholder')" /></template>
            </UiField>
            <UiButton type="submit" variant="primary" :loading="activeSubmission === 'ask'" :disabled="!workspace.chatQuestion.value.trim()">
              <template #icon><Search /></template>{{ t("dashboard.command.ask") }}
            </UiButton>
            <p v-if="workspace.chatResult.value" class="answer">{{ workspace.chatResult.value.answer }}</p>
          </form>

          <form v-else @submit.prevent="submitCommand('companion', workspace.askCompanion)">
            <header><h2>{{ t("dashboard.command.companion") }}</h2><p>{{ t("dashboard.command.companionHint") }}</p></header>
            <UiField :label="t('dashboard.reflection')">
              <template #default="{ props: fieldProps }"><textarea v-bind="fieldProps" v-model="workspace.companionQuestion.value" :placeholder="t('dashboard.companionPlaceholder')" /></template>
            </UiField>
            <UiButton type="submit" variant="primary" :loading="activeSubmission === 'companion'" :disabled="!workspace.companionQuestion.value.trim()">
              <template #icon><Bot /></template>{{ t("dashboard.command.companion") }}
            </UiButton>
            <p v-if="workspace.companionResult.value" class="answer">{{ workspace.companionResult.value.direct_answer }}</p>
          </form>
        </div>
      </section>
    </section>
  </section>
</template>

<style scoped>
.view-page { width: min(100%, 1160px); margin: 0 auto; padding: clamp(1.25rem, 3vw, 2.5rem); }
.continue-work { display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.72fr); align-items: end; gap: clamp(1.25rem, 4vw, 3.5rem); }
.continue-work__copy > p, .recent-work header p { margin: 0; color: var(--accent-primary); font: 600 var(--font-size-xs) var(--font-mono); text-transform: uppercase; letter-spacing: 0.09em; }
.continue-work h1 { margin: 0.55rem 0 0; font: 600 clamp(1.85rem, 4vw, 3rem) var(--font-serif); line-height: 1.08; }
.continue-work__copy > span { display: block; max-width: 40rem; margin-top: 0.7rem; color: var(--content-secondary); line-height: 1.7; }
.continue-work__primary { display: grid; min-width: 0; gap: 0.35rem; padding: 1rem; background: var(--surface-panel); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-panel); }
.continue-work__primary strong, .continue-work__primary small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.continue-work__primary small { color: var(--content-tertiary); font-size: var(--font-size-xs); }
.continue-work__primary :deep(.ui-button) { width: fit-content; margin-top: 0.55rem; }
.continue-work__eyebrow { color: var(--content-tertiary); font: 600 var(--font-size-xs) var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }
.dashboard-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 2rem; border-block: 1px solid var(--stroke-subtle); }
.dashboard-stats article { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 0.2rem 0.6rem; padding: 0.85rem 1rem; border-right: 1px solid var(--stroke-subtle); }
.dashboard-stats article:last-child { border-right: 0; }
.dashboard-stats svg { grid-row: 1 / 3; width: 1rem; color: var(--accent-primary); }
.dashboard-stats span, .dashboard-stats small { color: var(--content-secondary); font-size: var(--font-size-xs); }
.dashboard-stats strong { grid-row: 1 / 3; grid-column: 3; font-size: 1.2rem; }
.dashboard-stats small { color: var(--content-tertiary); }
.dashboard-body { display: grid; grid-template-columns: minmax(15rem, 0.7fr) minmax(0, 1.3fr); gap: 1rem; margin-top: 1.25rem; }
.recent-work, .command-module { min-width: 0; background: var(--surface-panel); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-panel); }
.recent-work { align-self: start; padding: 0.65rem; }
.recent-work > header { display: flex; align-items: end; justify-content: space-between; gap: 0.75rem; padding: 0.45rem 0.55rem 0.75rem; }
.recent-work h2 { margin: 0.15rem 0 0; font-size: var(--font-size-md); }
.recent-work header > span { overflow: hidden; color: var(--content-tertiary); font-size: var(--font-size-xs); text-overflow: ellipsis; white-space: nowrap; }
.recent-work > button { display: grid; width: 100%; min-height: 3.25rem; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.65rem; padding: 0.55rem; color: var(--content-secondary); text-align: left; background: transparent; border: 0; border-radius: var(--radius-control); transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, transform var(--duration-press) var(--ease-out-ui); }
.recent-work > button > svg { width: 0.95rem; }
.recent-work > button > svg:last-child { color: var(--content-tertiary); }
.recent-work strong, .recent-work small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-work strong { color: var(--content-primary); font-size: var(--font-size-sm); }
.recent-work small { margin-top: 0.18rem; color: var(--content-tertiary); font-size: var(--font-size-xs); }
.recent-work > button:active:not(:focus-visible) { transform: scale(0.97); }
.recent-work__empty { padding: 1rem 0.55rem; color: var(--content-tertiary); font-size: var(--font-size-sm); line-height: 1.6; }
.command-module { display: grid; grid-template-columns: 13.5rem minmax(0, 1fr); overflow: hidden; }
.command-module nav { display: grid; align-content: start; gap: 0.85rem; padding: 0.55rem; background: var(--surface-sidebar); border-right: 1px solid var(--stroke-subtle); }
.command-group { display: grid; gap: 0.2rem; }
.command-group > span { padding: 0.35rem 0.55rem 0.2rem; color: var(--content-tertiary); font: 600 0.62rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.07em; }
.command-module nav button { display: flex; min-width: 0; gap: 0.65rem; padding: 0.7rem; color: var(--content-secondary); text-align: left; background: transparent; border: 0; border-radius: var(--radius-control); transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, transform var(--duration-press) var(--ease-out-ui); }
.command-module nav button.active { color: var(--content-primary); background: var(--accent-subtle); box-shadow: inset 2px 0 var(--accent-primary); }
.command-module nav button:active:not(:focus-visible) { transform: scale(0.97); }
.command-module nav svg { flex: 0 0 auto; width: 1rem; }
.command-module nav strong, .command-module nav small { display: block; }
.command-module nav strong { font-size: var(--font-size-sm); }
.command-module nav small { margin-top: 0.15rem; color: var(--content-tertiary); font-size: var(--font-size-xs); line-height: 1.35; }
.command-panel { min-height: 22rem; padding: clamp(1rem, 3vw, 1.5rem); }
.command-panel form, .command-panel > div { display: grid; align-content: start; gap: 0.85rem; }
.command-panel header h2 { margin: 0; font-size: var(--font-size-md); }
.command-panel header p { margin: 0.25rem 0 0; color: var(--content-tertiary); font-size: var(--font-size-xs); line-height: 1.5; }
.command-panel :deep(.ui-button) { width: fit-content; }
.drop-zone { position: relative; display: grid; min-height: 13rem; place-items: center; align-content: center; gap: 0.35rem; padding: 1rem; color: var(--content-secondary); text-align: center; border: 1px dashed var(--stroke-default); border-radius: var(--radius-panel); transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, border-color var(--duration-fast) ease; }
.drop-zone svg { width: 1.2rem; color: var(--accent-primary); }
.drop-zone small { color: var(--content-tertiary); font-size: var(--font-size-xs); }
.drop-zone input { position: absolute; inset: 0; cursor: pointer; opacity: 0; }
.drop-zone--pending { opacity: 0.58; }
.answer { margin: 0; padding: 1rem; color: var(--content-secondary); background: var(--surface-sidebar); border-left: 2px solid var(--accent-primary); border-radius: var(--radius-control); line-height: 1.65; }
@media (hover: hover) and (pointer: fine) {
  .recent-work > button:hover, .command-module nav button:hover:not(.active) { color: var(--content-primary); background: var(--surface-raised); }
  .drop-zone:hover { background: var(--surface-raised); border-color: var(--accent-primary); }
}
@media (max-width: 900px) {
  .dashboard-body { grid-template-columns: 1fr; }
  .recent-work { order: 2; }
}
@media (max-width: 767px) {
  .view-page { padding: 1.1rem; }
  .continue-work { grid-template-columns: 1fr; }
  .dashboard-stats { grid-template-columns: 1fr; }
  .dashboard-stats article { border-right: 0; border-bottom: 1px solid var(--stroke-subtle); }
  .dashboard-stats article:last-child { border-bottom: 0; }
  .command-module { display: block; }
  .command-module nav { display: flex; gap: 0.25rem; overflow-x: auto; padding: 0.4rem; border-right: 0; border-bottom: 1px solid var(--stroke-subtle); }
  .command-group { display: contents; }
  .command-group > span { display: none; }
  .command-module nav button { min-width: 4.25rem; flex: 1 0 auto; justify-content: center; padding: 0.6rem 0.45rem; }
  .command-module nav button.active { box-shadow: inset 0 -2px var(--accent-primary); }
  .command-module nav button > span small { display: none; }
  .command-panel { min-height: 20rem; }
}
@media (prefers-reduced-motion: reduce) {
  .recent-work > button, .command-module nav button { transition-property: color, background-color; }
  .recent-work > button:active:not(:focus-visible), .command-module nav button:active:not(:focus-visible) { transform: none; }
}
</style>
