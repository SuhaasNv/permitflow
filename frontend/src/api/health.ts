import { request } from './client'

/** `GET /health`: liveness, the database, and the build that answers (US-094). Public, no token needed. */
export interface Health {
  status: 'ok' | 'degraded'
  database: 'ok' | 'unreachable'
  version: string
  commit: string
  environment: 'development' | 'test' | 'production'
}

export function getHealth(): Promise<Health> {
  return request<Health>('/health')
}
