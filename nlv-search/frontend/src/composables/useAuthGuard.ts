import { computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

interface AuthGuardOptions {
  autoRedirect?: boolean;
  redirectTo?: string;
}

export function useAuthGuard(options: AuthGuardOptions = {}) {
  const { autoRedirect = false, redirectTo = "/profile" } = options;
  const router = useRouter();
  const authStore = useAuthStore();

  const isAuthenticated = computed(() => authStore.isAuthenticated);

  watch(
    isAuthenticated,
    (isAuth) => {
      if (!isAuth && autoRedirect) {
        router.push(redirectTo);
      }
    },
    { immediate: false },
  );

  function requireAuth(): boolean {
    if (!isAuthenticated.value && autoRedirect) {
      router.push(redirectTo);
      return false;
    }
    return isAuthenticated.value;
  }

  return { isAuthenticated, requireAuth, authStore };
}
