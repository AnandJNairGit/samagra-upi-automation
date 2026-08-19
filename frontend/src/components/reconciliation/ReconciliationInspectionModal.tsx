import React, { useEffect, useState } from 'react';
import { reconciliationApi } from '../../services/reconciliationApi';
import { ReconciliationResultDetailResponse, ReconciliationStatus } from '../../types/reconciliation';
import {
  X,
  Loader2,
  AlertCircle,
  Check,
  Minus,
  FileSpreadsheet,
  Layers,
  CreditCard,
  Send,
  Code,
  AlertTriangle,
} from 'lucide-react';

interface ReconciliationInspectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  resultPublicId?: string | null;
  paymentSessionPublicId?: string | null;
  initialDetail?: ReconciliationResultDetailResponse | null;
}

export const ReconciliationInspectionModal: React.FC<ReconciliationInspectionModalProps> = ({
  isOpen,
  onClose,
  resultPublicId,
  paymentSessionPublicId,
  initialDetail = null,
}) => {
  const [detail, setDetail] = useState<ReconciliationResultDetailResponse | null>(initialDetail);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch detail when modal opens with a resultPublicId or paymentSessionPublicId
  useEffect(() => {
    if (!isOpen) {
      setDetail(null);
      setError(null);
      return;
    }

    if (initialDetail) {
      setDetail(initialDetail);
      setLoading(false);
      setError(null);
      return;
    }

    if (resultPublicId) {
      setLoading(true);
      setError(null);
      reconciliationApi
        .getReconciliationResultDetail(resultPublicId)
        .then((res) => {
          setDetail(res);
        })
        .catch((err: any) => {
          setError(err.message || 'Unable to load reconciliation details. Please try again.');
        })
        .finally(() => {
          setLoading(false);
        });
    } else if (paymentSessionPublicId) {
      setLoading(true);
      setError(null);
      reconciliationApi
        .getReconciliationResultBySession(paymentSessionPublicId)
        .then((res) => {
          setDetail(res);
        })
        .catch((err: any) => {
          setError(err.message || 'Unable to load reconciliation details for session. Please try again.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, resultPublicId, paymentSessionPublicId, initialDetail]);

  // Keyboard Escape listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const formatINR = (amount?: number | null): string => {
    if (amount === undefined || amount === null) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const renderStatusBadge = (status: ReconciliationStatus | string) => {
    switch (status) {
      case 'MATCHED':
        return (
          <span
            className="status-pill active-pill"
            style={{
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            <Check size={14} /> MATCHED ✓
          </span>
        );
      case 'AMOUNT_MISMATCH':
        return (
          <span
            className="status-pill archived-pill"
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              color: '#f87171',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            <AlertTriangle size={14} /> AMOUNT MISMATCH
          </span>
        );
      case 'UTR_MISMATCH':
        return (
          <span
            className="status-pill pending-pill"
            style={{
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#fbbf24',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            <AlertTriangle size={14} /> UTR MISMATCH
          </span>
        );
      case 'UNKNOWN_REFERENCE':
        return (
          <span
            className="status-pill"
            style={{
              background: 'rgba(96, 165, 250, 0.15)',
              color: '#60a5fa',
              border: '1px solid rgba(96, 165, 250, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            UNKNOWN REFERENCE
          </span>
        );
      case 'NO_REFERENCE':
        return (
          <span
            className="status-pill"
            style={{
              background: 'rgba(148, 163, 184, 0.15)',
              color: '#94a3b8',
              border: '1px solid rgba(148, 163, 184, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            NO REFERENCE
          </span>
        );
      case 'DUPLICATE_TRANSACTION':
        return (
          <span
            className="status-pill"
            style={{
              background: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            DUPLICATE TRANSACTION
          </span>
        );
      case 'UNMATCHED':
        return (
          <span
            className="status-pill archived-pill"
            style={{
              background: 'rgba(100, 116, 139, 0.15)',
              color: '#94a3b8',
              border: '1px solid rgba(100, 116, 139, 0.4)',
              fontWeight: 600,
              fontSize: '0.85rem',
            }}
          >
            NON-CREDIT / DEBIT
          </span>
        );
      default:
        return <span className="status-pill">{status}</span>;
    }
  };

  // 3-State Match Evaluation Indicator
  const renderEvaluationIndicator = (val?: boolean | null, label?: string) => {
    if (val === true) {
      return (
        <span
          style={{
            color: '#34d399',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(16, 185, 129, 0.12)',
            padding: '2px 8px',
            borderRadius: '4px',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            fontSize: '0.8rem',
          }}
        >
          <Check size={14} /> MATCH
        </span>
      );
    }
    if (val === false) {
      return (
        <span
          style={{
            color: '#f87171',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'rgba(239, 68, 68, 0.12)',
            padding: '2px 8px',
            borderRadius: '4px',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            fontSize: '0.8rem',
          }}
        >
          <X size={14} /> MISMATCH
        </span>
      );
    }
    return (
      <span
        style={{
          color: '#94a3b8',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(148, 163, 184, 0.1)',
          padding: '2px 8px',
          borderRadius: '4px',
          border: '1px solid rgba(148, 163, 184, 0.2)',
          fontSize: '0.78rem',
        }}
      >
        <Minus size={14} /> {label || 'NOT AVAILABLE'}
      </span>
    );
  };

  const formatCellValue = (val: unknown): string => {
    if (val === null || val === undefined || val === '') return '—';
    if (typeof val === 'boolean') return val ? 'true' : 'false';
    if (typeof val === 'object') return JSON.stringify(val);
    return String(val);
  };

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="recon-modal-title"
    >
      <div
        className="modal-card"
        style={{
          maxWidth: '840px',
          width: '95%',
          maxHeight: '92vh',
          overflowY: 'auto',
          background: '#0f172a',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.9)',
          padding: '24px 28px',
        }}
      >
        {/* Modal Header */}
        <div className="modal-header" style={{ marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={20} color="#818cf8" />
              <h3 id="recon-modal-title" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                Reconciliation Inspection Evidence
              </h3>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Side-by-side audit comparison between raw bank statement, normalized transaction, and application payment.
            </p>
          </div>
          <button
            onClick={onClose}
            className="icon-btn"
            aria-label="Close modal"
            style={{
              padding: '6px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              background: 'rgba(255, 255, 255, 0.05)',
              cursor: 'pointer',
            }}
          >
            <X size={18} color="#94a3b8" />
          </button>
        </div>

        {/* Body Content */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '4rem 0' }}>
            <Loader2 size={36} className="spinner" color="#818cf8" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Loading reconciliation audit evidence...</p>
          </div>
        ) : error ? (
          <div style={{ padding: '2rem 1rem', textAlign: 'center' }}>
            <div className="error-banner" style={{ marginBottom: '16px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={18} color="#ef4444" />
              <span>{error}</span>
            </div>
            <div>
              <button onClick={onClose} className="btn btn-outline btn-sm">
                Close
              </button>
            </div>
          </div>
        ) : detail ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* 1. Verdict & Reason Header Banner */}
            <div
              style={{
                background:
                  detail.status === 'MATCHED'
                    ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(5, 150, 105, 0.05))'
                    : 'linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(185, 28, 28, 0.05))',
                border: detail.status === 'MATCHED' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '12px',
                padding: '16px 20px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {renderStatusBadge(detail.status)}
                  <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8', fontSize: '0.9rem' }}>
                    {detail.bank_reference_id || detail.expected_reference_id || 'NO REF'}
                  </span>
                </div>
                <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Reason Code: <span style={{ fontFamily: 'monospace', color: '#e2e8f0', fontWeight: 600 }}>{detail.reason_code}</span>
                </div>
              </div>
              <p style={{ fontSize: '0.875rem', color: '#e2e8f0', margin: 0, lineHeight: 1.5 }}>
                {detail.explanation}
              </p>
            </div>

            {/* 2. 3-State Evaluation Matrix */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                padding: '14px 18px',
              }}
            >
              <h4 style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: 700 }}>
                Reconciliation Evaluation Matrix
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
                <div>
                  <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Reference Code Match</span>
                  {renderEvaluationIndicator(detail.reference_match, 'Not Evaluated')}
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Amount Match</span>
                  {renderEvaluationIndicator(detail.amount_match, 'Not Evaluated')}
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Bank UTR Match</span>
                  {renderEvaluationIndicator(detail.utr_match, 'Optional / Not Provided')}
                </div>
                <div>
                  <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>Payer Name Match</span>
                  {renderEvaluationIndicator(detail.payer_match, 'Not Evaluated')}
                </div>
              </div>
            </div>

            {/* 3. Side-by-Side Comparison: Bank Transaction vs Application Payment */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              {/* Left Column: Bank Transaction Data */}
              <div
                className="summary-section"
                style={{
                  padding: '16px',
                  background: 'rgba(17, 24, 39, 0.7)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  borderRadius: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                  <FileSpreadsheet size={16} color="#38bdf8" />
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                    Bank Statement Transaction
                  </h4>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Statement File:</span>
                    <span style={{ fontWeight: 600, color: '#f8fafc', wordBreak: 'break-all', textAlign: 'right' }}>{detail.statement_filename}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Bank Reference ID:</span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' }}>{detail.bank_reference_id || '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Credit Amount:</span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#34d399', fontSize: '0.95rem' }}>
                      {formatINR(detail.bank_amount_inr)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Direction:</span>
                    <span className={`status-pill ${detail.bank_direction === 'CREDIT' ? 'active-pill' : 'inactive-pill'}`} style={{ padding: '2px 8px', fontSize: '0.72rem' }}>
                      {detail.bank_direction || 'CREDIT'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Bank UTR:</span>
                    <span style={{ fontFamily: 'monospace', color: '#e2e8f0' }}>{detail.bank_utr || '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Payer Name:</span>
                    <span style={{ color: '#e2e8f0' }}>{detail.bank_counterparty_name || '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#94a3b8' }}>Transaction Date:</span>
                    <span style={{ color: '#94a3b8' }}>{detail.bank_transaction_at ? new Date(detail.bank_transaction_at).toLocaleString() : '—'}</span>
                  </div>
                  {detail.bank_description && (
                    <div style={{ marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                      <span style={{ display: 'block', fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase' }}>Description / Remarks:</span>
                      <span style={{ fontSize: '0.8rem', color: '#cbd5e1', wordBreak: 'break-word', fontFamily: 'monospace' }}>
                        {detail.bank_description}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Application Payment Session Data */}
              <div
                className="summary-section"
                style={{
                  padding: '16px',
                  background: 'rgba(17, 24, 39, 0.7)',
                  border: '1px solid rgba(129, 140, 248, 0.25)',
                  borderRadius: '10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                  <CreditCard size={16} color="#818cf8" />
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                    Application Payment Session
                  </h4>
                </div>

                {detail.expected_reference_id || detail.participant_name ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Participant:</span>
                      <span style={{ fontWeight: 600, color: '#f8fafc' }}>{detail.participant_name || '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Course:</span>
                      <span style={{ color: '#e2e8f0', textAlign: 'right' }}>{detail.course_name_snapshot || '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Batch:</span>
                      <span style={{ color: '#e2e8f0', textAlign: 'right' }}>{detail.batch_name_snapshot || '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Expected Ref ID:</span>
                      <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' }}>{detail.expected_reference_id || '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Expected Amount:</span>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#f8fafc', fontSize: '0.95rem' }}>
                        {formatINR(detail.expected_amount_inr)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Payment Status:</span>
                      <span className={`status-pill ${detail.payment_session_status === 'APPROVED' ? 'active-pill' : 'inactive-pill'}`} style={{ padding: '2px 8px', fontSize: '0.72rem' }}>
                        {detail.payment_session_status || '—'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Submitted UTR:</span>
                      <span style={{ fontFamily: 'monospace', color: '#e2e8f0' }}>{detail.submitted_utr || 'Not Provided (Optional)'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Submission Status:</span>
                      <span style={{ color: '#e2e8f0' }}>{detail.submission_status || '—'}</span>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#64748b' }}>
                    <AlertCircle size={28} color="#64748b" style={{ margin: '0 auto 8px' }} />
                    <p style={{ fontSize: '0.85rem', fontStyle: 'italic' }}>
                      No matching PaymentSession record found for this batch.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* 4. Exact Original Imported Row Table (raw_row_data) */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                padding: '16px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <FileSpreadsheet size={16} color="#34d399" /> Original Spreadsheet Row (`raw_row_data`)
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Exact column headers and cell values as imported from the original spreadsheet (verbatim without normalization).
                  </span>
                </div>
              </div>

              {detail.raw_row_data && Object.keys(detail.raw_row_data).length > 0 ? (
                <div className="table-responsive" style={{ maxHeight: '240px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                  <table className="admin-table" style={{ margin: 0, fontSize: '0.825rem' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '35%', background: 'rgba(0,0,0,0.3)', color: '#94a3b8' }}>Column Header</th>
                        <th style={{ width: '65%', background: 'rgba(0,0,0,0.3)', color: '#94a3b8' }}>Original Excel/CSV Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(detail.raw_row_data).map(([key, value], idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600, color: '#a5b4fc', fontFamily: 'monospace', wordBreak: 'break-word' }}>
                            {key}
                          </td>
                          <td style={{ color: '#f8fafc', wordBreak: 'break-word', fontFamily: 'monospace' }}>
                            {formatCellValue(value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ padding: '16px', background: 'rgba(245, 158, 11, 0.08)', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.2)', textAlign: 'center', fontSize: '0.825rem', color: '#fbbf24' }}>
                  ⚠ Original raw row is unavailable for this historical transaction. Normalized transaction data is displayed above.
                </div>
              )}
            </div>

            {/* 5. Payment Submission Information */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                padding: '14px 18px',
              }}
            >
              <h4 style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '10px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Send size={14} color="#818cf8" /> Participant Submission Claim
              </h4>
              {detail.submitted_utr || detail.submission_status ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', fontSize: '0.85rem' }}>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8' }}>Submitted UTR</span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#38bdf8' }}>{detail.submitted_utr || '—'}</span>
                  </div>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8' }}>Submission Status</span>
                    <span style={{ color: '#e2e8f0' }}>{detail.submission_status || '—'}</span>
                  </div>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8' }}>Submitted At</span>
                    <span style={{ color: '#94a3b8' }}>{detail.submitted_at ? new Date(detail.submitted_at).toLocaleString() : '—'}</span>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: '0.825rem', color: '#64748b', margin: 0, fontStyle: 'italic' }}>
                  No participant UTR submission was recorded for this session (UTR submission is optional).
                </p>
              )}
            </div>

            {/* 6. Technical JSON Details (Collapsible Drawer) */}
            <details
              style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '10px 14px',
                fontSize: '0.8rem',
              }}
            >
              <summary style={{ cursor: 'pointer', fontWeight: 600, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Code size={14} /> ⚙ Technical System Information (Raw JSON)
              </summary>
              <pre
                style={{
                  marginTop: '10px',
                  padding: '12px',
                  background: 'rgba(0, 0, 0, 0.6)',
                  borderRadius: '6px',
                  color: '#38bdf8',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                  fontFamily: 'monospace',
                  maxHeight: '200px',
                }}
              >
                {JSON.stringify(detail, null, 2)}
              </pre>
            </details>
          </div>
        ) : null}

        {/* Modal Footer */}
        <div className="modal-footer" style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
          <button onClick={onClose} className="btn btn-outline" style={{ minWidth: '120px' }}>
            Close Inspection Window
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReconciliationInspectionModal;
