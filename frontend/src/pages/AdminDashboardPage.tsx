import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { useAuth } from '../context/AuthContext';
import { getAdminHealthApi } from '../services/apiClient';
import { fetchAdminDashboardSummary } from '../services/adminPaymentApi';
import { AdminHealthResponse } from '../types/auth';
import { AdminDashboardSummary } from '../types/adminPayment';
import {
  ShieldCheck,
  UserCheck,
  Radio,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  CreditCard,
  CheckSquare,
  Clock,
  XCircle,
  IndianRupee,
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

  // Summary Metrics State (Phase 8)
  const [summary, setSummary] = useState<AdminDashboardSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

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

  const loadSummaryMetrics = async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await fetchAdminDashboardSummary();
      setSummary(data);
    } catch (err: any) {
      setSummaryError(err.message || 'Unable to load payment summary metrics');
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    loadSummaryMetrics();
  }, []);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="dashboard" onNavigate={onNavigate} />

      <header className="page-header">
        <div>
          <div className="badge success-badge">
            <ShieldCheck size={14} />
            Phase 8 — Admin Payment Dashboard
          </div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">
            Read-only payment summary metrics, course offerings, and operational controls.
          </p>
        </div>
      </header>

      {/* Summary Metrics Grid (Phase 8) */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#f8fafc' }}>Payment Summary Metrics</h2>
          <button
            onClick={loadSummaryMetrics}
            disabled={summaryLoading}
            className="icon-btn"
            title="Refresh Summary Metrics"
          >
            <RefreshCw size={14} className={summaryLoading ? 'spinner' : ''} />
          </button>
        </div>

        {summaryError ? (
          <div className="error-banner">
            <AlertTriangle size={16} color="#ef4444" />
            <span>{summaryError}</span>
          </div>
        ) : summaryLoading ? (
          <div className="grid-3" style={{ opacity: 0.7 }}>
            {[1, 2, 3, 4, 5, 6].map((idx) => (
              <div key={idx} className="card" style={{ textAlign: 'center', padding: '24px' }}>
                <Loader2 size={24} className="spinner" color="#818cf8" style={{ margin: '0 auto 8px' }} />
                <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Calculating metric...</span>
              </div>
            ))}
          </div>
        ) : summary ? (
          <div className="grid-3">
            {/* Total Registrations */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Total Registrations</span>
                  <div className="metric-value">{summary.total_registrations}</div>
                  <span className="metric-sub text-muted">All payment sessions</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                  <CreditCard size={22} />
                </div>
              </div>
            </div>

            {/* Pending Payments */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments?status=PENDING')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Pending Payments</span>
                  <div className="metric-value" style={{ color: '#fbbf24' }}>{summary.pending_payments}</div>
                  <span className="metric-sub text-muted">Awaiting participant payment</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
                  <Clock size={22} />
                </div>
              </div>
            </div>

            {/* Submitted Payments */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments/submitted')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Submitted Payments</span>
                  <div className="metric-value" style={{ color: '#10b981' }}>{summary.submitted_payments}</div>
                  <span className="metric-sub text-muted">UTR submitted, pending review</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
                  <CheckSquare size={22} />
                </div>
              </div>
            </div>

            {/* Approved Payments */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments?status=APPROVED')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Approved Payments</span>
                  <div className="metric-value" style={{ color: '#34d399' }}>{summary.approved_payments}</div>
                  <span className="metric-sub text-muted">Verified & enrolled</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(52, 211, 153, 0.15)', color: '#34d399' }}>
                  <CheckCircle2 size={22} />
                </div>
              </div>
            </div>

            {/* Rejected Payments */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments?status=REJECTED')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Rejected Payments</span>
                  <div className="metric-value" style={{ color: '#f87171' }}>{summary.rejected_payments}</div>
                  <span className="metric-sub text-muted">Rejected claims</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
                  <XCircle size={22} />
                </div>
              </div>
            </div>

            {/* Total Revenue Collected */}
            <div
              className="card metric-card-interactive"
              onClick={() => onNavigate('/upi/admin/payments?status=APPROVED')}
              style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="metric-label">Total Revenue Collected</span>
                  <div className="metric-value" style={{ color: '#a78bfa' }}>{formatINR(summary.total_amount_collected_inr)}</div>
                  <span className="metric-sub text-muted">Approved sessions only</span>
                </div>
                <div className="shortcut-icon" style={{ background: 'rgba(167, 139, 250, 0.15)', color: '#a78bfa' }}>
                  <IndianRupee size={22} />
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Module Navigation Shortcuts */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        <div
          className="card shortcut-card"
          onClick={() => onNavigate('/upi/admin/payments')}
          style={{ cursor: 'pointer' }}
        >
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="shortcut-icon" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
                <CreditCard size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Payment Sessions</h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Inspect all payment registrations, reference IDs, and UTRs
                </p>
              </div>
            </div>
            <ArrowRight size={18} color="#818cf8" />
          </div>
        </div>

        <div
          className="card shortcut-card"
          onClick={() => onNavigate('/upi/admin/payments/submitted')}
          style={{ cursor: 'pointer' }}
        >
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="shortcut-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
                <CheckSquare size={22} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Submitted Payments</h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  View participant UTR claims awaiting verification
                </p>
              </div>
            </div>
            <ArrowRight size={18} color="#10b981" />
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
