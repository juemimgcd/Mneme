<script setup lang="ts">
import { Download, Files, MoreHorizontal, PanelRight, Trash2, WandSparkles, X } from "@lucide/vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import DocumentProperties from "../components/documents/DocumentProperties.vue";
import DocumentReader from "../components/documents/DocumentReader.vue";
import DocumentTree from "../components/documents/DocumentTree.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiIconButton from "../components/ui/UiIconButton.vue";
import UiPopover from "../components/ui/UiPopover.vue";
import { useI18n } from "../composables/useI18n";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();
defineEmits<{ create: [] }>();
const treeOpen = ref(true);
const propertiesOpen = ref(false);
const deleteDialogOpen = ref(false);
const actionPending = ref<"index" | "delete" | null>(null);
const compactQuery = window.matchMedia("(max-width: 1100px)");
const isCompact = ref(compactQuery.matches);
const treeError = ref("");
const filesTrigger = ref<HTMLButtonElement | null>(null);
const propertiesTrigger = ref<HTMLButtonElement | null>(null);
const activeTab = computed(() => props.workspace.openDocumentTabs.value.find((tab) => tab.documentId === props.workspace.activeDocumentId.value));
const blobUrl = computed(() => activeTab.value?.blobUrl ?? null);

async function openDocument(documentId: string) {
  await props.workspace.openDocument(documentId);
  if (window.matchMedia("(max-width: 1100px)").matches) treeOpen.value = false;
}

async function createFolder(parentId: string, name: string) {
  treeError.value = "";
  try {
    const folder = await props.workspace.createFolder(parentId, name);
    props.workspace.selectedFolderId.value = folder.id;
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.createFolderError");
  }
}

async function renameFolder(folderId: string, name: string) {
  treeError.value = "";
  try {
    await props.workspace.updateFolder(folderId, { name });
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.renameFolderError");
  }
}

async function deleteFolder(folderId: string) {
  treeError.value = "";
  const hasDocuments = props.workspace.selectedDocuments.value.some((document) => document.folder_id === folderId);
  const hasChildren = props.workspace.documentFolders.value.some((folder) => folder.parent_id === folderId && folder.id !== folderId);
  if (hasDocuments || hasChildren) {
    treeError.value = t("reader.folderNotEmpty");
    return;
  }
  try {
    await props.workspace.deleteFolder(folderId);
    props.workspace.selectedFolderId.value = "";
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.folderNotEmpty");
  }
}

async function moveFolder(folderId: string, parentId: string) {
  treeError.value = "";
  try {
    await props.workspace.updateFolder(folderId, { parent_id: parentId });
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.moveFolderError");
  }
}

async function moveDocument(documentId: string, folderId: string) {
  treeError.value = "";
  try {
    await props.workspace.moveDocument(documentId, folderId);
    await props.workspace.loadKnowledgeBasePanels();
  } catch (error) {
    treeError.value = error instanceof Error ? error.message : t("reader.moveDocumentError");
  }
}

async function indexActiveDocument() {
  if (!props.workspace.activeDocumentId.value || actionPending.value) return;
  actionPending.value = "index";
  try {
    await props.workspace.indexDocument(props.workspace.activeDocumentId.value);
  } finally {
    actionPending.value = null;
  }
}

async function deleteActiveDocument() {
  if (!props.workspace.activeDocumentId.value || actionPending.value) return;
  actionPending.value = "delete";
  try {
    await props.workspace.deleteDocument(props.workspace.activeDocumentId.value);
    deleteDialogOpen.value = false;
    propertiesOpen.value = false;
  } finally {
    actionPending.value = null;
  }
}

watch(
  () => [props.workspace.documentContent.value?.document_id, props.workspace.documentContent.value?.render_mode] as const,
  ([documentId, renderMode]) => {
    if (documentId && renderMode === "pdf") void props.workspace.ensureDocumentBlob(documentId);
  },
  { immediate: true },
);
watch(
  () => props.workspace.activeDocumentId.value,
  (documentId) => {
    if (documentId && window.matchMedia("(max-width: 1100px)").matches) treeOpen.value = false;
    if (documentId) void nextTick(() => document.querySelector<HTMLElement>('[data-testid="document-reader"]')?.focus({ preventScroll: true }));
  },
  { immediate: true },
);

function handleEscape(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  if (propertiesOpen.value) {
    propertiesOpen.value = false;
    void nextTick(() => propertiesTrigger.value?.focus());
  } else if (treeOpen.value && window.matchMedia("(max-width: 1100px)").matches) {
    treeOpen.value = false;
    void nextTick(() => filesTrigger.value?.focus());
  }
}

async function focusDrawerPane(id: string) {
  await nextTick();
  const pane = document.getElementById(id);
  if (!pane) return;
  const deadline = performance.now() + 500;
  const focusWhenVisible = () => {
    if (window.getComputedStyle(pane).visibility !== "hidden") {
      pane.focus();
      return;
    }
    if (performance.now() < deadline) window.requestAnimationFrame(focusWhenVisible);
  };
  window.requestAnimationFrame(focusWhenVisible);
}

function closeCompactPanes() {
  const restoreTarget = treeOpen.value ? filesTrigger.value : propertiesTrigger.value;
  treeOpen.value = false;
  propertiesOpen.value = false;
  void nextTick(() => restoreTarget?.focus());
}

async function toggleTree() {
  const opening = !treeOpen.value;
  treeOpen.value = opening;
  if (opening) {
    propertiesOpen.value = false;
    await focusDrawerPane("document-tree-pane");
  }
}

async function toggleProperties() {
  if (!props.workspace.activeDocumentId.value) return;
  const opening = !propertiesOpen.value;
  propertiesOpen.value = opening;
  if (opening) {
    treeOpen.value = false;
    await focusDrawerPane("document-properties-pane");
  }
}

function syncCompact() {
  isCompact.value = compactQuery.matches;
  if (!isCompact.value) {
    treeOpen.value = true;
    propertiesOpen.value = false;
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleEscape);
  compactQuery.addEventListener("change", syncCompact);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleEscape);
  compactQuery.removeEventListener("change", syncCompact);
});
</script>

<template>
  <section
    data-testid="document-workspace"
    class="document-workspace"
    :class="{ 'tree-open': treeOpen, 'properties-open': propertiesOpen, 'has-properties': Boolean(workspace.activeDocumentId.value) }"
  >
    <div class="reader-mobile-tools">
      <button ref="filesTrigger" type="button" :aria-label="t('reader.files')" aria-controls="document-tree-pane" :aria-expanded="treeOpen" @click="toggleTree"><Files />{{ t("reader.files") }}</button>
      <span>{{ workspace.documentContent.value?.file_name ?? workspace.selectedKnowledgeBase.value?.name }}</span>
      <button ref="propertiesTrigger" type="button" :aria-label="t('reader.properties')" aria-controls="document-properties-pane" :aria-expanded="propertiesOpen" :disabled="!workspace.activeDocumentId.value" @click="toggleProperties"><PanelRight />{{ t("reader.properties") }}</button>
    </div>

    <DocumentTree
      :folders="workspace.documentFolders.value"
      :documents="workspace.selectedDocuments.value"
      :active-document-id="workspace.activeDocumentId.value"
      :selected-folder-id="workspace.selectedFolderId.value"
      :error="treeError"
      :aria-hidden="isCompact && !treeOpen"
      :inert="isCompact && !treeOpen ? true : undefined"
      @open-document="openDocument"
      @create-folder="createFolder"
      @rename-folder="renameFolder"
      @delete-folder="deleteFolder"
      @move-folder="moveFolder"
      @interaction-error="treeError = $event"
      @move-document="moveDocument"
      @select-folder="workspace.selectedFolderId.value = $event"
    />

    <section class="reader-center">
      <div v-if="workspace.activeDocumentId.value" class="document-actions" :aria-label="t('reader.documentActions')">
        <div class="document-actions__desktop">
          <UiButton size="sm" variant="secondary" @click="workspace.downloadDocument()"><template #icon><Download /></template>{{ t("reader.download") }}</UiButton>
          <UiButton size="sm" variant="secondary" :loading="actionPending === 'index'" :disabled="workspace.documentPreview.value?.status === 'indexed'" @click="indexActiveDocument"><template #icon><WandSparkles /></template>{{ t("reader.index") }}</UiButton>
          <UiButton size="sm" variant="danger" @click="deleteDialogOpen = true"><template #icon><Trash2 /></template>{{ t("reader.delete") }}</UiButton>
        </div>
        <div class="document-actions__mobile">
          <UiPopover align="end" role="menu" :ariaLabel="t('reader.documentActions')">
            <template #trigger="{ props: triggerProps }">
              <UiIconButton v-bind="triggerProps" :label="t('reader.documentActions')"><MoreHorizontal /></UiIconButton>
            </template>
            <template #default="{ close }">
              <div class="document-action-menu">
                <button type="button" role="menuitem" @click="workspace.downloadDocument(); close()"><Download />{{ t("reader.download") }}</button>
                <button type="button" role="menuitem" :disabled="workspace.documentPreview.value?.status === 'indexed' || Boolean(actionPending)" @click="indexActiveDocument(); close()"><WandSparkles />{{ t("reader.index") }}</button>
                <button type="button" role="menuitem" class="danger" @click="deleteDialogOpen = true; close()"><Trash2 />{{ t("reader.delete") }}</button>
              </div>
            </template>
          </UiPopover>
        </div>
      </div>
      <DocumentReader
        :tabs="workspace.openDocumentTabs.value"
        :active-document-id="workspace.activeDocumentId.value"
        :content="workspace.documentContent.value"
        :phase="workspace.documentContentPhase.value"
        :error="workspace.documentContentError.value"
        :blob-url="blobUrl"
        :blob-phase="workspace.documentBlobPhase.value"
        :blob-error="workspace.documentBlobError.value"
        @select-tab="openDocument"
        @close-tab="workspace.closeDocument"
        @download="workspace.downloadDocument()"
        @retry="workspace.retryDocumentBlob()"
      />
    </section>

    <DocumentProperties
      v-if="workspace.activeDocumentId.value"
      :preview="workspace.documentPreview.value"
      :versions="workspace.documentVersions.value"
      :active-document-id="workspace.activeDocumentId.value"
      :aria-hidden="isCompact && !propertiesOpen"
      :inert="isCompact && !propertiesOpen ? true : undefined"
      @select-version="openDocument"
    />
    <button v-if="isCompact && (treeOpen || propertiesOpen)" class="pane-scrim" :aria-label="treeOpen ? t('reader.closeFiles') : t('reader.closeProperties')" @click="closeCompactPanes" />
    <button v-if="treeOpen" class="overlay-dismiss tree-dismiss" :aria-label="t('reader.closeFiles')" @click="closeCompactPanes"><X /></button>
    <button v-if="propertiesOpen" class="overlay-dismiss properties-dismiss" :aria-label="t('reader.closeProperties')" @click="closeCompactPanes"><X /></button>

    <UiDialog
      v-model="deleteDialogOpen"
      :title="t('reader.deleteTitle')"
      :description="t('reader.deleteDescription', { name: workspace.documentContent.value?.file_name ?? '' })"
      :confirm-label="t('reader.delete')"
      :cancel-label="t('reader.cancel')"
      confirm-variant="danger"
      :busy="actionPending === 'delete'"
      @confirm="deleteActiveDocument"
    />
  </section>
</template>

<style scoped>
.document-workspace { position: relative; display: grid; width: 100%; height: 100%; min-height: 0; grid-template-columns: 240px minmax(0, 1fr); overflow: hidden; background: var(--surface-canvas); }
.document-workspace.has-properties { grid-template-columns: 240px minmax(0, 1fr) 280px; }
.reader-center { display: grid; min-width: 0; min-height: 0; grid-template-rows: auto minmax(0, 1fr); }
.document-actions { display: flex; min-height: 2.65rem; align-items: center; justify-content: flex-end; padding: 0.3rem 0.55rem; background: var(--surface-sidebar); border-bottom: 1px solid var(--stroke-subtle); }
.document-actions__desktop { display: flex; gap: 0.35rem; }
.document-actions__mobile { display: none; }
.document-action-menu { display: grid; min-width: 11rem; gap: 0.2rem; }
.document-action-menu button { display: flex; min-height: 2.35rem; align-items: center; gap: 0.55rem; padding: 0.45rem 0.6rem; color: var(--content-secondary); text-align: left; background: transparent; border: 0; border-radius: var(--radius-control); }
.document-action-menu button.danger { color: var(--status-danger); }
.document-action-menu button:disabled { opacity: 0.42; }
.document-action-menu svg { width: 0.95rem; }
.reader-mobile-tools, .overlay-dismiss, .pane-scrim { display: none; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
@media (hover: hover) and (pointer: fine) {
  .document-action-menu button:hover:not(:disabled) { color: var(--content-primary); background: var(--surface-raised); }
  .document-action-menu button.danger:hover:not(:disabled) { color: var(--status-danger); background: color-mix(in srgb, var(--status-danger) 10%, transparent); }
}

@media (max-width: 1100px) {
  .document-workspace, .document-workspace.has-properties { grid-template-columns: minmax(0, 1fr); grid-template-rows: auto minmax(0, 1fr); }
  .reader-mobile-tools { display: grid; z-index: 3; min-height: 2.6rem; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 0.5rem; padding: 0 0.55rem; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-muted); }
  .reader-mobile-tools button { display: flex; align-items: center; gap: 0.35rem; padding: 0.35rem 0.45rem; color: var(--text-secondary); background: transparent; border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.68rem; }
  .reader-mobile-tools svg { width: 0.8rem; }
  .reader-mobile-tools span { overflow: hidden; color: var(--text-tertiary); text-align: center; text-overflow: ellipsis; white-space: nowrap; font: 0.62rem var(--font-mono); }
  .reader-center { grid-row: 2; grid-column: 1; }
  :deep([data-testid="document-tree-pane"]), :deep([data-testid="document-properties"]) { position: absolute; z-index: 12; top: 2.6rem; bottom: 0; width: min(86vw, 320px); visibility: hidden; pointer-events: none; box-shadow: var(--shadow-popover); transition: transform 160ms var(--ease-out-ui), visibility 0s linear 160ms; }
  :deep([data-testid="document-tree-pane"]) { left: 0; transform: translateX(-102%); }
  :deep([data-testid="document-properties"]) { right: 0; transform: translateX(102%); }
  .tree-open :deep([data-testid="document-tree-pane"]), .properties-open :deep([data-testid="document-properties"]) { visibility: visible; pointer-events: auto; transform: translateX(0); transition-duration: 220ms; transition-delay: 0s; }
  .pane-scrim { position: absolute; inset: 2.6rem 0 0; z-index: 10; display: block; width: 100%; background: rgb(0 0 0 / 38%); border: 0; }
  .overlay-dismiss { position: absolute; z-index: 13; top: 3rem; display: grid; width: 1.8rem; height: 1.8rem; place-items: center; color: var(--text-secondary); background: var(--bg-elevated); border: 1px solid var(--border-muted); border-radius: 50%; box-shadow: var(--shadow-float); }
  .overlay-dismiss svg { width: 0.8rem; }
  .tree-dismiss { left: min(86vw, 320px); transform: translateX(-50%); }
  .properties-dismiss { right: min(86vw, 320px); transform: translateX(50%); }
}

@media (max-width: 767px) {
  .document-actions { min-height: 2.5rem; padding-block: 0.15rem; }
  .document-actions__desktop { display: none; }
  .document-actions__mobile { display: inline-flex; }
  .reader-mobile-tools button { font-size: 0.62rem; }
  .reader-mobile-tools button svg { width: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  :deep([data-testid="document-tree-pane"]), :deep([data-testid="document-properties"]) { transition: none; }
}
</style>
