<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="tabs">
        <RouterLink
          to="/chat"
          class="tab"
          :class="{ active: route.name === 'chat' }"
          >Чат</RouterLink
        >
        <RouterLink
          to="/status"
          class="tab"
          :class="{ active: route.name === 'status' }"
          >Статусы сервисов</RouterLink
        >
        <RouterLink
          to="/profile"
          class="tab"
          :class="{ active: route.name === 'profile' }"
          >Профиль</RouterLink
        >
      </div>
      <div class="auth-actions">
        <div v-if="auth.user" class="pill">
          {{ auth.user.username }} · {{ auth.user.email }}
        </div>
        <RouterLink v-if="!auth.isAuthenticated" to="/auth" class="btn secondary">
          Войти
        </RouterLink>
        <button v-else class="btn secondary" @click="auth.logout()">Выйти</button>
      </div>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const route = useRoute();

onMounted(() => {
  auth.hydrate();
});
</script>
