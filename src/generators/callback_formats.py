"""DOB/gender format transforms for bureau callback fields."""


def dob_to_cibil(dob: str) -> str:
    """YYYY-MM-DD → DDMMYYYY."""
    y, m, d = dob.split("-")
    return f"{d}{m}{y}"


def dob_to_highmark(dob: str) -> str:
    """YYYY-MM-DD → DD-MM-YYYY."""
    y, m, d = dob.split("-")
    return f"{d}-{m}-{y}"


def gender_cibil(gender: str) -> str:
    return "MALE" if gender == "M" else "FEMALE"


def gender_highmark(gender: str) -> str:
    return "Male" if gender == "M" else "Female"
