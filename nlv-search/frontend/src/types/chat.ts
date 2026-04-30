export interface EventPreview {
  event_id: string;
  snapshot_url: string; // relative path — pass to buildSnapshotProxyUrl()
  timestamp: string; // ISO 8601
}

export interface VmsPersonLink {
  label: string; // display name: "Иван Иванов"
  url: string;   // vms frontend URL with firstName/lastName in searchData
}

export interface DialogPayload {
  vms_link?: string | null;
  vms_links?: VmsPersonLink[] | null; // per-person links для multi-person поиска
  vms_request?: Record<string, unknown> | null;
  event_previews?: EventPreview[];
  image_url?: string | null;
}

export interface OptionsPayload {
  resolution_id: string;
  entity_value: string;
  entity_type: "person" | "address" | "vehicle" | "face";
  selection_mode: "single" | "multi";
  options: Array<{ id: string; value: string }>;
  selected_ids?: string[];
}

export interface Chat {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  last_message?: Message | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  type: "dialog" | "options";
  content: string;
  payload: DialogPayload | OptionsPayload | null;
  created_at: string;
}

export interface ChatDetailResponse extends Chat {
  messages: Message[];
}

/** Extended message used by ChatView streaming drafts (stage is transient, not persisted) */
export interface ChatMessage extends Message {
  stage?: string | null;
  streamStatus?: string | null;
}
