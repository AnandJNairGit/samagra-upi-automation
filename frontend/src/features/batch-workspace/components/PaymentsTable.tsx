import React from 'react';
import { CreditCard, Search, Loader2, Play, Check, Eye } from 'lucide-react';
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
}) => {
  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div>
      {/* Top Section: Ultra-Compact Batch Overview Summary Strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '10px 20px',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Generated</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.payments_generated}</span>
          <span style={{ fontSize: '0.75rem', color: '#818cf8', background: 'rgba(129, 140, 248, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
            {formatINR(summary.expected_amount_inr)}
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Submitted</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.payments_submitted}</span>
          <span style={{ fontSize: '0.75rem', color: '#fbbf24', background: 'rgba(251, 191, 36, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 500 }}>
            UTR Payer
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Approved</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399', fontFamily: 'var(--font-mono)' }}>{summary.payments_approved}</span>
          <span style={{ fontSize: '0.75rem', color: '#34d399', background: 'rgba(52, 211, 153, 0.12)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
            {formatINR(summary.approved_amount_inr)}
          </span>
        </div>

        <div style={{ width: '1px', height: '20px', background: 'var(--border-color)', opacity: 0.5 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>Statements</span>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>{summary.statement_count}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255, 255, 255, 0.05)', padding: '2px 8px', borderRadius: '12px' }}>
            Files
          </span>
        </div>
      </div>

      {/* Main Section: Batch Payments Table */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ margin: 0 }}>Public Registrations & Payments</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '2px' }}>
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
                style={{ width: '170px' }}
              />
            </div>
            <select
              value={paymentStatusFilter}
              onChange={(e) => setPaymentStatusFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="APPROVED">APPROVED</option>
              <option value="REJECTED">REJECTED</option>
              <option value="EXPIRED">EXPIRED</option>
            </select>
            <button onClick={loadPayments} className="btn btn-outline btn-sm">
              <Search size={14} /> Filter
            </button>

            <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 2px' }} />

            <select
              value={selectedStatementIdForPaymentsMatch}
              onChange={(e) => setSelectedStatementIdForPaymentsMatch(e.target.value)}
              className="filter-select"
              style={{ width: '210px', background: 'var(--bg-secondary)', fontWeight: 600, borderColor: '#818cf8' }}
            >
              <option value="">Select Transaction...</option>
              {imports.map((imp) => (
                <option key={imp.public_id} value={imp.public_id}>
                  {imp.filename} ({imp.valid_rows} txns)
                </option>
              ))}
            </select>

            <button
              disabled={!selectedStatementIdForPaymentsMatch || matchingInPaymentsTable}
              onClick={handleMatchInPaymentsTable}
              className="btn btn-primary btn-sm"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', borderColor: '#10b981', fontWeight: 600 }}
            >
              {matchingInPaymentsTable ? (
                <>
                  <Loader2 size={14} className="spinner" />
                  <span>Matching...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Match</span>
                </>
              )}
            </button>
          </div>
        </div>

        {paymentsLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}><Loader2 size={24} className="spinner" /></div>
        ) : payments.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <CreditCard size={36} color="#6b7280" style={{ margin: '0 auto 8px' }} />
            <p style={{ color: 'var(--text-muted)' }}>No payment sessions generated for this batch yet.</p>
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
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => {
                  const reconRes = reconResultsBySession[p.payment_session_public_id] || reconResultsBySession[p.reference_id];
                  return (
                    <tr key={p.payment_session_public_id}>
                      <td>
                        <div style={{ fontWeight: 600, color: '#f8fafc' }}>{p.participant_name}</div>
                      </td>
                      <td>
                        <div style={{ fontSize: '0.85rem' }}>{p.phone}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.email}</div>
                      </td>
                      <td className="monospace font-semibold" style={{ color: '#38bdf8' }}>{p.reference_id}</td>
                      <td className="monospace">{formatINR(p.amount_inr)}</td>
                      <td className="monospace">{p.utr || '—'}</td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                          {/* Payment Session Status (Admin / Lifecycle State) */}
                          <span
                            className={`status-pill ${
                              p.payment_session_status === 'APPROVED'
                                ? 'active-pill'
                                : p.payment_session_status === 'SUBMITTED'
                                ? 'status-pill-submitted'
                                : p.payment_session_status === 'REJECTED'
                                ? 'archived-pill'
                                : 'pending-pill'
                            }`}
                            style={{ fontSize: '0.72rem', padding: '1px 8px' }}
                          >
                            {p.payment_session_status}
                          </span>

                          {/* Reconciliation Status (Automated Statement Verification) */}
                          {reconRes?.status === 'MATCHED' ? (
                            <span
                              className="status-pill active-pill"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                background: 'rgba(52, 211, 153, 0.15)',
                                color: '#34d399',
                                border: '1px solid rgba(52, 211, 153, 0.4)',
                                fontWeight: 600,
                                fontSize: '0.72rem',
                                padding: '1px 8px',
                              }}
                            >
                              <Check size={12} /> Matched
                            </span>
                          ) : reconRes ? (
                            <span
                              className="status-pill pending-pill"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                fontSize: '0.72rem',
                                padding: '1px 8px',
                              }}
                            >
                              ⚠ {reconRes.status.replace(/_/g, ' ')}
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.72rem', color: '#64748b', fontStyle: 'italic', paddingLeft: '2px' }}>
                              Unreconciled
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="text-sm">{new Date(p.created_at).toLocaleDateString()}</td>
                      <td>
                        <button
                          onClick={() => {
                            if (reconRes) {
                              // Has a reconciliation result — open detailed side-by-side comparison modal
                              onInspectReconResult(reconRes.public_id);
                            } else {
                              // Not reconciled — open payment session drawer
                              onInspectPaymentSession(p.payment_session_public_id);
                            }
                          }}
                          className="btn-action"
                          title={reconRes ? 'Inspect Reconciliation Comparison' : 'Inspect Payment Session'}
                        >
                          <Eye size={14} /> Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
