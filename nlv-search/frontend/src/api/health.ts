import api from "./http";
import type { HealthResponse, HealthServicesResponse } from "../types/health";

export const fetchHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
};

export const fetchHealthServices = async (): Promise<HealthServicesResponse> => {
  const { data } = await api.get<HealthServicesResponse>("/health/services");
  return data;
};
