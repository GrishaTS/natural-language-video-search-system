<script setup lang="ts">
const props = defineProps<{
  title?: string;
  message?: string;
  tone?: "info" | "success" | "warning" | "danger";
}>();

const toneClass = (tone?: string) => {
  if (tone === "success") return "alert success";
  if (tone === "warning") return "alert warning";
  if (tone === "danger") return "alert danger";
  return "alert info";
};
</script>

<template>
  <div :class="toneClass(props.tone)">
    <div v-if="props.title" class="alert-title">{{ props.title }}</div>
    <div>
      <slot>{{ props.message }}</slot>
    </div>
  </div>
</template>
