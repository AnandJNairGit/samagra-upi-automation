/**
 * Authentication and Admin Types
 */

export interface AdminUser {
  public_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  admin: AdminUser;
}

export interface AdminHealthResponse {
  status: string;
  authenticated: boolean;
  admin_email: string;
  admin_public_id: string;
}

export interface AuthState {
  admin: AdminUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
