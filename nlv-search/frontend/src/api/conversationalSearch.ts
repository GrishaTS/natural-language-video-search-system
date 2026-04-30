import api, { backendUrl } from "./http";
import type { Chat, ChatDetailResponse } from "../types/chat";

const MESSAGE_TIMEOUT_MS = 5 * 60 * 1000; // 5 min — LLM can be slow

export function buildSnapshotProxyUrl(snapshotPath: string): string {
  if (!snapshotPath) return "";
  const base =
    snapshotPath.startsWith("http://") || snapshotPath.startsWith("https://")
      ? snapshotPath
      : `${backendUrl}${snapshotPath.startsWith("/") ? "" : "/"}${snapshotPath}`;
  const token = localStorage.getItem("access_token");
  if (!token) return base;
  return `${base}${base.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
}

export const listChats = async (): Promise<Chat[]> => {
  const { data } = await api.get<Chat[]>("/chats");
  return data;
};

export const createChat = async (title?: string | null): Promise<Chat> => {
  const { data } = await api.post<Chat>("/chats", { title: title || null });
  return data;
};

export const deleteChat = async (chatId: string): Promise<void> => {
  await api.delete(`/chats/${chatId}`);
};

export const fetchChatDetail = async (chatId: string): Promise<ChatDetailResponse> => {
  const { data } = await api.get<ChatDetailResponse>(`/chats/${chatId}`);
  return data;
};

// ── SSE streaming ────────────────────────────────────────────────────────────

/**
 * Low-level SSE POST helper.
 * Calls onEvent(type, rawEvent) for each parsed event.
 * rawEvent is the full parsed JSON object (not just content).
 */
async function streamSseRequest(
  path: string,
  body: FormData | Record<string, unknown>,
  onEvent: (type: string, raw: unknown) => void,
): Promise<void> {
  const token = localStorage.getItem("access_token");
  const isFormData = body instanceof FormData;

  let response: Response;
  try {
    response = await fetch(`${backendUrl}${path}`, {
      method: "POST",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: isFormData ? body : JSON.stringify(body),
      signal: AbortSignal.timeout(MESSAGE_TIMEOUT_MS),
    });
  } catch (err) {
    throw err;
  }

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (raw === "[DONE]") continue;
        try {
          const ev = JSON.parse(raw);
          onEvent(ev.type, ev);
        } catch { /* malformed chunk — skip */ }
      }
    }
    if (buf.startsWith("data: ")) {
      const raw = buf.slice(6).trim();
      if (raw !== "[DONE]") {
        try {
          const ev = JSON.parse(raw);
          onEvent(ev.type, ev);
        } catch { /* skip */ }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const streamMessage = async (
  chatId: string,
  content: string,
  onEvent: (type: string, raw: unknown) => void,
  image?: File,
): Promise<void> => {
  const formData = new FormData();
  formData.append("content", content);
  if (image) {
    formData.append("image", image);
  }
  return streamSseRequest(`/chats/${chatId}/messages/stream`, formData, onEvent);
};

export const streamResolution = async (
  chatId: string,
  resolutionId: string,
  selectedIds: string[],
  onEvent: (type: string, raw: unknown) => void,
): Promise<void> =>
  streamSseRequest(
    `/chats/${chatId}/resolution`,
    { resolution_id: resolutionId, selected_ids: selectedIds },
    onEvent,
  );
