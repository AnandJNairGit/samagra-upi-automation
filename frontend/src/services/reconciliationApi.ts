import { apiFetch } from './apiClient';
import {
  ReconciliationResultDetailResponse,
  ReconciliationResultListResponse,
  ReconciliationRunListResponse,
  ReconciliationRunResponse,
} from '../types/reconciliation';

export const reconciliationApi = {
  startReconciliationRun: async (
    batchPublicId: string,
    statementImportPublicId: string
  ): Promise<ReconciliationRunResponse> => {
    const response = await apiFetch('/v1/admin/reconciliation/runs', {
      method: 'POST',
      body: JSON.stringify({
        batch_public_id: batchPublicId,
        statement_import_public_id: statementImportPublicId,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to start payment reconciliation run.');
    }

    return response.json();
  },

  getReconciliationRuns: async (
    statementImportPublicId?: string,
    batchPublicId?: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<ReconciliationRunListResponse> => {
    let url = `/v1/admin/reconciliation/runs?page=${page}&page_size=${pageSize}`;
    if (statementImportPublicId) {
      url += `&statement_import_public_id=${statementImportPublicId}`;
    }
    if (batchPublicId) {
      url += `&batch_public_id=${batchPublicId}`;
    }

    const response = await apiFetch(url, { method: 'GET' });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch reconciliation runs history.');
    }

    return response.json();
  },

  getReconciliationRun: async (runPublicId: string): Promise<ReconciliationRunResponse> => {
    const response = await apiFetch(`/v1/admin/reconciliation/runs/${runPublicId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Reconciliation run record not found.');
    }

    return response.json();
  },

  getReconciliationResults: async (
    runPublicId: string,
    status?: string,
    reasonCode?: string,
    search?: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<ReconciliationResultListResponse> => {
    let url = `/v1/admin/reconciliation/runs/${runPublicId}/results?page=${page}&page_size=${pageSize}`;
    if (status) {
      url += `&status=${encodeURIComponent(status)}`;
    }
    if (reasonCode) {
      url += `&reason_code=${encodeURIComponent(reasonCode)}`;
    }
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }

    const response = await apiFetch(url, { method: 'GET' });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch reconciliation results.');
    }

    return response.json();
  },

  getReconciliationResultDetail: async (
    resultPublicId: string
  ): Promise<ReconciliationResultDetailResponse> => {
    const response = await apiFetch(`/v1/admin/reconciliation/results/${resultPublicId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Reconciliation result detail not found.');
    }

    return response.json();
  },
};
