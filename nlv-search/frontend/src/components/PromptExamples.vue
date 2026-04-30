<script setup lang="ts">
const props = defineProps<{
  examples: string[];
}>();

const emit = defineEmits<{
  (e: "choose", prompt: string): void;
}>();
</script>

<template>
  <div class="card prompt-card">
    <div class="card-head">
      <div>
        <p class="eyebrow">Быстрый старт</p>
        <h3>Примеры запросов</h3>
      </div>
    </div>
    <div class="prompt-chips">
      <button
        v-for="example in props.examples"
        :key="example"
        class="chip actionable"
        @click="emit('choose', example)"
      >
        <span aria-hidden="true">✦</span>
        <span>{{ example }}</span>
      </button>
    </div>
  </div>
</template>
