import { apiFetch } from './apiClient';
import {
  BankTransactionListResponse,
  ImportConfirmRequest,
  ImportPreviewResponse,
  ImportSummaryResponse,
  StatementImportDetail,
  StatementImportListResponse,
} from '../types/statementImport';

export const statementImportApi = {
  previewStatementImport: async (
    file: File,
    sheetName?: string,
    headerRowIndex: number = 1
  ): Promise<ImportPreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sheetName) {
      formData.append('sheet_name', sheetName);
    }
    formData.append('header_row_index', headerRowIndex.toString());

    const response = await apiFetch('/v1/admin/statement-imports/preview', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to process statement file preview.');
    }

    return response.json();
  },

  confirmStatementImport: async (
    payload: ImportConfirmRequest
  ): Promise<ImportSummaryResponse> => {
    const response = await apiFetch('/v1/admin/statement-imports/confirm', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Statement import confirmation failed.');
    }

    return response.json();
  },

  getStatementImports: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<StatementImportListResponse> => {
    const response = await apiFetch(
      `/v1/admin/statement-imports?page=${page}&page_size=${pageSize}`,
      { method: 'GET' }
    );

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch statement import history.');
    }

    return response.json();
  },

  getStatementImportDetail: async (
    importPublicId: string
  ): Promise<StatementImportDetail> => {
    const response = await apiFetch(`/v1/admin/statement-imports/${importPublicId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Statement import record not found.');
    }

    return response.json();
  },

  getImportTransactions: async (
    importPublicId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<BankTransactionListResponse> => {
    const response = await apiFetch(
      `/v1/admin/statement-imports/${importPublicId}/transactions?page=${page}&page_size=${pageSize}`,
      { method: 'GET' }
    );

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch import transactions.');
    }

    return response.json();
  },
};
