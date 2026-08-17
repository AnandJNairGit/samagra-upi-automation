"""WhatsApp notification formatting, deep-link generation, and UTR masking service."""

import re
import urllib.parse


def format_whatsapp_admin_message(
    full_name: str,
    phone: str,
    email: str,
    course_name: str,
    batch_name: str,
    amount_inr: int,
    reference_id: str,
    utr: str,
) -> str:
    """Format standard notification message for the administrator using immutable snapshot data."""
    return (
        f"NEW PAYMENT SUBMISSION\n\n"
        f"Name: {full_name}\n"
        f"Phone: {phone}\n"
        f"Email: {email}\n\n"
        f"Course: {course_name}\n"
        f"Batch: {batch_name}\n"
        f"Amount: ₹{amount_inr:,}\n\n"
        f"Reference ID: {reference_id}\n"
        f"UTR: {utr}\n\n"
        f"Payment Status: SUBMITTED"
    )


def build_whatsapp_admin_url(
    admin_phone: str,
    full_name: str,
    phone: str,
    email: str,
    course_name: str,
    batch_name: str,
    amount_inr: int,
    reference_id: str,
    utr: str,
) -> str:
    """Construct a URL-encoded WhatsApp deep link directed to the administrator."""
    clean_admin_phone = re.sub(r"\D", "", admin_phone.strip())
    message = format_whatsapp_admin_message(
        full_name=full_name,
        phone=phone,
        email=email,
        course_name=course_name,
        batch_name=batch_name,
        amount_inr=amount_inr,
        reference_id=reference_id,
        utr=utr,
    )
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{clean_admin_phone}?text={encoded_message}"


def mask_utr(utr: str) -> str:
    """Mask UTR transaction reference for privacy (e.g., 1234••••9012)."""
    clean = utr.strip()
    if len(clean) <= 4:
        return "••••"
    if len(clean) <= 8:
        return f"{clean[:2]}••••{clean[-2:]}"
    return f"{clean[:4]}••••{clean[-4:]}"
