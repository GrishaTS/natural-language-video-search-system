<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { ChatMessage, OptionsPayload } from "@/types/chat";

const props = withDefaults(defineProps<{
  message: ChatMessage;
  sending?: boolean;
  locked?: boolean;
  selectedIds?: string[];
}>(), {
  sending: false,
  locked: false,
  selectedIds: () => [],
});

const emit = defineEmits<{
  (e: "confirm", payload: { selected_ids: string[] }): void;
}>();

const localSelectedIds = ref<string[]>([]);

watch(
  [() => props.selectedIds, () => props.locked],
  ([ids, locked]) => {
    if (!locked && !(ids?.length)) return;
    localSelectedIds.value = (ids ?? []).map(String);
  },
  { immediate: true },
);

const optionsPayload = computed(() => props.message.payload as OptionsPayload | null);

const selectionMode = computed(() => optionsPayload.value?.selection_mode ?? "single");
const isMultiSelect = computed(() => selectionMode.value === "multi");

const title = computed(() => {
  const header = String(props.message.content || "").split("\n")[0]?.trim();
  return header || "Доступны варианты для уточнения";
});

const helperText = computed(() =>
  isMultiSelect.value
    ? "Можно выбрать несколько вариантов."
    : "Выберите один вариант и подтвердите выбор.",
);

const options = computed(() => optionsPayload.value?.options ?? []);

function sameId(left: string, right: string): boolean {
  return String(left) === String(right);
}

function isSelected(optionId: string): boolean {
  return localSelectedIds.value.some((item) => sameId(item, optionId));
}

function toggle(optionId: string): void {
  if (props.locked || props.sending) return;
  const normalizedId = String(optionId);
  if (!isMultiSelect.value) {
    localSelectedIds.value = [normalizedId];
    return;
  }

  const exists = localSelectedIds.value.some((item) => sameId(item, normalizedId));
  localSelectedIds.value = exists
    ? localSelectedIds.value.filter((item) => !sameId(item, normalizedId))
    : [...localSelectedIds.value, normalizedId];
}

const canConfirm = computed(() => localSelectedIds.value.length > 0);

function handleConfirm(): void {
  if (props.locked || props.sending || !canConfirm.value) return;
  emit("confirm", { selected_ids: [...localSelectedIds.value] });
}
</script>

<template>
  <section class="inline-options-card" :class="{ locked: props.locked }">
    <header class="card-header">
      <span class="card-kicker">Уточнение</span>
      <h4 class="card-title">{{ title }}</h4>
      <p class="card-helper">{{ helperText }}</p>
    </header>

    <div class="options-list">
      <label
        v-for="option in options"
        :key="String(option.id)"
        class="option-row"
        :class="{ selected: isSelected(option.id), disabled: props.locked || props.sending }"
      >
        <input
          :type="isMultiSelect ? 'checkbox' : 'radio'"
          :name="`options-${props.message.id}`"
          :checked="isSelected(option.id)"
          :disabled="props.locked || props.sending"
          @change="toggle(option.id)"
        />
        <span class="option-text">{{ option.value || "—" }}</span>
      </label>
    </div>

    <footer class="card-actions">
      <button
        type="button"
        class="confirm-btn"
        :disabled="props.locked || props.sending || !canConfirm"
        @click="handleConfirm"
      >
        {{ props.locked ? "Выбор сохранен" : "Подтвердить" }}
      </button>
    </footer>
  </section>
</template>

<style scoped>
.inline-options-card {
  width: min(420px, 100%);
  background: #fff;
  border: 1px solid #d7dce5;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.inline-options-card.locked {
  opacity: 0.92;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.card-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #2563eb;
}

.card-title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  color: #111827;
}

.card-helper {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.options-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.option-row {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  cursor: pointer;
  border-bottom: 1px solid #eef1f5;
}

.option-row:last-child {
  border-bottom: 0;
}

.option-row.selected {
  color: #111827;
}

.option-row.disabled {
  cursor: default;
}

.option-row input {
  margin: 0;
  width: 18px;
  height: 18px;
}

.option-text {
  color: #111827;
  font-size: 15px;
  line-height: 1.35;
}

.card-actions {
  display: flex;
  justify-content: flex-start;
  margin-top: 16px;
}

.confirm-btn {
  border: 0;
  border-radius: 10px;
  background: #1d4ed8;
  color: #fff;
  padding: 12px 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
