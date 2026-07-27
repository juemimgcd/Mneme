<script setup lang="ts">
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  CircleOff,
  Copy,
  Link2,
  MessageSquareMore,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
} from "@lucide/vue";
import { computed, reactive, ref, watch } from "vue";
import type { MnemeWorkspace } from "../../composables/useMnemeWorkspace";
import { useI18n } from "../../composables/useI18n";
import type { AnswerMode, ChannelConversationData } from "../../types";
import UiButton from "../ui/UiButton.vue";
import UiEmptyState from "../ui/UiEmptyState.vue";
import UiStatusPanel from "../ui/UiStatusPanel.vue";

const props = defineProps<{
  workspace: MnemeWorkspace;
  formatDate: (value: string | number | Date) => string;
}>();

const { t } = useI18n();
const drafts = reactive<Record<string, {
  chat_session_id: string;
  knowledge_base_id: string;
  answer_mode: AnswerMode;
}>>({});
const copied = ref("");
const copyFailed = ref("");
const actionTarget = ref("");
const actionFeedback = ref<{ target: string; message: string; tone: "success" | "error" } | null>(null);
const modes = computed<Array<{ value: AnswerMode; label: string }>>(() => [
  { value: "kb_qa", label: t("channel.mode.kb") },
  { value: "memory_query", label: t("channel.mode.memory") },
  { value: "profile_query", label: t("channel.mode.profile") },
  { value: "analysis_query", label: t("channel.mode.analysis") },
  { value: "general_chat", label: t("channel.mode.general") },
]);
const gatewayState = computed<"ready" | "degraded" | "offline">(() => {
  const configuration = props.workspace.channelConfiguration.value;
  if (!configuration || !configuration.enabled) return "offline";
  return configuration.ready ? "ready" : "degraded";
});
const gatewayStateLabel = computed(() => t(`channel.${gatewayState.value}`));
const gatewayStateIcon = computed(() =>
  gatewayState.value === "ready" ? CheckCircle2 : gatewayState.value === "degraded" ? AlertTriangle : CircleOff,
);

function syncDrafts(items: ChannelConversationData[]) {
  items.forEach((item) => {
    drafts[item.id] = {
      chat_session_id: item.chat_session_id,
      knowledge_base_id: item.knowledge_base_id ?? "",
      answer_mode: item.answer_mode,
    };
  });
}

watch(props.workspace.channelConversations, syncDrafts, { immediate: true });

async function copyText(value: string, key: string) {
  copyFailed.value = "";
  try {
    await navigator.clipboard.writeText(value);
    copied.value = key;
    window.setTimeout(() => {
      if (copied.value === key) copied.value = "";
    }, 1600);
  } catch {
    copyFailed.value = key;
  }
}

async function runAction(target: string, action: () => Promise<void>) {
  if (actionTarget.value) return;
  actionTarget.value = target;
  actionFeedback.value = null;
  await action();
  const message = props.workspace.channelActionStatus.value;
  actionFeedback.value = {
    target,
    message,
    tone: /unable|failed|error|无法|失败|错误/i.test(message) ? "error" : "success",
  };
  actionTarget.value = "";
}

function saveConversation(conversationId: string) {
  const draft = drafts[conversationId];
  if (!draft) return;
  void runAction(`route:${conversationId}`, () =>
    props.workspace.updateChannelConversation(conversationId, {
      chat_session_id: draft.chat_session_id || null,
      knowledge_base_id: draft.knowledge_base_id || null,
      answer_mode: draft.answer_mode,
    }),
  );
}

function isRetryable(status: string) {
  return ["failed", "dead_letter"].includes(status);
}
</script>

<template>
  <section id="channels" class="channel-panel" data-testid="channel-gateway-panel">
    <header class="channel-panel__header">
      <div>
        <small>{{ t("channel.kicker") }}</small>
        <h2>{{ t("channel.title") }}</h2>
        <p>{{ t("channel.description") }}</p>
      </div>
      <div class="gateway-actions">
        <span class="readiness" :data-state="gatewayState">
          <component :is="gatewayStateIcon" />
          {{ gatewayStateLabel }}
        </span>
        <UiButton
          variant="ghost"
          size="sm"
          :loading="actionTarget === 'refresh'"
          :disabled="!!actionTarget"
          :aria-label="t('channel.refreshLabel')"
          @click="runAction('refresh', workspace.refreshChannelGateway)"
        >
          <template #icon><RefreshCw /></template>
          {{ t("channel.refresh") }}
        </UiButton>
        <UiStatusPanel
          v-if="actionFeedback?.target === 'refresh'"
          class="gateway-actions__feedback"
          :title="actionFeedback.message"
          :tone="actionFeedback.tone"
        />
      </div>
    </header>

    <div
      v-if="!workspace.channelConfiguration.value"
      class="channel-loading"
      role="status"
      :aria-label="t('channel.loading')"
    >
      <span /><span /><span />
    </div>

    <template v-else>
      <section class="channel-section deployment-section">
        <header class="channel-section__header">
          <div>
            <small>01</small>
            <h3>{{ t("channel.deployment") }}</h3>
            <p>{{ t("channel.deploymentDescription") }}</p>
          </div>
          <code>{{ workspace.channelConfiguration.value.account_id }}</code>
        </header>

        <div class="config-rows">
          <div>
            <span>{{ t("channel.gatewayEnabled") }}</span>
            <strong :data-ok="workspace.channelConfiguration.value.enabled">
              <CheckCircle2 v-if="workspace.channelConfiguration.value.enabled" />
              <AlertTriangle v-else />
              {{ workspace.channelConfiguration.value.enabled ? t("channel.enabled") : t("channel.disabled") }}
            </strong>
          </div>
          <div>
            <span>{{ t("channel.appId") }}</span>
            <strong :data-ok="workspace.channelConfiguration.value.app_id_configured">
              <CheckCircle2 v-if="workspace.channelConfiguration.value.app_id_configured" />
              <AlertTriangle v-else />
              {{ workspace.channelConfiguration.value.app_id_configured ? t("channel.configured") : t("channel.missing") }}
            </strong>
          </div>
          <div>
            <span>{{ t("channel.appSecret") }}</span>
            <strong :data-ok="workspace.channelConfiguration.value.app_secret_configured">
              <CheckCircle2 v-if="workspace.channelConfiguration.value.app_secret_configured" />
              <AlertTriangle v-else />
              {{ workspace.channelConfiguration.value.app_secret_configured ? t("channel.configured") : t("channel.missing") }}
            </strong>
          </div>
          <div>
            <span>{{ t("channel.verificationToken") }}</span>
            <strong :data-ok="workspace.channelConfiguration.value.verification_token_configured">
              <CheckCircle2 v-if="workspace.channelConfiguration.value.verification_token_configured" />
              <AlertTriangle v-else />
              {{ workspace.channelConfiguration.value.verification_token_configured ? t("channel.configured") : t("channel.missing") }}
            </strong>
          </div>
        </div>

        <div class="callback-card">
          <span>{{ t("channel.callbackPath") }}</span>
          <code>{{ workspace.channelConfiguration.value.callback_path }}</code>
          <UiButton
            variant="ghost"
            size="sm"
            :aria-label="t('channel.copyCallback')"
            @click="copyText(workspace.channelConfiguration.value.callback_path, 'callback')"
          >
            <template #icon><Check v-if="copied === 'callback'" /><Copy v-else /></template>
            {{ copied === "callback" ? t("channel.copied") : t("channel.copyCallback") }}
          </UiButton>
          <small v-if="copyFailed === 'callback'" role="alert">{{ t("channel.copyFailed") }}</small>
        </div>
        <p class="security-note"><ShieldCheck />{{ t("channel.securityNote") }}</p>
      </section>

      <section class="channel-section binding-section">
        <header class="channel-section__header">
          <div>
            <small>02</small>
            <h3>{{ t("channel.bindings") }}</h3>
            <p>{{ t("channel.bindingsDescription") }}</p>
          </div>
          <UiButton
            variant="primary"
            size="sm"
            :loading="actionTarget === 'binding'"
            :disabled="!!actionTarget"
            @click="runAction('binding', workspace.createFeishuLinkCode)"
          >
            <template #icon><Link2 /></template>
            {{ t("channel.generateCode") }}
          </UiButton>
        </header>
        <UiStatusPanel
          v-if="actionFeedback?.target === 'binding'"
          :title="actionFeedback.message"
          :tone="actionFeedback.tone"
        />

        <div v-if="workspace.channelLinkCode.value" class="binding-command">
          <div>
            <small>{{ t("channel.sendCommand") }}</small>
            <code>{{ workspace.channelLinkCode.value.binding_command }}</code>
            <span>{{ t("channel.expires", { date: formatDate(workspace.channelLinkCode.value.expires_at) }) }}</span>
          </div>
          <UiButton
            variant="secondary"
            size="sm"
            :aria-label="t('channel.copyCommand')"
            @click="copyText(workspace.channelLinkCode.value.binding_command, 'binding')"
          >
            <template #icon><Check v-if="copied === 'binding'" /><Copy v-else /></template>
            {{ copied === "binding" ? t("channel.copied") : t("channel.copyCommand") }}
          </UiButton>
          <small v-if="copyFailed === 'binding'" role="alert">{{ t("channel.copyFailed") }}</small>
        </div>

        <ul v-if="workspace.channelIdentities.value.length" class="identity-list">
          <li v-for="identity in workspace.channelIdentities.value" :key="identity.id">
            <CheckCircle2 />
            <div>
              <strong>{{ identity.external_user_id }}</strong>
              <small>{{ identity.account_id }} · {{ t("channel.verified", { date: formatDate(identity.verified_at) }) }}</small>
            </div>
            <span>{{ identity.status }}</span>
          </li>
        </ul>
        <UiEmptyState
          v-else
          :title="t('channel.noLinkedTitle')"
          :description="t('channel.noLinkedDescription')"
        >
          <template #icon><Link2 /></template>
        </UiEmptyState>
      </section>

      <section class="channel-section routing-section">
        <header class="channel-section__header">
          <div>
            <small>03</small>
            <h3>{{ t("channel.routing") }}</h3>
            <p>{{ t("channel.routingDescription") }}</p>
          </div>
          <span>{{ t("channel.routeCount", { count: workspace.channelConversations.value.length }) }}</span>
        </header>

        <div v-if="workspace.channelConversations.value.length" class="route-list">
          <form
            v-for="conversation in workspace.channelConversations.value"
            :key="conversation.id"
            @submit.prevent="saveConversation(conversation.id)"
          >
            <div class="route-id">
              <MessageSquareMore />
              <div>
                <strong>{{ conversation.external_conversation_id }}</strong>
                <small>{{ conversation.external_thread_id || t("channel.mainThread") }}</small>
              </div>
            </div>
            <label>
              {{ t("channel.mode") }}
              <select v-model="drafts[conversation.id].answer_mode">
                <option v-for="mode in modes" :key="mode.value" :value="mode.value">{{ mode.label }}</option>
              </select>
            </label>
            <label>
              {{ t("channel.knowledgeBase") }}
              <select v-model="drafts[conversation.id].knowledge_base_id">
                <option value="">{{ t("channel.none") }}</option>
                <option v-for="knowledgeBase in workspace.knowledgeBases.value" :key="knowledgeBase.id" :value="knowledgeBase.id">
                  {{ knowledgeBase.name }}
                </option>
              </select>
            </label>
            <label>
              {{ t("channel.chatSession") }}
              <select v-model="drafts[conversation.id].chat_session_id">
                <option value="">{{ t("channel.automatic") }}</option>
                <option
                  v-if="conversation.chat_session_id && !workspace.chatSessions.value.some((session) => session.id === conversation.chat_session_id)"
                  :value="conversation.chat_session_id"
                >
                  {{ t("channel.currentMapping", { id: conversation.chat_session_id }) }}
                </option>
                <option v-for="session in workspace.chatSessions.value" :key="session.id" :value="session.id">
                  {{ session.title || t("channel.untitledChat") }}
                </option>
              </select>
            </label>
            <UiButton
              size="sm"
              type="submit"
              :loading="actionTarget === `route:${conversation.id}`"
              :disabled="!!actionTarget"
            >
              {{ t("channel.saveRoute") }}
            </UiButton>
            <UiStatusPanel
              v-if="actionFeedback?.target === `route:${conversation.id}`"
              class="route-feedback"
              :title="actionFeedback.message"
              :tone="actionFeedback.tone"
            />
          </form>
        </div>
        <UiEmptyState
          v-else
          :title="t('channel.noRoutesTitle')"
          :description="t('channel.noRoutesDescription')"
        >
          <template #icon><MessageSquareMore /></template>
        </UiEmptyState>
      </section>

      <section class="channel-section delivery-section">
        <header class="channel-section__header">
          <div>
            <small>04</small>
            <h3>{{ t("channel.delivery") }}</h3>
            <p>{{ t("channel.deliveryDescription") }}</p>
          </div>
          <code>{{ workspace.channelConfiguration.value.delivery_queue }}</code>
        </header>

        <div v-if="workspace.channelDeliveries.value.length" class="delivery-table">
          <div class="delivery-header" aria-hidden="true">
            <span>{{ t("channel.status") }}</span>
            <span>{{ t("channel.run") }}</span>
            <span>{{ t("channel.parts") }}</span>
            <span>{{ t("channel.attempts") }}</span>
            <span>{{ t("channel.lastActivity") }}</span>
            <span />
          </div>
          <article v-for="delivery in workspace.channelDeliveries.value" :key="delivery.id" class="delivery-row">
            <strong :data-label="t('channel.status')" :data-status="delivery.status">{{ delivery.status }}</strong>
            <code :data-label="t('channel.run')">{{ delivery.agent_run_id || "—" }}</code>
            <span :data-label="t('channel.parts')">{{ delivery.parts_sent }}/{{ delivery.part_count }}</span>
            <span :data-label="t('channel.attempts')">{{ delivery.attempt_count }}</span>
            <span :data-label="t('channel.lastActivity')" :title="delivery.last_error || ''">
              {{ delivery.last_error || (delivery.processed_at ? formatDate(delivery.processed_at) : t("channel.pending")) }}
            </span>
            <UiButton
              v-if="isRetryable(delivery.status)"
              variant="ghost"
              size="sm"
              :loading="actionTarget === `delivery:${delivery.id}`"
              :disabled="!!actionTarget"
              @click="runAction(`delivery:${delivery.id}`, () => workspace.retryChannelDelivery(delivery.id))"
            >
              <template #icon><RotateCcw /></template>
              {{ t("channel.retry") }}
            </UiButton>
            <UiStatusPanel
              v-if="actionFeedback?.target === `delivery:${delivery.id}`"
              class="delivery-feedback"
              :title="actionFeedback.message"
              :tone="actionFeedback.tone"
            />
          </article>
        </div>
        <UiEmptyState
          v-else
          :title="t('channel.noDeliveriesTitle')"
          :description="t('channel.noDeliveriesDescription')"
        >
          <template #icon><MessageSquareMore /></template>
        </UiEmptyState>
      </section>
    </template>
  </section>
</template>

<style scoped>
.channel-panel {
  display: grid;
  min-width: 0;
  gap: var(--space-5);
  scroll-margin-top: var(--space-5);
  color: var(--content-primary);
}
.channel-panel__header,
.channel-section__header,
.gateway-actions,
.readiness,
.config-rows strong,
.security-note,
.identity-list li,
.route-id {
  display: flex;
  align-items: center;
}
.channel-panel__header,
.channel-section__header {
  justify-content: space-between;
  gap: var(--space-4);
}
.channel-panel__header {
  align-items: flex-start;
}
.channel-panel__header > div:first-child,
.channel-section__header > div {
  min-width: 0;
}
.channel-panel__header small,
.channel-section__header small,
.binding-command small {
  color: var(--content-tertiary);
  font: 600 var(--font-size-xs) var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.channel-panel h2,
.channel-section h3 {
  margin: var(--space-1) 0 0;
  line-height: var(--line-height-tight);
}
.channel-panel h2 {
  font-size: var(--font-size-lg);
}
.channel-section h3 {
  font-size: var(--font-size-md);
}
.channel-panel__header p,
.channel-section__header p {
  max-width: 42rem;
  margin: var(--space-2) 0 0;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-body);
}
.gateway-actions {
  position: relative;
  flex: 0 0 auto;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}
.gateway-actions__feedback {
  width: 100%;
}
.readiness {
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  color: var(--status-danger);
  background: color-mix(in srgb, var(--status-danger) 8%, var(--surface-sidebar));
  border: 1px solid color-mix(in srgb, var(--status-danger) 30%, var(--stroke-subtle));
  border-radius: var(--radius-round);
  font: 600 var(--font-size-xs) var(--font-mono);
}
.readiness[data-state="ready"] {
  color: var(--status-success);
  background: color-mix(in srgb, var(--status-success) 8%, var(--surface-sidebar));
  border-color: color-mix(in srgb, var(--status-success) 30%, var(--stroke-subtle));
}
.readiness[data-state="degraded"] {
  color: var(--status-warning);
  background: color-mix(in srgb, var(--status-warning) 8%, var(--surface-sidebar));
  border-color: color-mix(in srgb, var(--status-warning) 30%, var(--stroke-subtle));
}
.readiness svg {
  width: 0.9rem;
  height: 0.9rem;
}
.channel-loading {
  display: grid;
  gap: var(--space-2);
}
.channel-loading span {
  height: 3rem;
  background: var(--surface-raised);
  border-radius: var(--radius-control);
  animation: channel-pulse 1.4s ease-in-out infinite;
}
.channel-section {
  display: grid;
  min-width: 0;
  gap: var(--space-4);
  padding-top: var(--space-5);
  border-top: 1px solid var(--stroke-subtle);
}
.channel-section__header > code,
.channel-section__header > span {
  color: var(--content-tertiary);
  font: var(--font-size-xs) var(--font-mono);
}
.config-rows {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-block: 1px solid var(--stroke-subtle);
}
.config-rows > div {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border-right: 1px solid var(--stroke-subtle);
}
.config-rows > div:last-child {
  border-right: 0;
}
.config-rows span {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.config-rows strong {
  gap: var(--space-1);
  color: var(--status-danger);
  font-size: var(--font-size-sm);
}
.config-rows strong[data-ok="true"] {
  color: var(--status-success);
}
.config-rows svg {
  width: 0.85rem;
}
.callback-card {
  display: grid;
  min-width: 0;
  grid-template-columns: 7rem minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--surface-panel);
  border: 1px solid var(--stroke-subtle);
  border-radius: var(--radius-control);
}
.callback-card > span {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.callback-card code {
  min-width: 0;
  overflow: hidden;
  color: var(--content-secondary);
  font-size: var(--font-size-sm);
  text-overflow: ellipsis;
}
.callback-card > small {
  grid-column: 2 / -1;
  color: var(--status-danger);
}
.security-note {
  gap: var(--space-2);
  margin: 0;
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
  line-height: 1.55;
}
.security-note svg {
  width: 0.9rem;
  flex: 0 0 auto;
  color: var(--accent-primary);
}
.binding-command {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--accent-subtle);
  border-left: 2px solid var(--accent-primary);
}
.binding-command > div {
  display: grid;
  min-width: 0;
  gap: var(--space-2);
}
.binding-command code {
  overflow-wrap: anywhere;
  color: var(--content-primary);
  font-size: var(--font-size-md);
}
.binding-command span {
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.binding-command > small {
  grid-column: 1 / -1;
  color: var(--status-danger);
}
.identity-list,
.route-list {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--stroke-subtle);
}
.identity-list li {
  min-width: 0;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--stroke-subtle);
}
.identity-list li > svg {
  width: 0.9rem;
  color: var(--status-success);
}
.identity-list li > div {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}
.identity-list strong {
  overflow: hidden;
  font: var(--font-size-xs) var(--font-mono);
  text-overflow: ellipsis;
}
.identity-list small {
  color: var(--content-tertiary);
}
.identity-list li > span {
  color: var(--status-success);
  font-size: var(--font-size-xs);
}
.route-list form {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(9rem, 1.2fr) repeat(3, minmax(7rem, 1fr)) auto;
  align-items: end;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--stroke-subtle);
}
.route-id {
  min-width: 0;
  gap: var(--space-2);
  align-self: center;
}
.route-id > svg {
  width: 0.9rem;
  flex: 0 0 auto;
  color: var(--accent-primary);
}
.route-id > div {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}
.route-id strong {
  overflow: hidden;
  font: var(--font-size-xs) var(--font-mono);
  text-overflow: ellipsis;
}
.route-id small {
  color: var(--content-tertiary);
}
.route-list label {
  display: grid;
  gap: var(--space-1);
  color: var(--content-tertiary);
  font-size: var(--font-size-xs);
}
.route-list select {
  min-width: 0;
  width: 100%;
}
.route-feedback {
  grid-column: 1 / -1;
}
.delivery-table {
  min-width: 0;
  border-top: 1px solid var(--stroke-subtle);
}
.delivery-header,
.delivery-row {
  display: grid;
  min-width: 0;
  grid-template-columns: 6rem minmax(8rem, 1.2fr) 4rem 4rem minmax(9rem, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}
.delivery-header {
  color: var(--content-tertiary);
  border-bottom: 1px solid var(--stroke-subtle);
  font-size: var(--font-size-xs);
}
.delivery-row {
  margin: 0;
  color: var(--content-secondary);
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--stroke-subtle);
  border-radius: 0;
  font-size: var(--font-size-xs);
}
.delivery-row > strong {
  color: var(--content-secondary);
  text-transform: capitalize;
}
.delivery-row > strong[data-status="succeeded"] {
  color: var(--status-success);
}
.delivery-row > strong[data-status="dead_letter"],
.delivery-row > strong[data-status="failed"] {
  color: var(--status-danger);
}
.delivery-row > code,
.delivery-row > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.delivery-feedback {
  grid-column: 1 / -1;
}
:deep(.ui-empty-state) {
  min-height: 8rem;
  padding: var(--space-4);
}
@keyframes channel-pulse {
  50% { opacity: 0.45; }
}
@media (max-width: 1080px) {
  .route-list form {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .route-id,
  .route-feedback {
    grid-column: 1 / -1;
  }
}
@media (max-width: 720px) {
  .channel-panel__header,
  .channel-section__header {
    align-items: flex-start;
    flex-direction: column;
  }
  .gateway-actions {
    width: 100%;
    justify-content: flex-start;
  }
  .config-rows {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .config-rows > div:nth-child(2) {
    border-right: 0;
  }
  .config-rows > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--stroke-subtle);
  }
  .callback-card {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .callback-card > span {
    grid-column: 1 / -1;
  }
  .route-list form {
    grid-template-columns: minmax(0, 1fr);
  }
  .route-id,
  .route-feedback {
    grid-column: auto;
  }
  .delivery-header {
    display: none;
  }
  .delivery-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3) var(--space-4);
  }
  .delivery-row > strong,
  .delivery-row > code,
  .delivery-row > span {
    display: grid;
    gap: var(--space-1);
    white-space: normal;
  }
  .delivery-row > strong::before,
  .delivery-row > code::before,
  .delivery-row > span::before {
    color: var(--content-tertiary);
    content: attr(data-label);
    font-family: var(--font-sans);
    font-size: var(--font-size-xs);
    font-weight: 400;
    text-transform: none;
  }
  .delivery-row :deep(.ui-button),
  .delivery-feedback {
    grid-column: 1 / -1;
  }
}
@media (max-width: 480px) {
  .config-rows,
  .delivery-row {
    grid-template-columns: minmax(0, 1fr);
  }
  .config-rows > div {
    border-right: 0;
    border-bottom: 1px solid var(--stroke-subtle);
  }
  .config-rows > div:last-child {
    border-bottom: 0;
  }
  .binding-command {
    grid-template-columns: minmax(0, 1fr);
  }
  .binding-command :deep(.ui-button) {
    width: 100%;
  }
}
@media (prefers-reduced-motion: reduce) {
  .channel-loading span {
    animation: none;
  }
}
</style>
