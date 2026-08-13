/**
 * Centralized API client for health and infrastructure checks
 */

import { config } from '../core/config';

export interface HealthResponse {
  status: string;
  app?: string;
  env?: string;
}

export interface DbHealthResponse {
  status: string;
  database?: string;
}

export async function checkAppHealth(): Promise<HealthResponse> {
  const url = `${config.apiBaseUrl}/v1/health`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`App health check failed with status: ${response.status}`);
  }

  return response.json();
}

export async function checkDatabaseHealth(): Promise<DbHealthResponse> {
  const url = `${config.apiBaseUrl}/v1/health/db`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`DB health check failed with status: ${response.status}`);
  }

  return response.json();
}
