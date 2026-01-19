def parse_float(text):
    text = text.strip()
    if text == "":
        return None, True, True
    try:
        value = float(text)
    except ValueError:
        return None, False, False
    if value < 0:
        return None, False, False
    return value, True, False


def parse_int(text):
    text = text.strip()
    if text == "":
        return None, True, True
    try:
        value = int(text)
    except ValueError:
        return None, False, False
    if value < 0:
        return None, False, False
    return value, True, False


def format_float(value):
    return f"{value:.2f}"


FIELD_LABELS = {
    "sub_division": "Sub-Division",
    "account_code": "Account Code",
    "number_of_works": "Number of Works",
    "estimate_amount": "Estimate Amount",
    "agreement_amount": "Agreement Amount",
    "exp_upto_31_03_2025": "Expenditure up to 31-03-2025",
    "exp_upto_last_month": "Expenditure up to Last Month",
    "exp_during_this_month": "Expenditure During This Month",
    "works_completed": "Number of Works Completed",
}

INT_FIELDS = {
    "number_of_works": "Number of Works",
    "works_completed": "Number of Works Completed",
}

FLOAT_FIELDS = {
    "estimate_amount": "Estimate Amount",
    "agreement_amount": "Agreement Amount",
    "exp_upto_31_03_2025": "Expenditure up to 31-03-2025",
    "exp_upto_last_month": "Expenditure up to Last Month",
    "exp_during_this_month": "Expenditure During This Month",
}


def validate_values(values):
    errors = {}

    sub_division = (values.get("sub_division") or "").strip()
    account_code = (values.get("account_code") or "").strip()

    if not sub_division:
        errors["sub_division"] = "Sub-Division is required."
    if account_code not in ("Spill", "New"):
        errors["account_code"] = "Account Code is required."

    parsed_ints = {}
    for key, label in INT_FIELDS.items():
        text = values.get(key, "")
        value, ok, empty = parse_int(str(text))
        if empty:
            errors[key] = f"{label} is required."
            continue
        if not ok:
            errors[key] = f"{label} must be a non-negative integer."
            continue
        parsed_ints[key] = value

    parsed_floats = {}
    for key, label in FLOAT_FIELDS.items():
        text = values.get(key, "")
        value, ok, empty = parse_float(str(text))
        if empty:
            errors[key] = f"{label} is required."
            continue
        if not ok:
            errors[key] = f"{label} must be a non-negative number."
            continue
        parsed_floats[key] = value

    works = parsed_ints.get("number_of_works")
    completed = parsed_ints.get("works_completed")
    if works is not None and completed is not None and completed > works:
        errors["works_completed"] = "Number of Works Completed cannot exceed Number of Works."

    agreement = parsed_floats.get("agreement_amount")
    exp_31 = parsed_floats.get("exp_upto_31_03_2025")
    if agreement is not None and exp_31 is not None and agreement < exp_31:
        errors["exp_upto_31_03_2025"] = (
            "Expenditure up to 31-03-2025 must be <= Agreement Amount."
        )

    return errors
