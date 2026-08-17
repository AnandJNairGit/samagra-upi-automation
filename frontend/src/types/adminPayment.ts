/**
 * TypeScript interfaces for Admin Payment Dashboard & Inspection (Phase 8).
 */

export interface AdminDashboardSummary {
  total_registrations: number;
  pending_payments: number;
  submitted_payments: number;
  approved_payments: number;
  rejected_payments: number;
  total_amount_collected_inr: number;
}

export interface AdminPaymentListItem {
  payment_session_public_id: string;
  participant_name: string;
  phone: string;
  email: string;
  course_public_id: string;
  course_name: string;
  batch_public_id: string;
  batch_name: string;
  amount_inr: number;
  reference_id: string;
  payment_session_status: string;
  utr?: string | null;
  submission_status?: string | null;
  submitted_at?: string | null;
  created_at: string;
}

export interface AdminPaymentListResponse {
  items: AdminPaymentListItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface AdminPaymentDetailParticipant {
  full_name: string;
  phone: string;
  email: string;
}

export interface AdminPaymentDetailTraining {
  course_public_id: string;
  course_name: string;
  batch_public_id: string;
  batch_name: string;
}

export interface AdminPaymentDetailPayment {
  amount_inr: number;
  reference_id: string;
  upi_id_snapshot: string;
  payee_name_snapshot: string;
  upi_uri: string;
  status: string;
  created_at: string;
  expires_at?: string | null;
}

export interface AdminPaymentDetailSubmission {
  public_id: string;
  utr: string;
  status: string;
  is_current: boolean;
  submitted_at: string;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
}

export interface AdminPaymentDetailResponse {
  payment_session_public_id: string;
  participant: AdminPaymentDetailParticipant;
  training: AdminPaymentDetailTraining;
  payment: AdminPaymentDetailPayment;
  current_submission?: AdminPaymentDetailSubmission | null;
  submission_history: AdminPaymentDetailSubmission[];
}

export interface AdminPaymentFilterParams {
  status?: string;
  course_public_id?: string;
  batch_public_id?: string;
  search?: string;
  reference_id?: string;
  utr?: string;
  page?: number;
  page_size?: number;
}
