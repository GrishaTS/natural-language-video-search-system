/// <reference types="vitest" />
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AxiosError, type AxiosRequestConfig } from "axios";
import { api, configureSessionHandlers } from "./http";
import { ApiError } from "./errors";

type AxiosAdapterResponse = {
  data: unknown;
  status: number;
  statusText: string;
  headers: Record<string, unknown>;
  config: AxiosRequestConfig;
};

describe("api http client session handlers", () => {
  beforeEach(() => {
    localStorage.clear();
    api.defaults.adapter = async (config) => {
      if (config?.url === "/unauthorized") {
        const error = new AxiosError("Unauthorized", "ERR_BAD_REQUEST", config, {}, {
          status: 401,
          statusText: "Unauthorized",
          headers: {},
          config: config || {},
          data: { message: "Unauthorized" },
        });
        throw error;
      }
      const safeConfig = config || {};
      return {
        data: { headers: safeConfig.headers },
        status: 200,
        statusText: "OK",
        headers: safeConfig.headers || {},
        config: safeConfig,
      } satisfies AxiosAdapterResponse;
    };
  });

  it("attaches Authorization header from token provider", async () => {
    configureSessionHandlers({
      getToken: () => "token-xyz",
      onUnauthorized: undefined,
    });

    const response = await api.get("/any");
    const headers = (response.data as { headers?: Record<string, string> }).headers;
    expect(headers?.Authorization).toBe("Bearer token-xyz");
  });

  it("notifies on unauthorized responses and returns ApiError", async () => {
    const onUnauthorized = vi.fn();
    configureSessionHandlers({
      getToken: () => null,
      onUnauthorized,
    });

    await expect(api.get("/unauthorized")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});
