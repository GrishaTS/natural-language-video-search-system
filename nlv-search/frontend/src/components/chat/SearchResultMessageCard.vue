<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { DialogPayload, EventPreview, VmsPersonLink, Message } from "@/types/chat";
import { API_BASE_URL, readStoredToken } from "@/config";
import { useMarkdownRenderer } from "@/composables/useMarkdownRenderer";
import { buildFocusedEventLink } from "./vmsLinks";

const props = withDefaults(defineProps<{
  message: Message;
  stage?: string | null;
  statusLabel?: string | null;
  mediaBaseUrl?: string | null;
  streaming?: boolean;
}>(), {
  stage: null,
  statusLabel: null,
  mediaBaseUrl: null,
  streaming: false,
});

const { renderMarkdown } = useMarkdownRenderer();

const PIPELINE_STAGES = [
  { key: "parsing", label: "Анализ запроса" },
  { key: "resolution", label: "Уточнение" },
  { key: "respond", label: "Поиск" },
] as const;

const STAGE_PROGRESS: Record<string, number> = {
  parsing: 25,
  resolution: 55,
  respond: 85,
};

const currentStageIndex = computed(() =>
  PIPELINE_STAGES.findIndex((stage) => stage.key === props.stage),
);

const progressPct = computed(() =>
  props.stage ? (STAGE_PROGRESS[props.stage] ?? 10) : 0,
);

const isLinksExpanded = ref(false);

const activeImage = ref<{
  src: string;
  alt: string;
  eventLink: string | null;
} | null>(null);

let previousBodyOverflow = "";

const bodyHtml = computed(() => {
  if (props.message.content && props.message.content !== "...") {
    return renderMarkdown(props.message.content);
  }
  if (props.streaming || props.stage || props.statusLabel) {
    return "<span class='typing'>Обработка запроса…</span>";
  }
  return "";
});

function stepState(stepKey: string): "done" | "active" | "pending" {
  const activeIndex = currentStageIndex.value;
  const stepIndex = PIPELINE_STAGES.findIndex((stage) => stage.key === stepKey);
  if (activeIndex === -1 || stepIndex === -1) return "pending";
  if (stepIndex < activeIndex) return "done";
  if (stepIndex === activeIndex) return "active";
  return "pending";
}

function buildImageUrl(snapshotPath: string): string {
  if (!snapshotPath) return "";
  // If an absolute URL is given (e.g. VMS returns http://vms-host/api/v1/media/snapshot/...),
  // extract only path+query so the request is routed through the backend proxy
  // at /api/v1/media/snapshot/{path}, which authenticates with VMS own token.
  let relativePath = snapshotPath;
  if (snapshotPath.startsWith("http://") || snapshotPath.startsWith("https://")) {
    const url = new URL(snapshotPath);
    relativePath = url.pathname + url.search;
  }
  const mediaBaseUrl = (props.mediaBaseUrl || API_BASE_URL).replace(/\/$/, "");
  const base = `${mediaBaseUrl}${relativePath.startsWith("/") ? "" : "/"}${relativePath}`;
  const token = readStoredToken();
  if (!token) return base;
  const hasQuery = base.includes("?");
  return `${base}${hasQuery ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

const dialogPayload = computed(() => props.message.payload as DialogPayload | null);

const eventPreviews = computed((): EventPreview[] =>
  dialogPayload.value?.event_previews ?? [],
);

const vmsLinks = computed((): VmsPersonLink[] => {
  const links = dialogPayload.value?.vms_links;
  return Array.isArray(links) ? links : [];
});

function getVmsLink(): string | null {
  const rawLink = dialogPayload.value?.vms_link;
  return typeof rawLink === "string" ? rawLink : null;
}

function hasVmsRequest(): boolean {
  return Boolean(dialogPayload.value?.vms_request);
}

function buildFilterLink(): string {
  return `#filter:${props.message.id}`;
}

function buildEventLink(eventId: string | null | undefined): string | null {
  return buildFocusedEventLink(getVmsLink(), eventId);
}

function buildImageAlt(eventId: string): string {
  return eventId ? `Event snapshot ${eventId}` : "Event snapshot";
}

function openImage(preview: EventPreview) {
  activeImage.value = {
    src: buildImageUrl(preview.snapshot_url),
    alt: buildImageAlt(preview.event_id),
    eventLink: buildEventLink(preview.event_id),
  };
}

function closeImage() {
  activeImage.value = null;
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    closeImage();
  }
}

watch(activeImage, (image) => {
  if (typeof window === "undefined" || typeof document === "undefined") return;

  if (image) {
    previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleWindowKeydown);
    return;
  }

  document.body.style.overflow = previousBodyOverflow;
  window.removeEventListener("keydown", handleWindowKeydown);
});

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("keydown", handleWindowKeydown);
  }
  if (typeof document !== "undefined") {
    document.body.style.overflow = previousBodyOverflow;
  }
});
</script>

<template>
  <div class="search-result-card">
    <section class="message-surface">
      <section v-if="props.stage" class="pipeline-progress" aria-label="Прогресс обработки запроса">
        <div class="pipeline-header">
          <span class="pipeline-kicker">Обработка запроса</span>
          <span class="pipeline-percent">{{ progressPct }}%</span>
        </div>

        <div class="pipeline-bar" aria-hidden="true">
          <span class="pipeline-bar-fill" :style="{ width: `${progressPct}%` }"></span>
        </div>

        <div class="pipeline-steps">
          <div
            v-for="stage in PIPELINE_STAGES"
            :key="stage.key"
            class="pipeline-step"
            :class="stepState(stage.key)"
          >
            <span class="pipeline-step-dot"></span>
            <span class="pipeline-step-label">{{ stage.label }}</span>
          </div>
        </div>
      </section>

      <section v-if="props.statusLabel" class="stream-status" aria-live="polite">
        <span class="stream-status-dot"></span>
        <span>{{ props.statusLabel }}</span>
      </section>

      <div v-if="eventPreviews.length" class="image-strip">
        <div
          v-for="preview in eventPreviews"
          :key="`${preview.event_id}-${preview.snapshot_url}`"
          class="image-card"
        >
          <button
            type="button"
            class="image-preview-button"
            :aria-label="`Открыть увеличенное изображение ${preview.event_id}`"
            @click="openImage(preview)"
          >
            <img
              :src="buildImageUrl(preview.snapshot_url)"
              :alt="buildImageAlt(preview.event_id)"
              loading="lazy"
            />
          </button>
          <a
            v-if="buildEventLink(preview.event_id)"
            class="event-link"
            :href="buildEventLink(preview.event_id) || undefined"
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть событие
          </a>
        </div>
      </div>

      <div
        class="message-body"
        v-html="bodyHtml"
      />

      <div v-if="vmsLinks.length > 0 || getVmsLink() || hasVmsRequest()" class="message-actions">
        <!-- Multi-person: toggle-список -->
        <div v-if="vmsLinks.length > 1" class="vms-links-toggle">
          <button
            type="button"
            class="message-action message-action-primary"
            @click="isLinksExpanded = !isLinksExpanded"
          >
            Открыть в VMS ({{ vmsLinks.length }})&nbsp;{{ isLinksExpanded ? '▲' : '▼' }}
          </button>
          <div v-if="isLinksExpanded" class="vms-links-list">
            <a
              v-for="link in vmsLinks"
              :key="link.url"
              class="vms-person-link"
              :href="link.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ link.label }}
            </a>
          </div>
        </div>

        <!-- Одна персона: кнопка с именем -->
        <a
          v-else-if="vmsLinks.length === 1"
          class="message-action message-action-primary"
          :href="vmsLinks[0].url"
          target="_blank"
          rel="noopener noreferrer"
        >
          Открыть в VMS
        </a>

        <!-- Fallback: не-персональный поиск -->
        <a
          v-else-if="getVmsLink()"
          class="message-action message-action-primary"
          :href="getVmsLink() || undefined"
          target="_blank"
          rel="noopener noreferrer"
        >
          Открыть в VMS
        </a>

        <a
          v-if="hasVmsRequest()"
          class="message-action message-action-secondary"
          :href="buildFilterLink()"
        >
          Запрос поиска
        </a>
      </div>
    </section>

    <Teleport to="body">
      <div
        v-if="activeImage"
        class="image-lightbox-overlay"
        @click.self="closeImage"
      >
        <div class="image-lightbox" role="dialog" aria-modal="true" :aria-label="activeImage.alt">
          <button
            type="button"
            class="image-lightbox-close"
            aria-label="Закрыть изображение"
            @click="closeImage"
          >
            ✕
          </button>
          <img class="image-lightbox-media" :src="activeImage.src" :alt="activeImage.alt" />
          <a
            v-if="activeImage.eventLink"
            class="event-link image-lightbox-link"
            :href="activeImage.eventLink"
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть событие
          </a>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.search-result-card {
  width: 100%;
}

.message-surface {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border, #e6e8ee);
  border-radius: 12px;
  background: var(--panel, #ffffff);
}

.pipeline-progress {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border, #e6e8ee);
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pipeline-kicker {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted, #6b7280);
}

.pipeline-percent {
  font-size: 13px;
  font-weight: 600;
  color: var(--text, #1f2933);
}

.pipeline-bar {
  overflow: hidden;
  height: 8px;
  border-radius: 999px;
  background: #eef2f7;
}

.pipeline-bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent, #2563eb);
  transition: width 220ms ease;
}

.pipeline-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--border, #e6e8ee);
  border-radius: 999px;
  background: #f9fafb;
  color: var(--muted, #6b7280);
  font-size: 12px;
  line-height: 1.2;
}

.pipeline-step-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 999px;
  background: #cbd5e1;
}

.pipeline-step.done {
  color: var(--text, #1f2933);
  background: #f9fafb;
}

.pipeline-step.done .pipeline-step-dot {
  background: #22c55e;
}

.pipeline-step.active {
  color: var(--accent, #2563eb);
  background: var(--accent-light, #e1e9ff);
  border-color: rgba(37, 99, 235, 0.22);
  font-weight: 600;
}

.pipeline-step.active .pipeline-step-dot {
  background: var(--accent, #2563eb);
}

.pipeline-step-label {
  min-width: 0;
}

.stream-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  max-width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
  line-height: 1.4;
}

.stream-status-dot {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 999px;
  background: currentColor;
  animation: statusPulse 1.2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1); }
}

.image-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.image-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--panel, #ffffff);
  border: 1px solid var(--border, #e6e8ee);
  border-radius: 10px;
  overflow: hidden;
}

.image-preview-button {
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
}

.image-preview-button:focus-visible {
  outline: 2px solid var(--accent, #2563eb);
  outline-offset: -2px;
}

.image-preview-button img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
}

.image-lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(4px);
}

.image-lightbox {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: min(100%, 1200px);
  max-height: 100%;
}

.image-lightbox-media {
  display: block;
  width: 100%;
  max-height: calc(100vh - 96px);
  border-radius: 14px;
  background: #0f172a;
  object-fit: contain;
}

.image-lightbox-close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #ffffff;
  font-size: 18px;
  cursor: pointer;
}

.image-lightbox-link {
  align-self: flex-end;
  border: 0;
  border-radius: 999px;
  background: #ffffff;
  color: var(--accent, #2563eb);
}

.event-link {
  display: block;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--accent, #2563eb);
  text-decoration: none;
  text-align: center;
  border-top: 1px solid var(--border, #e6e8ee);
}

.event-link:hover {
  text-decoration: underline;
}

.message-body {
  line-height: 1.6;
  word-break: break-word;
}

.message-body:empty {
  display: none;
}

.message-body :deep(p) {
  margin: 0 0 8px;
}

.message-body :deep(p:last-child) {
  margin: 0;
}

.message-body :deep(.typing) {
  color: var(--muted, #6b7280);
  font-style: italic;
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 8px;
}

.message-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.message-action-primary {
  background: var(--accent, #2563eb);
  color: #ffffff;
}

.message-action-secondary {
  border: 1px solid var(--border, #e6e8ee);
  background: #f8fafc;
  color: var(--text, #1f2933);
}

.vms-links-toggle {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.vms-links-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  border: 1px solid var(--border, #e6e8ee);
  border-radius: 10px;
  background: #f8fafc;
}

.vms-person-link {
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--accent, #2563eb);
  text-decoration: none;
  transition: background 0.12s;
}

.vms-person-link:hover {
  background: var(--accent-light, #e1e9ff);
  text-decoration: none;
}

@media (max-width: 520px) {
  .pipeline-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .pipeline-steps {
    grid-template-columns: minmax(0, 1fr);
  }

  .image-lightbox-overlay {
    padding: 12px;
  }

  .image-lightbox-media {
    max-height: calc(100vh - 64px);
  }
}
</style>
