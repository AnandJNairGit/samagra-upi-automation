/**
 * TypeScript types for Public Registration flow (Phase 5).
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

export interface FormErrors {
  fullName?: string;
  phone?: string;
  email?: string;
}
