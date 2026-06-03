import re
import pandas as pd


def load_validation_rules(file_path="data/validation_rules.xlsx"):
    sheets = pd.read_excel(file_path, sheet_name=None)

    for sheet_name, df in sheets.items():
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        if "validation_id" in df.columns:
            return df

    raise ValueError("Could not find a sheet with a validation_id column.")


def clean_answer(answer):
    return str(answer or "").strip().lower()


def is_too_short(answer):
    answer = clean_answer(answer)
    words = answer.split()

    if len(answer) < 8:
        return True

    if len(words) < 3:
        return True

    return False


def is_random_or_junk(answer):
    answer = clean_answer(answer)

    if not answer:
        return True

    if re.fullmatch(r"[a-zA-Z]{1,3}", answer):
        return True

    if re.fullmatch(r"[^a-zA-Z0-9]+", answer):
        return True

    return False


def has_likely_typo_or_unclear_text(answer):
    answer = clean_answer(answer)

    suspicious_fragments = [
        "csh register",
        "rgister",
        "regster",
        "cas register",
        "idk",
        "dk",
        "n/a n/a",
    ]

    return any(fragment in answer for fragment in suspicious_fragments)


def answer_has_number(answer):
    return bool(re.search(r"\d+", clean_answer(answer)))


def answer_has_time_or_frequency(answer):
    answer = clean_answer(answer)

    time_words = [
        "hour", "hours", "minute", "minutes",
        "per day", "per shift", "per week",
        "daily", "weekly", "throughout",
        "all day", "most of the day", "half the day",
        "occasionally", "constantly"
    ]

    return answer_has_number(answer) or any(word in answer for word in time_words)


def answer_has_weight(answer):
    answer = clean_answer(answer)
    weight_words = ["lb", "lbs", "pound", "pounds", "kg"]

    return answer_has_number(answer) and any(word in answer for word in weight_words)


def answer_has_clear_task(answer):
    answer = clean_answer(answer)

    task_words = [
        "answered", "assisted", "cleaned", "completed",
        "prepared", "stocked", "scheduled", "filed",
        "typed", "entered", "reviewed", "organized",
        "supervised", "trained", "managed", "helped",
        "operated", "lifted", "carried", "moved",
        "scanned", "called", "greeted", "served",
        "processed", "documented", "monitored"
    ]

    return any(word in answer for word in task_words)


def answer_has_object_person_or_system(answer):
    answer = clean_answer(answer)

    object_words = [
        "customer", "customers", "coworker", "coworkers",
        "supervisor", "staff", "client", "clients",
        "patient", "patients", "public", "manager",
        "computer", "phone", "register", "cash register",
        "scanner", "paperwork", "reports", "files",
        "boxes", "inventory", "orders", "supplies",
        "equipment", "tools", "machines"
    ]

    return any(word in answer for word in object_words)


def score_job_duties(answer):
    score = 0

    if answer_has_clear_task(answer):
        score += 1

    if answer_has_object_person_or_system(answer):
        score += 1

    if answer_has_time_or_frequency(answer):
        score += 1

    if len(clean_answer(answer).split()) >= 10:
        score += 1

    return score


def score_tools(answer):
    score = 0

    if is_too_short(answer):
        return 0

    if answer_has_object_person_or_system(answer):
        score += 1

    if "used" in clean_answer(answer) or "operated" in clean_answer(answer):
        score += 1

    if answer_has_time_or_frequency(answer):
        score += 1

    return score


def score_general_answer(answer, required_categories):
    score = 0
    required_categories = str(required_categories).lower()

    if "task" in required_categories and answer_has_clear_task(answer):
        score += 1

    if (
        "object" in required_categories
        or "person" in required_categories
        or "system" in required_categories
    ) and answer_has_object_person_or_system(answer):
        score += 1

    if (
        "frequency" in required_categories
        or "time" in required_categories
        or "duration" in required_categories
    ) and answer_has_time_or_frequency(answer):
        score += 1

    if "weight" in required_categories and answer_has_weight(answer):
        score += 1

    return score


def validate_answer(answer, rule):
    answer = clean_answer(answer)
    validation_id = str(rule.get("validation_id", ""))

    if is_random_or_junk(answer):
        return {
            "score": 0,
            "minimum_score": int(rule.get("minimum_detail_score", 1)),
            "is_sufficient": False,
            "reason": "Answer appears blank, random, or incomplete."
        }

    if is_too_short(answer):
        return {
            "score": 0,
            "minimum_score": int(rule.get("minimum_detail_score", 1)),
            "is_sufficient": False,
            "reason": "Answer is too short to confirm enough detail."
        }

    if has_likely_typo_or_unclear_text(answer):
        return {
            "score": 0,
            "minimum_score": int(rule.get("minimum_detail_score", 1)),
            "is_sufficient": False,
            "reason": "Answer may contain unclear wording or spelling errors."
        }

    try:
        minimum_score = int(rule.get("minimum_detail_score", 1))
    except:
        minimum_score = 1

    required_categories = rule.get(
        "universal_detail_categories",
        rule.get("required_detail_types", "")
    )

    if validation_id == "JOB_DUTIES_DETAIL_001":
        score = score_job_duties(answer)
    elif validation_id == "JOB_DUTIES_TOOLS_002":
        score = score_tools(answer)
    else:
        score = score_general_answer(answer, required_categories)

    return {
        "score": score,
        "minimum_score": minimum_score,
        "is_sufficient": score >= minimum_score,
        "reason": ""
    }


if __name__ == "__main__":
    rules = load_validation_rules()
    print(rules.columns)
    print(rules.head())