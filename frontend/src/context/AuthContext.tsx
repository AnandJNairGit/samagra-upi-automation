/**
 * Authentication Context maintaining in-memory access token, admin profile,
 * and automatic session restoration on app initialization.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { AdminUser, AuthState } from '../types/auth';
import { getMeApi, loginApi, logoutAllApi, logoutApi, refreshApi } from '../services/apiClient';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [admin, setAdmin] = useState<AdminUser | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Function to refresh session from HttpOnly cookie
  const refreshSession = async (): Promise<boolean> => {
    try {
      const response = await refreshApi();
      if (response && response.access_token) {
        setAccessTokenState(response.access_token);
        // Also fetch fresh user profile to ensure active status
        const profile = await getMeApi();
        setAdmin(profile);
        return true;
      }
      setAdmin(null);
      setAccessTokenState(null);
      return false;
    } catch {
      setAdmin(null);
      setAccessTokenState(null);
      return false;
    }
  };

  // Restore session from HttpOnly refresh cookie on application mount
  useEffect(() => {
    let isMounted = true;

    async function initAuth() {
      await refreshSession();
      if (isMounted) {
        setIsLoading(false);
      }
    }

    initAuth();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await loginApi(email, password);
      setAccessTokenState(response.access_token);
      setAdmin(response.admin);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await logoutApi();
    } finally {
      setAdmin(null);
      setAccessTokenState(null);
      setIsLoading(false);
    }
  };

  const logoutAll = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await logoutAllApi();
    } finally {
      setAdmin(null);
      setAccessTokenState(null);
      setIsLoading(false);
    }
  };

  const value: AuthContextType = {
    admin,
    accessToken,
    isAuthenticated: !!admin && !!accessToken,
    isLoading,
    login,
    logout,
    logoutAll,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
