export type ReconciliationStatus =
  | 'MATCHED'
  | 'AMOUNT_MISMATCH'
  | 'UTR_MISMATCH'
  | 'UNKNOWN_REFERENCE'
  | 'NO_REFERENCE'
  | 'DUPLICATE_TRANSACTION'
  | 'NEEDS_REVIEW'
  | 'UNMATCHED';

export interface ReconciliationRunCreateRequest {
  statement_import_public_id: string;
}

export interface ReconciliationRunResponse {
  public_id: string;
  statement_import_public_id: string;
  filename: string;
  status: string;
  total_transactions: number;
  credit_transactions: number;
  debit_transactions: number;
  matched_count: number;
  amount_mismatch_count: number;
  unknown_reference_count: number;
  no_reference_count: number;
  utr_mismatch_count: number;
  duplicate_transaction_count: number;
  needs_review_count: number;
  unmatched_count: number;
  started_at: string;
  completed_at?: string;
  created_at: string;
}

export interface ReconciliationRunListResponse {
  items: ReconciliationRunResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReconciliationResultResponse {
  public_id: string;
  reconciliation_run_public_id: string;
  bank_transaction_public_id: string;
  payment_session_public_id?: string;
  payment_submission_public_id?: string;
  status: ReconciliationStatus;
  reason_code: string;
  explanation: string;

  reference_match?: boolean | null;
  amount_match?: boolean | null;
  utr_match?: boolean | null;
  payer_match?: boolean | null;

  bank_reference_id?: string;
  bank_amount_inr?: number;
  bank_utr?: string;
  bank_transaction_at?: string;
  bank_counterparty_name?: string;

  expected_reference_id?: string;
  expected_amount_inr?: number;
  submitted_utr?: string;
  participant_name?: string;
}

export interface ReconciliationResultDetailResponse extends ReconciliationResultResponse {
  statement_filename: string;
  bank_direction?: string;
  bank_description?: string;
  payment_session_status?: string;
  course_name_snapshot?: string;
  batch_name_snapshot?: string;
  submission_status?: string;
  submitted_at?: string;
}

export interface ReconciliationResultListResponse {
  items: ReconciliationResultResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
