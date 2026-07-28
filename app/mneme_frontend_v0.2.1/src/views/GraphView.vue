<script setup lang="ts">
import { ChevronLeft, File, FolderPlus, Network, Play, Search, Send, SlidersHorizontal, Target, X, ZoomIn, ZoomOut } from "@lucide/vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, watchEffect } from "vue";
import type { MnemeWorkspace } from "../composables/useMnemeWorkspace";
import type { GraphNodeData } from "../types";
import { useI18n } from "../composables/useI18n";
import { useGraphInteraction } from "../composables/useGraphInteraction";
import UiEmptyState from "../components/ui/UiEmptyState.vue";
import UiPopover from "../components/ui/UiPopover.vue";

const props = defineProps<{ workspace: MnemeWorkspace }>();
const { t } = useI18n();
const compactMedia = window.matchMedia("(max-width: 1024px)");
const previewSheetMedia = window.matchMedia("(max-width: 900px)");
const isCompact = ref(compactMedia.matches);
const isPreviewSheet = ref(previewSheetMedia.matches);
const railCollapsed = ref(compactMedia.matches);
const filtersOpen = ref(false);
const zoom = ref(1);
const graphViewBox = ref("0 0 760 680");
const graphSvg = ref<SVGSVGElement | null>(null);
const hoveredNodeId = ref<string | null>(null);
const previewInstant = ref(false);
const railPanel = ref<HTMLElement | null>(null);
const railTrigger = ref<HTMLButtonElement | null>(null);
const previewPanel = ref<HTMLElement | null>(null);
let railPreviousFocus: HTMLElement | null = null;
let previewPreviousFocus: HTMLElement | SVGElement | null = null;
let previewTrigger: HTMLElement | SVGElement | null = null;
let dragState: { nodeId: string; pointerId: number; startX: number; startY: number; moved: boolean; started: boolean } | null = null;
let suppressOpenUntil = 0;
let lastNodePointerDown: { nodeId: string; at: number } | null = null;
let selectionTimer: number | null = null;
let selectionIntentGeneration = 0;
let pendingSelectionNodeId: string | null = null;
let preservePositionsForLabelUpdate = false;

const graphNodes = computed(() => props.workspace.graphData.value?.nodes ?? []);
const graphEdges = computed(() => props.workspace.graphData.value?.edges ?? []);
const interaction = useGraphInteraction(graphNodes, graphEdges);
const positionedNodes = interaction.positionedNodes;
const positionedEdges = interaction.positionedEdges;
const previewNode = interaction.selectedNode;

function nodeRadius(node: GraphNodeData) { return interaction.nodeRadius(node); }
function nodeFill(node: GraphNodeData) { return node.depth === 0 ? "var(--accent-strong)" : node.node_type.includes("memory") ? "var(--accent)" : "var(--text-tertiary)"; }

async function selectGraphNode(node: GraphNodeData, instant = false) {
  cancelPendingSelection();
  previewInstant.value = instant;
  interaction.selectNode(node);
  if (node.node_type === "document") await props.workspace.loadDocumentPreview(node.entity_id);
  else props.workspace.clearDocumentPreview();
}

function cancelPendingSelection() {
  selectionIntentGeneration += 1;
  pendingSelectionNodeId = null;
  if (selectionTimer !== null) window.clearTimeout(selectionTimer);
  selectionTimer = null;
}

function startGraphNodeDrag(node: GraphNodeData, event: PointerEvent) {
  event.stopPropagation();
  previewTrigger = event.currentTarget as SVGElement;
  const now = performance.now();
  const isDoubleActivation = lastNodePointerDown?.nodeId === node.id && now - lastNodePointerDown.at < 360;
  lastNodePointerDown = { nodeId: node.id, at: now };
  if (isDoubleActivation) {
    cancelPendingSelection();
    openGraphDocument(node);
    return;
  }
  dragState = { nodeId: node.id, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, moved: false, started: false };
  cancelPendingSelection();
  const intentGeneration = selectionIntentGeneration;
  pendingSelectionNodeId = node.id;
  selectionTimer = window.setTimeout(() => {
    selectionTimer = null;
    if (
      intentGeneration !== selectionIntentGeneration
      || pendingSelectionNodeId !== node.id
      || !interaction.visibleNodes.value.some((item) => item.id === node.id)
    ) return;
    pendingSelectionNodeId = null;
    void selectGraphNode(node);
  }, 240);
}

function moveGraphNodeDrag(event: PointerEvent) {
  if (!dragState || !graphSvg.value) return;
  if (Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY) <= 6) return;
  dragState.moved = true;
  if (!dragState.started) {
    cancelPendingSelection();
    const draggedNode = graphNodes.value.find((node) => node.id === dragState?.nodeId);
    if (draggedNode) void selectGraphNode(draggedNode);
    graphSvg.value.setPointerCapture(event.pointerId);
    interaction.startDrag(dragState.nodeId);
    dragState.started = true;
  }
  const point = graphSvg.value.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const matrix = graphSvg.value.getScreenCTM()?.inverse();
  if (!matrix) return;
  const local = point.matrixTransform(matrix);
  interaction.dragNode(dragState.nodeId, local.x, local.y);
}

function endGraphNodeDrag(event?: PointerEvent) {
  if (!dragState || (event && event.pointerId !== dragState.pointerId)) return;
  if (dragState.moved) suppressOpenUntil = performance.now() + 400;
  if (dragState.started) interaction.endDrag(dragState.nodeId);
  dragState = null;
}

function clearGraphSelection(event: PointerEvent) {
  if (event.target === graphSvg.value) hideGraphDocumentPreview();
}

function hideGraphDocumentPreview() {
  cancelPendingSelection();
  previewInstant.value = false;
  interaction.selectNode(null);
  props.workspace.clearDocumentPreview();
}
function setGraphFilter(filter: "all" | "tags" | "orphans") {
  cancelPendingSelection();
  preservePositionsForLabelUpdate = true;
  interaction.setActiveFilter(filter);
  if (!interaction.selectedNode.value) props.workspace.clearDocumentPreview();
}
function toggleGraphNodeType(nodeType: string) {
  cancelPendingSelection();
  preservePositionsForLabelUpdate = true;
  interaction.toggleNodeType(nodeType);
  const selectedId = interaction.selectedNode.value?.id;
  if (selectedId && !interaction.visibleNodes.value.some((node) => node.id === selectedId)) {
    interaction.selectNode(null);
  }
  if (!interaction.selectedNode.value) props.workspace.clearDocumentPreview();
}
function setZoom(value: number) {
  zoom.value = Math.min(1.8, Math.max(0.65, value));
  const width = 760 / zoom.value;
  const height = 680 / zoom.value;
  graphViewBox.value = `${(760 - width) / 2} ${(680 - height) / 2} ${width} ${height}`;
}
function centerGraph() { zoom.value = 1; graphViewBox.value = "0 0 760 680"; }
function restartGraphLayout() { interaction.restartLayout(); centerGraph(); }

function openGraphDocument(node: GraphNodeData) {
  if (node.node_type !== "document" || performance.now() < suppressOpenUntil) return;
  void props.workspace.openDocument(node.entity_id);
}

function handleGraphNodeClick(node: GraphNodeData, event: MouseEvent) {
  if (event.detail >= 2) openGraphDocument(node);
}

function openSelectedDocument() {
  if (!previewNode.value || previewNode.value.node_type !== "document") return;
  void props.workspace.openDocument(previewNode.value.entity_id);
}

function openDocumentFromRail(documentId: string) {
  const node = graphNodes.value.find((item) => item.node_type === "document" && item.entity_id === documentId);
  if (node) interaction.selectNode(node);
  void props.workspace.openDocument(documentId);
}

function focusableElements(container: HTMLElement) {
  return [...container.querySelectorAll<HTMLElement>(
    'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
  )];
}

function trapFocus(event: KeyboardEvent, container: HTMLElement | null) {
  if (event.key !== "Tab" || !container) return;
  const focusable = focusableElements(container);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function closeRail() {
  railCollapsed.value = true;
}

function toggleRail() {
  railCollapsed.value = !railCollapsed.value;
}

function onOverlayKeydown(event: KeyboardEvent) {
  if (filtersOpen.value) return;
  if (event.key === "Escape") {
    if (previewNode.value && isPreviewSheet.value) {
      event.preventDefault();
      hideGraphDocumentPreview();
      return;
    }
    if (!railCollapsed.value && isCompact.value) {
      event.preventDefault();
      closeRail();
      return;
    }
  }
  if (!railCollapsed.value && isCompact.value) trapFocus(event, railPanel.value);
  else if (previewNode.value && isPreviewSheet.value) trapFocus(event, previewPanel.value);
}

function syncCompact() {
  isCompact.value = compactMedia.matches;
  railCollapsed.value = compactMedia.matches;
}

function syncPreviewSheet() {
  isPreviewSheet.value = previewSheetMedia.matches;
}

watch(railCollapsed, async (collapsed, previous) => {
  if (!isCompact.value) return;
  if (!collapsed) {
    railPreviousFocus = document.activeElement as HTMLElement | null;
    await nextTick();
    railPanel.value?.querySelector<HTMLElement>("button")?.focus();
  } else if (previous === false && railPreviousFocus) {
    const returnFocus = railPreviousFocus;
    railPreviousFocus = null;
    await nextTick();
    returnFocus.focus();
  }
});

watch([previewNode, isPreviewSheet], async ([node, sheet], [previousNode, previousSheet]) => {
  const modalOpen = Boolean(node && sheet);
  const modalWasOpen = Boolean(previousNode && previousSheet);
  if (modalOpen && !modalWasOpen) {
    const activeElement = document.activeElement as HTMLElement | SVGElement | null;
    previewPreviousFocus = activeElement && activeElement !== document.body ? activeElement : previewTrigger;
    await nextTick();
    if (previewNode.value && isPreviewSheet.value) previewPanel.value?.focus();
  } else if (!modalOpen && modalWasOpen) {
    const returnFocus = previewPreviousFocus;
    previewPreviousFocus = null;
    previewTrigger = null;
    await nextTick();
    returnFocus?.focus();
  }
});

watchEffect(() => {
  if (pendingSelectionNodeId && !interaction.visibleNodes.value.some((node) => node.id === pendingSelectionNodeId)) {
    cancelPendingSelection();
  }
  const next = new Set(
    positionedNodes.value
      .filter((node) => interaction.labelVisible(node.id, zoom.value, hoveredNodeId.value))
      .map((node) => node.id),
  );
  interaction.setVisibleLabelIds(next, !preservePositionsForLabelUpdate);
  preservePositionsForLabelUpdate = false;
});

onBeforeUnmount(() => {
  cancelPendingSelection();
  props.workspace.clearDocumentPreview();
  document.removeEventListener("keydown", onOverlayKeydown);
  compactMedia.removeEventListener("change", syncCompact);
  previewSheetMedia.removeEventListener("change", syncPreviewSheet);
});

onMounted(() => {
  document.addEventListener("keydown", onOverlayKeydown);
  compactMedia.addEventListener("change", syncCompact);
  previewSheetMedia.addEventListener("change", syncPreviewSheet);
});

function nodeTypeLabel(nodeType: string) {
  if (nodeType === "document") return t("graph.type.documents");
  if (nodeType === "memory_entry" || nodeType === "memory") return t("graph.type.memories");
  if (nodeType === "knowledge_base") return t("graph.type.vaults");
  return nodeType.replaceAll("_", " ");
}

const hoveredNeighborIds = computed(() => {
  if (!hoveredNodeId.value || previewNode.value) return new Set<string>();
  return new Set(graphEdges.value.flatMap((edge) => {
    if (edge.source === hoveredNodeId.value) return [edge.target];
    if (edge.target === hoveredNodeId.value) return [edge.source];
    return [];
  }));
});

function nodeFocusState(nodeId: string) {
  if (previewNode.value) return interaction.focusState(nodeId);
  if (!hoveredNodeId.value) return "normal";
  if (nodeId === hoveredNodeId.value) return "selected";
  return hoveredNeighborIds.value.has(nodeId) ? "neighbor" : "dimmed";
}

function edgeFocusState(source: string, target: string) {
  if (previewNode.value) return interaction.edgeFocusState(source, target);
  if (!hoveredNodeId.value) return "normal";
  return source === hoveredNodeId.value || target === hoveredNodeId.value ? "connected" : "dimmed";
}
</script>

<template>
  <div data-testid="stitch-graph-layout" class="graph-layout" :title="t('graph.workspace')">
    <div data-testid="graph-function-grid" class="graph-grid" :class="{ 'graph-grid--rail-closed': railCollapsed }">
      <aside
        ref="railPanel"
        data-testid="graph-file-rail"
        class="graph-file-panel"
        :aria-hidden="railCollapsed"
        :inert="railCollapsed ? true : undefined"
        :role="isCompact ? 'dialog' : undefined"
        :aria-modal="isCompact && !railCollapsed ? 'true' : undefined"
        :aria-label="t('graph.files')"
        tabindex="-1"
      >
        <header>
          <div><small>{{ t("graph.activeVault") }}</small><h2>{{ t("graph.files") }}</h2></div>
          <button v-if="isCompact" type="button" :aria-label="t('graph.closeFiles')" @click="closeRail"><X /></button>
          <FolderPlus v-else class="size-4" />
        </header>
        <nav>
          <button v-for="doc in workspace.selectedDocuments.value" :key="doc.id" :class="{ active: workspace.documentPreview.value?.document_id === doc.id }" @click="openDocumentFromRail(doc.id)"><File /><span>{{ doc.file_name }}</span></button>
        </nav>
      </aside>

      <button
        v-if="isCompact && !railCollapsed"
        type="button"
        class="graph-rail-scrim"
        :aria-label="t('graph.closeFiles')"
        @click="closeRail"
      />

      <section
        class="graph-canvas"
        :data-simulation-phase="interaction.simulationPhase.value"
        :inert="isCompact && !railCollapsed ? true : undefined"
      >
        <div
          data-testid="graph-output-workspace"
          class="graph-stage"
          :data-simulation-phase="interaction.simulationPhase.value"
          :inert="isPreviewSheet && previewNode ? true : undefined"
        >
        <div class="graph-toolbar">
          <div class="graph-title"><Network /><span>{{ t("graph.view") }}</span></div>
          <form @submit.prevent="workspace.runGraphRag"><Search /><input v-model="workspace.graphRagQuestion.value" :placeholder="t('graph.search')" /><button :aria-label="t('graph.run')"><Send /></button></form>
          <div class="graph-tabs">
            <button :class="{ active: interaction.activeFilter.value === 'all' }" :aria-pressed="interaction.activeFilter.value === 'all'" @click="setGraphFilter('all')">{{ t("graph.allNodes") }}</button>
            <button :class="{ active: interaction.activeFilter.value === 'tags' }" :aria-pressed="interaction.activeFilter.value === 'tags'" @click="setGraphFilter('tags')">{{ t("graph.tags") }}</button>
            <button :class="{ active: interaction.activeFilter.value === 'orphans' }" :aria-pressed="interaction.activeFilter.value === 'orphans'" @click="setGraphFilter('orphans')">{{ t("graph.orphans") }}</button>
            <UiPopover v-model="filtersOpen" align="end" :aria-label="t('graph.nodeTypes')">
              <template #trigger="{ props: triggerProps }">
                <button v-bind="triggerProps" type="button" :aria-label="t('graph.filters')"><SlidersHorizontal /></button>
              </template>
              <div data-testid="graph-node-type-filters" class="graph-filter-panel" role="group" :aria-label="t('graph.nodeTypes')">
                <small>{{ t("graph.nodeTypes") }}</small>
                <button v-for="nodeType in interaction.nodeTypes.value" :key="nodeType" :class="{ active: interaction.isNodeTypeEnabled(nodeType) }" :aria-pressed="interaction.isNodeTypeEnabled(nodeType)" @click="toggleGraphNodeType(nodeType)">{{ nodeTypeLabel(nodeType) }}</button>
              </div>
            </UiPopover>
          </div>
        </div>
        <p v-if="workspace.graphRagStatus.value" class="graph-status">{{ workspace.graphRagStatus.value }}</p>

        <UiEmptyState v-if="!positionedNodes.length" :title="t('graph.emptyTitle')" :description="t('graph.emptyDescription')">
          <template #icon><Network class="size-5" /></template>
        </UiEmptyState>
        <svg v-else ref="graphSvg" :viewBox="graphViewBox" role="img" :aria-label="t('graph.knowledgeGraph')" @pointerdown="clearGraphSelection" @pointermove="moveGraphNodeDrag" @pointerup="endGraphNodeDrag" @pointercancel="endGraphNodeDrag" @pointerleave="endGraphNodeDrag">
          <g class="graph-edges" stroke="var(--border-strong)" stroke-width="1">
            <line v-for="edge in positionedEdges" :key="edge.id" :data-focus-state="edgeFocusState(edge.source, edge.target)" :x1="edge.sourceNode!.x" :y1="edge.sourceNode!.y" :x2="edge.targetNode!.x" :y2="edge.targetNode!.y" />
          </g>
          <g v-for="node in positionedNodes" :key="node.id" data-testid="force-node" :data-node-id="node.id" :data-focus-state="nodeFocusState(node.id)" :data-label-visible="interaction.labelVisible(node.id, zoom, hoveredNodeId)" class="graph-node" role="button" tabindex="0" :aria-label="node.label" @pointerdown="startGraphNodeDrag(node, $event)" @click.stop="handleGraphNodeClick(node, $event)" @dblclick.stop="openGraphDocument(node)" @mouseenter="hoveredNodeId = node.id" @mouseleave="hoveredNodeId = null" @focus="hoveredNodeId = node.id" @blur="hoveredNodeId = null" @keydown.enter.prevent="openGraphDocument(node)" @keydown.space.prevent="selectGraphNode(node, true)">
            <circle :cx="node.x" :cy="node.y" :r="nodeRadius(node)" :fill="nodeFill(node)" :stroke="node.depth === 0 ? 'color-mix(in srgb, var(--accent) 55%, white)' : 'transparent'" :stroke-width="node.depth === 0 ? 4 : 0" />
            <text v-if="interaction.labelVisible(node.id, zoom, hoveredNodeId)" :x="node.x" :y="node.y + nodeRadius(node) + 22" fill="var(--text-primary)" :font-size="node.depth === 0 ? 18 : 14" :font-weight="node.depth === 0 ? 600 : 500" text-anchor="middle">{{ node.label }}</text>
          </g>
        </svg>

        <button ref="railTrigger" data-testid="graph-file-rail-toggle" class="rail-toggle" :title="railCollapsed ? t('graph.expandFiles') : t('graph.collapseFiles')" @click="toggleRail"><ChevronLeft :class="{ rotate: railCollapsed }" /></button>
        <div class="zoom-controls"><button :aria-label="t('graph.zoomIn')" @click="setZoom(zoom + 0.15)"><ZoomIn /></button><button :aria-label="t('graph.zoomOut')" @click="setZoom(zoom - 0.15)"><ZoomOut /></button><button :aria-label="t('graph.center')" @click="centerGraph"><Target /></button><button :aria-label="t('graph.restart')" @click="restartGraphLayout"><Play /></button></div>
        </div>

        <button
          v-if="previewNode && isPreviewSheet"
          type="button"
          class="graph-preview-scrim"
          :aria-label="t('graph.closePreview')"
          @click="hideGraphDocumentPreview"
        />

        <Transition name="graph-preview">
          <aside
            v-if="previewNode"
            ref="previewPanel"
            data-testid="graph-document-preview-panel"
            class="graph-preview"
            :class="{ 'graph-preview--instant': previewInstant }"
            :role="isPreviewSheet ? 'dialog' : undefined"
            :aria-modal="isPreviewSheet ? 'true' : undefined"
            :aria-label="t('graph.preview')"
            tabindex="-1"
          >
            <header><small>{{ t("graph.properties") }}</small><button :aria-label="t('graph.closePreview')" @click="hideGraphDocumentPreview"><X /></button></header>
            <h2>{{ workspace.documentPreview.value?.file_name ?? previewNode.label }}</h2>
            <div class="tags"><span>#{{ previewNode.node_type }}</span><span>#{{ workspace.documentPreview.value?.file_type ?? "graph" }}</span></div>
            <section><small>{{ t("graph.summary") }}</small><p>{{ workspace.documentPreview.value?.summary ?? t("graph.fallbackSummary", { name: previewNode.label }) }}</p><a href="#document" @click.prevent="openSelectedDocument">{{ t("graph.readFull") }}</a></section>
            <section v-if="workspace.documentPreview.value?.memory_entries.length"><small>{{ t("graph.backlinks") }}</small><article v-for="entry in workspace.documentPreview.value.memory_entries" :key="entry.entry_id"><strong>{{ entry.entry_name }}</strong><p>{{ entry.summary }}</p></article></section>
          </aside>
        </Transition>
      </section>
    </div>
  </div>
</template>

<style scoped>
.graph-layout, .graph-grid { height: 100%; min-height: 0; overflow: hidden; background: var(--bg-canvas); }
.graph-grid { position: relative; display: grid; grid-template-columns: 280px minmax(0, 1fr); }
.graph-grid.graph-grid--rail-closed { grid-template-columns: 0 minmax(0, 1fr); }
.graph-file-panel { min-width: 0; overflow: auto; background: var(--bg-sidebar); border-right: 1px solid var(--border-muted); }
.graph-file-panel[aria-hidden="true"] { visibility: hidden; overflow: hidden; pointer-events: none; }
.graph-file-panel header { display: flex; height: 3.5rem; align-items: center; justify-content: space-between; padding: 0 1rem; border-bottom: 1px solid var(--border-muted); }
.graph-file-panel header button { display: grid; width: 2rem; height: 2rem; place-items: center; color: var(--text-secondary); background: transparent; border: 0; border-radius: var(--radius-control); }
.graph-file-panel small { color: var(--text-tertiary); font: 0.62rem var(--font-mono); text-transform: uppercase; }
.graph-file-panel h2 { margin: 0.1rem 0 0; font-size: 0.9rem; }
.graph-file-panel nav { display: grid; gap: 0.2rem; padding: 0.8rem; }
.graph-file-panel nav section { display: grid; gap: 0.18rem; }
.graph-file-panel h3, .graph-file-panel nav button { display: flex; min-width: 0; align-items: center; gap: 0.55rem; margin: 0; padding: 0.55rem; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.35rem; font-size: 0.78rem; text-align: left; }
.graph-file-panel h3 { color: var(--text-primary); font-weight: 500; }
.graph-file-panel nav section button { padding-left: 1.9rem; }
.graph-file-panel nav button.active { color: var(--accent); background: var(--accent-soft); }
.graph-file-panel svg { width: 1rem; flex: 0 0 auto; }
.graph-file-panel nav span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.graph-canvas { display: grid; min-width: 0; overflow: hidden; grid-template-columns: minmax(0, 1fr) auto; background: var(--bg-canvas); }
.graph-stage { position: relative; min-width: 0; min-height: 0; overflow: hidden; }
.graph-stage > svg { width: 100%; height: 100%; min-height: 620px; touch-action: none; user-select: none; }
.graph-node { cursor: grab; }
.graph-node:active { cursor: grabbing; }
.graph-node:focus { outline: none; }
.graph-node:focus-visible circle { stroke: var(--accent); stroke-width: 3; }
.graph-node, .graph-edges line { transition: opacity 140ms ease; }
.graph-node[data-focus-state="dimmed"], .graph-edges line[data-focus-state="dimmed"] { opacity: 0.16; }
.graph-node[data-focus-state="selected"] circle { stroke: var(--accent); stroke-width: 3; }
.graph-node[data-focus-state="neighbor"] { opacity: 0.94; }
.graph-edges line[data-focus-state="connected"] { opacity: 0.9; stroke: color-mix(in srgb, var(--accent) 52%, var(--border-strong)); stroke-width: 1.4; }
.graph-toolbar { position: absolute; top: 4.25rem; right: 1rem; left: 1rem; z-index: 10; display: grid; min-width: 0; grid-template-columns: auto minmax(14rem, 1fr) auto; align-items: center; gap: 0.35rem; padding: 0.35rem; background: color-mix(in srgb, var(--bg-panel) 94%, transparent); border: 1px solid var(--border-muted); border-radius: 0.55rem; box-shadow: var(--shadow-float); backdrop-filter: blur(12px); }
.graph-title, .graph-toolbar form, .graph-tabs, .zoom-controls { display: flex; align-items: center; }
.graph-title { height: 2.5rem; gap: 0.5rem; padding: 0 0.65rem; font-size: 0.78rem; white-space: nowrap; }
.graph-title svg { width: 1rem; color: var(--accent); }
.graph-toolbar form { height: 2.5rem; min-width: 0; gap: 0.45rem; padding: 0 0.65rem; background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.graph-toolbar form > svg { width: 1rem; color: var(--text-tertiary); }
.graph-toolbar input { min-width: 0; flex: 1; background: transparent; border: 0; outline: 0; }
.graph-toolbar form button, .graph-tabs button, .zoom-controls button, .graph-preview button { display: grid; place-items: center; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.3rem; }
.graph-toolbar form button svg { width: 0.95rem; color: var(--accent); }
.graph-tabs { height: 2.5rem; gap: 0.15rem; padding: 0.25rem; box-shadow: none; }
.graph-tabs button { height: 2rem; padding: 0 0.65rem; font-size: 0.72rem; }
.graph-tabs button.active { color: var(--accent); background: var(--accent-soft); }
.graph-tabs svg { width: 1rem; }
.graph-filter-panel { display: flex; width: min(32rem, calc(100vw - 2rem)); flex-wrap: wrap; gap: 0.35rem; }
.graph-filter-panel small { width: 100%; color: var(--text-tertiary); font: 0.62rem var(--font-mono); text-transform: uppercase; }
.graph-filter-panel button { padding: 0.35rem 0.55rem; color: var(--text-secondary); background: var(--bg-canvas); border: 1px solid var(--border-muted); border-radius: 0.35rem; font-size: 0.7rem; text-transform: capitalize; }
.graph-filter-panel button.active { color: var(--accent); background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent) 45%, var(--border-muted)); }
.graph-status { position: absolute; top: 7.85rem; left: 1rem; z-index: 12; max-width: min(28rem, calc(100% - 2rem)); padding: 0.65rem 0.8rem; color: var(--text-secondary); background: var(--bg-panel); border-left: 2px solid var(--accent); font-size: 0.75rem; }
.graph-preview { position: relative; z-index: 45; width: 320px; min-height: 0; overflow: auto; padding: 1rem; background: var(--bg-panel); border-left: 1px solid var(--border-muted); }
.graph-preview-scrim { position: absolute; inset: 0; z-index: 44; width: 100%; background: rgb(0 0 0 / 34%); border: 0; }
.graph-preview header { display: flex; justify-content: space-between; }
.graph-preview header small, .graph-preview section small { color: var(--text-tertiary); font: 0.64rem var(--font-mono); text-transform: uppercase; }
.graph-preview button svg { width: 1rem; }
.graph-preview h2 { margin: 0.9rem 0 0; font: 600 1.6rem var(--font-serif); }
.graph-preview .tags { display: flex; gap: 0.35rem; margin-top: 0.7rem; }
.graph-preview .tags span { padding: 0.2rem 0.35rem; color: var(--accent); background: var(--accent-soft); border-radius: 0.25rem; font-size: 0.65rem; }
.graph-preview section { margin-top: 1.2rem; }
.graph-preview p { color: var(--text-secondary); font-size: 0.8rem; line-height: 1.6; }
.graph-preview a { display: inline-block; margin-top: 0.3rem; color: var(--accent); font-size: 0.75rem; text-decoration: none; }
.graph-preview article { margin-top: 0.6rem; padding-left: 0.7rem; border-left: 2px solid var(--accent); }
.graph-preview-enter-active { transition: transform 200ms ease-out, opacity 160ms ease-out; }
.graph-preview-leave-active { transition: transform 140ms ease, opacity 120ms ease; }
.graph-preview-enter-from, .graph-preview-leave-to { opacity: 0; transform: translateX(100%); }
.graph-preview-enter-active.graph-preview--instant, .graph-preview-leave-active.graph-preview--instant { transition: none; }
.rail-toggle { position: absolute; top: 50%; left: 0.4rem; z-index: 35; display: grid; width: 2.2rem; height: 2.6rem; place-items: center; color: var(--text-secondary); background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.4rem; }
.rail-toggle svg { width: 1rem; }
.rail-toggle svg.rotate { transform: rotate(180deg); }
.graph-rail-scrim { position: absolute; inset: 0; z-index: 29; width: 100%; background: rgb(0 0 0 / 38%); border: 0; }
.zoom-controls { position: absolute; right: 1rem; bottom: 3.5rem; gap: 0.15rem; padding: 0.25rem; background: var(--bg-panel); border: 1px solid var(--border-muted); border-radius: 0.45rem; box-shadow: var(--shadow-float); }
.zoom-controls button { width: 2.3rem; height: 2.3rem; }
.zoom-controls svg { width: 1rem; }
@media (hover: hover) and (pointer: fine) {
  .graph-toolbar form button:hover, .graph-tabs button:hover, .zoom-controls button:hover, .graph-preview button:hover { color: var(--accent); background: var(--accent-soft); }
}
@media (max-width: 1024px) {
  .graph-grid, .graph-grid.graph-grid--rail-closed { grid-template-columns: minmax(0, 1fr); }
  .graph-file-panel { position: absolute; inset: 0 auto 0 0; z-index: 30; width: min(84vw, 320px); box-shadow: var(--shadow-float); }
  .graph-file-panel[aria-hidden="true"] { display: none; }
}
@media (max-width: 900px) {
  .graph-canvas { position: relative; display: block; }
  .graph-stage { height: 100%; }
  .graph-preview { position: absolute; right: 0; bottom: 0; left: 0; width: auto; max-height: min(52%, 28rem); border-top: 1px solid var(--border-muted); border-left: 0; border-radius: 0.75rem 0.75rem 0 0; box-shadow: var(--shadow-float); }
  .graph-preview-enter-from, .graph-preview-leave-to { transform: translateY(100%); }
}
@media (max-width: 767px) {
  .graph-toolbar { top: 3.85rem; right: 0.6rem; left: 0.6rem; grid-template-columns: 2.5rem minmax(0, 1fr); }
  .graph-title { width: 2.5rem; padding: 0; justify-content: center; }
  .graph-title span { display: none; }
  .graph-toolbar form { width: 100%; }
  .graph-tabs { grid-column: 1 / -1; overflow-x: auto; }
  .graph-status { top: 10.75rem; }
  .graph-stage > :deep(.ui-empty-state) { min-height: 100%; padding-top: 9rem; padding-bottom: 6rem; }
  .graph-stage > svg { min-height: 560px; }
  .zoom-controls { right: 0.75rem; bottom: 4.25rem; }
}
@media (prefers-reduced-motion: reduce) {
  .graph-node, .graph-edges line, .graph-preview-enter-active, .graph-preview-leave-active { transition-duration: 0.01ms; }
  .graph-preview-enter-from, .graph-preview-leave-to { transform: none; }
}
</style>
