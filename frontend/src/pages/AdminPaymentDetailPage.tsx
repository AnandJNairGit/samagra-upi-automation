import React, { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { fetchAdminPaymentDetail } from '../services/adminPaymentApi';
import { AdminPaymentDetailResponse } from '../types/adminPayment';
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock,
  CreditCard,
  History,
  Info,
  Loader2,
  ShieldCheck,
  User,
  XCircle,
} from 'lucide-react';

interface AdminPaymentDetailPageProps {
  paymentSessionPublicId: string;
  onNavigate: (path: string) => void;
}

export const AdminPaymentDetailPage: React.FC<AdminPaymentDetailPageProps> = ({
  paymentSessionPublicId,
  onNavigate,
}) => {
  const [detail, setDetail] = useState<AdminPaymentDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadDetail() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchAdminPaymentDetail(paymentSessionPublicId);
        if (isMounted) {
          setDetail(data);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Payment record not found.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (paymentSessionPublicId) {
      loadDetail();
    } else {
      setError('Invalid payment session identifier.');
      setLoading(false);
    }

    return () => {
      isMounted = false;
    };
  }, [paymentSessionPublicId]);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const renderStatusBadge = (st: string) => {
    switch (st.toUpperCase()) {
      case 'PENDING':
        return (
          <span className="status-pill active-pill">
            <Clock size={12} /> Awaiting Payment
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="status-pill status-pill-submitted">
            <CheckCircle2 size={12} /> Submitted
          </span>
        );
      case 'APPROVED':
        return (
          <span className="status-pill" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
            <CheckCircle2 size={12} /> Approved
          </span>
        );
      case 'REJECTED':
        return (
          <span className="status-pill" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            <XCircle size={12} /> Rejected
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="status-pill archived-pill">
            <Clock size={12} /> Expired
          </span>
        );
      default:
        return <span className="status-pill">{st}</span>;
    }
  };

  if (loading) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="payments" onNavigate={onNavigate} />
        <div style={{ textAlign: 'center', padding: '4rem 0' }}>
          <Loader2 size={36} className="spinner" color="#818cf8" />
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.75rem' }}>
            Loading payment inspection details...
          </p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="admin-page-container">
        <AdminNav activeTab="payments" onNavigate={onNavigate} />
        <div className="card unavailable-card" style={{ maxWidth: '600px', margin: '2rem auto', textAlign: 'center' }}>
          <div className="icon-badge-danger">
            <AlertCircle size={32} color="#ef4444" />
          </div>
          <h1 className="unavailable-title">Payment Record Not Found</h1>
          <p className="unavailable-subtitle">{error || 'The requested payment session could not be retrieved.'}</p>
          <button onClick={() => onNavigate('/upi/admin/payments')} className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
            <ArrowLeft size={16} />
            <span>Back to Payments List</span>
          </button>
        </div>
      </div>
    );
  }

  const { participant, training, payment, current_submission, submission_history } = detail;

  return (
    <div className="admin-page-container">
      <AdminNav activeTab="payments" onNavigate={onNavigate} />

      {/* Header & Back Button */}
      <div style={{ marginBottom: '1.5rem' }}>
        <button
          onClick={() => onNavigate('/upi/admin/payments')}
          className="btn btn-outline"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', marginBottom: '1rem' }}
        >
          <ArrowLeft size={16} />
          <span>Back to Payments</span>
        </button>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 className="page-title">{participant.full_name}</h1>
              {renderStatusBadge(payment.status)}
            </div>
            <p className="page-subtitle" style={{ marginTop: '4px' }}>
              Payment Reference: <code className="monospace" style={{ color: '#38bdf8' }}>{payment.reference_id}</code>
            </p>
          </div>

          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border-color)', padding: '10px 16px', borderRadius: '12px', textAlign: 'right' }}>
            <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600, display: 'block' }}>Payment Amount</span>
            <span style={{ fontSize: '1.5rem', fontWeight: 700, color: '#34d399' }}>{formatINR(payment.amount_inr)}</span>
          </div>
        </div>
      </div>

      {/* Grid of Read-Only Inspection Cards */}
      <div className="grid-2" style={{ gap: '20px', marginBottom: '24px' }}>
        {/* Participant Information */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <User size={18} color="#818cf8" />
              Participant Information
            </h2>
          </div>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Full Name</td>
                <td className="meta-val font-semibold">{participant.full_name}</td>
              </tr>
              <tr>
                <td className="meta-key">Phone Number</td>
                <td className="meta-val">{participant.phone}</td>
              </tr>
              <tr>
                <td className="meta-key">Email Address</td>
                <td className="meta-val">{participant.email}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Training Program (Snapshots) */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <BookOpen size={18} color="#38bdf8" />
              Training Program (Historical Snapshots)
            </h2>
          </div>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Course Snapshot</td>
                <td className="meta-val font-semibold">{training.course_name}</td>
              </tr>
              <tr>
                <td className="meta-key">Batch Snapshot</td>
                <td className="meta-val">
                  <span className="course-tag">{training.batch_name}</span>
                </td>
              </tr>
              <tr>
                <td className="meta-key">Course Public UUID</td>
                <td className="meta-val monospace">{training.course_public_id}</td>
              </tr>
              <tr>
                <td className="meta-key">Batch Public UUID</td>
                <td className="meta-val monospace">{training.batch_public_id}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Payment Session Metadata */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <CreditCard size={18} color="#a78bfa" />
              Payment Session Details
            </h2>
          </div>
          <table className="meta-table">
            <tbody>
              <tr>
                <td className="meta-key">Payment Session UUID</td>
                <td className="meta-val monospace">{paymentSessionPublicId}</td>
              </tr>
              <tr>
                <td className="meta-key">Reference ID</td>
                <td className="meta-val monospace font-bold" style={{ color: '#38bdf8' }}>{payment.reference_id}</td>
              </tr>
              <tr>
                <td className="meta-key">Payee Name Snapshot</td>
                <td className="meta-val">{payment.payee_name_snapshot}</td>
              </tr>
              <tr>
                <td className="meta-key">Payee UPI ID Snapshot</td>
                <td className="meta-val monospace">{payment.upi_id_snapshot}</td>
              </tr>
              <tr>
                <td className="meta-key">Created Timestamp</td>
                <td className="meta-val">
                  {new Date(payment.created_at).toLocaleString('en-IN', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </td>
              </tr>
              {payment.expires_at && (
                <tr>
                  <td className="meta-key">Expiration Window</td>
                  <td className="meta-val">
                    {new Date(payment.expires_at).toLocaleString('en-IN', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Current UTR Submission */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <ShieldCheck size={18} color="#10b981" />
              Current UTR Submission Claim
            </h2>
          </div>

          {current_submission ? (
            <table className="meta-table">
              <tbody>
                <tr>
                  <td className="meta-key">Submission UUID</td>
                  <td className="meta-val monospace">{current_submission.public_id}</td>
                </tr>
                <tr>
                  <td className="meta-key">Transaction Reference (UTR)</td>
                  <td className="meta-val monospace font-bold" style={{ color: '#34d399', fontSize: '1.05rem' }}>
                    {current_submission.utr}
                  </td>
                </tr>
                <tr>
                  <td className="meta-key">Submission Status</td>
                  <td className="meta-val">{renderStatusBadge(current_submission.status)}</td>
                </tr>
                <tr>
                  <td className="meta-key">Submission Timestamp</td>
                  <td className="meta-val">
                    {new Date(current_submission.submitted_at).toLocaleString('en-IN', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </td>
                </tr>
                {current_submission.reviewed_at && (
                  <tr>
                    <td className="meta-key">Review Timestamp</td>
                    <td className="meta-val">
                      {new Date(current_submission.reviewed_at).toLocaleString('en-IN', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </td>
                  </tr>
                )}
                {current_submission.rejection_reason && (
                  <tr>
                    <td className="meta-key">Rejection Reason</td>
                    <td className="meta-val" style={{ color: '#f87171' }}>
                      {current_submission.rejection_reason}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: '2rem 1rem', textAlign: 'center' }}>
              <Clock size={28} color="#94a3b8" style={{ margin: '0 auto 8px' }} />
              <p style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                No UTR submission has been recorded for this session yet.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Submission History Table (If resubmissions exist) */}
      {submission_history && submission_history.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History size={18} color="#818cf8" />
            <h2 className="card-title">Submission History & Resubmission Log</h2>
          </div>

          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Submission UUID</th>
                  <th>UTR Reference</th>
                  <th>Claim Status</th>
                  <th>Active Current?</th>
                  <th>Submitted At</th>
                  <th>Reviewed At</th>
                  <th>Rejection Reason</th>
                </tr>
              </thead>
              <tbody>
                {submission_history.map((sub) => (
                  <tr key={sub.public_id} style={{ opacity: sub.is_current ? 1 : 0.65 }}>
                    <td className="monospace">{sub.public_id}</td>
                    <td className="monospace font-bold" style={{ color: sub.is_current ? '#34d399' : '#cbd5e1' }}>
                      {sub.utr}
                    </td>
                    <td>{renderStatusBadge(sub.status)}</td>
                    <td>
                      {sub.is_current ? (
                        <span className="status-pill active-pill" style={{ fontSize: '0.72rem' }}>
                          Current
                        </span>
                      ) : (
                        <span className="status-pill archived-pill" style={{ fontSize: '0.72rem' }}>
                          Historical
                        </span>
                      )}
                    </td>
                    <td>
                      {new Date(sub.submitted_at).toLocaleString('en-IN', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </td>
                    <td>
                      {sub.reviewed_at
                        ? new Date(sub.reviewed_at).toLocaleString('en-IN', {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })
                        : '—'}
                    </td>
                    <td>{sub.rejection_reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Strict Phase Boundary Banner */}
      <div className="verification-notice-box" style={{ background: 'rgba(99, 102, 241, 0.08)', borderColor: 'rgba(99, 102, 241, 0.25)', color: '#c7d2fe' }}>
        <Info size={18} color="#818cf8" />
        <div>
          <strong>Read-Only Inspection Mode (Phase 8):</strong> Approval and rejection workflows belong strictly to Phase 11. Payment statuses cannot be edited from the Phase 8 dashboard.
        </div>
      </div>
    </div>
  );
};
