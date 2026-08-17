export interface ColumnFieldMapping {
  column_index: number;
  header?: string;
}

export interface StatementColumnMapping {
  reference_id: ColumnFieldMapping;
  amount: ColumnFieldMapping;
  transaction_at?: ColumnFieldMapping;
  direction?: ColumnFieldMapping;
  utr?: ColumnFieldMapping;
  counterparty_name?: ColumnFieldMapping;
  description?: ColumnFieldMapping;
}

export interface HeaderItem {
  column_index: number;
  header: string;
}

export interface ImportPreviewResponse {
  preview_token: string;
  filename: string;
  file_type: 'csv' | 'xlsx';
  file_size: number;
  file_checksum_sha256: string;
  available_sheets: string[];
  selected_sheet_name?: string;
  header_row_index: number;
  headers: HeaderItem[];
  preview_rows: Record<string, any>[];
  total_detected_rows: number;
  expires_in_seconds: number;
}

export interface ImportConfirmRequest {
  preview_token: string;
  sheet_name?: string;
  header_row_index: number;
  column_mapping: StatementColumnMapping;
  source_timezone?: string;
}

export interface ImportSummaryResponse {
  already_imported: boolean;
  import_public_id: string;
  filename: string;
  file_type: string;
  selected_sheet_name?: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  new_transactions: number;
  rows_without_reference: number;
  created_at: string;
  completed_at?: string;
  error_summary?: any;
  message?: string;
}

export interface StatementImportListItem {
  public_id: string;
  filename: string;
  file_type: string;
  source: string;
  selected_sheet_name?: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  duplicate_rows: number;
  new_transactions: number;
  rows_without_reference: number;
  imported_by_name: string;
  created_at: string;
}

export interface StatementImportListResponse {
  items: StatementImportListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StatementImportDetail {
  public_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  file_checksum_sha256: string;
  canonical_mapping_hash: string;
  source: string;
  selected_sheet_name?: string;
  header_row_index: number;
  column_mapping: Record<string, any>;
  status: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  new_transactions: number;
  rows_without_reference: number;
  error_summary?: any;
  imported_by_name: string;
  created_at: string;
  completed_at?: string;
}

export interface BankTransactionItem {
  public_id: string;
  transaction_at?: string;
  amount_inr?: number;
  direction?: string;
  reference_id?: string;
  utr?: string;
  counterparty_name?: string;
  description?: string;
  source: string;
  source_transaction_key?: string;
  created_at: string;
}

export interface BankTransactionListResponse {
  items: BankTransactionItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
