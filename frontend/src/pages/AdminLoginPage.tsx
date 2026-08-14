/**
 * Administrator Login Page
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, AlertCircle, Loader2, KeyRound } from 'lucide-react';

interface AdminLoginPageProps {
  onNavigate: (path: string) => void;
}

export const AdminLoginPage: React.FC<AdminLoginPageProps> = ({ onNavigate }) => {
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // If already authenticated, redirect to admin dashboard
  useEffect(() => {
    if (isAuthenticated) {
      onNavigate('/upi/admin');
    }
  }, [isAuthenticated, onNavigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setError('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(cleanEmail, password);
      onNavigate('/upi/admin');
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-card">
        <div className="login-header">
          <div className="login-icon">
            <KeyRound size={28} color="#818cf8" />
          </div>
          <h2 className="login-title">Administrator Sign In</h2>
          <p className="login-subtitle">
            Enter your credentials to access the Samagra UPI administration console.
          </p>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <AlertCircle size={18} color="#ef4444" style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="admin-email" className="form-label">
              Admin Email
            </label>
            <div className="input-group">
              <Mail size={18} className="input-icon" />
              <input
                id="admin-email"
                type="email"
                required
                autoComplete="email"
                autoFocus
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="admin-password" className="form-label">
              Password
            </label>
            <div className="input-group">
              <Lock size={18} className="input-icon" />
              <input
                id="admin-password"
                type="password"
                required
                autoComplete="current-password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                className="form-input"
              />
            </div>
          </div>

          <button
            id="admin-login-submit"
            type="submit"
            disabled={isSubmitting}
            className="submit-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spinner" />
                <span>Authenticating...</span>
              </>
            ) : (
              'Sign In to Admin Console'
            )}
          </button>
        </form>

        <div className="login-footer">
          <button
            type="button"
            onClick={() => onNavigate('/upi/')}
            className="back-link"
          >
            &larr; Return to Public Portal
          </button>
        </div>
      </div>
    </div>
  );
};
