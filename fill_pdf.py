import os
import subprocess
import tempfile

INPUT_PDF = "data/raw_forms/Work History Report 3369.pdf"


# =========================================================
# DDS AI APP - STABLE fill_pdf.py
# =========================================================
# This file only does one job:
# clean case_data  ->  PDF field_values  ->  filled PDF
#
# Important fixes:
# - Job 1 interaction checkbox uses export values YES=10, NO=20.
# - Later job interaction checkboxes usually use YES=1, NO=1.
# - Keeps each job mapped to its own pages.
# - Adds fallback field names for later pages without breaking existing pages.
# =========================================================


def escape_fdf(value):
    value = "" if value is None else str(value)

    # Remove characters FDF/PDF cannot safely write
    value = value.encode("latin-1", errors="replace").decode("latin-1")

    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )

def make_fdf(field_values):
    lines = [
        "%FDF-1.2",
        "1 0 obj",
        "<<",
        "/FDF << /Fields [",
    ]

    for name, value in field_values.items():
        lines.append(f"<< /T ({escape_fdf(name)}) /V ({escape_fdf(value)}) >>")

    lines += [
        "] >>",
        ">>",
        "endobj",
        "trailer",
        "<< /Root 1 0 R >>",
        "%%EOF",
    ]

    return "\n".join(lines)


def add(field_values, field_name, value):
    field_values[field_name] = "" if value is None else str(value)


def add_checkbox(field_values, field_name, checked, on_value="1"):
    field_values[field_name] = on_value if checked else "Off"


def add_checkbox_aliases(field_values, field_names, checked, on_value="1"):
    """
    Adds the same checkbox value to multiple possible field names.
    This is safe with pdftk. If a field name does not exist in the PDF,
    pdftk ignores it.
    """
    for field_name in field_names:
        add_checkbox(field_values, field_name, checked, on_value)


def get_job(jobs, index):
    return jobs[index] if index < len(jobs) else {}


def is_yes(value):
    return str(value or "").strip().lower() == "yes"


def normalize_lift_value(value):
    """
    Keeps app values stable.

    App should send:
    less_than_1, less_than_10, 10, 20, 50, 100_or_more, other
    """
    text = str(value or "").strip().lower()

    mapping = {
        "less than 1": "less_than_1",
        "less than 1 lb": "less_than_1",
        "less than 1 lb.": "less_than_1",
        "less than 10": "less_than_10",
        "less than 10 lbs": "less_than_10",
        "less than 10 lbs.": "less_than_10",
        "10 lbs": "10",
        "10 lbs.": "10",
        "10 pounds": "10",
        "20 lbs": "20",
        "20 lbs.": "20",
        "20 pounds": "20",
        "50 lbs": "50",
        "50 lbs.": "50",
        "50 pounds": "50",
        "100 lbs": "100_or_more",
        "100 lbs.": "100_or_more",
        "100 pounds": "100_or_more",
        "100 or more": "100_or_more",
    }

    return mapping.get(text, text)


def add_interaction_checkboxes(field_values, page_num, interacted):
    """
    Interaction checkbox export values are different by page.

    Confirmed from pdftk:
    Page 4 / Job 1:
        YES = 10
        NO = 20

    Page 6 / Job 2:
        YES = 1
        NO = 1
    """

    yes_field = f"form1[0].Page{page_num}[0].P{page_num}-InteractYes-CB[0]"
    no_field = f"form1[0].Page{page_num}[0].P{page_num}-InteractNo-CB[0]"

    if page_num == 4:
        yes_value = "10"
        no_value = "20"
    else:
        yes_value = "1"
        no_value = "1"

    if interacted:
        field_values[yes_field] = yes_value
        field_values[no_field] = "Off"
    else:
        field_values[yes_field] = "Off"
        field_values[no_field] = no_value


def fill_detail_page(field_values, job, page_num, job_num):
    """
    Fills detailed job pages:
    Job 1 = Page 4
    Job 2 = Page 6
    Job 3 = Page 8
    Job 4 = Page 10
    Job 5 = Page 12
    """

    prefix = f"P{page_num}"

    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-JobTitle{job_num}-FLD[0]", job.get("job_title", ""))
    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-RateofPay-FLD[0]", job.get("pay_rate", ""))
    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-HoursperDay-FLD[0]", job.get("hours_per_day", ""))
    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-DaysperWeek-FLD[0]", job.get("days_per_week", ""))

    pay_type = job.get("pay_type", "hour")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Hour-CB[0]", pay_type == "hour")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Day-CB[0]", pay_type == "day")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Week-CB[0]", pay_type == "week")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Month-CB[0]", pay_type == "month")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Year-CB[0]", pay_type == "year")

    job_word = {
        1: "One",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
    }.get(job_num, "One")

    # Exact expected names first, fallbacks after.
    detail_candidates = [
        f"{prefix}-Job{job_word}Detail-FLD",
        f"{prefix}-DescribeTasks-FLD",
    ]

    report_candidates = [
        f"{prefix}-Job{job_word}Report-FLD",
        f"{prefix}-DescribeReports-FLD",
    ]

    supervise_candidates = [
        f"{prefix}-Job{job_word}Supervise-FLD",
        f"{prefix}-DescrbieSupervise-FLD",
        f"{prefix}-DescribeSupervise-FLD",
    ]

    equipment_candidates = [
        f"{prefix}-Job{job_word}List-FLD",
        f"{prefix}-DescribeList-FLD",
        f"{prefix}-DescribeEquipment-FLD",
    ]

    interaction_candidates = [
        f"{prefix}-Job{job_word}Describe-FLD",
        f"{prefix}-Job{job_word}Interact-FLD",
        f"{prefix}-DescribeWho-FLD",
        f"{prefix}-DescribeInteract-FLD",
    ]

    for field in detail_candidates:
        add(field_values, f"form1[0].Page{page_num}[0].{field}[0]", job.get("job_duties", ""))

    for field in report_candidates:
        add(field_values, f"form1[0].Page{page_num}[0].{field}[0]", job.get("reports", ""))

    for field in supervise_candidates:
        add(field_values, f"form1[0].Page{page_num}[0].{field}[0]", job.get("supervise", ""))

    for field in equipment_candidates:
        add(field_values, f"form1[0].Page{page_num}[0].{field}[0]", job.get("equipment", ""))

    interacted = is_yes(job.get("interacted_with_people"))
    add_interaction_checkboxes(field_values, page_num, interacted)

    interaction_text = job.get("interaction_details", "") or job.get("interaction_description", "")

    for field in interaction_candidates:
        add(field_values, f"form1[0].Page{page_num}[0].{field}[0]", interaction_text)


def fill_physical_page(field_values, job, page_num):
    """
    Fills physical activity pages:
    Job 1 = Page 5
    Job 2 = Page 7
    Job 3 = Page 9
    Job 4 = Page 11
    Job 5 = Page 13
    """

    prefix = f"P{page_num}"
    physical = job.get("physical_activities", {}) or {}
    exposures = job.get("exposures", {}) or {}

    physical_fields = [
        ("HowMuch1-FLD", "standing_walking"),
        ("HowMuch2-FLD", "sitting"),
        ("HowMuch3-FLD", "stooping"),
        ("HowMuch4-FLD", "kneeling"),
        ("HowMuch5-FLD", "crouching"),
        ("HowMuch6-FLD", "crawling"),
        ("HowMuch7-FLD", "fingers_time"),
        ("HowMuch8-FLD", "grasping_time"),
        ("HowMuch9-FLD", "reaching_below_time"),
        ("HowMuch10-FLD", "reaching_overhead_time"),
        ("HowMuch11-FLD", "stairs"),
        ("HowMuch12-FLD", "ladders"),

        # Fallback names for some later pages.
        ("HoursMins1-FLD", "standing_walking"),
        ("HoursMins2-FLD", "sitting"),
        ("HoursMins3-FLD", "stooping"),
        ("HoursMins4-FLD", "kneeling"),
        ("HoursMins5-FLD", "crouching"),
        ("HoursMins6-FLD", "crawling"),
        ("HoursMins7-FLD", "fingers_time"),
        ("HoursMins8-FLD", "grasping_time"),
        ("HoursMins9-FLD", "reaching_below_time"),
        ("HoursMins10-FLD", "reaching_overhead_time"),
        ("HoursMins11-FLD", "stairs"),
        ("HoursMins12-FLD", "ladders"),
    ]

    for pdf_suffix, data_key in physical_fields:
        add(
            field_values,
            f"form1[0].Page{page_num}[0].{prefix}-{pdf_suffix}[0]",
            physical.get(data_key, "")
        )

    # Hand / arm usage checkboxes.
    fingers_usage = physical.get("fingers_hand_usage", "None")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-OneHand1-CB[0]", fingers_usage == "One Hand")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-BothHands1-CB[0]", fingers_usage == "Both Hands")

    grasping_usage = physical.get("grasping_hand_usage", "None")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-OneHand2-CB[0]", grasping_usage == "One Hand")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-BothHands2-CB[0]", grasping_usage == "Both Hands")

    below_usage = physical.get("reaching_below_arm_usage", "None")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-OneArm1-CB[0]", below_usage == "One Arm")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-BothArms1-CB[0]", below_usage == "Both Arms")

    overhead_usage = physical.get("reaching_overhead_arm_usage", "None")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-OneArm2-CB[0]", overhead_usage == "One Arm")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-BothArms2-CB[0]", overhead_usage == "Both Arms")

    # Lifting description text.
    for lift_field in [
        f"{prefix}-ExplainLift-FLD",
        f"{prefix}-ExplainLIft-FLD",
        f"{prefix}-DescribeLift-FLD",
    ]:
        add(field_values, f"form1[0].Page{page_num}[0].{lift_field}[0]", job.get("lifting_description", ""))

    heaviest = normalize_lift_value(job.get("heaviest_lift", ""))

    # Heaviest lift: exact Page 5 names + fallback numbered names.
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-LessThan1-CB[0]", heaviest == "less_than_1")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-LessThan10-CB[0]", heaviest == "less_than_10")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-10pounds-CB[0]", heaviest == "10")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-20pounds-CB[0]", heaviest == "20")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-50pounds-CB[0]", heaviest == "50")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-100orMore-CB[0]", heaviest == "100_or_more")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Other1-CB[0]", heaviest == "other")

    # Later page fallbacks. These are harmless if the field names do not exist.
    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift1-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift1-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight1-CB[0]",
        ],
        heaviest == "less_than_1",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift2-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift2-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight2-CB[0]",
        ],
        heaviest == "less_than_10",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift3-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift3-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight3-CB[0]",
        ],
        heaviest == "10",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift4-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift4-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight4-CB[0]",
        ],
        heaviest == "20",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift5-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift5-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight5-CB[0]",
        ],
        heaviest == "50",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift6-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift6-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight6-CB[0]",
        ],
        heaviest == "100_or_more",
    )

    add_checkbox_aliases(
        field_values,
        [
            f"form1[0].Page{page_num}[0].{prefix}-HeaviestLift7-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Lift7-CB[0]",
            f"form1[0].Page{page_num}[0].{prefix}-Weight7-CB[0]",
        ],
        heaviest == "other",
    )

    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-ExplainOther1-FLD[0]", job.get("other_lift_text", ""))

    frequent = normalize_lift_value(job.get("frequent_lift", ""))

    # Frequent lift.
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq1-CB[0]", frequent == "less_than_1")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq2-CB[0]", frequent == "less_than_10")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq3-CB[0]", frequent == "10")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq4-CB[0]", frequent == "25")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq5-CB[0]", frequent == "50_or_more")
    add_checkbox(field_values, f"form1[0].Page{page_num}[0].{prefix}-Freq6-CB[0]", frequent == "other")

    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-ExplainOther2-FLD[0]", job.get("other_frequent_lift_text", ""))

    # Environmental exposure checkboxes.
    exposure_map = {
        "outdoors": "Exposure1-CB",
        "heat": "Exposure2-CB",
        "cold": "Exposure3-CB",
        "wetness": "Exposure4-CB",
        "humidity": "Exposure5-CB",
        "hazardous_substances": "Exposure6-CB",
        "moving_parts": "Exposure7-CB",
        "heights": "Exposure8-CB",
        "vibrations": "Exposure9-CB",
        "loud_noise": "Exposure10-CB",
        "other": "Exposure11-CB",
    }

    for key, pdf_suffix in exposure_map.items():
        add_checkbox(
            field_values,
            f"form1[0].Page{page_num}[0].{prefix}-{pdf_suffix}[0]",
            exposures.get(key, False),
        )

    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-ExplainOther3-FLD[0]", job.get("other_exposure_text", ""))

    for exposure_text_field in [
        f"{prefix}-JobExposure2-FLD",
        f"{prefix}-ExplainExposure-FLD",
    ]:
        add(field_values, f"form1[0].Page{page_num}[0].{exposure_text_field}[0]", job.get("exposure_description", ""))

    add(field_values, f"form1[0].Page{page_num}[0].{prefix}-MedConditions-FLD[0]", job.get("medical_conditions", ""))


def fill_work_history_pdf(case_data, output_pdf):
    if not os.path.exists(INPUT_PDF):
        raise FileNotFoundError(f"Could not find input PDF: {INPUT_PDF}")

    jobs = case_data.get("jobs", []) or []
    field_values = {}

    # -----------------------------
    # PAGE 3: Client info + job list
    # -----------------------------
    add(field_values, "form1[0].Page3[0].P3-Sec1AName-FLD[0]", case_data.get("client_name", ""))
    add(field_values, "form1[0].Page3[0].P3-Sec1BSSN-FLD[0]", case_data.get("ssn", ""))
    add(field_values, "form1[0].Page3[0].P3-Sec1CPrim-FLD[0]", case_data.get("primary_phone", ""))
    add(field_values, "form1[0].Page3[0].P3-Sec1CSec-FLD[0]", case_data.get("secondary_phone", ""))

    for idx in range(10):
        job = get_job(jobs, idx)
        n = idx + 1
        add(field_values, f"form1[0].Page3[0].P3-JobTitle{n}-FLD[0]", job.get("job_title", ""))
        add(field_values, f"form1[0].Page3[0].P3-Buiness{n}-FLD[0]", job.get("employer", ""))
        add(field_values, f"form1[0].Page3[0].P3-DatesFrom{n}-FLD[0]", job.get("dates_from", ""))
        add(field_values, f"form1[0].Page3[0].P3-DatesTo{n}-FLD[0]", job.get("dates_to", ""))

    # -----------------------------
    # DETAIL PAGES FOR JOBS 1-5
    # -----------------------------
    detail_pages = [4, 6, 8, 10, 12]
    physical_pages = [5, 7, 9, 11, 13]

    for idx in range(min(len(jobs), 5)):
        job = jobs[idx]
        job_num = idx + 1
        fill_detail_page(field_values, job, detail_pages[idx], job_num)
        fill_physical_page(field_values, job, physical_pages[idx])

    # -----------------------------
    # PAGE 14: Remarks / completion
    # -----------------------------
    add(field_values, "form1[0].Page14[0].P14-Remarks-FLD[0]", case_data.get("remarks", ""))
    add(field_values, "form1[0].Page14[0].P14-ReportComp-FLD[0]", case_data.get("date_completed", ""))

    completed_by_self = case_data.get("who_completed") == "The person listed in Section 1.A."
    add_checkbox(field_values, "form1[0].Page14[0].P14-WhoComplete1-CB[0]", completed_by_self)
    add_checkbox(field_values, "form1[0].Page14[0].P14-WhoComplete2-CB[0]", not completed_by_self)

    add(field_values, "form1[0].Page14[0].P14-Name-FLD[0]", case_data.get("preparer_name", ""))
    add(field_values, "form1[0].Page14[0].P14-Relation-FLD[0]", case_data.get("preparer_relationship", ""))
    add(field_values, "form1[0].Page14[0].P14-MailAdd-FLD[0]", case_data.get("preparer_address", ""))
    add(field_values, "form1[0].Page14[0].P14-City-FLD[0]", case_data.get("preparer_city", ""))
    add(field_values, "form1[0].Page14[0].P14-State-FLD[0]", case_data.get("preparer_state", ""))
    add(field_values, "form1[0].Page14[0].P14-ZIP-FLD[0]", case_data.get("preparer_zip", ""))
    add(field_values, "form1[0].Page14[0].P14-Country-FLD[0]", case_data.get("preparer_country", ""))
    add(field_values, "form1[0].Page14[0].P14-Phone-FLD[0]", case_data.get("preparer_phone", ""))

    fdf_text = make_fdf(field_values)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".fdf",
        mode="w",
        encoding="latin-1"
    ) as fdf_file:
        fdf_file.write(fdf_text)
        fdf_path = fdf_file.name

    try:
        subprocess.run(
            [
                "pdftk",
                INPUT_PDF,
                "fill_form",
                fdf_path,
                "output",
                output_pdf,
                "need_appearances",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise RuntimeError("pdftk is not installed. Run: brew install pdftk-java")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "pdftk failed.\nSTDOUT:\n"
            + e.stdout
            + "\nSTDERR:\n"
            + e.stderr
        )

    finally:
        try:
            os.remove(fdf_path)
        except OSError:
            pass
