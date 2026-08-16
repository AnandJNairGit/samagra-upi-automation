/**
 * Public, unauthenticated API client for shared batch registration endpoints.
 */

import { config } from '../core/config';
import { ParticipantFormData, PublicBatch, PublicRegistrationContext } from '../types/public';

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
 * Validate participant registration details prior to Phase 6 payment handoff.
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
      // Pydantic validation error format
      const firstError = errorData.detail[0];
      throw new Error(firstError?.msg || 'Invalid registration details provided.');
    }
    throw new Error(errorData.detail || 'Validation failed. Please check your information.');
  }

  return response.json();
}
