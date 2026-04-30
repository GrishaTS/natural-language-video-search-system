<template>
  <div class="card panel">
    <div class="chat-header" style="margin-bottom: 16px;">
      <div>
        <div class="title" style="font-weight: 700;">Статусы сервисов</div>
        <div class="muted" style="font-size: 13px;">Состояние интеграций backend</div>
      </div>
      <button class="icon-btn" title="Обновить" @click="refetchAll">⟳</button>
    </div>

    <div class="status-grid">
      <div class="status-card">
        <div class="muted">Backend</div>
        <div style="font-weight: 700;">{{ health?.service }}</div>
        <div :class="health?.status === 'ok' ? 'status-ok' : 'status-error'">
          {{ health?.status || "…" }} <span class="muted">v{{ health?.version }}</span>
        </div>
      </div>

      <div
        v-for="(value, key) in services"
        :key="key"
        class="status-card"
      >
        <div class="muted">{{ key }}</div>
        <div :class="getStatusClass(value)" style="font-weight: 700;">
          {{ value }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { fetchHealth, fetchHealthServices } from "../api/health";

const healthQuery = useQuery({
  queryKey: ["health"],
  queryFn: () => fetchHealth(),
});

const servicesQuery = useQuery({
  queryKey: ["health-services"],
  queryFn: () => fetchHealthServices(),
});

const health = computed(() => healthQuery.data.value);
const services = computed(() => servicesQuery.data.value);

const isHealthy = (value?: string) => {
  if (!value) return false;
  if (value === "ok") return true;
  const ratioMatch = value.match(/^(\d+)\/(\d+)$/);
  if (!ratioMatch) return false;
  const [, current, total] = ratioMatch;
  return Number(current) === Number(total);
};

const getStatusClass = (value?: string) => {
  return isHealthy(value) ? "status-ok" : "status-error";
};

const refetchAll = () => {
  healthQuery.refetch();
  servicesQuery.refetch();
};
</script>
