<template>
  <div class="card panel" style="max-width: 520px; margin: 60px auto;">
    <div class="chat-header">
      <div>
        <div class="title" style="font-size: 18px; font-weight: 700;">
          {{ mode === "login" ? "Вход" : "Регистрация" }}
        </div>
        <div class="muted" style="margin-top: 4px;">
          Подключитесь, чтобы вести чаты и управлять профилем
        </div>
      </div>
      <div class="tabs" style="gap: 6px;">
        <button
          type="button"
          class="tab"
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >
          Вход
        </button>
        <button
          type="button"
          class="tab"
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >
          Регистрация
        </button>
      </div>
    </div>

    <form class="list" @submit.prevent="onSubmit">
      <div class="form-row">
        <label class="muted">Логин</label>
        <input v-model="form.username" class="input" autocomplete="username" required />
      </div>
      <div v-if="mode === 'register'" class="form-row">
        <label class="muted">Email</label>
        <input
          v-model="form.email"
          class="input"
          type="email"
          autocomplete="email"
          required
        />
      </div>
      <div class="form-row">
        <label class="muted">Пароль</label>
        <input
          v-model="form.password"
          class="input"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>
      <p v-if="error" style="color: #dc2626; margin: 0;">{{ error }}</p>
      <button class="btn" type="submit" :disabled="auth.loading">
        {{ auth.loading ? "..." : mode === "login" ? "Войти" : "Создать аккаунт" }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const mode = ref<"login" | "register">("login");
const error = ref("");
const form = reactive({
  username: "",
  email: "",
  password: "",
});

const onSubmit = async () => {
  error.value = "";
  try {
    if (mode.value === "login") {
      await auth.login({ username: form.username, password: form.password });
    } else {
      await auth.register({
        username: form.username,
        email: form.email,
        password: form.password,
      });
    }
    const redirect = (route.query.redirect as string) || "/chat";
    router.push(redirect);
  } catch (err: any) {
    const detail = err?.response?.data?.detail;
    error.value =
      typeof detail === "string"
        ? detail
        : err?.message === "Request timeout"
          ? "Backend не ответил за 15 секунд"
          : "Не удалось выполнить запрос";
  }
};
</script>
