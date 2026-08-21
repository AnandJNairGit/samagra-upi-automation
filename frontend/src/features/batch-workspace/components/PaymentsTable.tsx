import React, { useState } from 'react';
import {
  CreditCard,
  Loader2,
  Play,
  Check,
  Eye,
  CheckCircle,
  AlertTriangle,
  X,
} from 'lucide-react';
import { BatchSummary } from '../../../types/batch';
import { AdminPaymentListItem } from '../../../types/adminPayment';
import { StatementImportListItem } from '../../../types/statementImport';
import { ReconciliationResultResponse } from '../../../types/reconciliation';

interface PaymentsTableProps {
  summary: BatchSummary;
  payments: AdminPaymentListItem[];
  paymentsLoading: boolean;
  paymentSearch: string;
  setPaymentSearch: (val: string) => void;
  paymentStatusFilter: string;
  setPaymentStatusFilter: (val: string) => void;
  selectedStatementIdForPaymentsMatch: string;
  setSelectedStatementIdForPaymentsMatch: (val: string) => void;
  matchingInPaymentsTable: boolean;
  loadPayments: () => void;
  handleMatchInPaymentsTable: () => void;
  
  imports: StatementImportListItem[];
  reconResultsBySession: Record<string, ReconciliationResultResponse>;
  onInspectReconResult: (resultPublicId: string) => void;
  onInspectPaymentSession: (sessionPublicId: string) => void;
  onApprovePayment: (sessionPublicId: string) => Promise<void>;
}

export const PaymentsTable: React.FC<PaymentsTableProps> = ({
  summary,
  payments,
  paymentsLoading,
  paymentSearch,
  setPaymentSearch,
  paymentStatusFilter,
  setPaymentStatusFilter,
  selectedStatementIdForPaymentsMatch,
  setSelectedStatementIdForPaymentsMatch,
  matchingInPaymentsTable,
  loadPayments,
  handleMatchInPaymentsTable,
  imports,
  reconResultsBySession,
  onInspectReconResult,
  onInspectPaymentSession,
  onApprovePayment,
}) => {
  const [approvingSessionId, setApprovingSessionId] = useState<string | null>(null);
  const [approveConfirm, setApproveConfirm] = useState<{ sessionId: string; name: string } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleApproveClick = (sessionPublicId: string, participantName: string) => {
    setActionError(null);
    setApproveConfirm({ sessionId: sessionPublicId, name: participantName });
  };

  const executeApprove = async () => {
    if (!approveConfirm) return;
    const { sessionId } = approveConfirm;
    setApproveConfirm(null);
    setApprovingSessionId(sessionId);
    setActionError(null);
    try {
      await onApprovePayment(sessionId);
    } catch (err: any) {
      setActionError(err.message || 'Approval failed. Please try again.');
    } finally {
      setApprovingSessionId(null);
    }
  };

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div>
      {/* Top Section: Batch Overview Summary Strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 20px',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Generated</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{summary.payments_generated}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-light)', background: 'var(--accent-bg)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
            {formatINR(summary.expected_amount_inr)}
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Submitted</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{summary.payments_submitted}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--warning)', background: 'var(--warning-bg)', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
            UTR Claims
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Approved</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--success)', fontFamily: 'var(--font-mono)' }}>{summary.payments_approved}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--success)', background: 'var(--success-bg)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
            {formatINR(summary.approved_amount_inr)}
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Statements</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{summary.statement_count}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-secondary)', padding: '2px 8px', borderRadius: '12px' }}>
            Files
          </span>
        </div>
      </div>

      {/* Action Error Banner */}
      {actionError && (
        <div className="error-banner" style={{ marginBottom: '16px' }}>
          <AlertTriangle size={16} />
          <span>{actionError}</span>
          <button
            onClick={() => setActionError(null)}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Section: Batch Payments Table */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Public Registrations & Payments
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Payment sessions generated for candidates registering through the public batch link.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="filter-group">
              <input
                type="text"
                placeholder="Search Ref, Name, UTR..."
                value={paymentSearch}
                onChange={(e) => setPaymentSearch(e.target.value)}
                className="form-input"
                style={{ width: '180px' }}
              />
            </div>
            <select
              value={paymentStatusFilter}
              onChange={(e) => setPaymentStatusFilter(e.target.value)}
              className="filter-select"
              style={{ width: '140px' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
            <button onClick={loadPayments} className="btn btn-outline btn-sm">
              Refresh
            </button>

            {/* In-table Statement Match Selector + Button */}
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', borderLeft: '1px solid var(--border-color)', paddingLeft: '10px' }}>
              <select
                value={selectedStatementIdForPaymentsMatch}
                onChange={(e) => setSelectedStatementIdForPaymentsMatch(e.target.value)}
                className="filter-select"
                style={{ width: '180px' }}
                disabled={imports.length === 0 || matchingInPaymentsTable}
              >
                {imports.length === 0 ? (
                  <option value="">No statements imported</option>
                ) : (
                  <>
                    <option value="">Select statement...</option>
                    {imports.map((imp) => (
                      <option key={imp.public_id} value={imp.public_id}>
                        {imp.filename} ({imp.new_transactions} txns)
                      </option>
                    ))}
                  </>
                )}
              </select>
              <button
                onClick={handleMatchInPaymentsTable}
                disabled={!selectedStatementIdForPaymentsMatch || matchingInPaymentsTable}
                className="btn btn-primary btn-sm"
                title="Run reconciliation against selected statement"
              >
                {matchingInPaymentsTable ? (
                  <>
                    <Loader2 size={13} className="spinner" />
                    <span>Matching...</span>
                  </>
                ) : (
                  <>
                    <Play size={13} />
                    <span>Match</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {paymentsLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton skeleton-table-row" />
            ))}
          </div>
        ) : payments.length === 0 ? (
          <div style={{ padding: '2.5rem', textAlign: 'center' }}>
            <CreditCard size={36} color="var(--text-muted)" style={{ margin: '0 auto 8px' }} />
            <p style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>No payment sessions generated for this batch yet.</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Share the public registration link with participants to begin collecting payments.
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Participant Name</th>
                  <th>Contact Info</th>
                  <th>Reference ID</th>
                  <th>Fee Amount</th>
                  <th>Submitted UTR</th>
                  <th>Status & Reconciliation</th>
                  <th>Registration Date</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => {
                  const reconRes = reconResultsBySession[p.payment_session_public_id] || reconResultsBySession[p.reference_id];
                  return (
                    <tr key={p.payment_session_public_id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.participant_name}</div>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{p.phone}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.email}</div>
                      </td>
                      <td className="monospace font-semibold" style={{ color: 'var(--info)' }}>{p.reference_id}</td>
                      <td className="monospace">{formatINR(p.amount_inr)}</td>
                      <td className="monospace">{p.utr || '—'}</td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                          {/* Payment Session Status */}
                          <span
                            className={`status-badge ${
                              p.payment_session_status === 'APPROVED'
                                ? 'status-badge-approved'
                                : p.payment_session_status === 'SUBMITTED'
                                ? 'status-badge-submitted'
                                : p.payment_session_status === 'REJECTED'
                                ? 'status-badge-rejected'
                                : 'status-badge-pending'
                            }`}
                          >
                            {p.payment_session_status}
                          </span>

                          {/* Reconciliation Status */}
                          {reconRes?.status === 'MATCHED' ? (
                            <span
                              className="status-badge status-badge-approved"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                            >
                              <Check size={11} /> Matched
                            </span>
                          ) : reconRes ? (
                            <span
                              className="status-badge status-badge-pending"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                            >
                              ⚠ {reconRes.status.replace(/_/g, ' ')}
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic', paddingLeft: '2px' }}>
                              Unreconciled
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                        {new Date(p.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                          <button
                            onClick={() => {
                              if (reconRes) {
                                onInspectReconResult(reconRes.public_id);
                              } else {
                                onInspectPaymentSession(p.payment_session_public_id);
                              }
                            }}
                            className="btn-action"
                            title={reconRes ? 'Inspect Reconciliation Comparison' : 'Inspect Payment Session'}
                          >
                            <Eye size={13} /> Inspect
                          </button>

                          {p.payment_session_status !== 'APPROVED' && (
                            <button
                              onClick={() => handleApproveClick(p.payment_session_public_id, p.participant_name)}
                              disabled={approvingSessionId === p.payment_session_public_id}
                              className="btn-action"
                              style={{
                                color: 'var(--success)',
                                borderColor: 'var(--success-border)',
                                background: 'var(--success-bg)',
                              }}
                              title="Approve Payment Session"
                            >
                              {approvingSessionId === p.payment_session_public_id ? (
                                <Loader2 size={13} className="spinner" />
                              ) : (
                                <CheckCircle size={13} />
                              )}
                              {approvingSessionId === p.payment_session_public_id ? 'Approving...' : 'Approve'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Approve Confirmation Modal (Replaces window.confirm) */}
      {approveConfirm && (
        <div className="confirm-modal-overlay" onClick={() => setApproveConfirm(null)}>
          <div className="confirm-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="confirm-modal-icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
              <CheckCircle size={24} />
            </div>
            <h3 className="confirm-modal-title">Confirm Manual Approval</h3>
            <p className="confirm-modal-body">
              Are you sure you want to approve the payment for <strong>{approveConfirm.name}</strong>?
              This will transition the participant's payment status to <strong>APPROVED</strong>.
            </p>
            <div className="confirm-modal-actions">
              <button className="btn btn-outline" onClick={() => setApproveConfirm(null)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={executeApprove}>
                Confirm Approval
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
