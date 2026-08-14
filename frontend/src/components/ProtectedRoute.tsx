/**
 * Protected route guard requiring active authenticated administrator.
 */

import React, { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  onNavigate?: (path: string) => void;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, onNavigate }) => {
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      if (onNavigate) {
        onNavigate('/upi/admin/login');
      } else {
        window.history.pushState({}, '', '/upi/admin/login');
        window.dispatchEvent(new PopStateEvent('popstate'));
      }
    }
  }, [isLoading, isAuthenticated, onNavigate]);

  if (isLoading) {
    return (
      <div className="card loading-card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <Loader2 className="spinner" size={36} color="#818cf8" />
        <p style={{ marginTop: '1rem', color: '#94a3b8' }}>Verifying administrator session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem 1rem' }}>
        <ShieldAlert size={40} color="#f87171" style={{ margin: '0 auto 1rem' }} />
        <h2 style={{ color: '#f87171', fontSize: '1.25rem', marginBottom: '0.5rem' }}>
          Authentication Required
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
          Redirecting to administrator login...
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
