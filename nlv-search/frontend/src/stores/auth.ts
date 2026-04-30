import { defineStore } from "pinia";
import api from "../api/http";
import {
  deleteMe,
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from "../api/auth";
import type { AuthResponse, UserRead } from "../types/auth";

interface AuthState {
  token: string | null;
  user: UserRead | null;
  loading: boolean;
}

const ACCESS_TOKEN_KEY = "access_token";

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: localStorage.getItem(ACCESS_TOKEN_KEY),
    user: null,
    loading: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
  },
  actions: {
    setToken(token: string | null) {
      this.token = token;
      if (token) {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
        api.defaults.headers.common.Authorization = `Bearer ${token}`;
      } else {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        delete api.defaults.headers.common.Authorization;
      }
    },
    async hydrate() {
      if (!this.token) return;
      try {
        this.user = await fetchCurrentUser();
      } catch (err) {
        this.setToken(null);
        this.user = null;
      }
    },
    async register(payload: {
      username: string;
      email: string;
      password: string;
    }): Promise<AuthResponse> {
      this.loading = true;
      try {
        const data = await apiRegister(payload);
        this.setToken(data.access_token);
        this.user = data.user;
        return data;
      } finally {
        this.loading = false;
      }
    },
    async login(payload: { username: string; password: string }): Promise<AuthResponse> {
      this.loading = true;
      try {
        const data = await apiLogin(payload);
        this.setToken(data.access_token);
        this.user = data.user;
        return data;
      } finally {
        this.loading = false;
      }
    },
    async logout() {
      try {
        await apiLogout();
      } catch (err) {
        // ignore
      } finally {
        this.setToken(null);
        this.user = null;
      }
    },
    async deleteAccount() {
      await deleteMe();
      this.setToken(null);
      this.user = null;
    },
  },
});
