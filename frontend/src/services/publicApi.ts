/**
 * Public, unauthenticated API client for shared batch registration and UPI checkout endpoints.
 */

import { config } from '../core/config';
import {
  ParticipantFormData,
  PaymentSessionPublic,
  PublicBatch,
  PublicRegistrationContext,
  UTRSubmissionResponse,
} from '../types/public';

/**
 * Resolve public cohort registration details by batch UUID.
 * Returns PublicBatch if both batch and course are ACTIVE; otherwise throws error (404).
 */
export async function fetchPublicBatch(batchPublicId: string): Promise<PublicBatch> {
  const url = `${config.apiBaseUrl}/v1/public/batches/${batchPublicId}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'This registration link is no longer available.');
  }

  return response.json();
}

/**
 * Validate participant registration details (Phase 5 stateless validation).
 */
export async function validateRegistration(
  batchPublicId: string,
  participant: ParticipantFormData,
): Promise<PublicRegistrationContext> {
  const url = `${config.apiBaseUrl}/v1/public/register/validate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      batch_public_id: batchPublicId,
      full_name: participant.fullName.trim(),
      phone: participant.phone.trim(),
      email: participant.email.trim(),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (errorData.detail && Array.isArray(errorData.detail)) {
      const firstError = errorData.detail[0];
      throw new Error(firstError?.msg || 'Invalid registration details provided.');
    }
    throw new Error(errorData.detail || 'Validation failed. Please check your information.');
  }

  return response.json();
}

/**
 * Initiate a new UPI checkout payment session (Phase 6).
 * Persists payment session, derives authoritative amount, generates reference ID and UPI URI.
 */
export async function createPaymentSession(
  batchPublicId: string,
  participant: ParticipantFormData,
): Promise<PaymentSessionPublic> {
  const url = `${config.apiBaseUrl}/v1/public/payment-sessions`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      batch_public_id: batchPublicId,
      full_name: participant.fullName.trim(),
      phone: participant.phone.trim(),
      email: participant.email.trim(),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (errorData.detail && Array.isArray(errorData.detail)) {
      const firstError = errorData.detail[0];
      throw new Error(firstError?.msg || 'Invalid registration details provided.');
    }
    throw new Error(errorData.detail || 'Unable to initiate payment session. Please try again.');
  }

  return response.json();
}

/**
 * Resolve public payment session details by payment session UUID for rendering the payment page.
 */
export async function fetchPaymentSession(
  paymentSessionPublicId: string,
): Promise<PaymentSessionPublic> {
  const url = `${config.apiBaseUrl}/v1/public/payment-sessions/${paymentSessionPublicId}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'This payment session is no longer available.');
  }

  return response.json();
}

/**
 * Submit UTR / transaction reference number for an active payment session (Phase 7).
 */
export async function submitPaymentSessionUTR(
  paymentSessionPublicId: string,
  utr: string,
): Promise<UTRSubmissionResponse> {
  const url = `${config.apiBaseUrl}/v1/public/payment-sessions/${paymentSessionPublicId}/submissions`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      utr: utr.trim(),
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (errorData.detail && Array.isArray(errorData.detail)) {
      const firstError = errorData.detail[0];
      throw new Error(firstError?.msg || 'Invalid transaction reference provided.');
    }
    throw new Error(errorData.detail || 'Unable to submit transaction reference. Please try again.');
  }

  return response.json();
}
