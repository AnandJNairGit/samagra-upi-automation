/**
 * WhatsApp Notification & Deep-Link Utilities
 */

export interface PaymentReceiptDetails {
  participant_name: string;
  phone: string;
  amount_inr: number;
  reference_id: string;
  course_name?: string;
  batch_name?: string;
  utr?: string | null;
}

/**
 * Format standard payment receipt confirmation message for participant.
 */
export function formatPaymentReceivedMessage({
  participant_name,
  amount_inr,
  reference_id,
  course_name,
  batch_name,
  utr,
}: Omit<PaymentReceiptDetails, 'phone'>): string {
  const formattedAmount = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount_inr);

  return (
    `*PAYMENT RECEIVED & CONFIRMED*\n\n` +
    `Dear ${participant_name},\n\n` +
    `We are pleased to inform you that your payment for *${course_name || 'Training Program'}* (${batch_name || 'Cohort'}) has been successfully received and verified.\n\n` +
    `• *Name:* ${participant_name}\n` +
    `• *Amount:* ${formattedAmount}\n` +
    `• *Reference ID:* ${reference_id}\n` +
    (utr ? `• *UTR:* ${utr}\n` : '') +
    `• *Status:* APPROVED\n\n` +
    `Thank you for completing your registration. We look forward to having you in the cohort!`
  );
}

/**
 * Construct URL-encoded WhatsApp deep link to participant's phone number.
 */
export function buildPaymentReceivedWhatsAppUrl(details: PaymentReceiptDetails): string {
  // Clean phone number (extract digits only)
  let cleanPhone = details.phone.replace(/\D/g, '');

  // Add India country code (91) if 10 digits provided
  if (cleanPhone.length === 10) {
    cleanPhone = `91${cleanPhone}`;
  } else if (cleanPhone.startsWith('0') && cleanPhone.length === 11) {
    cleanPhone = `91${cleanPhone.slice(1)}`;
  }

  const message = formatPaymentReceivedMessage(details);
  const encodedMessage = encodeURIComponent(message);

  return `https://wa.me/${cleanPhone}?text=${encodedMessage}`;
}
