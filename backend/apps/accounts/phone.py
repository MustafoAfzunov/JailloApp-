import re


def normalize_phone(raw) -> str:
    """Normalise to E.164-like '+996XXXXXXXXX'. Raises ValueError if invalid."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 9:  # 700123456
        digits = "996" + digits
    elif len(digits) == 10 and digits.startswith("0"):  # 0700123456
        digits = "996" + digits[1:]
    if not 11 <= len(digits) <= 15:
        raise ValueError("Invalid phone number")
    return "+" + digits
