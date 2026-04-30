<template>
  <div class="card panel" style="max-width: 640px;">
    <div class="chat-header" style="margin-bottom: 12px;">
      <div>
        <div class="title" style="font-weight: 700;">Профиль</div>
        <div class="muted" style="font-size: 13px;">Учётная запись и действия</div>
      </div>
      <button class="icon-btn" title="Обновить" @click="refresh">⟳</button>
    </div>

    <div v-if="user" class="list">
      <div><strong>Логин:</strong> {{ user.username }}</div>
      <div><strong>Email:</strong> {{ user.email }}</div>
      <div class="muted">ID: {{ user.id }}</div>
      <div class="muted">Статус: {{ user.is_active ? "активен" : "заблокирован" }}</div>
      <div style="display: flex; gap: 10px; margin-top: 6px;">
        <button class="btn secondary" @click="logout">Выйти</button>
        <button class="btn" style="background: #dc2626;" @click="deleteAccount">
          Удалить аккаунт
        </button>
      </div>
    </div>
    <div v-else class="empty-state">Авторизуйтесь, чтобы увидеть профиль</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const user = computed(() => auth.user);

const refresh = () => auth.hydrate();

const logout = async () => {
  await auth.logout();
  router.push("/auth");
};

const deleteAccount = async () => {
  await auth.deleteAccount();
  router.push("/auth");
};
</script>
