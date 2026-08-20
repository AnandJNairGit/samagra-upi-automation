import { apiFetch } from './apiClient';
import {
  AdminDashboardSummary,
  AdminPaymentDetailResponse,
  AdminPaymentFilterParams,
  AdminPaymentListResponse,
} from '../types/adminPayment';

/**
 * Fetch admin dashboard payment summary metrics (Phase 8).
 */
export async function fetchAdminDashboardSummary(): Promise<AdminDashboardSummary> {
  const response = await apiFetch('/v1/admin/dashboard/summary', { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Unable to load payment summary metrics.');
  }
  return response.json();
}

/**
 * Build URL search query parameters for payment listing endpoints.
 */
function buildQueryString(params: AdminPaymentFilterParams): string {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.append('status', params.status);
  if (params.course_public_id) searchParams.append('course_public_id', params.course_public_id);
  if (params.batch_public_id) searchParams.append('batch_public_id', params.batch_public_id);
  if (params.search) searchParams.append('search', params.search.trim());
  if (params.reference_id) searchParams.append('reference_id', params.reference_id.trim());
  if (params.utr) searchParams.append('utr', params.utr.trim());
  if (params.page && params.page > 1) searchParams.append('page', params.page.toString());
  if (params.page_size) searchParams.append('page_size', params.page_size.toString());

  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Fetch paginated, filtered admin payment sessions.
 */
export async function fetchAdminPayments(
  params: AdminPaymentFilterParams = {},
): Promise<AdminPaymentListResponse> {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/v1/admin/payments${qs}`, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Unable to load payment records.');
  }
  return response.json();
}

/**
 * Convenience API call for submitted payments shortcut route.
 */
export async function fetchAdminSubmittedPayments(
  params: AdminPaymentFilterParams = {},
): Promise<AdminPaymentListResponse> {
  const qs = buildQueryString(params);
  const response = await apiFetch(`/v1/admin/payments/submitted${qs}`, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Unable to load submitted payment records.');
  }
  return response.json();
}

/**
 * Fetch comprehensive read-only payment detail by payment session UUID.
 */
export async function fetchAdminPaymentDetail(
  paymentSessionPublicId: string,
): Promise<AdminPaymentDetailResponse> {
  const response = await apiFetch(`/v1/admin/payments/${paymentSessionPublicId}`, {
    method: 'GET',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Payment record not found.');
  }
  return response.json();
}

/**
 * Admin approve payment session by public UUID.
 */
export async function approveAdminPayment(
  paymentSessionPublicId: string,
): Promise<AdminPaymentDetailResponse> {
  const response = await apiFetch(`/v1/admin/payments/${paymentSessionPublicId}/approve`, {
    method: 'POST',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to approve payment.');
  }
  return response.json();
}
