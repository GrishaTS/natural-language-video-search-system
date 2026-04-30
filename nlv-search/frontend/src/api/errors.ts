import axios, { AxiosError } from "axios";
import type { ApiErrorShape } from "@/types/common";

export class ApiError extends Error implements ApiErrorShape {
  status: number;
  code?: string;
  details?: unknown;

  constructor(payload: ApiErrorShape) {
    super(payload.message);
    this.status = payload.status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

function extractAxiosData(error: AxiosError) {
  const status = error.response?.status ?? 0;
  const data = (error.response?.data ?? {}) as Record<string, unknown>;
  const message =
    typeof data.message === "string"
      ? data.message
      : typeof error.message === "string"
        ? error.message
        : "Request failed";
  const code = typeof data.code === "string" ? data.code : undefined;
  const details = data.details ?? data;
  return { status, code, message, details };
}

export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    const payload = extractAxiosData(error);
    return new ApiError(payload);
  }
  if (error instanceof Error) {
    return new ApiError({ status: 0, message: error.message });
  }
  return new ApiError({ status: 0, message: "Unknown error" });
}
