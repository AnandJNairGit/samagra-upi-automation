export type BatchStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface Batch {
  public_id: string;
  course_public_id: string;
  course_name: string | null;
  name: string;
  amount_inr: number;
  status: BatchStatus;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BatchCreateInput {
  course_public_id: string;
  name: string;
  amount_inr: number;
  status?: 'ACTIVE' | 'INACTIVE';
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface BatchUpdateInput {
  course_public_id?: string;
  name?: string;
  amount_inr?: number;
  status?: BatchStatus;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface BatchSummary {
  batch_public_id: string;
  batch_name: string;
  course_name: string;
  amount_inr: number;
  status: BatchStatus;
  payments_generated: number;
  payments_submitted: number;
  payments_approved: number;
  expected_amount_inr: number;
  approved_amount_inr: number;
  statement_count: number;
  latest_reconciliation_status: string | null;
  latest_reconciliation_run_public_id: string | null;
}
