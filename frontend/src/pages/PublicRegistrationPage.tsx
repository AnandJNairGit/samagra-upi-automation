/**
 * Public participant registration page for a shared batch link.
 * Route: /upi/register/:batchPublicId
 */

import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronRight,
  GraduationCap,
  HelpCircle,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  User,
} from 'lucide-react';
import { fetchPublicBatch, validateRegistration } from '../services/publicApi';
import { FormErrors, ParticipantFormData, PublicBatch, PublicRegistrationContext } from '../types/public';

interface PublicRegistrationPageProps {
  batchPublicId: string;
}

const INDIAN_PHONE_REGEX = /^[6-9]\d{9}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const PublicRegistrationPage: React.FC<PublicRegistrationPageProps> = ({
  batchPublicId,
}) => {
  // Page states
  const [loading, setLoading] = useState<boolean>(true);
  const [unavailableError, setUnavailableError] = useState<string | null>(null);
  const [batch, setBatch] = useState<PublicBatch | null>(null);

  // Form states
  const [formData, setFormData] = useState<ParticipantFormData>({
    fullName: '',
    phone: '',
    email: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  // Phase 5 validated handoff context
  const [validatedContext, setValidatedContext] = useState<PublicRegistrationContext | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadBatch() {
      setLoading(true);
      setUnavailableError(null);
      try {
        const data = await fetchPublicBatch(batchPublicId);
        if (isMounted) {
          setBatch(data);
        }
      } catch (err: any) {
        if (isMounted) {
          setUnavailableError(err.message || 'This registration link is no longer available.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (batchPublicId) {
      loadBatch();
    } else {
      setUnavailableError('Invalid registration link.');
      setLoading(false);
    }

    return () => {
      isMounted = false;
    };
  }, [batchPublicId]);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const validateField = (name: keyof ParticipantFormData, value: string): string | undefined => {
    switch (name) {
      case 'fullName': {
        const clean = value.trim();
        if (!clean) return 'Please enter your full name.';
        if (clean.length < 2) return 'Full name must be at least 2 characters.';
        if (clean.length > 255) return 'Full name cannot exceed 255 characters.';
        return undefined;
      }
      case 'phone': {
        let clean = value.replace(/[\s\-()]/g, '');
        if (clean.startsWith('+91')) clean = clean.slice(3);
        else if (clean.startsWith('91') && clean.length === 12) clean = clean.slice(2);
        else if (clean.startsWith('0') && clean.length === 11) clean = clean.slice(1);

        if (!clean) return 'Please enter your mobile number.';
        if (!INDIAN_PHONE_REGEX.test(clean)) {
          return 'Enter a valid 10-digit Indian mobile number (starts with 6-9).';
        }
        return undefined;
      }
      case 'email': {
        const clean = value.trim();
        if (!clean) return 'Please enter your email address.';
        if (!EMAIL_REGEX.test(clean)) return 'Please enter a valid email address.';
        return undefined;
      }
    }
  };

  const handleInputChange = (field: keyof ParticipantFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear field-specific error as user types
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleBlur = (field: keyof ParticipantFormData) => {
    const errorMsg = validateField(field, formData[field]);
    setErrors((prev) => ({ ...prev, [field]: errorMsg }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batch) return;

    // Validate all fields
    const nameErr = validateField('fullName', formData.fullName);
    const phoneErr = validateField('phone', formData.phone);
    const emailErr = validateField('email', formData.email);

    if (nameErr || phoneErr || emailErr) {
      setErrors({
        fullName: nameErr,
        phone: phoneErr,
        email: emailErr,
      });
      return;
    }

    setSubmitting(true);
    setSubmissionError(null);

    try {
      const result = await validateRegistration(batch.public_id, formData);
      setValidatedContext(result);
    } catch (err: any) {
      setSubmissionError(err.message || 'Registration validation failed. Please try again.');
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
            Loading Registration Details
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Resolving program details and cohort schedule...
          </p>
        </div>
      </div>
    );
  }

  // 2. Unavailable State (404 / Inactive / Archived)
  if (unavailableError || !batch) {
    return (
      <div className="public-container">
        <div className="public-card unavailable-card">
          <div className="icon-badge-danger">
            <AlertCircle size={32} color="#ef4444" />
          </div>
          <h1 className="unavailable-title">Registration Unavailable</h1>
          <p className="unavailable-subtitle">
            {unavailableError || 'This registration link is no longer active.'}
          </p>
          <div className="unavailable-box">
            <HelpCircle size={18} color="#94a3b8" />
            <span>
              If you believe this is an error, please contact the training coordinator or program
              administrator for an updated link.
            </span>
          </div>
        </div>
      </div>
    );
  }

  // 3. Validated Registration Context State (Clean Handoff Boundary)
  if (validatedContext) {
    return (
      <div className="public-container">
        <div className="public-card confirmed-card">
          <div className="icon-badge-success">
            <CheckCircle2 size={32} color="#10b981" />
          </div>
          <h1 className="confirmed-title">Registration Details Validated</h1>
          <p className="confirmed-subtitle">
            Your participant information is verified and ready for payment initiation.
          </p>

          <div className="summary-section">
            <h3 className="section-heading">Program Summary</h3>
            <div className="summary-row">
              <span className="summary-label">Course</span>
              <span className="summary-val font-semibold">{validatedContext.course_name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Batch</span>
              <span className="summary-val">{validatedContext.batch_name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Training Fee</span>
              <span className="summary-val amount-highlight font-semibold">
                {formatINR(validatedContext.amount_inr)}
              </span>
            </div>
          </div>

          <div className="summary-section" style={{ marginTop: '1rem' }}>
            <h3 className="section-heading">Participant Information</h3>
            <div className="summary-row">
              <span className="summary-label">Full Name</span>
              <span className="summary-val font-semibold">{validatedContext.full_name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Mobile</span>
              <span className="summary-val monospace">{validatedContext.phone}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Email</span>
              <span className="summary-val monospace">{validatedContext.email}</span>
            </div>
          </div>

          <div className="phase-boundary-notice">
            <ShieldCheck size={18} color="#818cf8" />
            <div>
              <strong>Phase 5 Complete:</strong> Validated registration handoff established. Real-time
              UPI QR payment processing and verification will be handled in Phase 6.
            </div>
          </div>

          <button
            onClick={() => setValidatedContext(null)}
            className="btn btn-outline"
            style={{ width: '100%', marginTop: '1.25rem' }}
          >
            Edit Participant Information
          </button>
        </div>
      </div>
    );
  }

  // 4. Available Registration Form State
  return (
    <div className="public-container">
      <div className="public-card">
        {/* Header & Institute Branding */}
        <header className="public-header">
          <div className="institute-brand">
            <div className="brand-icon">
              <GraduationCap size={22} color="#818cf8" />
            </div>
            <div>
              <span className="brand-name">Samagra Institute</span>
              <span className="brand-tagline">Program Enrollment Portal</span>
            </div>
          </div>
        </header>

        {/* Read-Only Course & Batch Context */}
        <div className="program-hero-card">
          <div className="program-meta-badge">
            <ShieldCheck size={13} />
            <span>Verified Cohort Link</span>
          </div>

          <h1 className="program-title">{batch.course_name}</h1>
          <div className="program-batch-pill">
            <span>{batch.batch_name}</span>
          </div>

          <div className="program-details-grid">
            <div className="program-detail-item">
              <span className="detail-label">Training Fee</span>
              <span className="detail-val fee-val">{formatINR(batch.amount_inr)}</span>
            </div>

            <div className="program-detail-item">
              <span className="detail-label">Schedule</span>
              <span className="detail-val schedule-val">
                {batch.starts_at || batch.ends_at ? (
                  <>
                    <Calendar size={13} style={{ display: 'inline', marginRight: '4px' }} />
                    {batch.starts_at ? new Date(batch.starts_at).toLocaleDateString() : '—'}
                    {batch.ends_at ? ` to ${new Date(batch.ends_at).toLocaleDateString()}` : ''}
                  </>
                ) : (
                  'Flexible / Immediate Access'
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Participant Registration Form */}
        <div className="registration-form-section">
          <h2 className="form-section-title">Participant Information</h2>
          <p className="form-section-subtitle">
            Please enter your contact details. Confirmations will be sent via Email & SMS.
          </p>

          {submissionError && (
            <div className="error-banner" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={16} />
              <span>{submissionError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            {/* Full Name */}
            <div className="form-group">
              <label htmlFor="reg-fullname" className="form-label">
                Full Name <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <div className="input-with-icon">
                <User size={16} className="input-icon" />
                <input
                  id="reg-fullname"
                  type="text"
                  placeholder="e.g. Anand J Nair"
                  value={formData.fullName}
                  onChange={(e) => handleInputChange('fullName', e.target.value)}
                  onBlur={() => handleBlur('fullName')}
                  className={`form-input public-input ${errors.fullName ? 'input-error' : ''}`}
                  disabled={submitting}
                  autoComplete="name"
                />
              </div>
              {errors.fullName && <p className="field-error-text">{errors.fullName}</p>}
            </div>

            {/* Mobile Number */}
            <div className="form-group">
              <label htmlFor="reg-phone" className="form-label">
                Mobile Number (India) <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <div className="input-with-prefix">
                <span className="input-prefix">+91</span>
                <input
                  id="reg-phone"
                  type="tel"
                  placeholder="9876543210"
                  maxLength={10}
                  value={formData.phone}
                  onChange={(e) => {
                    const onlyNums = e.target.value.replace(/\D/g, '');
                    handleInputChange('phone', onlyNums);
                  }}
                  onBlur={() => handleBlur('phone')}
                  className={`form-input public-input ${errors.phone ? 'input-error' : ''}`}
                  disabled={submitting}
                  autoComplete="tel"
                />
              </div>
              {errors.phone && <p className="field-error-text">{errors.phone}</p>}
            </div>

            {/* Email Address */}
            <div className="form-group">
              <label htmlFor="reg-email" className="form-label">
                Email Address <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <div className="input-with-icon">
                <Mail size={16} className="input-icon" />
                <input
                  id="reg-email"
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  onBlur={() => handleBlur('email')}
                  className={`form-input public-input ${errors.email ? 'input-error' : ''}`}
                  disabled={submitting}
                  autoComplete="email"
                />
              </div>
              {errors.email && <p className="field-error-text">{errors.email}</p>}
            </div>

            {/* CTA Button */}
            <button
              type="submit"
              disabled={submitting}
              className="btn btn-primary public-submit-btn"
            >
              {submitting ? (
                <>
                  <Loader2 size={18} className="spinner" />
                  <span>Validating Registration...</span>
                </>
              ) : (
                <>
                  <span>Continue to Pay</span>
                  <ChevronRight size={18} />
                </>
              )}
            </button>

            <div className="security-footer">
              <Lock size={13} />
              <span>Safe & Secure UPI Payment Gateway Authorization</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
