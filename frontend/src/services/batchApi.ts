import { apiFetch } from './apiClient';
import { Batch, BatchCreateInput, BatchSummary, BatchUpdateInput } from '../types/batch';

export async function getBatches(coursePublicId?: string, status?: string): Promise<Batch[]> {
  const params = new URLSearchParams();
  if (coursePublicId) {
    params.append('course_public_id', coursePublicId);
  }
  if (status) {
    params.append('status', status);
  }
  const queryString = params.toString();
  const url = queryString ? `/v1/admin/batches?${queryString}` : '/v1/admin/batches';

  const response = await apiFetch(url, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch batches.');
  }
  return response.json();
}

export async function getBatch(publicId: string): Promise<Batch> {
  const response = await apiFetch(`/v1/admin/batches/${publicId}`, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch batch details.');
  }
  return response.json();
}

export async function getBatchSummary(publicId: string): Promise<BatchSummary> {
  const response = await apiFetch(`/v1/admin/batches/${publicId}/summary`, { method: 'GET' });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch batch summary metrics.');
  }
  return response.json();
}

export async function createBatch(data: BatchCreateInput): Promise<Batch> {
  const response = await apiFetch('/v1/admin/batches', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create batch.');
  }
  return response.json();
}

export async function updateBatch(publicId: string, data: BatchUpdateInput): Promise<Batch> {
  const response = await apiFetch(`/v1/admin/batches/${publicId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update batch.');
  }
  return response.json();
}
