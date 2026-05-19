from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


INPUT_PDF = "data/raw_forms/Work History Report 3369.pdf"
OUTPUT_PDF = "data/filled_work_history_master.pdf"


def check(value):
    return "/1" if value else "/Off"


def is_selected(value, target):
    return check(value == target)


def add_job_list_fields(pdf_data, jobs):
    for index, job in enumerate(jobs, start=1):
        if index > 10:
            break

        pdf_data[f"form1[0].Page3[0].P3-JobTitle{index}-FLD[0]"] = job.get("title", "")
        pdf_data[f"form1[0].Page3[0].P3-Buiness{index}-FLD[0]"] = job.get("business", "")
        pdf_data[f"form1[0].Page3[0].P3-DatesFrom{index}-FLD[0]"] = job.get("from", "")
        pdf_data[f"form1[0].Page3[0].P3-DatesTo{index}-FLD[0]"] = job.get("to", "")


def add_job_detail_fields(pdf_data, job, job_number):
    detail_pages = {
        1: {
            "page": 4,
            "physical_page": 5,
            "title": "P4-JobTitle1-FLD[0]",
            "rate": "P4-RateofPay-FLD[0]",
            "hours": "P4-HoursperDay-FLD[0]",
            "days": "P4-DaysperWeek-FLD[0]",
            "tasks": "P4-JobOneDetail-FLD[0]",
            "reports": "P4-JobOneReport-FLD[0]",
            "supervise": "P4-JobOneSupervise-FLD[0]",
            "equipment": "P4-JobOneList-FLD[0]",
            "interact_text": "P4-JobOneDescribe-FLD[0]",
            "med": "P5-MedConditions-FLD[0]",
            "activity_prefix": "P5-HowMuch",
        },
        2: {
            "page": 6,
            "physical_page": 7,
            "title": "P6-JobTitle2-FLD[0]",
            "rate": "P6-RateofPay-FLD[0]",
            "hours": "P6-HoursperDay-FLD[0]",
            "days": "P6-DaysperWeek-FLD[0]",
            "tasks": "P6-JobTwoDetail-FLD[0]",
            "reports": "P6-JobTwoReport-FLD[0]",
            "supervise": "P6-JobTwoSupervise-FLD[0]",
            "equipment": "P6-JobTwoList-FLD[0]",
            "interact_text": "P6-JobTwoInteract-FLD[0]",
            "med": "P7-MedConditions-FLD[0]",
            "activity_prefix": "P7-HowMuch",
        },
        3: {
            "page": 8,
            "physical_page": 9,
            "title": "P8-JobTitle3-FLD[0]",
            "rate": "P8-RateofPay-FLD[0]",
            "hours": "P8-HoursperDay-FLD[0]",
            "days": "P8-DaysperWeek-FLD[0]",
            "tasks": "P8-DescribeTasks-FLD[0]",
            "reports": "P8-DescribeReports-FLD[0]",
            "supervise": "P8-DescrbieSupervise-FLD[0]",
            "equipment": "P8-DescribeList-FLD[0]",
            "interact_text": "P8-DescribeWho-FLD[0]",
            "med": "P9-MedConditions-FLD[0]",
            "activity_prefix": "P9-HoursMins",
        },
        4: {
            "page": 10,
            "physical_page": 11,
            "title": "P10-JobTitle4-FLD[0]",
            "rate": "P10-RateofPay-FLD[0]",
            "hours": "P10-HoursperDay-FLD[0]",
            "days": "P10-DaysperWeek-FLD[0]",
            "tasks": "P10-DescribeTasks-FLD[0]",
            "reports": "P10-DescribeReports-FLD[0]",
            "supervise": "P10-DescribeSupervise-FLD[0]",
            "equipment": "P10-DescribeEquipment-FLD[0]",
            "interact_text": "P10-DescribeInteract-FLD[0]",
            "med": "P11-MedConditions-FLD[0]",
            "activity_prefix": "P11-HoursMins",
        },
        5: {
            "page": 12,
            "physical_page": 13,
            "title": "P12-JobTitle5-FLD[0]",
            "rate": "P12-RateofPay-CB[0]",
            "hours": "P12-HoursperDay-CB[0]",
            "days": "P12-DaysperWeek-CB[0]",
            "tasks": "P12-DescribeTasks-FLD[0]",
            "reports": "P12-DescribeReports-FLD[0]",
            "supervise": "P12-DescribeSupervise-FLD[0]",
            "equipment": "P12-DescribeEquipment-FLD[0]",
            "interact_text": "P12-DescribeInteract-FLD[0]",
            "med": "P13-MedConditions-FLD[0]",
            "activity_prefix": "P13-HoursMins",
        },
    }

    config = detail_pages[job_number]
    page = config["page"]
    physical_page = config["physical_page"]

    base = f"form1[0].Page{page}[0]"
    physical_base = f"form1[0].Page{physical_page}[0]"

    pdf_data[f"{base}.{config['title']}"] = job.get("title", "")
    pdf_data[f"{base}.{config['rate']}"] = job.get("rate_of_pay", "")
    pdf_data[f"{base}.{config['hours']}"] = job.get("hours_per_day", "")
    pdf_data[f"{base}.{config['days']}"] = job.get("days_per_week", "")

    pay_type = job.get("pay_type", "hour")

    pdf_data[f"{base}.P{page}-Hour-CB[0]"] = is_selected(pay_type, "hour")
    pdf_data[f"{base}.P{page}-Day-CB[0]"] = is_selected(pay_type, "day")
    pdf_data[f"{base}.P{page}-Week-CB[0]"] = is_selected(pay_type, "week")
    pdf_data[f"{base}.P{page}-Month-CB[0]"] = is_selected(pay_type, "month")
    pdf_data[f"{base}.P{page}-Year-CB[0]"] = is_selected(pay_type, "year")

    pdf_data[f"{base}.{config['tasks']}"] = job.get("tasks", "")
    pdf_data[f"{base}.{config['reports']}"] = job.get("reports", "")
    pdf_data[f"{base}.{config['supervise']}"] = job.get("supervise", "")
    pdf_data[f"{base}.{config['equipment']}"] = job.get("equipment", "")
    pdf_data[f"{base}.{config['interact_text']}"] = job.get("interact", "")

    interacted = job.get("interacted_with_people", False)
    pdf_data[f"{base}.P{page}-InteractYes-CB[0]"] = "/1" if interacted else "/Off"
    pdf_data[f"{base}.P{page}-InteractNo-CB[0]"] = "/1" if not interacted else "/Off"

    physical = job.get("physical_activities", {})

    activity_order = [
        "standing_walking",
        "sitting",
        "stooping",
        "kneeling",
        "crouching",
        "crawling",
        "fingers_time",
        "grasping_time",
        "reaching_below_time",
        "reaching_overhead_time",
        "stairs",
        "ladders",
    ]

    for i, key in enumerate(activity_order, start=1):
        pdf_data[f"{physical_base}.{config['activity_prefix']}{i}-FLD[0]"] = physical.get(key, "")

    pdf_data[f"{physical_base}.P{physical_page}-OneHand1-CB[0]"] = check(physical.get("fingers_one_hand", False))
    pdf_data[f"{physical_base}.P{physical_page}-BothHands1-CB[0]"] = check(physical.get("fingers_both_hands", False))

    pdf_data[f"{physical_base}.P{physical_page}-OneHand2-CB[0]"] = check(physical.get("grasping_one_hand", False))
    pdf_data[f"{physical_base}.P{physical_page}-BothHands2-CB[0]"] = check(physical.get("grasping_both_hands", False))

    pdf_data[f"{physical_base}.P{physical_page}-OneArm1-CB[0]"] = check(physical.get("reaching_below_one_arm", False))
    pdf_data[f"{physical_base}.P{physical_page}-BothArms1-CB[0]"] = check(physical.get("reaching_below_both_arms", False))

    pdf_data[f"{physical_base}.P{physical_page}-OneArm2-CB[0]"] = check(physical.get("reaching_overhead_one_arm", False))
    pdf_data[f"{physical_base}.P{physical_page}-BothArms2-CB[0]"] = check(physical.get("reaching_overhead_both_arms", False))

    lift_description = job.get("lifting_description", "")

    if physical_page == 5:
        pdf_data[f"{physical_base}.P5-ExplainLift-FLD[0]"] = lift_description
    elif physical_page == 7:
        pdf_data[f"{physical_base}.P7-ExplainLift-FLD[0]"] = lift_description
    elif physical_page == 9:
        pdf_data[f"{physical_base}.P9-ExplainLIft-FLD[0]"] = lift_description
    elif physical_page in [11, 13]:
        pdf_data[f"{physical_base}.P{physical_page}-DescribeLift-FLD[0]"] = lift_description

    heaviest = job.get("heaviest_lift", "")
    frequent = job.get("frequent_lift", "")

    if physical_page == 5:
        pdf_data[f"{physical_base}.P5-LessThan1-CB[0]"] = is_selected(heaviest, "less_than_1")
        pdf_data[f"{physical_base}.P5-LessThan10-CB[0]"] = is_selected(heaviest, "less_than_10")
        pdf_data[f"{physical_base}.P5-10pounds-CB[0]"] = is_selected(heaviest, "10")
        pdf_data[f"{physical_base}.P5-20pounds-CB[0]"] = is_selected(heaviest, "20")
        pdf_data[f"{physical_base}.P5-50pounds-CB[0]"] = is_selected(heaviest, "50")
        pdf_data[f"{physical_base}.P5-100orMore-CB[0]"] = is_selected(heaviest, "100_or_more")
        pdf_data[f"{physical_base}.P5-Other1-CB[0]"] = is_selected(heaviest, "other")

    elif physical_page == 7:
        pdf_data[f"{physical_base}.P7-LessThan1-CB[0]"] = is_selected(heaviest, "less_than_1")
        pdf_data[f"{physical_base}.P7-LessThan10-CB[0]"] = is_selected(heaviest, "less_than_10")
        pdf_data[f"{physical_base}.P7-10Pounds-CB[0]"] = is_selected(heaviest, "10")
        pdf_data[f"{physical_base}.P7-20Pounds-CB[0]"] = is_selected(heaviest, "20")
        pdf_data[f"{physical_base}.P7-50Pounds-CB[0]"] = is_selected(heaviest, "50")
        pdf_data[f"{physical_base}.P7-100orMore-CB[0]"] = is_selected(heaviest, "100_or_more")
        pdf_data[f"{physical_base}.P7-Other1-CB[0]"] = is_selected(heaviest, "other")

    else:
        for n, option in enumerate(
            ["less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"],
            start=1,
        ):
            pdf_data[f"{physical_base}.P{physical_page}-HeaviestLift{n}-CB[0]"] = is_selected(heaviest, option)

    for n, option in enumerate(
        ["less_than_1", "less_than_10", "10", "25", "50_or_more", "other"],
        start=1,
    ):
        pdf_data[f"{physical_base}.P{physical_page}-Freq{n}-CB[0]"] = is_selected(frequent, option)

    exposures = job.get("exposures", {})

    exposure_order = [
        "outdoors",
        "heat",
        "cold",
        "wetness",
        "humidity",
        "hazardous_substances",
        "moving_parts",
        "heights",
        "vibrations",
        "loud_noise",
        "other",
    ]

    for n, key in enumerate(exposure_order, start=1):
        pdf_data[f"{physical_base}.P{physical_page}-Exposure{n}-CB[0]"] = check(exposures.get(key, False))

    other_lift_text = job.get("other_lift_text", "")
    other_frequent_text = job.get("other_frequent_lift_text", "")
    other_exposure_text = job.get("other_exposure_text", "")
    exposure_description = job.get("exposure_description", "")

    if physical_page in [5, 7, 9, 13]:
        pdf_data[f"{physical_base}.P{physical_page}-ExplainOther1-FLD[0]"] = other_lift_text
        pdf_data[f"{physical_base}.P{physical_page}-ExplainOther2-FLD[0]"] = other_frequent_text
        pdf_data[f"{physical_base}.P{physical_page}-ExplainOther3-FLD[0]"] = other_exposure_text

    if physical_page == 5:
        pdf_data[f"{physical_base}.P5-JobExposure2-FLD[0]"] = exposure_description
    else:
        pdf_data[f"{physical_base}.P{physical_page}-ExplainExposure-FLD[0]"] = exposure_description

    pdf_data[f"{physical_base}.{config['med']}"] = job.get("medical_conditions", "")


def generate_work_history_pdf(client_data, jobs, completed_by=None, output_pdf=OUTPUT_PDF):
    if completed_by is None:
        completed_by = {}

    pdf_data = {
        "form1[0].Page3[0].P3-Sec1AName-FLD[0]": client_data.get("name", ""),
        "form1[0].Page3[0].P3-Sec1BSSN-FLD[0]": client_data.get("ssn", ""),
        "form1[0].Page3[0].P3-Sec1CPrim-FLD[0]": client_data.get("primary_phone", ""),
        "form1[0].Page3[0].P3-Sec1CSec-FLD[0]": client_data.get("secondary_phone", ""),

        "form1[0].Page14[0].P14-Remarks-FLD[0]": completed_by.get("remarks", ""),
        "form1[0].Page14[0].P14-ReportComp-FLD[0]": completed_by.get("date_completed", ""),
        "form1[0].Page14[0].P14-WhoComplete1-CB[0]": check(completed_by.get("completed_by_claimant", True)),
        "form1[0].Page14[0].P14-WhoComplete2-CB[0]": check(not completed_by.get("completed_by_claimant", True)),
        "form1[0].Page14[0].P14-Name-FLD[0]": completed_by.get("name", ""),
        "form1[0].Page14[0].P14-Relation-FLD[0]": completed_by.get("relationship", ""),
        "form1[0].Page14[0].P14-MailAdd-FLD[0]": completed_by.get("mailing_address", ""),
        "form1[0].Page14[0].P14-City-FLD[0]": completed_by.get("city", ""),
        "form1[0].Page14[0].P14-State-FLD[0]": completed_by.get("state", ""),
        "form1[0].Page14[0].P14-ZIP-FLD[0]": completed_by.get("zip", ""),
        "form1[0].Page14[0].P14-Country-FLD[0]": completed_by.get("country", ""),
        "form1[0].Page14[0].P14-Phone-FLD[0]": completed_by.get("phone", ""),
    }

    add_job_list_fields(pdf_data, jobs)

    for job_number, job in enumerate(jobs[:5], start=1):
        add_job_detail_fields(pdf_data, job, job_number)

    reader = PdfReader(INPUT_PDF)

    if reader.is_encrypted:
        reader.decrypt("")

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    for page in writer.pages:
        writer.update_page_form_field_values(page, pdf_data)

    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)

    return output_pdf


if __name__ == "__main__":
    test_client_data = {
        "name": "John Doe",
        "ssn": "123-45-6789",
        "primary_phone": "555-123-4567",
        "secondary_phone": "",
    }

    test_jobs = [
        {
            "title": "Warehouse Worker",
            "business": "Warehouse / Shipping",
            "from": "01/2020",
            "to": "06/2023",
            "rate_of_pay": "18.50",
            "pay_type": "hour",
            "hours_per_day": "8",
            "days_per_week": "5",
            "tasks": "Loaded trucks, lifted boxes, moved pallets, scanned inventory, and prepared shipments.",
            "reports": "Reported to a warehouse supervisor.",
            "supervise": "No supervisory duties.",
            "equipment": "Used pallet jack, scanner, carts, and warehouse shelving.",
            "interacted_with_people": True,
            "interact": "Interacted with coworkers and supervisors daily.",
            "physical_activities": {
                "standing_walking": "6 hours",
                "sitting": "2 hours",
                "stooping": "30 minutes",
                "kneeling": "15 minutes",
                "crouching": "15 minutes",
                "crawling": "None",
                "fingers_time": "2 hours",
                "fingers_both_hands": True,
                "grasping_time": "4 hours",
                "grasping_both_hands": True,
                "reaching_below_time": "3 hours",
                "reaching_below_both_arms": True,
                "reaching_overhead_time": "30 minutes",
                "reaching_overhead_both_arms": True,
                "stairs": "30 minutes",
                "ladders": "None",
            },
            "lifting_description": "Lifted boxes, moved packages, and carried items across the warehouse throughout the shift.",
            "heaviest_lift": "50",
            "frequent_lift": "25",
            "exposures": {
                "outdoors": False,
                "heat": False,
                "cold": False,
                "wetness": False,
                "humidity": False,
                "hazardous_substances": False,
                "moving_parts": True,
                "heights": False,
                "vibrations": True,
                "loud_noise": True,
                "other": False,
            },
            "exposure_description": "Exposed to moving warehouse equipment, loud noise, and vibration from machinery.",
            "medical_conditions": "Back pain and anxiety would make lifting, standing, and working around loud equipment difficult.",
        }
    ]

    test_completed_by = {
        "remarks": "This is a test completed from the master PDF generator.",
        "date_completed": "05/14/2026",
        "completed_by_claimant": True,
        "name": "",
        "relationship": "",
        "mailing_address": "",
        "city": "",
        "state": "",
        "zip": "",
        "country": "",
        "phone": "",
    }

    output = generate_work_history_pdf(test_client_data, test_jobs, test_completed_by)
    print("Master PDF generated successfully.")
    print("Saved to:", output)

def fill_work_history_pdf(case_data, output_pdf):

    raw_jobs = case_data.get("jobs", [])

    filtered_jobs = []

    for job in raw_jobs:
        has_data = any([
            job.get("job_title"),
            job.get("employer"),
            job.get("job_duties"),
            job.get("pay_rate"),
        ])

        if has_data:
            filtered_jobs.append(job)

    raw_jobs = filtered_jobs

    client_data = {
        "name": case_data.get("client_name", ""),
        "ssn": case_data.get("ssn", ""),
        "primary_phone": case_data.get("primary_phone", ""),
        "secondary_phone": case_data.get("secondary_phone", ""),
    }

    jobs = []

    for job in raw_jobs:
        converted_job = {
            "title": job.get("title") or job.get("job_title", ""),
            "business": job.get("business") or job.get("employer", ""),
            "from": job.get("from") or job.get("dates_from", ""),
            "to": job.get("to") or job.get("dates_to", ""),
            "rate_of_pay": job.get("rate_of_pay") or job.get("pay_rate", ""),
            "pay_type": job.get("pay_type", "hour"),
            "hours_per_day": job.get("hours_per_day", ""),
            "days_per_week": job.get("days_per_week", ""),
            "tasks": job.get("tasks") or job.get("job_duties", ""),
            "reports": job.get("reports", ""),
            "supervise": job.get("supervise", ""),
            "equipment": job.get("equipment") or job.get("used_machines_tools", ""),
            "interacted_with_people": (
                job.get("interacted_with_people") == "Yes"
                or job.get("interacted_with_people") is True
            ),
            "physical_activities": job.get("physical_activities", {}),
            "lifting_description": job.get("lifting_description") or job.get("lifting", ""),
            "heaviest_lift": job.get("heaviest_lift", ""),
            "frequent_lift": job.get("frequent_lift", ""),
            "exposures": job.get("exposures", {}),
            "exposure_description": job.get("exposure_description", ""),
            "medical_conditions": job.get("medical_conditions", ""),
        }

        jobs.append(converted_job)

    completed_by = {
        "remarks": case_data.get("remarks", ""),
        "date_completed": case_data.get("date_completed", ""),
        "completed_by_claimant": True,
    }

    return generate_work_history_pdf(
        client_data=client_data,
        jobs=jobs,
        completed_by=completed_by,
        output_pdf=output_pdf
    )