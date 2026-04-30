export interface ApiErrorShape {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
}

export interface HealthResponse {
  service: string;
  version: string;
  status?: string;
}

export type ServicesHealthResponse = Record<string, unknown>;
