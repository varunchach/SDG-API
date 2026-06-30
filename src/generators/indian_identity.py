"""Indian identity field generators — PAN, mobile, pin/state pairs."""

from __future__ import annotations

import random
import string
from typing import Iterable

# Common Indian states for realistic pin + state pairing
INDIAN_LOCATIONS: list[dict[str, str]] = [
    {"city": "MUMBAI", "state": "MAHARASHTRA", "pinCode": "400001"},
    {"city": "MUMBAI", "state": "MAHARASHTRA", "pinCode": "400071"},
    {"city": "PUNE", "state": "MAHARASHTRA", "pinCode": "411001"},
    {"city": "NAGPUR", "state": "MAHARASHTRA", "pinCode": "440001"},
    {"city": "DELHI", "state": "DELHI", "pinCode": "110001"},
    {"city": "NEW DELHI", "state": "DELHI", "pinCode": "110020"},
    {"city": "BENGALURU", "state": "KARNATAKA", "pinCode": "560001"},
    {"city": "BENGALURU", "state": "KARNATAKA", "pinCode": "560034"},
    {"city": "CHENNAI", "state": "TAMIL NADU", "pinCode": "600001"},
    {"city": "HYDERABAD", "state": "TELANGANA", "pinCode": "500001"},
    {"city": "KOLKATA", "state": "WEST BENGAL", "pinCode": "700001"},
    {"city": "AHMEDABAD", "state": "GUJARAT", "pinCode": "380001"},
    {"city": "SURAT", "state": "GUJARAT", "pinCode": "395009"},
    {"city": "JAIPUR", "state": "RAJASTHAN", "pinCode": "302001"},
    {"city": "LUCKNOW", "state": "UTTAR PRADESH", "pinCode": "226001"},
    {"city": "CHANDIGARH", "state": "CHANDIGARH", "pinCode": "160001"},
    {"city": "KOCHI", "state": "KERALA", "pinCode": "682001"},
    {"city": "INDORE", "state": "MADHYA PRADESH", "pinCode": "452001"},
    {"city": "BHOPAL", "state": "MADHYA PRADESH", "pinCode": "462001"},
    {"city": "PATNA", "state": "BIHAR", "pinCode": "800001"},
]

# Weighted toward common Indian given names (Faker supplements these)
INDIAN_FIRST_NAMES_MALE = [
    "ARJUN", "ROHAN", "VIKRAM", "RAHUL", "AMIT", "SURESH", "PRANAV", "KARAN",
    "NIKHIL", "SANJAY", "RAMESH", "ANIL", "DEEPAK", "MANOJ", "ASHOK", "VIVEK",
]
INDIAN_FIRST_NAMES_FEMALE = [
    "PRIYA", "ANITA", "KAVITA", "POOJA", "NEHA", "SUNITA", "MEERA", "DIVYA",
    "SHREYA", "NANDINI", "LAKSHMI", "REKHA", "SWATI", "ANJALI", "RITU", "KIRAN",
]
INDIAN_LAST_NAMES = [
    "SHARMA", "PATEL", "SINGH", "KUMAR", "REDDY", "NAIR", "IYER", "GUPTA",
    "MEHTA", "DESAI", "JOSHI", "RAO", "MENON", "PILLAI", "CHOPRA", "MALHOTRA",
    "KAPOOR", "BANERJEE", "MUKHERJEE", "SHAH", "AGARWAL", "VERMA", "SANTOSH",
    "KULKARNI", "BHAT", "PANDEY", "MISHRA", "THAKUR", "RATHORE", "CHAUHAN",
]

INDIAN_EMPLOYERS = [
    "TATA CONSULTANCY SERVICES LIMITED",
    "INFOSYS LIMITED",
    "WIPRO LIMITED",
    "HDFC BANK LIMITED",
    "ICICI BANK LIMITED",
    "RELIANCE INDUSTRIES LIMITED",
    "MAHINDRA AND MAHINDRA LIMITED",
    "HCL TECHNOLOGIES LIMITED",
    "BAJAJ FINSERV LIMITED",
    "LARSEN AND TOUBRO LIMITED",
    "BUREAUID INDIA PRIVATE LIMITED",
    "SIEMENS INDIA LIMITED",
    "CARBON TECHNOLOGIES PRIVATE LIMITED",
]


def _letters(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))


def _digits(n: int, rng: random.Random) -> str:
    return "".join(rng.choice(string.digits) for _ in range(n))


def generate_pan(last_name: str, rng: random.Random) -> str:
    """
    Generate a PAN resembling real Indian format: AAAAA9999A

    Position 4 is 'P' (Person/Individual).
    Position 5 is first letter of surname (common convention).
    """
    surname_initial = (last_name[0].upper() if last_name else rng.choice(string.ascii_uppercase))
    return (
        f"{_letters(3, rng)}"
        f"P"
        f"{surname_initial}"
        f"{_digits(4, rng)}"
        f"{rng.choice(string.ascii_uppercase)}"
    )


def generate_indian_mobile(rng: random.Random) -> str:
    """10-digit Indian mobile starting with 6–9."""
    first = rng.choice("6789")
    return first + _digits(9, rng)


def unique_mobile(rng: random.Random, used: Iterable[str]) -> str:
    used_set = set(used)
    for _ in range(5000):
        mobile = generate_indian_mobile(rng)
        if mobile not in used_set:
            return mobile
    raise RuntimeError("Could not generate unique mobile after 5000 attempts")


def unique_email(
    first: str,
    last: str,
    rng: random.Random,
    used: Iterable[str],
    *,
    seq: int | None = None,
) -> str:
    used_set = set(used)
    for attempt in range(5000):
        suffix = seq if seq is not None else rng.randint(1, 99999)
        if attempt > 0:
            suffix = f"{suffix}{attempt}"
        local = f"{first.lower()}.{last.lower()}.{suffix}"
        email = f"{local}@gmail.com"
        if email not in used_set:
            return email
    raise RuntimeError("Could not generate unique email after 5000 attempts")


def unique_customer_id(rng: random.Random, used: Iterable[str]) -> str:
    used_set = set(used)
    for _ in range(5000):
        cid = str(rng.randint(10000, 99999999))
        if cid not in used_set:
            return cid
    raise RuntimeError("Could not generate unique customerId after 5000 attempts")


def pick_location(rng: random.Random) -> dict[str, str]:
    loc = rng.choice(INDIAN_LOCATIONS)
    return dict(loc)


def pick_indian_name(rng: random.Random, gender: str) -> tuple[str, str, str]:
    """Returns (firstName, middleName, lastName) in uppercase as per spec samples."""
    if gender == "F":
        first = rng.choice(INDIAN_FIRST_NAMES_FEMALE)
    else:
        first = rng.choice(INDIAN_FIRST_NAMES_MALE)
    last = rng.choice(INDIAN_LAST_NAMES)
    middle = ""
    if rng.random() < 0.25:
        middle = rng.choice(INDIAN_FIRST_NAMES_MALE + INDIAN_FIRST_NAMES_FEMALE)
    return first, middle, last


def unique_pan(
    last_name: str,
    rng: random.Random,
    used: Iterable[str],
) -> str:
    used_set = set(used)
    for _ in range(500):
        pan = generate_pan(last_name, rng)
        if pan not in used_set:
            return pan
    raise RuntimeError("Could not generate unique PAN after 500 attempts")
