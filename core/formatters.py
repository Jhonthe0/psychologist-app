import re


def only_digits(value):
    return re.sub(r"\D", "", str(value or ""))


def format_cpf(value):
    digits = only_digits(value)
    if len(digits) != 11:
        return value
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def format_phone(value):
    digits = only_digits(value)
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    return value
