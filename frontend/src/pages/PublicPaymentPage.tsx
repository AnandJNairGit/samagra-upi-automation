/**
 * Public UPI Payment Page (Phases 6 & 7).
 * Route: /upi/payment/:paymentSessionPublicId
 */

import React, { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  GraduationCap,
  HelpCircle,
  Info,
  Loader2,
  Lock,
  MessageCircle,
  QrCode,
  Send,
  ShieldCheck,
  User,
} from 'lucide-react';
import { fetchPaymentSession, submitPaymentSessionUTR } from '../services/publicApi';
import { PaymentSessionPublic } from '../types/public';

interface PublicPaymentPageProps {
  paymentSessionPublicId: string;
  onNavigate?: (path: string) => void;
}

export const PublicPaymentPage: React.FC<PublicPaymentPageProps> = ({
  paymentSessionPublicId,
  onNavigate,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [session, setSession] = useState<PaymentSessionPublic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<'ref' | 'upi' | null>(null);

  // UTR Submission Form state (Phase 7)
  const [utrInput, setUtrInput] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPaymentSession() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchPaymentSession(paymentSessionPublicId);
        if (isMounted) {
          setSession(data);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'This payment session is no longer available.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (paymentSessionPublicId) {
      loadPaymentSession();
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

  const copyToClipboard = async (text: string, field: 'ref' | 'upi') => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2500);
    } catch {
      alert(`Could not copy to clipboard. Text: ${text}`);
    }
  };

  const handleUTRSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUTR = utrInput.trim() || null;  // Treat empty as null — UTR is optional

    if (!session) return;

    setSubmitting(true);
    setSubmitError(null);

    try {
      const response = await submitPaymentSessionUTR(session.public_id, cleanUTR);

      // Update session state to SUBMITTED
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: 'SUBMITTED',
          utr_masked: response.utr_masked,
          submitted_at: response.submitted_at,
          whatsapp_url: response.whatsapp_url,
          submission_public_id: response.submission_public_id,
        };
      });

      // Attempt to open WhatsApp in a new tab
      if (response.whatsapp_url) {
        try {
          window.open(response.whatsapp_url, '_blank', 'noopener,noreferrer');
        } catch {
          // Graceful fallback: manual button remains available
        }
      }
    } catch (err: any) {
      setSubmitError(err.message || 'Unable to submit payment reference. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // 1. Loading State
  if (loading) {
    return (
      <div className="public-container">
        <div className="public-card loading-card">
          <Loader2 size={36} className="spinner" color="#818cf8" />
          <h2 style={{ marginTop: '1rem', color: '#f8fafc', fontSize: '1.25rem' }}>
            Loading Payment Checkout
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Retrieving payment session details...
          </p>
        </div>
      </div>
    );
  }

  // 2. Error / Unavailable State
  if (error || !session) {
    return (
      <div className="public-container">
        <div className="public-card unavailable-card">
          <div className="icon-badge-danger">
            <AlertCircle size={32} color="#ef4444" />
          </div>
          <h1 className="unavailable-title">Payment Session Unavailable</h1>
          <p className="unavailable-subtitle">
            {error || 'This payment session could not be found or has expired.'}
          </p>
          <div className="unavailable-box">
            <HelpCircle size={18} color="#94a3b8" />
            <span>
              If you experienced an error or closed your registration prematurely, please return to the
              registration link to generate a fresh payment session.
            </span>
          </div>
          {onNavigate && (
            <button
              onClick={() => onNavigate('/')}
              className="btn btn-outline"
              style={{ marginTop: '1.5rem', width: '100%' }}
            >
              <ArrowLeft size={16} />
              <span>Back to Home</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  // 3. Expired State
  if (session.is_expired || session.status === 'EXPIRED') {
    return (
      <div className="public-container">
        <div className="public-card unavailable-card">
          <div
            className="icon-badge-danger"
            style={{ background: 'rgba(245, 158, 11, 0.12)', borderColor: 'rgba(245, 158, 11, 0.3)' }}
          >
            <Clock size={32} color="#f59e0b" />
          </div>
          <h1 className="unavailable-title" style={{ color: '#fbbf24' }}>
            Payment Session Expired
          </h1>
          <p className="unavailable-subtitle">
            This payment session has exceeded its validity window. For security and financial accuracy,
            please generate a new checkout session.
          </p>
          <div className="summary-section" style={{ textAlign: 'left', marginBottom: '1.5rem' }}>
            <div className="summary-row">
              <span className="summary-label">Course</span>
              <span className="summary-val font-semibold">{session.course_name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Batch</span>
              <span className="summary-val">{session.batch_name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Participant</span>
              <span className="summary-val">{session.full_name}</span>
            </div>
          </div>
          {onNavigate && (
            <button
              onClick={() => onNavigate('/')}
              className="btn btn-primary"
              style={{ width: '100%' }}
            >
              <span>Return to Program Enrollment</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  const isSubmitted = session.status === 'SUBMITTED';

  // 4. Active UPI Payment & UTR Submission Page
  return (
    <div className="public-container">
      <div className="public-card payment-checkout-card">
        {/* Header & Institute Branding */}
        <header className="public-header">
          <div className="institute-brand">
            <div className="brand-icon">
              <GraduationCap size={22} color="#818cf8" />
            </div>
            <div>
              <span className="brand-name">Samagra Institute</span>
              <span className="brand-tagline">Secure UPI Payment Checkout</span>
            </div>
          </div>
          {isSubmitted ? (
            <div className="status-pill status-pill-submitted">
              <CheckCircle2 size={13} color="#10b981" />
              <span>Payment Submitted</span>
            </div>
          ) : (
            <div className="status-pill active-pill" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
              <Clock size={12} />
              <span>Awaiting Payment</span>
            </div>
          )}
        </header>

        {/* Program & Participant Context */}
        <div className="payment-summary-box">
          <div className="payment-course-info">
            <h1 className="payment-course-title">{session.course_name}</h1>
            <span className="payment-batch-tag">{session.batch_name}</span>
          </div>

          <div className="payment-participant-row">
            <div className="participant-chip">
              <User size={13} color="#94a3b8" />
              <span>{session.full_name}</span>
            </div>
            <div className="payment-meta-badge">
              <ShieldCheck size={13} />
              <span>Verified Merchant</span>
            </div>
          </div>
        </div>

        {/* Amount Section */}
        <div className="amount-hero-banner">
          <span className="amount-label">Total Amount Payable</span>
          <span className="amount-val-hero">{formatINR(session.amount_inr)}</span>
        </div>

        {/* Dynamic UPI QR Code */}
        <div className="qr-code-section">
          <div className="qr-code-wrapper">
            <QRCodeSVG
              value={session.upi_uri}
              size={220}
              level="H"
              includeMargin={true}
              bgColor="#ffffff"
              fgColor="#0f172a"
              className="qr-svg-canvas"
            />
          </div>
          <div className="qr-instructions-badge">
            <QrCode size={14} />
            <span>Scan with any UPI App (GPay, PhonePe, Paytm, BHIM)</span>
          </div>
        </div>

        {/* Copyable Reference ID & UPI ID */}
        <div className="payment-keys-grid">
          {/* Reference ID */}
          <div className="payment-key-card">
            <div className="key-card-header">
              <span className="key-card-label">Payment Reference ID</span>
              <button
                onClick={() => copyToClipboard(session.reference_id, 'ref')}
                className="btn-copy-small"
                title="Copy Reference ID"
              >
                {copiedField === 'ref' ? (
                  <>
                    <Check size={12} color="#34d399" />
                    <span style={{ color: '#34d399' }}>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <span className="key-card-value monospace font-bold">{session.reference_id}</span>
          </div>

          {/* UPI ID */}
          <div className="payment-key-card">
            <div className="key-card-header">
              <span className="key-card-label">Payee UPI ID</span>
              <button
                onClick={() => copyToClipboard(session.upi_id, 'upi')}
                className="btn-copy-small"
                title="Copy UPI ID"
              >
                {copiedField === 'upi' ? (
                  <>
                    <Check size={12} color="#34d399" />
                    <span style={{ color: '#34d399' }}>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <span className="key-card-value monospace">{session.upi_id}</span>
          </div>
        </div>

        {/* Optional Mobile Deep Link */}
        <div style={{ marginTop: '1rem' }}>
          <a
            href={session.upi_uri}
            className="btn btn-outline upi-deep-link-btn"
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={15} />
            <span>Pay directly via Installed UPI App</span>
          </a>
        </div>

        {/* Step-by-Step Payment Instructions */}
        <div className="instructions-card">
          <div className="instructions-header">
            <Info size={16} color="#818cf8" />
            <h3 className="instructions-title">Payment Instructions</h3>
          </div>
          <ol className="instructions-list">
            <li>
              Open your preferred UPI app (<strong>Google Pay, PhonePe, Paytm, or BHIM</strong>).
            </li>
            <li>
              Scan the QR code above or enter the Payee UPI ID <code>{session.upi_id}</code>.
            </li>
            <li>
              Verify that the payee is <strong>{session.payee_name}</strong> and fee is{' '}
              <strong>{formatINR(session.amount_inr)}</strong>.
            </li>
            <li>
              Complete the payment. If your UPI app shows a{' '}
              <strong>12-digit UTR/Reference number</strong>, note it down — it helps speed up verification.
            </li>
            <li>
              Click <strong>"Confirm Payment Submitted"</strong> below. UTR is optional but recommended.
            </li>
          </ol>
        </div>

        {/* ========================================================================= */}
        {/* PHASE 7: UTR SUBMISSION & WHATSAPP NOTIFICATION SECTION                    */}
        {/* ========================================================================= */}
        {isSubmitted ? (
          <div className="submitted-confirmation-card">
            <div className="submitted-icon-badge">
              <CheckCircle2 size={36} color="#10b981" />
            </div>
            <h2 className="submitted-title">Payment Details Submitted</h2>
            <p className="submitted-subtitle">
              Your transaction reference has been successfully submitted and is awaiting administrator verification.
            </p>

            <div className="submitted-meta-grid">
              <div className="submitted-meta-item">
                <span className="submitted-meta-label">Transaction Reference (UTR)</span>
                <span className="submitted-meta-val monospace font-bold">
                  {session.utr_masked || '••••'}
                </span>
              </div>
              <div className="submitted-meta-item">
                <span className="submitted-meta-label">Verification Status</span>
                <span className="submitted-meta-val status-tag-submitted">
                  SUBMITTED (Pending Review)
                </span>
              </div>
              {session.submitted_at && (
                <div className="submitted-meta-item submitted-meta-full">
                  <span className="submitted-meta-label">Submission Timestamp</span>
                  <span className="submitted-meta-val">
                    {new Date(session.submitted_at).toLocaleString('en-IN', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </span>
                </div>
              )}
            </div>

            <div className="verification-notice-box">
              <Info size={16} color="#38bdf8" />
              <span>
                Your payment will be manually verified against institutional bank records. Once verified,
                you will receive enrollment confirmation.
              </span>
            </div>

            {session.whatsapp_url && (
              <div className="whatsapp-action-container">
                <a
                  href={session.whatsapp_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-whatsapp"
                >
                  <MessageCircle size={18} />
                  <span>Notify Administrator on WhatsApp</span>
                </a>
                <p className="whatsapp-action-note">
                  Click above to open WhatsApp with your pre-filled payment details to notify the administrator.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="utr-form-section">
            <div className="utr-form-header">
              <div className="utr-step-badge">Step 2</div>
              <div>
                <h3 className="utr-form-title">Confirm Payment Submitted</h3>
                <p className="utr-form-subtitle">
                  After completing your UPI payment, click below to confirm. You can optionally enter the
                  UTR / transaction reference number if your app shows one.
                </p>
              </div>
            </div>

            {submitError && (
              <div className="form-error-banner" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={16} />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleUTRSubmit} className="utr-form">
              <div className="form-group">
                <label className="form-label" htmlFor="utrInput">
                  UPI Reference / UTR Number{' '}
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 400 }}>(optional)</span>
                </label>
                <input
                  id="utrInput"
                  type="text"
                  className={`form-input monospace ${submitError ? 'input-error' : ''}`}
                  placeholder="e.g. 123456789012 (leave blank if not available)"
                  value={utrInput}
                  onChange={(e) => {
                    setUtrInput(e.target.value);
                    if (submitError) setSubmitError(null);
                  }}
                  disabled={submitting}
                  maxLength={100}
                  autoComplete="off"
                  spellCheck={false}
                />
                <span className="form-hint">
                  Found on your transaction confirmation in Google Pay, PhonePe, Paytm, or BHIM.
                  Leave blank if your app doesn't show one — your payment will still be verified.
                </span>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-submit-utr"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className="spinner" />
                    <span>Submitting Reference...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    <span>Submit Payment Reference</span>
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        <div className="security-footer" style={{ marginTop: '1.5rem' }}>
          <Lock size={13} />
          <span>NPCI Unified Payments Interface Standard • End-to-End Encrypted</span>
        </div>
      </div>
    </div>
  );
};
