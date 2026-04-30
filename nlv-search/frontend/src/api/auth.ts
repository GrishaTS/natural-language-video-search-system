import api from "./http";
import type { AuthResponse, UserRead } from "../types/auth";

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export const register = async (payload: RegisterPayload): Promise<AuthResponse> => {
  const { data } = await api.post<AuthResponse>("/auth/register", payload);
  return data;
};

export const login = async (payload: LoginPayload): Promise<AuthResponse> => {
  const params = new URLSearchParams();
  params.append("username", payload.username);
  params.append("password", payload.password);
  const { data } = await api.post<AuthResponse>("/auth/login", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
};

export const fetchCurrentUser = async (): Promise<UserRead> => {
  const { data } = await api.get<UserRead>("/auth/me");
  return data;
};

export const logout = async (): Promise<void> => {
  await api.post("/auth/logout");
};

export const deleteMe = async (): Promise<void> => {
  await api.delete("/auth/me");
};
