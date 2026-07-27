<script setup lang="ts">
import type { Component } from "vue";
import { computed } from "vue";
import {
  BookOpen,
  BrainCircuit,
  Brain,
  FlaskConical,
  GitBranch,
  LifeBuoy,
  Network,
  Plus,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
  FolderOpen,
} from "@lucide/vue";
import ActivityBar from "./components/shell/ActivityBar.vue";
import MobileNavigation from "./components/shell/MobileNavigation.vue";
import MoreNavigationSheet from "./components/shell/MoreNavigationSheet.vue";
import ResourceSidebar from "./components/shell/ResourceSidebar.vue";
import StatusBar from "./components/shell/StatusBar.vue";
import WorkspaceToolbar from "./components/shell/WorkspaceToolbar.vue";
import UiButton from "./components/ui/UiButton.vue";
import UiField from "./components/ui/UiField.vue";
import UiIconButton from "./components/ui/UiIconButton.vue";
import UiSkeleton from "./components/ui/UiSkeleton.vue";
import UiStatusPanel from "./components/ui/UiStatusPanel.vue";
import { useI18n } from "./composables/useI18n";
import { useMnemeWorkspace } from "./composables/useMnemeWorkspace";
import { useResponsiveShell } from "./composables/useResponsiveShell";
import type { WorkspaceView } from "./types";
import AiLabView from "./views/AiLabView.vue";
import DashboardView from "./views/DashboardView.vue";
import GraphView from "./views/GraphView.vue";
import SettingsView from "./views/SettingsView.vue";
import MemoryCenterView from "./views/MemoryCenterView.vue";
import VaultView from "./views/VaultView.vue";

type ViewItem = { id: WorkspaceView; label: string; shortLabel: string; icon: Component; hint: string };

const workspace = useMnemeWorkspace();
const shell = useResponsiveShell();
const { formatDate, t } = useI18n();

const VIEW_ITEMS = computed<ViewItem[]>(() => [
  { id: "dashboard", label: t("nav.map"), shortLabel: t("nav.short.map"), icon: Network, hint: t("nav.hint.map") },
  { id: "notes", label: t("nav.vault"), shortLabel: t("nav.short.vault"), icon: FolderOpen, hint: t("nav.hint.vault") },
  { id: "graph", label: t("nav.graph"), shortLabel: t("nav.short.graph"), icon: GitBranch, hint: t("nav.hint.graph") },
  { id: "ai", label: t("nav.ai"), shortLabel: t("nav.short.ai"), icon: FlaskConical, hint: t("nav.hint.ai") },
  { id: "memory", label: `${t("nav.memory")}${workspace.memoryPendingCount.value ? ` (${workspace.memoryPendingCount.value})` : ""}`, shortLabel: t("nav.short.memory"), icon: Brain, hint: t("nav.hint.memory") },
  { id: "settings", label: t("nav.settings"), shortLabel: t("nav.short.settings"), icon: SlidersHorizontal, hint: t("nav.hint.settings") },
]);

const currentViewItem = computed(() => VIEW_ITEMS.value.find((item) => item.id === workspace.view.value) ?? VIEW_ITEMS.value[0]);
const primaryNavigationItems = computed(() => VIEW_ITEMS.value.slice(0, 4));
const secondaryNavigationItems = computed(() => VIEW_ITEMS.value.slice(4));
const moreNavigationActive = computed(() => secondaryNavigationItems.value.some((item) => item.id === workspace.view.value) || shell.moreOpen.value);
const activeHealthLabel = computed(() => workspace.readiness.value?.overall_status ?? workspace.serviceHealth.value?.status ?? "preview");
const activeViewLoadState = computed(() => workspace.viewLoadStates[workspace.view.value]);
const activeViewLoading = computed(() => activeViewLoadState.value.phase.value === "loading");
const toolbarContext = computed(() => workspace.selectedKnowledgeBase.value?.name ?? "");
const resourceTitle = computed(() => {
  if (workspace.view.value === "ai") return t("nav.ai");
  if (workspace.view.value === "graph") return t("nav.graph");
  if (workspace.view.value === "notes") return t("nav.vault");
  return t("shell.researchSpaces");
});

function navigate(id: string) {
  workspace.view.value = id as WorkspaceView;
  shell.closeOverlays();
}

function openCreateCommand() {
  workspace.workspaceCommandTab.value = "create";
  workspace.view.value = "dashboard";
  shell.closeOverlays();
}
</script>

<template>
  <main v-if="!workspace.isAuthenticated.value" class="auth-screen">
    <section class="auth-layout">
      <aside class="auth-story">
        <header class="auth-brand"><div class="auth-mark"><BrainCircuit /></div><div><strong>Mneme</strong><span>{{ t("auth.brandKicker") }}</span></div></header>
        <div class="auth-story__copy">
          <p>{{ t("auth.brandKicker") }}</p>
          <h1>{{ t("auth.brandTitle") }}</h1>
          <span>{{ t("auth.brandDescription") }}</span>
        </div>
        <div class="auth-capabilities">
          <div><BookOpen /><span>{{ t("auth.capability.capture") }}</span></div>
          <div><Network /><span>{{ t("auth.capability.connect") }}</span></div>
          <div><Brain /><span>{{ t("auth.capability.remember") }}</span></div>
        </div>
      </aside>

      <section class="auth-card">
        <header class="auth-card__brand"><div class="auth-mark"><BrainCircuit /></div><div><strong>Mneme</strong><span>{{ t("auth.brandKicker") }}</span></div></header>
        <div class="auth-card__intro">
          <h2>{{ t("auth.welcome") }}</h2>
          <p>{{ workspace.authMode.value === "login" ? t("auth.loginDescription") : t("auth.registerDescription") }}</p>
        </div>
        <div class="auth-mode" role="group" :aria-label="t('auth.mode')">
          <button type="button" :class="{ active: workspace.authMode.value === 'login' }" @click="workspace.setAuthMode('login')">{{ t("auth.login") }}</button>
          <button type="button" :class="{ active: workspace.authMode.value === 'register' }" @click="workspace.setAuthMode('register')">{{ t("auth.register") }}</button>
        </div>
        <form v-if="workspace.authMode.value === 'login'" @submit.prevent="workspace.login">
          <UiField :label="t('auth.username')" required :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.loginForm.value.username" autocomplete="username" /></template>
          </UiField>
          <UiField :label="t('auth.password')" required :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.loginForm.value.password" type="password" autocomplete="current-password" /></template>
          </UiField>
          <p v-if="workspace.authError.value" class="auth-error" role="alert">{{ workspace.authError.value }}</p>
          <UiButton type="submit" variant="primary" :loading="workspace.authPending.value">
            <template #icon><ShieldCheck /></template>{{ t("auth.login") }}
          </UiButton>
        </form>
        <form v-else @submit.prevent="workspace.register">
          <UiField :label="t('auth.username')" required :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.registerForm.value.username" autocomplete="username" minlength="3" /></template>
          </UiField>
          <UiField :label="t('auth.displayName')" :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.registerForm.value.displayName" autocomplete="name" /></template>
          </UiField>
          <UiField :label="t('auth.password')" required :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.registerForm.value.password" type="password" autocomplete="new-password" minlength="8" /></template>
          </UiField>
          <UiField :label="t('auth.confirmPassword')" required :disabled="workspace.authPending.value">
            <template #default="{ props: fieldProps }"><input v-bind="fieldProps" v-model="workspace.registerForm.value.confirmPassword" type="password" autocomplete="new-password" minlength="8" /></template>
          </UiField>
          <p v-if="workspace.authError.value" class="auth-error" role="alert">{{ workspace.authError.value }}</p>
          <UiButton type="submit" variant="primary" :loading="workspace.authPending.value">
            <template #icon><ShieldCheck /></template>{{ t("auth.createAccount") }}
          </UiButton>
        </form>
      </section>
    </section>
  </main>

  <main v-else data-testid="obsidian-shell" class="mneme-workbench">
    <input
      id="workspace-upload"
      :key="workspace.uploadInputKey.value"
      class="sr-only"
      type="file"
      :aria-label="t('reader.uploadDocument')"
      @change="workspace.uploadFile(($event.target as HTMLInputElement).files?.[0])"
    />
    <div class="mneme-shell" :class="{ 'mneme-shell--resource-closed': !shell.resourceOpen.value }">
      <ActivityBar
        :items="VIEW_ITEMS"
        :active-id="workspace.view.value"
        :resource-open="shell.resourceOpen.value"
        @create="openCreateCommand"
        @toggle-resource="shell.toggleResource"
        @navigate="navigate"
      />

      <ResourceSidebar :open="shell.resourceOpen.value" @close="shell.closeOverlays">
        <div data-testid="sanctuary-sidebar" class="explorer">
          <header class="explorer-brand">
            <div class="brand-mark"><BrainCircuit /></div>
            <div><h1>{{ resourceTitle }}</h1><p>{{ currentViewItem.hint }}</p></div>
          </header>
          <button class="new-research" @click="openCreateCommand"><Plus />{{ t("shell.newResearch") }}</button>

          <nav class="explorer-scroll">
            <section v-if="workspace.view.value === 'ai'" data-testid="sidebar-group-chats">
              <header><span>{{ t("nav.ai") }}</span></header>
              <button
                v-for="session in workspace.chatSessions.value.slice(0, 10)"
                :key="session.id"
                :class="{ active: workspace.activeChatSessionId.value === session.id }"
                @click="workspace.selectChatSession(session.id)"
              >
                <strong>{{ session.title || "Untitled chat" }}</strong>
                <small>{{ session.message_count }} messages · {{ formatDate(session.updated_at) }}</small>
              </button>
            </section>
            <section v-else-if="workspace.view.value === 'notes' || workspace.view.value === 'graph'" data-testid="sidebar-group-context-files">
              <header><span>{{ workspace.view.value === "graph" ? t("nav.graph") : t("shell.recentFiles") }}</span></header>
              <button
                v-for="doc in workspace.selectedDocuments.value.slice(0, 10)"
                :key="doc.id"
                @click="workspace.openDocument(doc.id)"
              >
                <strong>{{ doc.file_name }}</strong>
                <small>{{ doc.status }} · {{ formatDate(doc.created_at) }}</small>
              </button>
            </section>
            <section data-testid="sidebar-group-vaults">
              <header><span>{{ t("shell.researchSpaces") }}</span><UiIconButton label="Create vault" size="sm" @click="openCreateCommand"><Plus /></UiIconButton></header>
              <button v-for="vault in workspace.knowledgeBases.value" :key="vault.id" :class="{ active: workspace.selectedKnowledgeBaseId.value === vault.id }" @click="workspace.selectKnowledgeBase(vault.id)">
                <strong>{{ vault.name }}</strong><small>{{ vault.description || t("shell.noDescription") }}</small>
              </button>
            </section>
            <section v-if="workspace.view.value !== 'ai' && workspace.view.value !== 'notes' && workspace.view.value !== 'graph'" data-testid="sidebar-group-files">
              <header><span>{{ t("shell.recentFiles") }}</span></header>
              <button v-for="doc in workspace.selectedDocuments.value.slice(0, 6)" :key="doc.id" @click="workspace.openDocument(doc.id)"><strong>{{ doc.file_name }}</strong><small>{{ doc.status }} · {{ formatDate(doc.created_at) }}</small></button>
            </section>
          </nav>

          <footer>
            <button @click="workspace.showDocumentationStatus"><BookOpen />{{ t("shell.documentation") }}</button>
            <button @click="workspace.showSupportStatus"><LifeBuoy />{{ t("shell.support") }}</button>
            <div class="user-card"><div><UserRound /></div><span><strong>{{ workspace.user.value?.display_name || t("shell.previewUser") }}</strong><small>{{ workspace.user.value?.username }}</small></span></div>
          </footer>
        </div>
      </ResourceSidebar>

      <section class="mneme-shell__main">
        <WorkspaceToolbar
          v-if="workspace.view.value !== 'graph'"
          v-model:notifications-open="workspace.notificationPanelOpen.value"
          :title="currentViewItem.label"
          :hint="currentViewItem.hint"
          :context="toolbarContext"
          :health-label="activeHealthLabel"
          :notification-count="workspace.notificationUnreadCount.value"
          :compact="workspace.view.value === 'ai'"
          @toggle-resources="shell.toggleResource"
          @refresh="workspace.loadKnowledgeBasePanels"
          @logout="workspace.logout"
        >
          <template #notifications>
            <section data-testid="notification-center-panel" class="notification-panel" aria-label="Notifications">
              <header><strong>Notifications</strong><button type="button" @click="workspace.refreshNotifications">Refresh</button></header>
              <p v-if="!workspace.notifications.value.length" class="notification-empty">You are all caught up.</p>
              <button
                v-for="notification in workspace.notifications.value"
                :key="notification.id"
                type="button"
                class="notification-item"
                :class="{ unread: !notification.read_at }"
                @click="workspace.readNotification(notification.id)"
              >
                <span><strong>{{ notification.title }}</strong><small>{{ formatDate(notification.created_at) }}</small></span>
                <p>{{ notification.body }}</p>
              </button>
            </section>
          </template>
        </WorkspaceToolbar>
        <UiStatusPanel v-if="workspace.banner.value" class="workspace-banner" :title="workspace.banner.value" dismissible @dismiss="workspace.dismissBanner" />
        <UiStatusPanel v-if="workspace.authNotice.value" class="workspace-banner" :title="workspace.authNotice.value" />
        <UiStatusPanel v-if="workspace.documentActionStatus.value" class="workspace-banner" :title="workspace.documentActionStatus.value" />
        <UiStatusPanel v-if="activeViewLoadState.message.value" class="workspace-banner" :title="activeViewLoadState.message.value" variant="warning" />
        <UiStatusPanel
          v-if="workspace.duplicateUpload.value"
          data-testid="duplicate-upload-notice"
          class="workspace-banner"
          :title="`${workspace.duplicateUpload.value.file_name} already exists`"
        >
          <template #action><button type="button" @click="workspace.openDuplicateUpload">Open existing file</button></template>
        </UiStatusPanel>

        <section data-testid="obsidian-editor-pane" class="workspace-content">
          <div
            v-if="workspace.isLoading.value || activeViewLoading"
            class="workspace-loading"
            :class="{ 'workspace-loading--dashboard': workspace.view.value === 'dashboard' }"
            aria-label="Loading workspace"
          >
            <template v-if="workspace.view.value === 'dashboard'">
              <div class="workspace-loading__hero">
                <div><UiSkeleton width="28%" height="0.7rem" /><UiSkeleton width="62%" height="2.5rem" /><UiSkeleton width="88%" height="0.8rem" /></div>
                <UiSkeleton width="100%" height="8.5rem" />
              </div>
              <div class="workspace-loading__metrics"><UiSkeleton v-for="index in 3" :key="index" width="100%" height="4.8rem" /></div>
              <div class="workspace-loading__body"><UiSkeleton width="100%" height="18rem" /><UiSkeleton width="100%" height="22rem" /></div>
            </template>
            <template v-else>
              <UiSkeleton width="38%" height="1.8rem" />
              <UiSkeleton width="72%" height="0.8rem" />
              <UiSkeleton width="100%" height="13rem" />
            </template>
          </div>
          <DashboardView v-else-if="workspace.view.value === 'dashboard'" :workspace="workspace" />
          <VaultView v-else-if="workspace.view.value === 'notes'" :workspace="workspace" @create="openCreateCommand" />
          <GraphView v-else-if="workspace.view.value === 'graph'" :workspace="workspace" />
          <AiLabView v-else-if="workspace.view.value === 'ai'" :workspace="workspace" :format-date="formatDate" />
          <MemoryCenterView v-else-if="workspace.view.value === 'memory'" :workspace="workspace" />
          <SettingsView v-else :workspace="workspace" :health-label="activeHealthLabel" :format-date="formatDate" />
        </section>

        <StatusBar :status="activeHealthLabel" :detail="workspace.selectedKnowledgeBase.value?.name" />
      </section>

      <MobileNavigation
        :items="primaryNavigationItems"
        :active-id="workspace.view.value"
        :more-active="moreNavigationActive"
        @open-more="shell.openMore"
        @navigate="navigate"
      />
      <MoreNavigationSheet
        :open="shell.moreOpen.value"
        :items="secondaryNavigationItems"
        :active-id="workspace.view.value"
        :user-name="workspace.user.value?.display_name || t('shell.previewUser')"
        @close="shell.closeMore"
        @navigate="navigate"
        @documentation="workspace.showDocumentationStatus"
        @support="workspace.showSupportStatus"
        @logout="workspace.logout"
      />
    </div>
  </main>
</template>

<style scoped>
.auth-screen { display: grid; min-height: 100vh; place-items: center; padding: clamp(1rem, 4vw, 3rem); color: var(--content-primary); background: radial-gradient(circle at 22% 18%, color-mix(in srgb, var(--accent-primary) 9%, transparent), transparent 34rem), var(--surface-canvas); }
.auth-layout { display: grid; width: min(100%, 1040px); grid-template-columns: minmax(0, 1.05fr) minmax(22rem, 0.75fr); overflow: hidden; background: var(--surface-panel); border: 1px solid var(--stroke-subtle); border-radius: calc(var(--radius-panel) + 4px); box-shadow: var(--shadow-popover); }
.auth-story { display: flex; min-height: 39rem; flex-direction: column; justify-content: space-between; padding: clamp(2rem, 5vw, 4rem); background: linear-gradient(145deg, color-mix(in srgb, var(--surface-sidebar) 88%, var(--accent-subtle)), var(--surface-sidebar)); border-right: 1px solid var(--stroke-subtle); }
.auth-brand, .auth-card__brand { display: flex; align-items: center; gap: 0.75rem; }
.auth-brand strong, .auth-brand span, .auth-card__brand strong, .auth-card__brand span { display: block; }
.auth-brand strong, .auth-card__brand strong { font: 600 1rem var(--font-serif); }
.auth-brand span, .auth-card__brand span { margin-top: 0.12rem; color: var(--content-tertiary); font-size: var(--font-size-xs); }
.auth-story__copy { max-width: 31rem; }
.auth-story__copy p { margin: 0; color: var(--accent-primary); font: 600 var(--font-size-xs) var(--font-mono); text-transform: uppercase; letter-spacing: 0.1em; }
.auth-story__copy h1 { margin: 0.75rem 0 0; font: 600 clamp(2rem, 4vw, 3.5rem) var(--font-serif); line-height: 1.08; text-wrap: balance; }
.auth-story__copy > span { display: block; max-width: 28rem; margin-top: 1rem; color: var(--content-secondary); line-height: 1.75; }
.auth-capabilities { display: grid; gap: 0.75rem; }
.auth-capabilities > div { display: flex; align-items: center; gap: 0.75rem; color: var(--content-secondary); font-size: var(--font-size-sm); }
.auth-capabilities svg { width: 1rem; color: var(--accent-primary); }
.auth-card { display: flex; flex-direction: column; justify-content: center; padding: clamp(1.5rem, 5vw, 3.25rem); }
.auth-card__brand { display: none; }
.auth-mark, .brand-mark { display: grid; width: 2.4rem; height: 2.4rem; place-items: center; color: var(--accent); background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent) 35%, var(--border-muted)); border-radius: 0.5rem; }
.auth-mark svg, .brand-mark svg { width: 1.1rem; }
.auth-card__intro h2 { margin: 0; font: 600 1.55rem var(--font-serif); }
.auth-card__intro p { margin: 0.4rem 0 0; color: var(--content-secondary); font-size: var(--font-size-sm); line-height: 1.6; }
.auth-card form { display: grid; gap: 0.8rem; margin-top: 1.2rem; }
.auth-card form :deep(.ui-button) { width: 100%; margin-top: 0.15rem; }
.auth-mode { display: grid; grid-template-columns: 1fr 1fr; gap: 0.2rem; margin-top: 1.35rem; padding: 0.2rem; background: var(--surface-sidebar); border: 1px solid var(--stroke-subtle); border-radius: var(--radius-control); }
.auth-mode button { min-height: 2.15rem; color: var(--content-secondary); background: transparent; border: 0; border-radius: calc(var(--radius-control) - 2px); font-weight: 600; transition: color var(--duration-fast) ease, background-color var(--duration-fast) ease, transform var(--duration-press) var(--ease-out-ui); }
.auth-mode button.active { color: var(--content-primary); background: var(--surface-panel); box-shadow: inset 0 0 0 1px var(--stroke-subtle); }
.auth-mode button:active:not(:focus-visible) { transform: scale(0.97); }
.auth-error { margin: 0; color: var(--status-danger); font-size: var(--font-size-xs); line-height: 1.5; }
@media (hover: hover) and (pointer: fine) { .auth-mode button:hover:not(.active) { color: var(--content-primary); background: var(--surface-raised); } }
@media (max-width: 767px) {
  .auth-screen { align-items: start; padding: 0; background: var(--surface-canvas); }
  .auth-layout { display: block; width: 100%; min-height: 100dvh; border: 0; border-radius: 0; box-shadow: none; }
  .auth-story { display: none; }
  .auth-card { min-height: 100dvh; justify-content: start; padding: max(1.25rem, env(safe-area-inset-top)) 1.25rem max(1.25rem, env(safe-area-inset-bottom)); }
  .auth-card__brand { display: flex; margin-bottom: clamp(2.5rem, 12vh, 5rem); }
}
@media (prefers-reduced-motion: reduce) {
  .auth-mode button { transition-property: color, background-color; }
  .auth-mode button:active:not(:focus-visible) { transform: none; }
}
.explorer { display: flex; min-height: 0; flex: 1; flex-direction: column; }
.explorer-brand { display: flex; align-items: center; gap: 0.7rem; padding: 1rem; }
.explorer-brand h1 { margin: 0; font: 600 1.15rem var(--font-serif); }
.explorer-brand p { margin: 0.15rem 0 0; color: var(--text-tertiary); font: 0.6rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.08em; }
.new-research { display: flex; min-height: 2.4rem; align-items: center; justify-content: center; gap: 0.45rem; margin: 0 0.8rem 0.6rem; color: var(--accent-contrast); background: var(--accent); border: 0; border-radius: 0.4rem; font-size: 0.75rem; font-weight: 500; }
.new-research svg { width: 0.9rem; }
.explorer-scroll { flex: 1; overflow: auto; padding: 0.5rem 0.65rem; }
.explorer-scroll section + section { margin-top: 1.25rem; }
.explorer-scroll section > header { display: flex; min-height: 1.8rem; align-items: center; justify-content: space-between; padding: 0 0.35rem; color: var(--text-tertiary); font: 0.62rem var(--font-mono); text-transform: uppercase; letter-spacing: 0.06em; }
.explorer-scroll section > button { display: block; width: 100%; padding: 0.55rem 0.65rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.35rem; }
.explorer-scroll section > button:hover { background: var(--bg-elevated); }
.explorer-scroll section > button.active { color: var(--text-primary); background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.explorer-scroll strong, .explorer-scroll small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.explorer-scroll strong { font-size: 0.78rem; font-weight: 500; }
.explorer-scroll small { margin-top: 0.18rem; color: var(--text-tertiary); font-size: 0.65rem; }
.explorer > footer { display: grid; gap: 0.2rem; padding: 0.65rem; border-top: 1px solid var(--border-muted); }
.explorer > footer > button { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem; color: var(--text-secondary); background: transparent; border: 0; border-radius: 0.35rem; font-size: 0.75rem; }
.explorer > footer > button:hover { color: var(--text-primary); background: var(--bg-elevated); }
.explorer > footer svg { width: 0.95rem; }
.user-card { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.35rem; padding: 0.6rem; background: var(--bg-panel); border-radius: 0.4rem; }
.user-card > div { display: grid; width: 1.8rem; height: 1.8rem; place-items: center; color: var(--accent); background: var(--accent-soft); border-radius: 50%; }
.user-card strong, .user-card small { display: block; }
.user-card strong { font-size: 0.75rem; }
.user-card small { color: var(--text-tertiary); font-size: 0.64rem; }
.workspace-banner { width: 100%; min-width: 0; flex: 0 0 auto; margin: 0; padding: 0.55rem 1rem; color: var(--text-secondary); background: var(--accent-soft); border-width: 0 0 1px; border-radius: 0; font-size: 0.72rem; }
.workspace-content { min-width: 0; min-height: 0; flex: 1; overflow: auto; }
.notification-panel { width: min(22rem, calc(100vw - 2rem)); max-height: min(31rem, calc(100vh - 5rem)); overflow: auto; }
.notification-panel > header { display: flex; align-items: center; justify-content: space-between; padding: 0.45rem 0.55rem 0.6rem; border-bottom: 1px solid var(--border-muted); }
.notification-panel > header strong { font-size: 0.78rem; }
.notification-panel > header button { color: var(--text-tertiary); background: transparent; border: 0; font-size: 0.68rem; }
.notification-item { display: block; width: 100%; margin-top: 0.3rem; padding: 0.65rem; color: var(--text-secondary); text-align: left; background: transparent; border: 0; border-radius: 0.4rem; }
.notification-item:hover, .notification-item:focus-visible { color: var(--text-primary); background: var(--bg-elevated); outline: none; }
.notification-item.unread { background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent); }
.notification-item span { display: flex; align-items: baseline; justify-content: space-between; gap: 0.8rem; }
.notification-item strong { color: var(--text-primary); font-size: 0.75rem; }
.notification-item small { color: var(--text-tertiary); font: 0.58rem var(--font-mono); white-space: nowrap; }
.notification-item p, .notification-empty { margin: 0.35rem 0 0; color: var(--text-secondary); font-size: 0.68rem; line-height: 1.45; }
.notification-empty { padding: 1rem; text-align: center; }
.workspace-loading { display: grid; width: min(100%, 900px); gap: 0.9rem; margin: 0 auto; padding: 2rem; }
.workspace-loading--dashboard { width: min(100%, 1160px); gap: 1.25rem; }
.workspace-loading__hero { display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.72fr); align-items: end; gap: clamp(1.25rem, 4vw, 3.5rem); }
.workspace-loading__hero > div { display: grid; gap: 0.75rem; }
.workspace-loading__metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; }
.workspace-loading__body { display: grid; grid-template-columns: minmax(15rem, 0.7fr) minmax(0, 1.3fr); gap: 1rem; }
@media (max-width: 900px) {
  .workspace-loading__body { grid-template-columns: 1fr; }
}
@media (max-width: 767px) {
  .workspace-loading { padding: 1.1rem; }
  .workspace-loading__hero, .workspace-loading__metrics { grid-template-columns: 1fr; }
}
</style>
