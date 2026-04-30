<script setup lang="ts">
const props = defineProps<{
  services: Record<string, unknown>;
}>();

function isOk(status: unknown) {
  return String(status).toLowerCase() === "ok";
}

function isQdrantHealthy(status: unknown): boolean {
  const value = String(status).toLowerCase();
  if (value === "ok") return true;
  const match = value.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (!match) return false;
  const current = Number(match[1]);
  const total = Number(match[2]);
  return Number.isFinite(current) && Number.isFinite(total) && total > 0 && current === total;
}

function statusClass(name: string, status: unknown): string {
  if (name.toLowerCase() === "qdrant" && isQdrantHealthy(status)) {
    return "status-ok";
  }
  return isOk(status) ? "status-ok" : "status-bad";
}

function statusLabel(name: string, status: unknown): string {
  if (name.toLowerCase() === "qdrant" && isQdrantHealthy(status)) {
    return "ok";
  }
  return isOk(status) ? "ok" : String(status);
}
</script>

<template>
  <div class="status-grid">
    <div v-for="(serviceStatus, name) in props.services" :key="name" class="status-card">
      <div class="input-row status-row">
        <span>{{ name }}</span>
        <span :class="statusClass(name, serviceStatus)">
          {{ statusLabel(name, serviceStatus) }}
        </span>
      </div>
    </div>
    <div v-if="!Object.keys(props.services).length" class="muted">
      Нет информации о зависимостях.
    </div>
  </div>
</template>
