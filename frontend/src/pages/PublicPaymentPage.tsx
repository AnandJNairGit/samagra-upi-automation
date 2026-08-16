/**
 * Public UPI Payment Page (Phase 6).
 * Route: /upi/payment/:paymentSessionPublicId
 */

import React, { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  Clock,
  Copy,
  ExternalLink,
  GraduationCap,
  HelpCircle,
  Info,
  Loader2,
  Lock,
  QrCode,
  ShieldCheck,
  User,
} from 'lucide-react';
import { fetchPaymentSession } from '../services/publicApi';
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
            Generating dynamic UPI QR code and payment reference...
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
          <div className="icon-badge-danger" style={{ background: 'rgba(245, 158, 11, 0.12)', borderColor: 'rgba(245, 158, 11, 0.3)' }}>
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

  // 4. Active UPI Payment Page
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
          <div className="status-pill active-pill" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
            <Clock size={12} />
            <span>Awaiting Payment</span>
          </div>
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

        {/* Large Dynamic UPI QR Code */}
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
              Complete the payment. Keep your <strong>12-digit UPI Reference (UTR) number</strong>{' '}
              safe from your transaction receipt.
            </li>
          </ol>
        </div>

        <div className="security-footer" style={{ marginTop: '1.5rem' }}>
          <Lock size={13} />
          <span>NPCI Unified Payments Interface Standard • End-to-End Encrypted</span>
        </div>
      </div>
    </div>
  );
};
