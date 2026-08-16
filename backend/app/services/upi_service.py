"""UPI URI generation and payment reference helper services."""

import re
import secrets
import string
import urllib.parse


def generate_reference_id(full_name: str, phone: str) -> str:
    """Generate a unique, human-readable, and UPI transaction-safe payment reference ID.

    Format: <CLEAN_NAME_PREFIX>_<PHONE_SUFFIX>_<RANDOM_SUFFIX>
    Example: ANAND_4321_K8M2
    """
    # 1. Clean uppercase first name prefix (max 8 chars, alpha only)
    first_token = full_name.strip().split()[0] if full_name.strip() else "PAY"
    clean_name = re.sub(r"[^A-Z]", "", first_token.upper())[:8]
    if len(clean_name) < 2:
        clean_name = "PAY"

    # 2. Extract last 4 digits of phone
    clean_phone = re.sub(r"\D", "", phone)
    phone_suffix = clean_phone[-4:] if len(clean_phone) >= 4 else "0000"

    # 3. 4-character cryptographically secure uppercase alphanumeric random suffix
    chars = string.ascii_uppercase + string.digits
    random_suffix = "".join(secrets.choice(chars) for _ in range(4))

    return f"{clean_name}_{phone_suffix}_{random_suffix}"


def build_upi_uri(
    upi_id: str,
    payee_name: str,
    amount_inr: int,
    reference_id: str,
) -> str:
    """Construct a standardized, URL-encoded UPI Intent URI for QR code and deep linking.

    Specification:
        upi://pay?pa={UPI_ID}&pn={PAYEE_NAME}&am={AMOUNT}&cu=INR&tn={REFERENCE_ID}&tr={REFERENCE_ID}
    """
    params = {
        "pa": upi_id.strip(),
        "pn": payee_name.strip(),
        "am": str(int(amount_inr)),
        "cu": "INR",
        "tn": reference_id.strip(),
        "tr": reference_id.strip(),
    }

    # Encode query parameters with %20 for spaces to maximize UPI app compatibility
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{query_string}"
