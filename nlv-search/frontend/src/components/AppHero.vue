<script setup lang="ts">
const props = defineProps<{
  title: string;
  subtitle?: string;
  badges?: { label: string; tone?: "info" | "warn" | "accent" }[];
}>();

const toneClass = (tone?: string) => {
  if (tone === "warn") return "badge warn";
  if (tone === "accent") return "badge accent";
  return "badge";
};
</script>

<template>
  <div class="hero">
    <div class="hero-grid">
      <div class="hero-text">
        <p class="eyebrow">Natural Language Video Search</p>
        <h1>{{ props.title }}</h1>
        <p v-if="props.subtitle" class="subtitle">{{ props.subtitle }}</p>
        <div v-if="props.badges?.length" class="hero-badges">
          <span v-for="badge in props.badges" :key="badge.label" :class="toneClass(badge.tone)">
            {{ badge.label }}
          </span>
        </div>
      </div>
      <div class="hero-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>
