<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ChatMessage, DialogPayload, OptionsPayload } from "@/types/chat";
import { FEATURE_FLAGS, API_BASE_URL, readStoredToken } from "@/config";
import { useMarkdownRenderer } from "@/composables/useMarkdownRenderer";
import { buildFocusedEventLink } from "./vmsLinks";

const props = defineProps<{
  messages: ChatMessage[];
  sending?: boolean;
}>();

const emit = defineEmits<{
  (e: "confirm", payload?: { selected_ids: string[] }): void;
}>();

const { renderMarkdown } = useMarkdownRenderer();

function normalizeLink(link: string | null | undefined): string | null {
  if (!link) return null;
  if (link.startsWith("http://") || link.startsWith("https://")) return link;
  return `https://${link}`;
}

function getVmsLink(message: ChatMessage): string | null {
  const rawLink = (message.payload as DialogPayload)?.vms_link;
  return normalizeLink(typeof rawLink === "string" ? rawLink : null);
}

function getEventPreviews(message: ChatMessage) {
  return (message.payload as DialogPayload)?.event_previews ?? [];
}

function buildImageUrl(snapshotPath: string): string {
  if (!snapshotPath) return "";
  const base = snapshotPath.startsWith("http://") || snapshotPath.startsWith("https://")
    ? snapshotPath
    : `${API_BASE_URL}${snapshotPath.startsWith("/") ? "" : "/"}${snapshotPath}`;
  const token = readStoredToken();
  if (!token) return base;
  const hasQuery = base.includes("?");
  return `${base}${hasQuery ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

function buildEventLink(message: ChatMessage, eventId: string | null | undefined): string | null {
  return buildFocusedEventLink(getVmsLink(message), eventId);
}

function roleLabel(role?: string) {
  return role === "user" ? "Вы" : "Ассистент";
}

function sameId(left: string, right: string): boolean {
  return String(left) === String(right);
}

const localSelections = ref<Record<string, string[]>>({});
const localLocks = ref<Record<string, boolean>>({});

function getOptions(message: ChatMessage) {
  return (message.payload as OptionsPayload)?.options ?? [];
}

function getSelectionMode(message: ChatMessage): "single" | "multi" {
  return (message.payload as OptionsPayload)?.selection_mode ?? "single";
}

function isSelectionLocked(messageIndex: number): boolean {
  return Boolean(localLocks.value[String(messageIndex)]);
}

function isSelected(messageIndex: number, optionId: string): boolean {
  const selected = localSelections.value[String(messageIndex)] ?? [];
  return selected.some((id) => sameId(id, optionId));
}

function toggle(messageIndex: number, optionId: string, multi: boolean): void {
  const key = String(messageIndex);
  const current = localSelections.value[key] ?? [];
  if (!multi) {
    localSelections.value = { ...localSelections.value, [key]: [optionId] };
    return;
  }
  const exists = current.some((id) => sameId(id, optionId));
  localSelections.value = {
    ...localSelections.value,
    [key]: exists ? current.filter((id) => !sameId(id, optionId)) : [...current, optionId],
  };
}

function requestConfirm(messageIndex: number): void {
  const selected = localSelections.value[String(messageIndex)] ?? [];
  if (!selected.length) return;
  localLocks.value = { ...localLocks.value, [String(messageIndex)]: true };
  emit("confirm", { selected_ids: [...selected] });
}

function hasUserResponseAfter(messages: ChatMessage[], assistantIndex: number): boolean {
  for (let i = assistantIndex + 1; i < messages.length; i += 1) {
    if (messages[i]?.role === "user") return true;
  }
  return false;
}

watch(
  () => props.messages,
  (messages) => {
    messages.forEach((msg, idx) => {
      if (!(msg?.role === "assistant" && msg.type === "options")) return;
      if (hasUserResponseAfter(messages as ChatMessage[], idx)) {
        localLocks.value = { ...localLocks.value, [String(idx)]: true };
      }
    });
  },
  { deep: false, immediate: true },
);
</script>

<template>
  <div class="message-list card">
    <template v-if="!props.messages.length">
      <p class="muted">
        История пуста. Создайте новый чат и напишите запрос — ассистент предложит уточнения и ссылку
        на VMS, если она есть.
      </p>
    </template>

    <article
      v-for="(message, index) in props.messages"
      :key="index"
      class="message"
      :class="{ user: message.role === 'user' }"
    >
      <header class="message-meta">
        <div class="meta-left">
          <span class="pill ghost">{{ roleLabel(message.role) }}</span>
          <span v-if="message.type === 'options'" class="badge accent">Есть варианты</span>
        </div>
      </header>

      <div class="message-content" v-html="renderMarkdown(message.content)" />

      <div
        v-if="message.role === 'assistant' && getEventPreviews(message).length"
        class="image-strip"
      >
        <div
          v-for="preview in getEventPreviews(message)"
          :key="`${preview.event_id}-${preview.snapshot_url}`"
          class="image-card"
        >
          <div class="image-label">Событие {{ preview.event_id }}</div>
          <img :src="buildImageUrl(preview.snapshot_url)" alt="Event snapshot" />
          <a
            v-if="buildEventLink(message, preview.event_id)"
            class="btn ghost tiny"
            :href="buildEventLink(message, preview.event_id) || undefined"
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть событие
          </a>
        </div>
      </div>

      <div v-if="message.role === 'assistant' && message.type === 'options'" class="message-options">
        <div class="option-radio-list">
          <label
            v-for="option in getOptions(message)"
            :key="option.id"
            class="option-radio"
          >
            <input
              :type="getSelectionMode(message) === 'multi' ? 'checkbox' : 'radio'"
              :name="`assistant-options-${index}`"
              :value="option.id"
              :checked="isSelected(index, option.id)"
              :disabled="props.sending || isSelectionLocked(index)"
              @change="toggle(index, option.id, getSelectionMode(message) === 'multi')"
            />
            <div class="option-line">
              <span class="option-text">{{ option.value || "—" }}</span>
            </div>
          </label>
        </div>
        <button
          type="button"
          class="btn small primary"
          :disabled="props.sending || isSelectionLocked(index)"
          @click.stop="requestConfirm(index)"
        >
          Подтвердить
        </button>
      </div>

      <div
        v-if="FEATURE_FLAGS.showVmsLinks && message.role === 'assistant' && getVmsLink(message)"
        class="message-actions"
      >
        <a
          class="btn primary"
          :href="getVmsLink(message)!"
          target="_blank"
          rel="noopener noreferrer"
        >
          Открыть в VMS
        </a>
      </div>
    </article>

    <article v-if="props.sending" class="message thinking">
      <header class="message-meta">
        <div class="meta-left">
          <span class="pill ghost">Ассистент</span>
          <span class="badge subtle">Обработка запроса</span>
        </div>
      </header>
      <div class="typing-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="typing-text">Ассистент думает…</span>
      </div>
    </article>
  </div>
</template>

<style scoped>
.message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.thinking .typing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f5f7fb;
  border-radius: 8px;
  color: #4a5568;
  font-size: 14px;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4a90e2;
  animation: pulse 1.2s infinite ease-in-out;
}

.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.typing-text { font-weight: 500; }

.image-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin: 10px 0;
}

.image-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
}

.image-card img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 8px;
  background: #e5e7eb;
}

.image-label {
  font-size: 12px;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.message-options {
  margin-top: 10px;
}

.option-radio-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.option-radio {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.option-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-text {
  font-size: 14px;
  color: #111827;
}
</style>
