import { request } from "./client";

export interface Health {
  status: "ok" | "degraded";
  database: "ok" | "unreachable";
}

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}
