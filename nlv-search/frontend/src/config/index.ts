const rawBaseUrl = (import.meta.env.VITE_BACKEND_URL as string | undefined) || "http://localhost:8000";
export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");
export const API_TIMEOUT = 60000;

export const STORAGE_KEYS = {
  token: "access_token",
  user: "nvs_user",
} as const;

export const FEATURE_FLAGS = {
  showVmsLinks: true,
};

export function readStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEYS.token);
  } catch {
    return null;
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.token);
  } catch {
    // ignore
  }
}
