export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface HealthServicesResponse {
  postgres: string;
  minio: string;
  qdrant: string;
  vms: string;
  ai: string;
  redis: string;
  tei: string;
  vllm: string;
}
