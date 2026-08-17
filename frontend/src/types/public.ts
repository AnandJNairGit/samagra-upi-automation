/**
 * TypeScript types for Public Registration, UPI Payment Checkout, and UTR Submission (Phases 5, 6 & 7).
 */

export interface PublicBatch {
  public_id: string;
  course_name: string;
  batch_name: string;
  amount_inr: number;
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface ParticipantFormData {
  fullName: string;
  phone: string;
  email: string;
}

export interface PublicRegistrationContext {
  batch_public_id: string;
  course_name: string;
  batch_name: string;
  amount_inr: number;
  full_name: string;
  phone: string;
  email: string;
}

export interface PaymentSessionPublic {
  public_id: string;
  full_name: string;
  phone: string;
  email: string;
  course_name: string;
  batch_name: string;
  amount_inr: number;
  reference_id: string;
  upi_id: string;
  payee_name: string;
  upi_uri: string;
  status: string;
  expires_at?: string | null;
  is_expired?: boolean;
  created_at: string;

  // Phase 7 Submission & WhatsApp Metadata
  submission_public_id?: string | null;
  utr_masked?: string | null;
  submitted_at?: string | null;
  whatsapp_url?: string | null;
}

export interface UTRSubmissionRequest {
  utr: string;
}

export interface UTRSubmissionResponse {
  payment_session_public_id: string;
  submission_public_id: string;
  status: string;
  utr_masked: string;
  submitted_at: string;
  whatsapp_url: string;
}

export interface FormErrors {
  fullName?: string;
  phone?: string;
  email?: string;
}
