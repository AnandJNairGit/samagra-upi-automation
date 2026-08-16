import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { useAuth } from '../context/AuthContext';
import { getAdminHealthApi } from '../services/apiClient';
import { AdminHealthResponse } from '../types/auth';
import {
  ShieldCheck,
  UserCheck,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  BookOpen,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface AdminDashboardPageProps {
  onNavigate: (path: string) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({ onNavigate }) => {
  const { admin } = useAuth();
  const [healthData, setHealthData] = useState<AdminHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await getAdminHealthApi();
      setHealthData(data);
    } catch (err: any) {
      setHealthError(err.message || 'Authorization check failed');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="dashboard" onNavigate={onNavigate} />

      <header className="page-header">
        <div>
          <div className="badge success-badge">
            <ShieldCheck size={14} />
            Phase 4 — Admin Console
          </div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">
            Manage course offerings, cohorts, and administrator controls.
          </p>
        </div>
      </header>

      {/* Module Navigation Shortcuts */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        <div
          className="card shortcut-card"
          onClick={() => onNavigate('/upi/admin/courses')}
          style={{ cursor: 'pointer' }}
        >
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="shortcut-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                <BookOpen size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Courses</h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Create and manage training programs & curricula
                </p>
              </div>
            </div>
            <ArrowRight size={18} color="#818cf8" />
          </div>
        </div>

        <div
          className="card shortcut-card"
          onClick={() => onNavigate('/upi/admin/batches')}
          style={{ cursor: 'pointer' }}
        >
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="shortcut-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                <Layers size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Batches & Cohorts</h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Configure cohorts, whole-rupee amounts & schedules
                </p>
              </div>
            </div>
            <ArrowRight size={18} color="#38bdf8" />
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Administrator Profile Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <UserCheck size={20} color="#818cf8" />
              Active Administrator Profile
            </h2>
          </div>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Full Name</td>
                <td className="meta-val font-semibold">{admin?.full_name || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Email Address</td>
                <td className="meta-val">{admin?.email || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Account Status</td>
                <td className="meta-val">
                  <span className="status-pill active-pill">
                    <CheckCircle2 size={12} /> Active
                  </span>
                </td>
              </tr>
              <tr>
                <td className="meta-key">Public UUID</td>
                <td className="meta-val monospace">{admin?.public_id || '—'}</td>
              </tr>
              <tr>
                <td className="meta-key">Token Storage</td>
                <td className="meta-val">
                  <span className="secure-tag">React Memory (Zero localStorage)</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Authorization Middleware Live Check */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 className="card-title">
              <Radio size={20} color="#38bdf8" />
              Protected API Authorization
            </h2>
            <button
              onClick={fetchHealth}
              disabled={healthLoading}
              className="icon-btn"
              title="Re-verify Authorization"
            >
              <RefreshCw size={14} className={healthLoading ? 'spinner' : ''} />
            </button>
          </div>

          <p style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '1rem' }}>
            Validates live authorization middleware on <code>/v1/admin/health</code> using your in-memory Bearer token.
          </p>

          {healthLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem 0' }}>
              <Loader2 size={24} className="spinner" color="#38bdf8" />
              <p style={{ color: '#94a3b8', fontSize: '0.8125rem', marginTop: '0.5rem' }}>Testing endpoint authorization...</p>
            </div>
          ) : healthError ? (
            <div className="error-banner">
              <AlertTriangle size={16} color="#ef4444" />
              <span>Authorization Failed: {healthError}</span>
            </div>
          ) : (
            <div className="verification-box">
              <div className="verification-item">
                <span className="verify-label">Endpoint Status:</span>
                <span className="verify-value success">{healthData?.status.toUpperCase()}</span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Authorization Guard:</span>
                <span className="verify-value success">
                  <CheckCircle2 size={14} /> Passed (require_admin)
                </span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Verified Email:</span>
                <span className="verify-value">{healthData?.admin_email}</span>
              </div>
              <div className="verification-item">
                <span className="verify-label">Verified Public ID:</span>
                <span className="verify-value monospace">{healthData?.admin_public_id}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
