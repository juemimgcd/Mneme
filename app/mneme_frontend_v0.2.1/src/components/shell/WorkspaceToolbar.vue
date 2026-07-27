<script setup lang="ts">
import { Bell, LogOut, PanelLeft, RefreshCw } from "@lucide/vue";
import UiIconButton from "../ui/UiIconButton.vue";
import UiPopover from "../ui/UiPopover.vue";

withDefaults(defineProps<{
  title: string;
  hint: string;
  context?: string;
  healthLabel?: string;
  notificationCount?: number;
  compact?: boolean;
}>(), {
  context: "",
  healthLabel: "",
  notificationCount: 0,
  compact: false,
});

const notificationsOpen = defineModel<boolean>("notificationsOpen", { default: false });
const emit = defineEmits<{ toggleResources: []; refresh: []; logout: [] }>();
</script>

<template>
  <header
    data-testid="sanctuary-topbar"
    class="workspace-toolbar"
    :class="{ 'workspace-toolbar--compact': compact }"
  >
    <div class="workspace-toolbar__leading">
      <UiIconButton
        class="workspace-toolbar__resource-toggle"
        label="Open resources"
        tooltip="Resources"
        @click="emit('toggleResources')"
      ><PanelLeft /></UiIconButton>
      <div data-testid="sanctuary-active-view" class="workspace-toolbar__title">
        <small>{{ hint }}</small>
        <div><h2>{{ title }}</h2><span v-if="context">{{ context }}</span></div>
      </div>
    </div>

    <div class="workspace-toolbar__actions">
      <slot name="actions" />
      <span v-if="healthLabel" class="workspace-toolbar__health">{{ healthLabel }}</span>
      <UiIconButton class="workspace-toolbar__desktop-action" label="Refresh panels" tooltip="Refresh" @click="emit('refresh')"><RefreshCw /></UiIconButton>
      <UiPopover v-model="notificationsOpen" align="end" aria-label="Notifications">
        <template #trigger="{ props: triggerProps }">
          <UiIconButton
            v-bind="triggerProps"
            data-testid="notification-center-toggle"
            :label="notificationCount ? `${notificationCount} unread notifications` : 'Notifications'"
            tooltip="Notifications"
          >
            <Bell />
            <span v-if="notificationCount" class="workspace-toolbar__badge">{{ notificationCount > 9 ? "9+" : notificationCount }}</span>
          </UiIconButton>
        </template>
        <slot name="notifications" />
      </UiPopover>
      <UiIconButton class="workspace-toolbar__desktop-action" label="Log out" tooltip="Log out" @click="emit('logout')"><LogOut /></UiIconButton>
    </div>
  </header>
</template>

<style scoped>
.workspace-toolbar {
  position: relative;
  z-index: 20;
  display: flex;
  min-height: 3.75rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.55rem 1rem;
  background: color-mix(in srgb, var(--surface-canvas) 96%, transparent);
  border-bottom: 1px solid var(--stroke-subtle);
}
.workspace-toolbar--compact { min-height: 3.25rem; }
.workspace-toolbar__leading,
.workspace-toolbar__actions,
.workspace-toolbar__title > div {
  display: flex;
  min-width: 0;
  align-items: center;
}
.workspace-toolbar__leading { gap: 0.55rem; }
.workspace-toolbar__actions { flex: 0 0 auto; gap: 0.25rem; }
.workspace-toolbar__title small {
  display: block;
  color: var(--content-tertiary);
  font: 0.62rem var(--font-mono);
}
.workspace-toolbar__title > div { gap: 0.55rem; }
.workspace-toolbar__title h2 {
  overflow: hidden;
  margin: 0.12rem 0 0;
  font-size: 0.92rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-toolbar__title span {
  overflow: hidden;
  max-width: 15rem;
  margin-top: 0.12rem;
  padding-left: 0.55rem;
  color: var(--content-tertiary);
  border-left: 1px solid var(--stroke-subtle);
  font-size: var(--font-size-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-toolbar__health {
  padding: 0.25rem 0.45rem;
  color: var(--content-tertiary);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
  font: 0.62rem var(--font-mono);
}
.workspace-toolbar__badge {
  position: absolute;
  top: -0.28rem;
  right: -0.28rem;
  display: grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  padding: 0 0.18rem;
  color: white;
  background: var(--danger);
  border: 2px solid var(--surface-canvas);
  border-radius: var(--radius-round);
  font: 0.56rem var(--font-mono);
}
.workspace-toolbar :deep(.ui-icon-button svg) { width: 1rem; height: 1rem; }
.workspace-toolbar__resource-toggle { display: none; }

@media (max-width: 1023px) {
  .workspace-toolbar__resource-toggle { display: inline-grid; }
}
@media (max-width: 767px) {
  .workspace-toolbar { min-height: 3.5rem; gap: 0.5rem; padding-inline: 0.6rem; }
  .workspace-toolbar__title small,
  .workspace-toolbar__title span,
  .workspace-toolbar__health,
  .workspace-toolbar__desktop-action { display: none; }
  .workspace-toolbar__title h2 { margin: 0; font-size: 0.86rem; }
  .workspace-toolbar__actions { gap: 0; }
}
</style>
