<template>
  <div class="chat-page" @click="handlePageClick">
    <vue-advanced-chat
      :key="selectedChatId || 'chat-root'"
      ref="chatComponent"
      height="calc(100vh - 109px)"
      :current-user-id="currentUserId"
      :room-id="selectedChatId"
      :rooms="roomsJson"
      :rooms-loaded="roomsLoaded"
      :messages="messagesJson"
      :messages-loaded="messagesLoaded"
      :room-actions="roomActionsJson"
      :message-actions="messageActionsJson"
      :text-formatting="textFormattingJson"
      :auto-scroll="autoScrollJson"
      :show-search="true"
      :show-add-room="true"
      :show-files="true"
      :accepted-files="'image/*'"
      :show-audio="false"
      :show-emojis="false"
      :show-reaction-emojis="false"
      @add-room="handleAddRoomEvent"
      @fetch-messages="handleFetchMessagesEvent"
      @send-message="handleSendMessageEvent"
      @room-action-handler="handleRoomActionEvent"
    >
      <div
        v-for="message in optionSlotMessages"
        :key="`options-slot-${message.id}`"
        :slot="`message_${message.id}`"
        class="inline-options-slot"
      >
        <InlineOptionsMessageCard
          :message="message"
          :sending="isStreaming"
          :locked="isOptionsMessageLocked(message)"
          :selected-ids="getResolvedOptionIds(message)"
          @confirm="handleOptionsConfirm(message, $event)"
        />
      </div>
      <div
        v-for="message in assistantSlotMessages"
        :key="`assistant-slot-${message.id}`"
        :slot="`message_${message.id}`"
      >
        <SearchResultMessageCard
          :message="message"
          :stage="message.stage ?? null"
          :streaming="isStreaming && message.id === getRuntimeDraftId(selectedChatId ?? '')"
        />
      </div>
    </vue-advanced-chat>

    <!-- VMS request filter modal -->
    <div v-if="filterModalPayload" class="filter-modal-overlay" @click.self="filterModalPayload = null">
      <div class="filter-modal">
        <div class="filter-modal-header">
          <span>Запрос поиска</span>
          <button class="filter-modal-close" @click="filterModalPayload = null">✕</button>
        </div>
        <pre class="filter-modal-body">{{ JSON.stringify(filterModalPayload, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onBeforeUnmount } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  createChat,
  deleteChat,
  buildSnapshotProxyUrl,
  fetchChatDetail,
  listChats,
  streamResolution,
  streamMessage,
} from "../api/conversationalSearch";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";
import type { Chat, ChatMessage, DialogPayload, EventPreview, VmsPersonLink, Message, OptionsPayload } from "../types/chat";
import InlineOptionsMessageCard from "../components/chat/InlineOptionsMessageCard.vue";
import SearchResultMessageCard from "../components/chat/SearchResultMessageCard.vue";

const auth = useAuthStore();
const chatStore = useChatStore();
const queryClient = useQueryClient();
const chatComponent = ref<HTMLElement | null>(null);

const localMessages = ref<Message[]>([]);
const messagesLoaded = ref(false);
const isStreaming = ref(false);
const lastMessageByChatId = ref<Record<string, Message | undefined>>({});
const slotRefreshNonce = ref(0);
const resolvedOptionIdsByMessageId = ref<Record<string, string[]>>({});

const currentUserId = computed(() => auth.user?.id ?? "user");
const selectedChatId = computed(() => chatStore.selectedChatId);

const currentStage = ref<string | null>(null);
const filterModalPayload = ref<object | null>(null);

function makeTempId(prefix: string) {
  if (typeof crypto !== "undefined") {
    if (typeof crypto.randomUUID === "function") return `${prefix}-${crypto.randomUUID()}`;
    if (typeof crypto.getRandomValues === "function") {
      const bytes = new Uint32Array(4);
      crypto.getRandomValues(bytes);
      return `${prefix}-${Array.from(bytes).map((v) => v.toString(16).padStart(8, "0")).join("-")}`;
    }
  }
  return `${prefix}-${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

const autoScrollJson = JSON.stringify({
  send: { new: true, newAfterScrollUp: true },
  receive: { new: true, newAfterScrollUp: false },
});
const textFormattingJson = JSON.stringify({ disabled: false });
const messageActionsJson = computed(() => (slotRefreshNonce.value % 2 === 0 ? "[]" : "[ ]"));
const roomActionsJson = JSON.stringify([{ name: "delete-chat", title: "Delete chat" }]);

const { data: chats, isLoading: chatsLoading } = useQuery({
  queryKey: ["chats"],
  queryFn: () => listChats(),
});

const roomsLoaded = computed(() => !chatsLoading.value);

watch(
  chats,
  (items) => {
    if (!items?.length) {
      chatStore.selectChat(null);
      localMessages.value = [];
      messagesLoaded.value = true;
      return;
    }
    const selectedExists = items.some((chat) => chat.id === selectedChatId.value);
    if (!selectedChatId.value || !selectedExists) {
      chatStore.selectChat(items[0].id);
    }
    for (const chat of items) {
      if (chat.last_message && !lastMessageByChatId.value[chat.id]) {
        lastMessageByChatId.value = {
          ...lastMessageByChatId.value,
          [chat.id]: chat.last_message,
        };
      }
    }
  },
  { immediate: true },
);

function focusChatInput() {
  const el = chatComponent.value;
  if (!el) return;
  const input = el.shadowRoot?.querySelector<HTMLElement>("textarea, [contenteditable]");
  input?.focus();
}

const SHADOW_STYLE_ID = "nlv-custom-link-styles";
function injectShadowStyles() {
  const shadow = chatComponent.value?.shadowRoot;
  if (!shadow || shadow.getElementById(SHADOW_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = SHADOW_STYLE_ID;
  style.textContent = `
    a[href^="#filter:"] {
      display: inline-block;
      padding: 3px 12px;
      margin-top: 6px;
      background: #f3f4f6;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      text-decoration: none !important;
      color: #374151 !important;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    a[href^="#filter:"]:hover { background: #e5e7eb !important; }
    a[href*="vms"][href^="http"] {
      display: inline-block;
      padding: 3px 12px;
      margin-top: 6px;
      background: #1976d2;
      border: 1px solid #1565c0;
      border-radius: 6px;
      text-decoration: none !important;
      color: #fff !important;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    a[href*="vms"][href^="http"]:hover { background: #1565c0 !important; }
  `;
  shadow.appendChild(style);
}

watch(
  selectedChatId,
  async (chatId) => {
    localMessages.value = [];
    messagesLoaded.value = false;
    resolvedOptionIdsByMessageId.value = {};
    await nextTick();
    if (chatComponent.value) {
      // @ts-expect-error custom element runtime prop
      chatComponent.value.roomId = chatId ?? null;
    }
    currentStage.value = null;
    filterModalPayload.value = null;
    if (!chatId) {
      localMessages.value = [];
      messagesLoaded.value = true;
      return;
    }
    await loadChat(chatId);
    injectShadowStyles();
    focusChatInput();
  },
  { immediate: true },
);

const roomsJson = computed(() =>
  JSON.stringify(
    (chats.value ?? []).map((chat) => {
      const lastMessage = lastMessageByChatId.value[chat.id];
      return {
        roomId: chat.id,
        roomName: chat.title || "New chat",
        avatar: "",
        index: chat.updated_at,
        lastMessage: lastMessage ? mapMessageForUi(lastMessage) : undefined,
        users: [
          { _id: currentUserId.value, username: auth.user?.username ?? "You", avatar: "" },
          { _id: "assistant", username: "Assistant", avatar: "" },
        ],
      };
    }),
  ),
);

const messagesJson = computed(() =>
  JSON.stringify(localMessages.value.map((message) => mapMessageForUi(message))),
);

const optionSlotMessages = computed(() =>
  localMessages.value
    .filter((message) => message.type === "options" && !!(message.payload as OptionsPayload)?.resolution_id)
    .map((message) => message as ChatMessage),
);

const assistantSlotMessages = computed(() =>
  localMessages.value.filter(
    (message) =>
      message.role === "assistant"
      && message.type === "dialog"
      && (
        Boolean((message as ChatMessage).stage)
        || Boolean((message.payload as DialogPayload)?.vms_link)
        || Boolean((message.payload as DialogPayload)?.vms_links?.length)
        || Boolean((message.payload as DialogPayload)?.vms_request)
        || (
          Array.isArray((message.payload as DialogPayload)?.event_previews)
          && ((message.payload as DialogPayload)?.event_previews?.length ?? 0) > 0
        )
      ),
  ) as ChatMessage[],
);

function getSearchResultVersion(message: Message): string {
  const payload = message.payload as DialogPayload | null;
  const previews = Array.isArray(payload?.event_previews)
    ? payload!.event_previews.map((p) => `${p.event_id}:${p.snapshot_url}`).join("|")
    : "";
  return [
    (message as ChatMessage).stage ?? "",
    payload?.vms_link ? "vms" : "",
    payload?.vms_links?.length ? `links${payload.vms_links.length}` : "",
    payload?.vms_request ? "request" : "",
    previews,
  ].join("::");
}

const slotSignature = computed(() =>
  [
    ...optionSlotMessages.value.map((message) => `options:${message.id}`),
    ...assistantSlotMessages.value.map(
      (message) => `assistant:${message.id}:${getSearchResultVersion(message)}`,
    ),
  ].join("|"),
);

watch(
  slotSignature,
  async (signature, previousSignature) => {
    if (!signature || signature === previousSignature) return;
    await nextTick();
    slotRefreshNonce.value += 1;
  },
);

function getRuntimeDraftId(chatId: string): string {
  return `runtime-draft-${chatId}`;
}

function mimeFromUrl(url: string): string {
  const ext = url.split("?")[0].split(".").pop()?.toLowerCase();
  const map: Record<string, string> = {
    png: "image/png", webp: "image/webp", gif: "image/gif",
    jpg: "image/jpeg", jpeg: "image/jpeg",
  };
  return map[ext ?? ""] ?? "image/jpeg";
}

function mapMessageForUi(message: Message) {
  const createdAt = new Date(message.created_at);
  let content = message.content;
  const payload = message.payload as DialogPayload | null;
  if (message.role === "assistant" && message.type === "dialog" && payload) {
    const vmsLink = payload.vms_link;
    const hasVmsRequest = !!payload.vms_request;
    const actions: string[] = [];
    if (vmsLink) actions.push(`[↗ Открыть в VMS](${vmsLink})`);
    if (hasVmsRequest) actions.push(`[🔍 Запрос поиска](#filter:${message.id})`);
    if (actions.length) content += `\n\n${actions.join("  ·  ")}`;
  }
  const searchResultVersion = getSearchResultVersion(message);
  const imageUrl = message.role === "user" ? payload?.image_url : undefined;
  const files = imageUrl
    ? [{ name: "photo", type: mimeFromUrl(imageUrl), url: buildSnapshotProxyUrl(imageUrl) }]
    : undefined;
  return {
    _id: message.id,
    content,
    senderId: message.role === "assistant" ? "assistant" : currentUserId.value,
    username: message.role === "assistant" ? "Assistant" : auth.user?.username ?? "You",
    timestamp: createdAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    date: createdAt.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    saved: true,
    distributed: true,
    seen: true,
    searchResultVersion,
    ...(files ? { files } : {}),
  };
}

// ── Chat loading ─────────────────────────────────────────────────────────────

function applyChatDetail(chatId: string, detail: Awaited<ReturnType<typeof fetchChatDetail>>) {
  lastMessageByChatId.value = {
    ...lastMessageByChatId.value,
    [chatId]: detail.messages.at(-1),
  };
  localMessages.value = detail.messages;
  const restored: Record<string, string[]> = {};
  for (const msg of detail.messages) {
    if (msg.type === "options") {
      const ids = (msg.payload as OptionsPayload | null)?.selected_ids;
      if (ids?.length) restored[msg.id] = ids;
    }
  }
  if (Object.keys(restored).length) {
    resolvedOptionIdsByMessageId.value = {
      ...resolvedOptionIdsByMessageId.value,
      ...restored,
    };
  }
}

async function loadChat(chatId: string, options: { silent?: boolean } = {}) {
  if (!options.silent) messagesLoaded.value = false;

  const detail = await fetchChatDetail(chatId);

  applyChatDetail(chatId, detail);

  if (!options.silent) {
    await nextTick(); // ← ключевая строка
    messagesLoaded.value = true;
  }
}

// ── Message creation helpers ─────────────────────────────────────────────────

function createLocalMessage(params: {
  id: string;
  role: "user" | "assistant";
  content: string;
  type?: "dialog" | "options";
  payload?: Record<string, unknown> | null;
}): Message {
  return {
    id: params.id,
    role: params.role,
    type: params.type ?? "dialog",
    content: params.content,
    payload: params.payload ?? null,
    created_at: new Date().toISOString(),
  };
}

// ── Streaming ────────────────────────────────────────────────────────────────

type StreamDraftState = { text: string; eventPreviews: EventPreview[]; vmsLink: string | null; vmsLinks: VmsPersonLink[] | null; vmsRequest: Record<string, unknown> | null };

function renderDraftContent(stream: StreamDraftState): string {
  return stream.text || "...";
}

function updateAssistantDraft(assistantDraftId: string, stream: StreamDraftState) {
  const content = renderDraftContent(stream);
  localMessages.value = localMessages.value.map((message) =>
    message.id === assistantDraftId
      ? ({
          ...message,
          content,
          stage: currentStage.value,
          payload: {
            ...(message.payload as DialogPayload | null),
            event_previews: stream.eventPreviews,
            vms_link: stream.vmsLink,
            vms_links: stream.vmsLinks,
            vms_request: stream.vmsRequest,
          },
        } as ChatMessage)
      : message,
  );
}

async function runAssistantStream(params: {
  roomId: string;
  assistantDraftId: string;
  request: (onEvent: (type: string, raw: unknown) => void) => Promise<void>;
  reloadOnError?: boolean;
}) {
  const stream: StreamDraftState = { text: "", eventPreviews: [], vmsLink: null, vmsLinks: null, vmsRequest: null };
  currentStage.value = null;
  let reloadRoomId: string | null = null;

  try {
    await params.request((type, raw) => {
      const data = raw as Record<string, unknown>;

      if (type === "text") {
        stream.text += String(data.content ?? "");
        updateAssistantDraft(params.assistantDraftId, stream);
        return;
      }
      if (type === "stage") {
        currentStage.value = String(data.stage ?? "");
        updateAssistantDraft(params.assistantDraftId, stream);
        return;
      }
      if (type === "previews") {
        stream.eventPreviews = (data.event_previews as EventPreview[]) ?? [];
        stream.vmsLink = (data.vms_link as string | null) ?? null;
        stream.vmsLinks = (data.vms_links as VmsPersonLink[] | null) ?? null;
        updateAssistantDraft(params.assistantDraftId, stream);
        return;
      }
      if (type === "interrupt") {
        // Remove streaming draft — chat reload will show the saved options message
        currentStage.value = null;
        localMessages.value = localMessages.value.filter(
          (m) => m.id !== params.assistantDraftId,
        );
        reloadRoomId = params.roomId;
        return;
      }
      if (type === "done") {
        stream.vmsRequest = (data.vms_request as Record<string, unknown> | null) ?? null;
        stream.vmsLink = (data.vms_link as string | null) ?? stream.vmsLink;
        stream.vmsLinks = (data.vms_links as VmsPersonLink[] | null) ?? stream.vmsLinks;
        stream.eventPreviews = (data.event_previews as EventPreview[] | null) ?? stream.eventPreviews;
        currentStage.value = null;
        updateAssistantDraft(params.assistantDraftId, stream);
        void queryClient.invalidateQueries({ queryKey: ["chats"] });
      }
    });
  } catch (error) {
    if (params.reloadOnError) {
      await loadChat(params.roomId);
      return;
    }
    localMessages.value = localMessages.value.map((message) =>
      message.id === params.assistantDraftId
        ? { ...message, content: "Failed to get response. Check backend logs and retry." }
        : message,
    );
  } finally {
    isStreaming.value = false;
    currentStage.value = null;
  }
  if (reloadRoomId) {
    await loadChat(reloadRoomId, { silent: true });
  }
}

// ── Resolution flow ──────────────────────────────────────────────────────────

function buildSelectedLabels(message: Message, selectedIds: string[]): string[] {
  const selectedSet = new Set(selectedIds.map(String));
  const options = (message.payload as OptionsPayload)?.options ?? [];
  const labels = options
    .filter((opt) => selectedSet.has(String(opt.id)))
    .map((opt) => opt.value.trim())
    .filter(Boolean);
  return labels.length ? labels : selectedIds.filter(Boolean);
}

function buildResolutionContent(labels: string[]): string {
  return labels.length ? labels.join(", ") : "Выбор подтвержден";
}

function isOptionsMessageLocked(message: Message): boolean {
  const index = localMessages.value.findIndex((m) => m.id === message.id);
  if (index === -1) return false;
  // Locked if any message exists after this options card (no user resolution message is saved to DB)
  return index < localMessages.value.length - 1;
}

function getResolvedOptionIds(message: Message): string[] {
  return resolvedOptionIdsByMessageId.value[message.id] ?? [];
}

async function startResolutionFlow(
  roomId: string,
  optionsMessage: Message,
  selectedIds: string[],
): Promise<void> {
  const resolutionId = (optionsMessage.payload as OptionsPayload)?.resolution_id;
  if (!resolutionId) return;

  const selectedLabels = buildSelectedLabels(optionsMessage, selectedIds);
  const userDraft = createLocalMessage({
    id: makeTempId("temp-resolution"),
    role: "user",
    content: buildResolutionContent(selectedLabels),
  });
  const assistantDraftId = makeTempId("temp-assistant");
  const assistantDraft = createLocalMessage({
    id: assistantDraftId,
    role: "assistant",
    content: "...",
  });

  localMessages.value = [...localMessages.value, userDraft, assistantDraft];
  lastMessageByChatId.value = { ...lastMessageByChatId.value, [roomId]: assistantDraft };
  isStreaming.value = true;

  await runAssistantStream({
    roomId,
    assistantDraftId,
    request: (onEvent) => streamResolution(roomId, resolutionId, selectedIds, onEvent),
    reloadOnError: true,
  });
}

async function handleResolutionResponse(
  roomId: string,
  content: string,
  optionsMessage: Message,
): Promise<boolean> {
  const payload = optionsMessage.payload as OptionsPayload | null;
  if (!payload?.resolution_id) return false;

  const options = payload.options ?? [];
  const selectionMode = payload.selection_mode ?? "single";

  const matched = options.filter((opt) =>
    opt.value.toLowerCase().includes(content.toLowerCase()),
  );
  if (matched.length === 0) return false;
  if (selectionMode === "single" && matched.length !== 1) return false;

  await startResolutionFlow(roomId, optionsMessage, matched.map((o) => String(o.id)));
  return true;
}

async function handleOptionsConfirm(
  message: Message,
  payload?: { selected_ids: string[] },
) {
  if (!(message.payload as OptionsPayload)?.resolution_id || !payload?.selected_ids?.length) return;
  const roomId = selectedChatId.value;
  if (!roomId) return;
  resolvedOptionIdsByMessageId.value = {
    ...resolvedOptionIdsByMessageId.value,
    [message.id]: payload.selected_ids,
  };
  await startResolutionFlow(roomId, message, payload.selected_ids);
}

// ── Chat CRUD mutations ──────────────────────────────────────────────────────

function upsertChat(chat: Chat) {
  queryClient.setQueryData<Chat[]>(["chats"], (current = []) => {
    const next = current.filter((item) => item.id !== chat.id);
    return [chat, ...next];
  });
}

function removeChat(chatId: string) {
  queryClient.setQueryData<Chat[]>(["chats"], (current = []) =>
    current.filter((item) => item.id !== chatId),
  );
}

function selectFallbackChat(deletedChatId: string) {
  const remaining = (chats.value ?? []).filter((chat) => chat.id !== deletedChatId);
  chatStore.selectChat(remaining[0]?.id ?? null);
}

const createChatMutation = useMutation({
  mutationFn: () => createChat(null),
  onSuccess: (chat) => {
    upsertChat(chat);
    lastMessageByChatId.value = { ...lastMessageByChatId.value, [chat.id]: undefined };
    localMessages.value = [];
    messagesLoaded.value = true;
    chatStore.selectChat(chat.id);
    void queryClient.invalidateQueries({ queryKey: ["chats"] });
  },
});

const deleteChatMutation = useMutation({
  mutationFn: (chatId: string) => deleteChat(chatId),
  onSuccess: async (_, chatId) => {
    removeChat(chatId);
    const nextMap = { ...lastMessageByChatId.value };
    delete nextMap[chatId];
    lastMessageByChatId.value = nextMap;
    if (selectedChatId.value === chatId) selectFallbackChat(chatId);
    await queryClient.invalidateQueries({ queryKey: ["chats"] });
  },
});

// ── Event handlers ───────────────────────────────────────────────────────────

function getEventDetail(event: CustomEvent) {
  const raw = event.detail;
  return Array.isArray(raw) ? raw[0] : raw;
}

function getRoomIdFromEvent(detail: any): string | null {
  return detail?.roomId ?? detail?.room?.roomId ?? detail?.message?.roomId ?? selectedChatId.value;
}

function getContentFromEvent(detail: any): string {
  return String(
    detail?.content ?? detail?.message?.content ?? detail?.newMessage?.content ?? "",
  ).trim();
}

function handleCreateChat() {
  createChatMutation.mutate();
}

function handleFetchMessages(event: CustomEvent) {
  const detail = getEventDetail(event);
  const roomId = getRoomIdFromEvent(detail);
  if (roomId && roomId !== selectedChatId.value) {
    chatStore.selectChat(roomId);
  }
}

function handleRoomAction(event: CustomEvent) {
  const detail = getEventDetail(event);
  const action = detail?.action?.name ?? detail?.action?.title ?? detail?.action?.value;
  const roomId = getRoomIdFromEvent(detail);
  if (action === "delete-chat" && roomId) {
    deleteChatMutation.mutate(roomId);
  }
}

async function handleSendMessage(event: CustomEvent) {
  const detail = getEventDetail(event);
  const roomId = getRoomIdFromEvent(detail);
  const content = getContentFromEvent(detail);

  // Extract attached image (only first; reject multiple)
  const rawFiles: unknown[] = detail?.files ?? detail?.message?.files ?? [];
  if (rawFiles.length > 1) {
    const errId = makeTempId("temp-error");
    localMessages.value = [
      ...localMessages.value,
      createLocalMessage({ id: errId, role: "assistant", content: "Можно прикрепить только одно изображение." }),
    ];
    return;
  }
  const rawFile = rawFiles[0] as Record<string, unknown> | undefined;
  // vue-advanced-chat passes a Blob (not File) in rawFile.blob
  let file: File | undefined;
  if (rawFile) {
    const blob = rawFile.blob;
    const name = String(rawFile.name ?? rawFile.extension ?? "photo");
    const type = String(rawFile.type ?? "image/jpeg");
    if (blob instanceof File) {
      file = blob;
    } else if (blob instanceof Blob) {
      file = new File([blob], name, { type });
    }
  }

  if (!roomId || (!content.trim() && !file) || isStreaming.value) return;

  // If last message is an OPTIONS type, try to handle as natural-language resolution
  const lastMsg = localMessages.value.at(-1);
  if (lastMsg?.type === "options" && !file) {
    const handled = await handleResolutionResponse(roomId, content, lastMsg);
    if (handled) return;
  }

  const userContent = content.trim() || "📎 Фотография";
  const userDraftId = makeTempId("temp-user");
  const assistantDraftId = makeTempId("temp-assistant");
  const userDraft = createLocalMessage({ id: userDraftId, role: "user", content: userContent });
  const assistantDraft = createLocalMessage({ id: assistantDraftId, role: "assistant", content: "..." });

  localMessages.value = [...localMessages.value, userDraft, assistantDraft];
  lastMessageByChatId.value = { ...lastMessageByChatId.value, [roomId]: assistantDraft };
  isStreaming.value = true;

  await runAssistantStream({
    roomId,
    assistantDraftId,
    request: (onEvent) => streamMessage(roomId, content, onEvent, file),
  });
}

function handleAddRoomEvent() { handleCreateChat(); }
function handleFetchMessagesEvent(event: Event) { handleFetchMessages(event as CustomEvent); }
function handleSendMessageEvent(event: Event) {
  void handleSendMessage(event as CustomEvent);
}
function handleRoomActionEvent(event: Event) { handleRoomAction(event as CustomEvent); }

function handlePageClick(e: MouseEvent) {
  const link = e.composedPath().find(
    (n): n is HTMLAnchorElement => (n as Element).tagName === "A",
  );
  if (!link) return;
  const href = link.getAttribute("href") ?? "";
  if (href.startsWith("#filter:")) {
    e.preventDefault();
    const msgId = href.slice("#filter:".length);
    const msg = localMessages.value.find((m) => m.id === msgId);
    const vmsRequest = (msg?.payload as DialogPayload)?.vms_request;
    if (vmsRequest) {
      filterModalPayload.value = vmsRequest as object;
    }
  }
}

onBeforeUnmount(() => {
  // nothing to clean up
});
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
}

.inline-options-slot {
  display: block;
}

/* ── VMS request filter modal ────────────────────────────── */
.filter-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.filter-modal {
  background: #fff;
  border-radius: 8px;
  width: 560px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.filter-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-weight: 600;
  border-bottom: 1px solid #eee;
}

.filter-modal-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  padding: 0 4px;
}

.filter-modal-body {
  overflow-y: auto;
  padding: 16px;
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}
</style>
