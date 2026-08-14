/**
 * Centralized API client with in-memory JWT storage, mutex-protected token refresh,
 * and automatic 401 replay handling.
 */

import { config } from '../core/config';
import { AdminHealthResponse, AdminUser, LoginResponse } from '../types/auth';

let inMemoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return inMemoryAccessToken;
}

export function setAccessToken(token: string | null): void {
  inMemoryAccessToken = token;
}

/**
 * Perform token refresh with single-flight mutex to avoid multiple concurrent refresh storms.
 */
async function performTokenRefresh(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${config.apiBaseUrl}/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
        credentials: 'same-origin',
      });

      if (!response.ok) {
        setAccessToken(null);
        return null;
      }

      const data: LoginResponse = await response.json();
      setAccessToken(data.access_token);
      return data.access_token;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Standardized fetch client with automatic token injection and 401 retry.
 */
export async function apiFetch(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  const url = endpoint.startsWith('http') ? endpoint : `${config.apiBaseUrl}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const currentToken = getAccessToken();
  if (currentToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${currentToken}`);
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: 'same-origin',
  };

  let response = await fetch(url, fetchOptions);

  // If 401 received and not currently calling login or refresh endpoints, attempt one refresh & replay
  const isAuthEndpoint = endpoint.includes('/v1/auth/login') || endpoint.includes('/v1/auth/refresh');
  if (response.status === 401 && !isAuthEndpoint) {
    const newToken = await performTokenRefresh();
    if (newToken) {
      const retryHeaders = new Headers(fetchOptions.headers);
      retryHeaders.set('Authorization', `Bearer ${newToken}`);
      response = await fetch(url, {
        ...fetchOptions,
        headers: retryHeaders,
      });
    }
  }

  return response;
}

// ----------------------------------------------------------------------------
// Typed Authentication API Functions
// ----------------------------------------------------------------------------

export async function loginApi(email: string, password: string): Promise<LoginResponse> {
  const response = await apiFetch('/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Invalid email or password.');
  }

  const data: LoginResponse = await response.json();
  setAccessToken(data.access_token);
  return data;
}

export async function refreshApi(): Promise<LoginResponse | null> {
  const response = await apiFetch('/v1/auth/refresh', {
    method: 'POST',
  });

  if (!response.ok) {
    setAccessToken(null);
    return null;
  }

  const data: LoginResponse = await response.json();
  setAccessToken(data.access_token);
  return data;
}

export async function logoutApi(): Promise<void> {
  try {
    await apiFetch('/v1/auth/logout', {
      method: 'POST',
    });
  } finally {
    setAccessToken(null);
  }
}

export async function logoutAllApi(): Promise<void> {
  try {
    await apiFetch('/v1/auth/logout-all', {
      method: 'POST',
    });
  } finally {
    setAccessToken(null);
  }
}

export async function getMeApi(): Promise<AdminUser> {
  const response = await apiFetch('/v1/auth/me', {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error('Failed to retrieve administrator profile.');
  }

  return response.json();
}

export async function getAdminHealthApi(): Promise<AdminHealthResponse> {
  const response = await apiFetch('/v1/admin/health', {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error('Admin health verification failed.');
  }

  return response.json();
}
