
import json
from datetime import datetime
from pathlib import Path
import streamlit as st
from fill_pdf import fill_work_history_pdf
import os 
from openai import OpenAI
import json
from ai_validation_engine import validate_answer
import re
from function_report_questions import FUNCTION_REPORT_QUESTIONS





st.set_page_config(page_title="DDS AI App", layout="wide")

CASES_FOLDER = Path("cases")
CASES_FOLDER.mkdir(exist_ok=True)

APP_DISCLAIMER = (
    "The assistant helps organize answers for review. "
    "It does not give legal advice, decide eligibility, or submit anything without review."
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai_client = None

if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

def guided_date_picker(label, key_prefix, current_value=""):
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    days = [""] + [str(i) for i in range(1, 32)]
    years = ["", "Present"] + [str(y) for y in range(2026, 1950, -1)]

    saved_month = ""
    saved_day = ""
    saved_year = ""

    current_value = str(current_value or "").strip()

    if current_value.lower() == "present":
        saved_year = "Present"
    elif current_value:
        try:
            parsed = datetime.strptime(current_value, "%B %d, %Y")
            saved_month = parsed.strftime("%B")
            saved_day = str(parsed.day)
            saved_year = str(parsed.year)
        except:
            try:
                parsed = datetime.strptime(current_value, "%B %Y")
                saved_month = parsed.strftime("%B")
                saved_year = str(parsed.year)
            except:
                pass

    col1, col2, col3 = st.columns(3)

    with col1:
        month = st.selectbox(
            "Month",
            months,
            index=safe_index(months, saved_month),
            key=f"{key_prefix}_month"
        )

    with col2:
        day = st.selectbox(
            "Day",
            days,
            index=safe_index(days, saved_day),
            key=f"{key_prefix}_day"
        )

    with col3:
        year = st.selectbox(
            "Year",
            years,
            index=safe_index(years, saved_year),
            key=f"{key_prefix}_year"
        )

    if year == "Present":
        return "Present"

    if month and year:
        return f"{month} {day + ', ' if day else ''}{year}"

    return current_value

def is_acceptable_time_answer(answer):
    if not answer:
        return False

    answer = str(answer).lower().strip()

    accepted_phrases = [
        "most of the day",
        "all day",
        "half the day",
        "half day",
        "part of the day",
        "none",
        "no",
        "unknown",
        "not sure",
        "unsure",
        "rarely",
        "occasionally",
        "most of the time",
        "majority of the day",
        "majority of the time",
        "almost all day",
        "almost all of the day",
        "almost all of the time",
    ]

    if any(phrase in answer for phrase in accepted_phrases):
        return True

    time_words = [
        "hour", "hours", "hr", "hrs",
        "minute", "minutes", "min", "mins"
    ]

    if any(word in answer for word in time_words):
        return True

    # If it's only a number like "30", reject it.
    if re.fullmatch(r"\d+(\.\d+)?", answer):
        return False

    return False

TIME_UNIT_KEYS = {
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
}

def empty_function_report():
    report = {}

    for q in FUNCTION_REPORT_QUESTIONS:
        key = q.get("key")
        q_type = q.get("type")

        if q_type == "multiselect":
            report[key] = []
        elif q_type == "radio":
            options = q.get("options", [])
            report[key] = options[0] if options else ""
        else:
            report[key] = ""

    return report

def empty_job():
    return {
        "job_title": "",
        "employer": "",
        "dates_from": "",
        "dates_to": "",
        "pay_rate": "",
        "pay_type": "hour",
        "hours_per_day": "",
        "days_per_week": "",
        "job_duties": "",
        "reports": "",
        "supervise": "",
        "equipment": "",
        "interacted_with_people": "No",
        "interaction_details": "",
        "physical_activities": {
            "standing_walking": "",
            "sitting": "",
            "stooping": "",
            "kneeling": "",
            "crouching": "",
            "crawling": "",
            "fingers_time": "",
            "fingers_hand_usage": "None",
            "grasping_time": "",
            "grasping_hand_usage": "None",
            "reaching_below_time": "",
            "reaching_below_arm_usage": "None",
            "reaching_overhead_time": "",
            "reaching_overhead_arm_usage": "None",
            "stairs": "",
            "ladders": "",
        },
        "lifting_description": "",
        "heaviest_lift": "",
        "other_lift_text": "",
        "frequent_lift": "",
        "other_frequent_lift_text": "",
        "exposures": {
            "outdoors": False,
            "heat": False,
            "cold": False,
            "wetness": False,
            "humidity": False,
            "hazardous_substances": False,
            "moving_parts": False,
            "heights": False,
            "vibrations": False,
            "loud_noise": False,
            "other": False,
        },
        "other_exposure_text": "",
        "exposure_description": "",
        "medical_conditions": "",
        "extra_notes": "",
    }


def init_session_state():
    defaults = {
        "guided_step": 0,
        "guided_job_number": 1,
        "guided_job": empty_job(),
        "function_report": empty_function_report(),
        "jobs": [],
        "case_memory": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


if "selected_form" not in st.session_state:
    st.session_state.selected_form = None



def is_blank(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, list):
        return len(value) == 0
    return False


def safe_index(options, value, default_index=0):
    return options.index(value) if value in options else default_index


def repair_job(job):
    base = empty_job()
    if not isinstance(job, dict):
        return base

    for key, value in job.items():
        if key not in ["physical_activities", "exposures"]:
            base[key] = value

    if isinstance(job.get("physical_activities"), dict):
        base["physical_activities"].update(job["physical_activities"])

    if isinstance(job.get("exposures"), dict):
        base["exposures"].update(job["exposures"])

    return base


def save_case(jobs, mode_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = CASES_FOLDER / f"work_history_case_{timestamp}.json"
    case_data = {"created_at": datetime.now().isoformat(), "mode": mode_name, "jobs": jobs}

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(case_data, f, indent=2)

    return filename, case_data


def clear_review_dismissals():
    keys_to_delete = [
        key for key in st.session_state.keys()
        if key.endswith("_dismissed")
    ]

    for key in keys_to_delete:
        del st.session_state[key]

def reset_guided_current_job():
    clear_review_dismissals()
    st.session_state.guided_step = 0
    st.session_state.guided_job = empty_job()
    st.session_state.inline_extraction_completed_for_job = False
    st.session_state.duties_extraction_completed_for_job = False


def reset_everything():
    clear_review_dismissals()
    st.session_state.guided_step = 0
    st.session_state.guided_job_number = 1
    st.session_state.guided_job = empty_job()
    st.session_state.jobs = []



GUIDED_QUESTIONS = [
    {"key": "job_title", "target": "job", "icon": "💼", "question": "What was your job title?", "helper": "Example: Warehouse Worker, Cashier, Home Health Aide, Cook, Cleaner.", "type": "text"},
    {"key": "employer", "target": "job", "icon": "🏢", "question": "Who did you work for?", "helper": "Enter the company or employer name. If you do not remember, write your best estimate.", "type": "text"},
    {"key": "dates_from", "target": "job", "icon": "📅", "question": "When did you start this job?", "helper": "Choose the closest start date you remember. An estimate is okay.", "type": "date"},
    {"key": "dates_to", "target": "job", "icon": "📅", "question": "When did this job end?", "helper": "Choose the closest end date. If you still work there, choose Present under Year.", "type": "date"},
    {"key": "pay_rate", "target": "job", "icon": "💰", "question": "How much were you paid?", "helper": "Example: $18 per hour, $2,800 per month, salary, commission, or unknown.", "type": "text"},
    {"key": "pay_type", "target": "job", "icon": "💵", "question": "Was that pay by hour, day, week, month, or year?", "helper": "If the previous question already selected the correct option, you can simply click Next.", "type": "radio", "options": ["hour", "day", "week", "month", "year"]},
    {"key": "hours_per_day", "target": "job", "icon": "⏰", "question": "How many hours did you usually work per day?", "helper": "Enter the average number of hours you worked each day (0–24).", "type": "number", "min": 0, "max": 24},
    {"key": "days_per_week", "target": "job", "icon": "🗓️", "question": "How many days did you usually work per week?", "helper": "Enter the average number of days you worked each week (0–7).", "type": "number", "min": 0, "max": 7},
    {"key": "job_duties", "target": "job", "icon": "📝", "question": "What did you do during a typical workday?", "helper": "Describe the main tasks you did.", "type": "textarea", "check_type": "job_duties"},
    {"key": "reports", "target": "job", "icon": "📄", "question": "Did this job involve writing, reports, forms, or computer work?", "helper": "Write No if it did not. If yes, describe what you completed and about how often.", "type": "textarea", "check_type": "reports"},
    {"key": "supervise", "target": "job", "icon": "👥", "question": "Did you supervise other people?", "helper": "Write No if not. If yes, describe who/how many and what you did.", "type": "textarea", "check_type": "supervise"},
    {"key": "equipment", "target": "job", "icon": "🧰", "question": "What tools, machines, or equipment did you use?", "helper": "Examples: computer, phone, register, scanner, cart, forklift, kitchen tools.", "type": "textarea", "check_type": "equipment"},
    {"key": "interacted_with_people", "target": "job", "icon": "🗣️", "question": "Did this job require interaction with coworkers, customers, the public, supervisors, or anyone else?", "helper": "Choose Yes or No.", "type": "radio", "options": ["No", "Yes"]},
    {"key": "interaction_details", "target": "job", "icon": "💬", "question": "Who did you interact with and why?", "helper": "Include who, why, and how often if you can.", "type": "textarea", "depends_on": {"key": "interacted_with_people", "value": "Yes"}, "check_type": "interaction_details"},

    {"key": "standing_walking", "target": "physical", "icon": "🚶", "question": "How much time did you spend standing or walking each workday?", "helper": "Example: 6 hours, 30 minutes, none, or unknown.", "type": "text"},
    {"key": "sitting", "target": "physical", "icon": "🪑", "question": "How much time did you spend sitting each workday?", "helper": "Example: 1 hour, 30 minutes, none, or unknown.", "type": "text"},
    {"key": "stooping", "target": "physical", "icon": "↘️", "question": "How much time did you spend stooping or bending?", "helper": "Example: 30 minutes per day, none, or unknown.", "type": "text"},
    {"key": "kneeling", "target": "physical", "icon": "🧎", "question": "How much time did you spend kneeling?", "helper": "Example: 15 minutes per day, none, or unknown.", "type": "text"},
    {"key": "crouching", "target": "physical", "icon": "🏃", "question": "How much time did you spend crouching?", "helper": "Example: 10 minutes per day, none, or unknown.", "type": "text"},
    {"key": "crawling", "target": "physical", "icon": "⬇️", "question": "How much time did you spend crawling?", "helper": "Example: none, rarely, 5 minutes per day, or unknown.", "type": "text"},
    {"key": "fingers_time", "target": "physical", "icon": "🤏", "question": "How much time did you use your fingers for typing, picking, pinching, or handling small objects?", "helper": "Example: 2 hours per day, most of the day, none, or unknown.", "type": "text"},
    {"key": "fingers_hand_usage", "target": "physical", "icon": "✋", "question": "For finger use, did you use one hand or both hands?", "helper": "Choose the closest answer.", "type": "radio", "options": ["None", "One Hand", "Both Hands"]},
    {"key": "grasping_time", "target": "physical", "icon": "✊", "question": "How much time did you spend grasping, holding, or turning objects?", "helper": "Example: 3 hours per day, most of the day, none, or unknown.", "type": "text"},
    {"key": "grasping_hand_usage", "target": "physical", "icon": "✋", "question": "For grasping or holding objects, did you use one hand or both hands?", "helper": "Choose the closest answer.", "type": "radio", "options": ["None", "One Hand", "Both Hands"]},
    {"key": "reaching_below_time", "target": "physical", "icon": "↔️", "question": "How much time did you reach at or below shoulder level?", "helper": "Example: 1 hour per day, 30 minutes, none, or unknown.", "type": "text"},
    {"key": "reaching_below_arm_usage", "target": "physical", "icon": "💪", "question": "For reaching at or below shoulder level, did you use one arm or both arms?", "helper": "Choose the closest answer.", "type": "radio", "options": ["None", "One Arm", "Both Arms"]},
    {"key": "reaching_overhead_time", "target": "physical", "icon": "⬆️", "question": "How much time did you reach overhead?", "helper": "Example: 30 minutes per day, none, or unknown.", "type": "text"},
    {"key": "reaching_overhead_arm_usage", "target": "physical", "icon": "🙆", "question": "For reaching overhead, did you use one arm or both arms?", "helper": "Choose the closest answer.", "type": "radio", "options": ["None", "One Arm", "Both Arms"]},
    {"key": "stairs", "target": "physical", "icon": "🪜", "question": "How much time did you climb stairs or ramps?", "helper": "Example: 30 minutes per day, none, or unknown.", "type": "text"},
    {"key": "ladders", "target": "physical", "icon": "🪜", "question": "How much time did you climb ladders, ropes, or scaffolds?", "helper": "Example: none, 10 minutes per week, or unknown.", "type": "text"},

    {"key": "lifting_description", "target": "job", "icon": "📦", "question": "What did you lift or carry, how heavy was it, how far, and how often?", "helper": "Example: Lifted 20-pound boxes from the freezer to the prep table several times per shift.", "type": "textarea", "check_type": "lifting"},
    {"key": "heaviest_lift", "target": "job", "icon": "🏋️", "question": "What was the heaviest weight you lifted?", "helper": "Choose the closest estimate.", "type": "select", "options": ["", "less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"]},
    {"key": "other_lift_text","target": "job","icon": "🏋️","question": "What was the heaviest weight you lifted?","helper": "Since you selected Other, type the amount. Example: 75 pounds, 80 pounds, or unknown.","type": "text","depends_on": {"key": "heaviest_lift", "value": "other"}},
    {"key": "frequent_lift", "target": "job", "icon": "📦", "question": "What weight did you frequently lift?", "helper": "Choose the closest estimate.", "type": "select", "options": ["", "less_than_1", "less_than_10", "10", "25", "50_or_more", "other"]},
    {"key": "other_frequent_lift_text","target": "job","icon": "📦","question": "What weight did you frequently lift?","helper": "Since you selected Other, type the amount. Example: 75 pounds, 80 pounds, or unknown.","type": "text","depends_on": {"key": "frequent_lift", "value": "other"}},
    {"key": "exposure_checkboxes","target": "exposures","icon": "⚠️","question": "Which of these workplace conditions applied to this job?","helper": "Select all that apply. Examples: loud noise, heat, cold, moving machinery, chemicals, working outside, or working at heights. If none apply, leave this blank and explain None on the next question.", "type": "multiselect","options": ["outdoors","heat","cold","wetness","humidity","hazardous_substances","moving_parts","heights","vibrations","loud_noise","other",],
     },
     {"key": "other_exposure_text","target": "job","icon": "⚠️","question": "What other workplace condition should we add?","helper": "Only answer this if you selected Other. Example: dust, fumes, smoke, chemicals, strong smells, poor ventilation, or unknown.","type": "text","depends_on": {"key": "exposure_checkboxes", "contains": "other"},},
    {"key": "exposure_description", "target": "job", "icon": "⚠️", "question": "Please describe the workplace conditions you selected.", "helper": "Example: Worked around loud machinery most of the day, worked outside in extreme heat, used cleaning chemicals, or None.", "type": "textarea"},
    {"key": "medical_conditions", "target": "job", "icon": "🩺", "question": "How did your medical conditions affect your ability to do this job?", "helper": "Example: Back pain made standing and lifting difficult. If not applicable, write None.", "type": "textarea", "check_type": "medical_conditions"},
    {"key": "extra_notes", "target": "job", "icon": "📌", "question": "Is there anything else important about this job?", "helper": "Add anything that helps explain the work. You can also write none.", "type": "textarea"},
]

def get_guided_value(question):
    job = st.session_state.guided_job

    if question["target"] == "physical":
        return job["physical_activities"].get(question["key"], "")

    if question["target"] == "exposures":
        return [
            key for key, checked in job["exposures"].items()
            if checked
        ]

    return job.get(question["key"], "")

def set_guided_value(question, value):
    if question["target"] == "physical":
        st.session_state.guided_job["physical_activities"][question["key"]] = value

    elif question["target"] == "exposures":
        selected = value if isinstance(value, list) else []

        for key in st.session_state.guided_job["exposures"].keys():
            st.session_state.guided_job["exposures"][key] = key in selected

    else:
        st.session_state.guided_job[question["key"]] = value


def should_show_guided_question(question):
    dep = question.get("depends_on")
    if not dep:
        return True

    dep_key = dep.get("key")
    dep_value = dep.get("value")
    dep_contains = dep.get("contains")

    if dep_key == "exposure_checkboxes":
        selected = [
            key for key, checked in st.session_state.guided_job["exposures"].items()
            if checked
        ]

        if dep_contains:
            return dep_contains in selected

        return selected == dep_value

    current_value = st.session_state.guided_job.get(dep_key)

    if dep_contains:
        if isinstance(current_value, list):
            return dep_contains in current_value
        return dep_contains in str(current_value)

    return current_value == dep_value


def next_guided_step(start):
    step = start
    while step < len(GUIDED_QUESTIONS):
        if should_show_guided_question(GUIDED_QUESTIONS[step]):
            return step
        step += 1
    return len(GUIDED_QUESTIONS)

def parse_work_date(date_str):
    if not date_str:
        return None

    date_str = str(date_str).strip()

    if date_str.lower() in ["present", "current", "now"]:
        return None

    formats = [
        "%B %d, %Y",
        "%B %Y",
        "%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            pass

    return None



def show_validation_warning(validation, follow_up):
    mentioned = validation.get("mentioned_details", [])
    missing = validation.get("missing_details", [])
    better_example = validation.get("better_example", "")

    st.warning("⚠️ Please add a little more detail before moving forward.")

    if mentioned:
        st.write("**You already mentioned:**")
        for item in mentioned:
            st.write(f"• {item}")

    if missing:
        st.write("**Try adding:**")
        for item in missing:
            st.write(f"• {item}")

    if better_example:
        st.info(f"Example: {better_example}")

    if follow_up:
        st.write(f"**Helpful question:** {follow_up}")

    st.info("You can revise your answer, or click Next again to continue.")




def check_job_warnings(job, job_number):



    warnings = []
    job = repair_job(job)
    physical = job["physical_activities"]

    required_job_fields = {
        "job_title": "Job title is missing.",
        "employer": "Employer is missing.",
        "dates_from": "Start date is missing.",
        "dates_to": "End date is missing.",
        "hours_per_day": "Hours per day is missing.",
        "days_per_week": "Days per week is missing.",
        "job_duties": "Job duties are missing.",
        "equipment": "Tools/equipment answer is missing.",
        "lifting_description": "Lifting/carrying explanation is missing.",
        "heaviest_lift": "Heaviest weight lifted is missing.",
        "frequent_lift": "Frequently lifted weight is missing.",
        "exposure_description": "Exposure explanation is missing.",
        "medical_conditions": "Medical condition impact answer is missing.",
    }

    for field, message in required_job_fields.items():
        if is_blank(job.get(field)):
            warnings.append(f"Job {job_number}: {message}")

    physical_required = [
        "standing_walking", "sitting", "stooping", "kneeling", "crouching", "crawling",
        "fingers_time", "fingers_hand_usage", "grasping_time", "grasping_hand_usage",
        "reaching_below_time", "reaching_below_arm_usage", "reaching_overhead_time",
        "reaching_overhead_arm_usage", "stairs", "ladders"
    ]

    physical_labels = {
        "standing_walking": "Standing/walking time",
        "sitting": "Sitting time",
        "stooping": "Stooping/bending time",
        "kneeling": "Kneeling time",
        "crouching": "Crouching time",
        "crawling": "Crawling time",
        "fingers_time": "Finger/hand use time",
        "fingers_hand_usage": "One hand or both hands for finger use",
        "grasping_time": "Grasping/holding time",
        "grasping_hand_usage": "One hand or both hands for grasping",
        "reaching_below_time": "Reaching at/below shoulder time",
        "reaching_below_arm_usage": "One arm or both arms for reaching below",
        "reaching_overhead_time": "Reaching overhead time",
        "reaching_overhead_arm_usage": "One arm or both arms for reaching overhead",
        "stairs": "Stairs/ramps time",
        "ladders": "Ladders/ropes/scaffolds time",
    }

    for key in physical_required:
        if is_blank(physical.get(key)):
            warnings.append(
                f"Job {job_number}: Missing physical activity answer — {physical_labels.get(key, key)}."
            )

    if job.get("interacted_with_people") == "Yes" and is_blank(job.get("interaction_details")):
        warnings.append(f"Job {job_number}: Interaction details are required because interaction is marked Yes.")

    for key, value in physical.items():
        if key.endswith("_usage"):
            continue

        clean = str(value or "").strip().lower()
        field_label = physical_labels.get(key, key)

        if clean and not is_acceptable_time_answer(clean):
            warnings.append(
                f"Job {job_number}: Please review {field_label} — answer may need a unit like hours/minutes, or write None."
            )

    # Days per week review
    try:
        days_text = str(job.get("days_per_week", "")).lower()

        days_number = float(
            days_text
            .replace("days", "")
            .replace("day", "")
            .strip()
        )

        if days_number > 7:
            warnings.append(
                f"Job {job_number}: Please review schedule — days worked per week is "
                f"{job.get('days_per_week')}, but a week only has 7 days."
            )

    except:
        pass

    
       # -----------------------------
    # Review checks / contradiction checks
    # -----------------------------

    duties_text = str(job.get("job_duties", "")).lower()
    lifting_text = str(job.get("lifting_description", "")).lower()
    interaction_text = str(job.get("interaction_details", "")).lower()


    frequent_lift = str(job.get("frequent_lift", "")).lower()
    other_frequent = str(job.get("other_frequent_lift_text", "")).lower()

    weight_words = [
        "lb", "lbs", "pound", "pounds",
        "10", "20", "25", "30", "40", "50", "75", "100"
    ]

    mentions_weight = any(
        word in lifting_text
        for word in weight_words
    )

    frequent_is_zero = (
        frequent_lift in ["0", "none", "no lifting", "less_than_1"]
        or other_frequent.strip() in ["0", "0 lbs", "0 pounds", "none"]
    )

    if mentions_weight and frequent_is_zero:
        warnings.append(
            f"Job {job_number}: Please review lifting answers — a weight is mentioned in the lifting description, but the frequently lifted weight appears to be zero or none."
        )

    # Interaction review check
    people_words = [
        "customer", "customers", "client", "clients", "patient", "patients",
        "coworker", "coworkers", "supervisor", "manager", "public",
        "answered questions", "took orders", "helped people", "served"
    ]

    combined_people_text = f"{duties_text} {interaction_text}"

    if job.get("interacted_with_people") == "No":
        if any(word in combined_people_text for word in people_words):
            warnings.append(
                f"Job {job_number}: Please review — the job duties mention interacting with people, but the interaction question is marked No."
            )

    # Lifting review check
    lift_words = [
        "lift", "lifted", "lifting", "carry", "carried", "carrying",
        "box", "boxes", "stock", "stocked", "moved", "loaded", "unloaded"
    ]

    if job.get("heaviest_lift") in ["", "less_than_1"]:
        if any(word in lifting_text for word in lift_words) or any(word in duties_text for word in lift_words):
            warnings.append(
                f"Job {job_number}: Please review — the job description mentions lifting or carrying, but the lifting section may need another look."
            )

    # Date review check: end date before start date
    def parse_work_date(date_text):
        date_text = str(date_text or "").strip()

        if not date_text:
            return None

        if date_text.lower() == "present":
            return "present"

        for fmt in ["%B %d, %Y", "%B %Y"]:
            try:
                return datetime.strptime(date_text, fmt)
            except:
                pass

        return None

    start_date = parse_work_date(job.get("dates_from", ""))
    end_date = parse_work_date(job.get("dates_to", ""))

    if start_date and end_date and end_date != "present":
        if end_date < start_date:
            warnings.append(
                f"Job {job_number}: Please review — the job end date appears to be before the start date."
            )

    # Hours vs physical activity review check
    try:
        hours_worked = float(
            str(job.get("hours_per_day", ""))
            .replace("hours", "")
            .replace("hour", "")
            .strip()
        )
    except:
        hours_worked = None

    physical_time_keys = [
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

    total_physical_hours = 0

    for key in physical_time_keys:
        value = str(physical.get(key, "")).lower().strip()

        if "hour" in value:
            number_part = (
                value.replace("hours", "")
                .replace("hour", "")
                .strip()
            )

            try:
                total_physical_hours += float(number_part)
            except:
                pass

    if hours_worked is not None and total_physical_hours > hours_worked:
        warnings.append(
            f"Job {job_number}: Please review physical activity times — total activity time "
            f"appears to be about {total_physical_hours} hours, but hours worked per day is "
            f"{hours_worked}."
        )


    # Physical use contradiction checks
    use_pairs = [
        ("fingers_time", "fingers_hand_usage", "finger/hand use"),
        ("grasping_time", "grasping_hand_usage", "grasping/holding"),
        ("reaching_below_time", "reaching_below_arm_usage", "reaching at/below shoulder"),
        ("reaching_overhead_time", "reaching_overhead_arm_usage", "reaching overhead"),
    ]

    none_values = ["none", "0", "0 minutes", "0 hours", "zero", "n/a", "na"]

    for time_key, usage_key, label in use_pairs:
        time_answer = str(physical.get(time_key, "")).lower().strip()
        usage_answer = str(physical.get(usage_key, "")).lower().strip()

        if time_answer in none_values and usage_answer not in ["none", ""]:
            warnings.append(
                f"Job {job_number}: Please review {label} — time is listed as none/zero, "
                f"but hand/arm use is marked as {physical.get(usage_key)}."
            )    

    return warnings

def render_big_question(question, step, total_steps):
    st.markdown(
        f"""
        <div style="background-color:#f7f7f7;padding:32px;border-radius:22px;margin-top:16px;margin-bottom:18px;border:1px solid #e5e5e5;">
            <div style="font-size:52px;margin-bottom:16px;">{question.get("icon", "📝")}</div>
            <div style="font-size:14px;color:#777;margin-bottom:8px;">Question {step + 1} of {total_steps}</div>
            <div style="font-size:34px;font-weight:700;line-height:1.2;color:#111;">{question["question"]}</div>
            <div style="font-size:16px;color:#666;margin-top:14px;line-height:1.5;">{question.get("helper", "")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_answer_input(question, current_value, unique_key):
    q_type = question["type"]

    if q_type == "date":
        return guided_date_picker("Your answer", key_prefix=unique_key, current_value=current_value)

    if q_type == "text":
        return st.text_input("Your answer", value=current_value if isinstance(current_value, str) else "", key=unique_key, label_visibility="collapsed")

    if q_type == "textarea":
        return st.text_area("Your answer", value=current_value if isinstance(current_value, str) else "", key=unique_key, height=170, label_visibility="collapsed")

    if q_type == "radio":
        options = question.get("options", ["No", "Yes"])
        return st.radio("Your answer", options, index=safe_index(options, current_value), key=unique_key, horizontal=True, label_visibility="collapsed")


    if q_type == "multiselect":
        options = question.get("options", [])
        default = current_value if isinstance(current_value, list) else []

        return st.multiselect(
            "Your answer",
            options,
            default=default,
            key=unique_key,
            label_visibility="collapsed",
        )


    if q_type == "number":

        try:
            default_value = int(current_value)
        except (TypeError, ValueError):
            default_value = question.get("min", 0)

        return st.number_input(
            "Your answer",
            min_value=question.get("min", 0),
            max_value=question.get("max", 100),
            value=default_value,
            step=1,
            key=unique_key,
            label_visibility="collapsed",
        )

    if q_type == "select":
        options = question.get("options", [])
        return st.selectbox("Your answer", options, index=safe_index(options, current_value), key=unique_key, label_visibility="collapsed")

    return st.text_input("Your answer", value=current_value if isinstance(current_value, str) else "", key=unique_key, label_visibility="collapsed")


def show_job_review(job, job_number):
    job = repair_job(job)
    physical = job["physical_activities"]

    st.markdown(f"### Job {job_number}: {job.get('job_title') or 'Untitled Job'}")
    col1, col2 = st.columns(2)



    with col1:
        st.write("**Employer:**", job.get("employer", ""))
        st.write("**Dates:**", f"{job.get('dates_from', '')} to {job.get('dates_to', '')}")
        st.write("**Hours/day:**", job.get("hours_per_day", ""))
        st.write("**Days/week:**", job.get("days_per_week", ""))
        st.write("**Pay:**", f"{job.get('pay_rate', '')} per {job.get('pay_type', '')}")

    with col2:
        st.write("**Interacted with people:**", job.get("interacted_with_people", "No"))
        st.write("**Heaviest lift:**",job.get("other_lift_text", "")if job.get("heaviest_lift") == "other" else job.get("heaviest_lift", ""))
        st.write("**Frequent lift:**",job.get("other_frequent_lift_text", "")if job.get("frequent_lift") == "other" else job.get("frequent_lift", ""))

    st.write("**Job duties:**")
    st.info(job.get("job_duties", "") or "No answer provided.")

    st.write("**Physical activity details:**")
    st.json(physical)

    st.write("**Lifting/carrying:**")
    st.info(job.get("lifting_description", "") or "No answer provided.")

    st.write("**Environmental exposures:**")
    st.info(job.get("exposure_description", "") or "No answer provided.")
    selected_exposures = [
        name.replace("_", " ").title()
        for name, checked in job.get("exposures", {}).items()
        if checked
    ]

    st.write("**Environmental exposures selected:**")

    if selected_exposures:
        st.info(", ".join(selected_exposures))
    else:
        st.info("None selected.")

    warnings = check_job_warnings(job, job_number)

    st.markdown("### 📋 Job Summary")

    summary_items = []

    if job.get("job_title") or job.get("employer"):
        summary_items.append(
            f"**Job:** {job.get('job_title') or 'Not answered'} at {job.get('employer') or 'Not answered'}"
        )

    if job.get("dates_from") or job.get("dates_to"):
        summary_items.append(
            f"**Dates:** {job.get('dates_from') or 'Not answered'} to {job.get('dates_to') or 'Not answered'}"
        )

    if job.get("hours_per_day") or job.get("days_per_week"):
        summary_items.append(
            f"**Schedule:** {job.get('hours_per_day') or 'Not answered'} hours/day, {job.get('days_per_week') or 'Not answered'} days/week"
        )

    if job.get("interacted_with_people"):
        summary_items.append(
            f"**People interaction:** {job.get('interacted_with_people')}"
        )

    if job.get("heaviest_lift") or job.get("frequent_lift"):
        heaviest = job.get("other_lift_text") if job.get("heaviest_lift") == "other" else job.get("heaviest_lift")
        frequent = job.get("other_frequent_lift_text") if job.get("frequent_lift") == "other" else job.get("frequent_lift")

        summary_items.append(
            f"**Lifting:** Heaviest: {heaviest or 'Not answered'} | Frequent: {frequent or 'Not answered'}"
        )

    for item in summary_items:
        st.write(item)

    if job.get("job_duties"):
        st.write("**Main duties:**")
        st.info(job.get("job_duties"))

    if warnings:
        st.warning(f"{len(warnings)} review item(s) may need another look.")

        with st.expander("View Review Items", expanded=False):
            st.info(
                "These are reminders to review. They do not mean the answers are wrong."
            )

            for warning in warnings:
                clean_warning = warning.replace(f"Job {job_number}: ", "")
                st.write(f"• {clean_warning}")
    else:
        st.success("No major missing items detected. Please review before saving.")

    with st.expander("View Full Details", expanded=False):
        st.markdown("### Work Duties")
        st.write("**Typical Workday:**")
        st.success(job.get("job_duties") or "Not answered")

        st.write("**Reports / Computer Work:**")
        st.info(job.get("reports") or "Not answered")

        st.write("**Tools / Equipment:**")
        st.info(job.get("equipment") or "Not answered")

        st.markdown("### People Interaction")
        st.write("**Interacted With People:**", job.get("interacted_with_people", "No"))

        if job.get("interacted_with_people") == "Yes":
            st.info(job.get("interaction_details") or "Not answered")

        st.markdown("### Physical Activity")
        st.write("**Standing/Walking:**", physical.get("standing_walking") or "Not answered")
        st.write("**Sitting:**", physical.get("sitting") or "Not answered")
        st.write("**Stooping/Bending:**", physical.get("stooping") or "Not answered")
        st.write("**Kneeling:**", physical.get("kneeling") or "Not answered")
        st.write("**Crouching:**", physical.get("crouching") or "Not answered")
        st.write("**Crawling:**", physical.get("crawling") or "Not answered")

        st.markdown("### Lifting / Carrying")
        st.write("**Lifting Description:**")
        st.info(job.get("lifting_description") or "Not answered")
        st.write("**Heaviest Lift:**", job.get("other_lift_text") if job.get("heaviest_lift") == "other" else job.get("heaviest_lift") or "Not answered")
        st.write("**Frequent Lift:**", job.get("other_frequent_lift_text") if job.get("frequent_lift") == "other" else job.get("frequent_lift") or "Not answered")

        st.markdown("### Environmental Exposures")
        selected_exposures = [
            name.replace("_", " ").title()
            for name, checked in job.get("exposures", {}).items()
            if checked
        ]

        st.write("**Selected Exposures:**", ", ".join(selected_exposures) if selected_exposures else "None selected")
        st.info(job.get("exposure_description") or "Not answered")

        st.markdown("### Medical Conditions")
        st.info(job.get("medical_conditions") or "Not answered")

def ask_help_assistant(user_question, current_form_question="", current_answer=""):
    if openai_client is None:
        return "OpenAI API key is missing. Please set OPENAI_API_KEY before using the help assistant."

    job_context = repair_job(st.session_state.guided_job)

    prompt = f"""
You are a helpful assistant inside a DDS Work History Report app.

Your role:
- Explain form questions in plain language.
- Help users understand what the question is asking.
- Do not tell users what answer to give.
- Do not invent facts.
- Do not provide legal advice.
- Encourage estimates if the user does not remember exact details.
- Keep answers short, calm, and supportive.
- Help determine whether their answer may need more detail.
- Help users understand what the question is asking.
- If the user asks what they answered previously, use the saved answers below.
- You may summarize or remind the user of earlier answers, but never invent or change them.

Current form question:
{current_form_question}

Current answer already entered:
{current_answer}

Previous answers entered for this job:
{json.dumps(job_context, indent=2)}

User's help question:
{user_question}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content

def transcribe_audio(audio_file):
    if openai_client is None:
        return "OpenAI API key is missing. Please set OPENAI_API_KEY before using voice input."

    audio_file.name = "voice_answer.wav"

    transcript = openai_client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
        prompt=(
            "This is a DDS Work History Report interview. "
            "The speaker may say employer names, business names, stores, restaurants, "
            "cleaning companies, clinics, warehouses, agencies, and people's names. "
            "Transcribe exactly what is spoken. "
            "Preserve company names and proper nouns."
        ),
    )

    return transcript.text

def create_question_audio(text, filename="question_audio.mp3"):
    if openai_client is None:
        return None

    with openai_client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text,
        instructions="Speak in a warm, calm, natural, supportive voice. Sound like a real person helping someone complete a form.",
    ) as response:
        response.stream_to_file(filename)

    return filename

def answer_status(value):
    if is_blank(value):
        return "⚠️"

    if str(value).strip() in ["0", "0.0"]:
        return "⚠️"

    return "✅"

def normalize_answer(question, answer):
    if question.get("key") in TIME_UNIT_KEYS:
        return normalize_none_time_answer(answer)

    return answer


def normalize_none_time_answer(answer):
    answer_text = str(answer or "").strip().lower()

    none_answers = [
        "i didn't",
        "i didnt",
        "i did not",
        "did not",
        "didn't",
        "didnt",
        "no",
        "none",
        "not at all",
        "never",
        "n/a",
        "na",
        "not applicable",
    ]

    if answer_text in none_answers:
        return "None"

    return answer


def review_row(label, value):
    display_value = value if not is_blank(value) else "Not answered"
    st.write(f"{answer_status(value)} **{label}:** {display_value}")

def review_dependent_row(label, parent_value, value):
    if is_blank(parent_value):
        review_row(label, "")
    else:
        review_row(label, value)    


def review_section(title):
    st.markdown("---")
    st.markdown(f"### {title}")

def show_client_job_review(job, job_number):
    job = repair_job(job)
    physical = job["physical_activities"]
    warnings = check_job_warnings(job, job_number)

    st.markdown(f"## Review Job {job_number}")
    st.info("Please review your answers before saving this job.")

    review_section("📋 Job Summary")

    if st.button("✏️ Edit Job Summary", key=f"edit_summary_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("job_title")
        st.rerun()




    review_row("Job title", job.get("job_title"))
    review_row("Employer", job.get("employer"))

    dates_from = job.get("dates_from")
    dates_to = job.get("dates_to")

    if is_blank(dates_from) or is_blank(dates_to):
        review_row("Dates", "")
    else:
        review_row("Dates", f"{dates_from} to {dates_to}")

    pay_rate = job.get("pay_rate")
    pay_type = job.get("pay_type")

    if is_blank(pay_rate):
        review_row("Pay", "")
    else:
        review_row("Pay", f"{pay_rate} per {pay_type}")

    review_row("Hours per day", job.get("hours_per_day"))
    review_row("Days per week", job.get("days_per_week"))

    review_section("📝 Work Duties")

    if st.button("✏️ Edit Work Duties", key=f"edit_duties_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("job_duties")
        st.rerun()

    review_row("Typical workday", job.get("job_duties"))
    review_row("Reports / forms / computer work", job.get("reports"))
    review_row("Supervision", job.get("supervise"))
    review_row("Tools / equipment", job.get("equipment"))

    review_section("👥 People Interaction")
    if is_blank(job.get("job_duties")):
        review_row("Interacted with people", "")
    else:
        review_row("Interacted with people", job.get("interacted_with_people"))
    if job.get("interacted_with_people") == "Yes":
        review_row("Interaction details", job.get("interaction_details"))

    review_section("🏃 Physical Activities")

    if st.button("✏️ Edit Physical Activities", key=f"edit_physical_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("standing_walking")
        st.rerun()    

    review_row("Standing / walking", physical.get("standing_walking"))
    review_row("Sitting", physical.get("sitting"))
    review_row("Stooping / bending", physical.get("stooping"))
    review_row("Kneeling", physical.get("kneeling"))
    review_row("Crouching", physical.get("crouching"))
    review_row("Crawling", physical.get("crawling"))

    review_row("Finger use", physical.get("fingers_time"))
    review_dependent_row(
        "Finger hand usage",
        physical.get("fingers_time"),
        physical.get("fingers_hand_usage")
    )

    review_row("Grasping / holding", physical.get("grasping_time"))
    review_dependent_row(
        "Grasping hand usage",
        physical.get("grasping_time"),
        physical.get("grasping_hand_usage")
    )

    review_row("Reaching at/below shoulder", physical.get("reaching_below_time"))
    review_dependent_row(
        "Reaching below arm usage",
        physical.get("reaching_below_time"),
        physical.get("reaching_below_arm_usage")
    )

    review_row("Reaching overhead", physical.get("reaching_overhead_time"))
    review_dependent_row(
        "Reaching overhead arm usage",
        physical.get("reaching_overhead_time"),
        physical.get("reaching_overhead_arm_usage")
    )

    review_row("Stairs / ramps", physical.get("stairs"))
    review_row("Ladders / scaffolds", physical.get("ladders"))

    

    review_section("📦 Lifting / Carrying")
    heaviest = job.get("other_lift_text") if job.get("heaviest_lift") == "other" else job.get("heaviest_lift")
    frequent = job.get("other_frequent_lift_text") if job.get("frequent_lift") == "other" else job.get("frequent_lift")

    if st.button("✏️ Edit Lifting", key=f"edit_lifting_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("lifting_description")
        st.rerun()

    review_row("Lifting description", job.get("lifting_description"))
    review_row("Heaviest lift", heaviest)
    review_row("Frequent lift", frequent)

    review_section("🌡 Work Environment")
    selected_exposures = [
        name.replace("_", " ").title()
        for name, checked in job.get("exposures", {}).items()
        if checked
    ]

    if st.button("✏️ Edit Work Environment", key=f"edit_environment_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("exposure_checkboxes")
        st.rerun()

    if is_blank(job.get("exposure_description")):
        review_row("Selected workplace conditions", "")
    else:
        review_row("Selected workplace conditions", ", ".join(selected_exposures) if selected_exposures else "None selected")
    review_row("Exposure description", job.get("exposure_description"))

    review_section("🩺 Medical Conditions")
    review_row("Medical impact", job.get("medical_conditions"))

    if st.button("✏️ Edit Medical Conditions", key=f"edit_medical_{job_number}"):
        st.session_state.editing_from_review = True
        st.session_state.guided_step = find_question_step("medical_conditions")
        st.rerun()

    review_section("📌 Extra Notes")
    review_row("Other important details", job.get("extra_notes"))

    review_section("⚠️ Review Items")

    if warnings:
        st.warning(f"{len(warnings)} review item(s) may need another look.")

        with st.expander("View Review Items", expanded=False):
            st.info("These are reminders to review. They do not mean the answers are wrong.")

            for i, warning in enumerate(warnings, start=1):
                clean_warning = warning.replace(f"Job {job_number}: ", "")

                target_key = get_warning_target_key(clean_warning)
                target_step = find_question_step(target_key)

                col1, col2 = st.columns([5, 1])

                with col1:
                    st.write(clean_warning)

                with col2:
                    if st.button(
                        "Review",
                        key=f"review_warning_{job_number}_{i}"
                    ):
                        st.session_state.editing_from_review = True
                        st.session_state.guided_step = target_step
                        st.rerun()

    else:
        st.success("No major missing items detected. Please review before saving.")


def value_is_yes(value):
    return str(value or "").strip().lower() == "yes"


def value_is_no(value):
    return str(value or "").strip().lower() == "no"


def review_optional_row(label, value):
    """
    Shows a row only if the user gave an answer.
    Good for optional remarks/details fields.
    """
    if not is_blank(value):
        review_row(label, value)


def review_yes_no_row(label, value):
    """
    Yes/No answers count as completed.
    """
    review_row(label, value)


def review_if_yes(label, parent_value, value):
    """
    Only reviews details when the parent question is Yes.
    Example: If Drive = Yes, then review drive details.
    """
    if value_is_yes(parent_value):
        review_row(label, value)


def review_if_parent_answered(label, parent_value, value):
    """
    Only reviews child/details answer if the parent question was answered.
    """
    if not is_blank(parent_value):
        review_row(label, value)


def review_text_or_none(label, value):
    """
    Open text field where None/No problem is acceptable.
    """
    review_row(label, value)


def job_memory_helper():
    with st.expander("🧠 Need help remembering jobs from the last 5 years?"):
        st.info(
            "This helper is only for memory. It does not fill the form unless you choose to use an answer."
        )

        job_types = st.multiselect(
            "Do any of these sound familiar?",
            [
                "Retail / store job",
                "Warehouse",
                "Restaurant / food service",
                "Cleaning / janitorial",
                "Home care / PCA / CNA",
                "Delivery / driving",
                "Office / computer work",
                "Temp agency",
                "Factory / production",
                "Hospital / clinic",
                "School / daycare",
                "Security",
                "Construction / labor",
                "Other",
            ],
            key="memory_job_types",
        )

        memory_notes = st.text_area(
            "Write anything you remember: employer names, cities, coworkers, managers, uniforms, schedules, or dates.",
            key="memory_notes",
            height=120,
        )

        if st.button("Create memory checklist", key="create_memory_checklist"):
            st.session_state.memory_checklist = {
                "job_types": job_types,
                "notes": memory_notes,
            }

        if st.session_state.get("memory_checklist"):
            st.markdown("### Possible job memory clues")

            if job_types:
                st.write("**Job areas remembered:**")
                for item in job_types:
                    st.write(f"- {item}")

            if memory_notes:
                st.write("**Notes remembered:**")
                st.info(memory_notes)

            st.warning(
                "Use these notes to help answer the form. Do not guess details you do not remember."
            )

def show_in_flow_review_banner(issue_id, message, target_step):
    dismissed_key = f"{issue_id}_dismissed"

    if st.session_state.get(dismissed_key):
        return

    message = (
        "⚠️ Please add more detail before moving forward.\n\n"
        + message
    )

    st.warning(message)

    col_a, col_b = st.columns(2)

    unique_suffix = f"{issue_id}_{st.session_state.guided_job_number}_{st.session_state.guided_step}"

    with col_a:
        if st.button("Review Earlier Answer", key=f"review_{unique_suffix}"):
            st.session_state.editing_from_banner = True
            st.session_state.return_step_after_banner_edit = st.session_state.guided_step
            st.session_state.guided_step = target_step
            st.rerun()

    with col_b:
        if st.button("Continue", key=f"continue_{unique_suffix}"):
            st.session_state[dismissed_key] = True
            st.rerun()

def check_in_flow_review_issues(job, current_question_key):
    issues = []

    duties_text = str(job.get("job_duties", "")).lower()
    lifting_text = str(job.get("lifting_description", "")).lower()

    people_words = [
        "customer", "customers", "client", "clients", "patient", "patients",
        "coworker", "coworkers", "supervisor", "manager", "public",
        "helped people", "answered questions", "served"
    ]

    lift_words = [
        "lift", "lifted", "lifting",
        "carry", "carried", "carrying",
        "box", "boxes",
        "stock", "stocked",
        "loaded", "unloaded",
        "equipment", "supplies"
    ]

    if current_question_key in ["interaction_details", "standing_walking"]:
        interaction_answer = job.get("interacted_with_people")

        if interaction_answer == "No":
            if any(word in duties_text for word in people_words):
                issues.append({
                    "issue_id": "people_interaction_review",
                    "message": (
                        "Helpful Review Item: You marked that this job did not involve "
                        "interaction with people, but your job duties mention customers, "
                        "coworkers, supervisors, or the public. Would you like to review that answer?"
                    ),
                    "target_step": find_question_step("interacted_with_people")
                })

    if current_question_key == "other_frequent_lift_text":

        if any(word in f"{duties_text} {lifting_text}" for word in lift_words):

            frequent_lift = str(job.get("frequent_lift", "")).strip().lower()
            other_frequent = str(job.get("other_frequent_lift_text", "")).strip().lower()

            frequent_is_zero_or_blank = (
                frequent_lift in ["", "less_than_1", "0", "none", "no lifting"]
                or other_frequent in ["0", "0 lbs", "0 pounds", "none", "no lifting"]
            )

            if frequent_is_zero_or_blank:

                issues.append({
                    "issue_id": "lifting_review",
                    "message": (
                        "Helpful Review Item: Your answers mention lifting, carrying, boxes, "
                        "equipment, or stocking, but the lifting weight answers may need another look. "
                        "Would you like to review the lifting questions?"
                    ),
                    "target_step": find_question_step("heaviest_lift")
                })

        # Date review banner
    if current_question_key == "dates_to":

        start = job.get("dates_from", "")
        end = job.get("dates_to", "")

        start_date = parse_work_date(start)
        end_date = parse_work_date(end)

        if start_date and end_date:
            if end_date < start_date:

                issues.append({
                    "issue_id": "date_review",
                    "message": (
                        f"Helpful Review Item: "
                        f"The start date is {start}, but the end date is {end}. "
                        f"Would you like to review the dates?"
                    ),
                    "target_step": find_question_step("dates_from")
                })

    return issues


def function_report_completion_score(report):
    required_keys = [
        "function_name",
        "function_phone",
        "living_place",
        "living_with",
        "condition_limits_work",
        "daily_routine",
        "before_conditions",
        "personal_care",
        "housework",
        "go_outside",
        "transportation",
        "pay_bills",
        "hobbies_interests",
        "ability_limitations",
        "assistive_devices",
        "medication_side_effects",
        "function_report_remarks",
    ]

    answered = 0

    for key in required_keys:
        if not is_blank(report.get(key)):
            answered += 1

    score = int((answered / len(required_keys)) * 100)
    return score

def function_answer_status(value):
    if is_blank(value):
        return "⚠️"

    if str(value).strip().lower() in [
        "no",
        "none",
        "n/a",
        "na",
        "not applicable",
    ]:
        return "➖"

    return "✅"


def function_review_row(label, value):
    display_value = value if not is_blank(value) else "Not answered"
    st.write(f"{function_answer_status(value)} **{label}:** {display_value}")


def function_selected_list(value):
    if isinstance(value, list):
        return ", ".join(value) if value else ""
    return value


def show_function_report_review(report):
    st.markdown("## Review Function Report")
    st.info("Please review your answers before saving this Function Report.")


    score = function_report_completion_score(report)

    st.markdown("### Function Report Completion")
    st.progress(score / 100)

    if score >= 90:
        st.success(f"{score}% complete — strong detail overall.")
    elif score >= 70:
        st.warning(f"{score}% complete — a few answers may need more detail.")
    else:
        st.error(f"{score}% complete — several important answers are missing.")

    review_section("👤 Basic Information")
    function_review_row("Name", report.get("function_name"))
    function_review_row("Social Security number", report.get("function_ssn"))
    function_review_row("Phone", report.get("function_phone"))
    function_review_row("Where you live", report.get("living_place"))

    if report.get("living_place") == "Other":
        function_review_row(
            "Where you live - Other details",
            report.get("living_place_other")
        )

    function_review_row("Who you live with", report.get("living_with"))

    if report.get("living_with") == "Other":
        function_review_row(
            "Who you live with - Other details",
            report.get("living_with_other")
        )

    review_section("🩺 Conditions and Daily Life")
    function_review_row("How conditions limit work", report.get("condition_limits_work"))
    function_review_row("Daily routine", report.get("daily_routine"))
    function_review_row("What you could do before", report.get("before_conditions"))

    review_section("🤝 Caring for Others / Pets")
    function_review_row("Care for others", report.get("care_for_others"))
    function_review_if_yes(report, "care_for_others", "care_for_others_details", "Care for others details")

    function_review_row("Care for pets", report.get("care_for_pets"))
    function_review_if_yes(report, "care_for_pets", "care_for_pets_details", "Care for pets details")

    function_review_row("Help with people or animals", report.get("help_care_others_animals"))
    function_review_if_yes(report, "help_care_others_animals", "help_care_others_animals_details", "Help details")

    review_section("🌙 Sleep and Personal Care")
    function_review_row("Sleep affected", report.get("sleep_affected"))
    function_review_if_yes(report, "sleep_affected", "sleep_affected_details", "Sleep details")

    function_review_row("Personal care", report.get("personal_care"))
    function_review_row("Grooming reminders", report.get("needs_grooming_reminders"))
    function_review_if_yes(report, "needs_grooming_reminders", "grooming_reminders_details", "Grooming reminder details")

    function_review_row("Medicine reminders", report.get("needs_medicine_reminders"))
    function_review_if_yes(report, "needs_medicine_reminders", "medicine_reminders_details", "Medicine reminder details")

    review_section("🍳 Meals and Housework")
    function_review_row("Prepare meals", report.get("prepare_meals"))
    function_review_if_yes(report, "prepare_meals", "meal_preparation_details", "Meal preparation details")

    function_review_optional_text(report, "meal_changes", "Cooking changes")
    function_review_row("Housework / yard work", report.get("housework"))
    function_review_row("Housework time and frequency", report.get("housework_time_frequency"))
    function_review_row("Housework help", report.get("housework_help"))

    review_section("🚗 Getting Around and Shopping")
    function_review_row("How often you go outside", report.get("go_outside"))
    function_review_row("Can go out alone", report.get("travel_alone"))
    function_review_row("Transportation", report.get("transportation"))
    function_review_row("Drive", report.get("drive"))
    if report.get("drive") == "No":
        function_review_row(
            "Why you don't drive",
            report.get("drive_no_reason")
        )

    function_review_if_yes(report, "drive", "drive_details", "Driving details")

    function_review_row("Shopping", report.get("shopping"))
    function_review_if_yes(report, "shopping", "shopping_details", "Shopping details")

    review_section("💰 Money")
    function_review_row("Money handling", report.get("pay_bills"))
    function_review_optional_text(report, "money_changes", "Money changes")

    review_section("🎨 Hobbies and Social Activities")
    function_review_row("Hobbies/interests", report.get("hobbies_interests"))
    function_review_row("Hobby changes", report.get("hobbies_changes"))
    function_review_row("Spend time with others", report.get("time_with_others"))
    function_review_if_yes(report, "time_with_others", "time_with_others_details", "Time with others details")

    function_review_optional_text(report, "social_changes", "Social changes")
    function_review_row("Need someone to go with you", report.get("need_accompaniment"))
    function_review_if_yes(report, "need_accompaniment", "need_accompaniment_details", "Accompaniment details")

    review_section("💪 Abilities")
    function_review_row("Affected abilities", function_selected_list(report.get("affected_abilities")))
    function_review_row("Ability limitations", report.get("ability_limitations"))

    review_section("🦯 Devices and Medications")
    function_review_row("Assistive devices", report.get("assistive_devices"))
    function_review_row("Devices prescribed", report.get("assistive_devices_prescribed"))
    function_review_if_yes(report, "assistive_devices_prescribed", "assistive_devices_details", "Device details")

    function_review_optional_text(report, "medication_side_effects", "Medication side effects")

    review_section("📌 Remarks")
    function_review_optional_text(report, "function_report_remarks", "Additional remarks")



def function_review_if_yes(report, parent_key, detail_key, label):
    if report.get(parent_key) == "Yes":
        function_review_row(label, report.get(detail_key))


def function_review_optional_text(report, key, label):
    value = report.get(key)

    if is_blank(value):
        st.write(f"➖ **{label}:** Not answered / may not apply")
    else:
        function_review_row(label, value)    



def find_question_step(question_key):
    for i, q in enumerate(GUIDED_QUESTIONS):
        if q.get("key") == question_key:
            return i
    return 0

def get_warning_target_key(warning):
    warning = warning.lower()

    if "total activity time" in warning or "hours worked per day" in warning:
        return "hours_per_day"

    if "finger/hand use" in warning:
        return "fingers_time"
    if "grasping/holding" in warning:
        return "grasping_time"
    if "reaching at/below" in warning:
        return "reaching_below_time"
    if "standing" in warning:
        return "standing_walking"
    if "sitting" in warning:
        return "sitting"
    if "lifting" in warning:
        return "lifting_description"
    if "equipment" in warning:
        return "equipment"
    if "exposure" in warning:
        return "exposure_description"
    if "medical" in warning:
        return "medical_conditions"

    return "job_title"

def show_job_memory_summary():
    job = repair_job(st.session_state.guided_job)
    physical = job["physical_activities"]

    has_any_info = any([
        job.get("job_title"),
        job.get("employer"),
        job.get("dates_from"),
        job.get("dates_to"),
        job.get("hours_per_day"),
        job.get("days_per_week"),
        job.get("job_duties"),
        job.get("lifting_description"),
        physical.get("standing_walking"),
        physical.get("sitting"),
    ])

    if not has_any_info:
        return

def apply_guided_autofill(question):
    job = st.session_state.guided_job
    physical = job["physical_activities"]

    key = question.get("key")

    none_answers = [
        "none",
        "no",
        "0",
        "0 hours",
        "0 minutes",
        "zero",
        "n/a",
        "na",
    ]

    def is_none_answer(value):
        return str(value or "").strip().lower() in none_answers

    if key == "fingers_time" and is_none_answer(physical.get("fingers_time")):
        physical["fingers_hand_usage"] = "None"

    if key == "grasping_time" and is_none_answer(physical.get("grasping_time")):
        physical["grasping_hand_usage"] = "None"

    if key == "reaching_below_time" and is_none_answer(physical.get("reaching_below_time")):
        physical["reaching_below_arm_usage"] = "None"

    if key == "reaching_overhead_time" and is_none_answer(physical.get("reaching_overhead_time")):
        physical["reaching_overhead_arm_usage"] = "None"





def should_skip_after_autofill(question):
    job = st.session_state.guided_job
    physical = job["physical_activities"]

    key = question.get("key")

    none_answers = [
        "none",
        "no",
        "0",
        "0 hours",
        "0 minutes",
        "zero",
        "n/a",
        "na",
    ]

    def is_none_answer(value):
        return str(value or "").strip().lower() in none_answers

    if key == "fingers_time" and is_none_answer(physical.get("fingers_time")):
        return True

    if key == "grasping_time" and is_none_answer(physical.get("grasping_time")):
        return True

    if key == "reaching_below_time" and is_none_answer(physical.get("reaching_below_time")):
        return True

    if key == "reaching_overhead_time" and is_none_answer(physical.get("reaching_overhead_time")):
        return True

    return False




def needs_time_unit(question, answer):

    time_question_keys = [
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

    if question.get("key") not in time_question_keys:
        return False

    return not is_acceptable_time_answer(answer)

def run_ai_json_extraction(prompt, default_result=None):
    if default_result is None:
        default_result = {}

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content.strip()
        return json.loads(content)

    except Exception as e:
        st.warning("AI extraction failed.")
        st.write(str(e))
        return default_result





def extract_inline_job_details(answer_text):
    if openai_client is None:
        return {}

    if not str(answer_text).strip():
        return {}

    prompt = f"""
You are extracting job details from a user's answer in a DDS Work History app.

Return ONLY valid JSON with these exact keys:
job_title, employer, dates_from, dates_to, pay_rate, pay_type

Rules:
- Do not guess.
- If missing, use "".
- Do not include explanations.

Job title rules:
- job_title should contain ONLY the actual job title.
- Do NOT include employer names.
- Do NOT include dates.
- Do NOT include pay.
- Do NOT include years worked.
- Do NOT include words like "for", "at", or the rest of the sentence.

Examples:
Input: "warehouse worker for Amazon for 13 years"
job_title = "warehouse worker"
employer = "Amazon"

Input: "cashier at Target from 2021 to 2024"
job_title = "cashier"
employer = "Target"

Input: "registered nurse at Mayo Clinic"
job_title = "registered nurse"
employer = "Mayo Clinic"

Employer rules:
- employer should be only the company/person/business name.

Pay rules:
- pay_rate should be only the number or range, without words. Examples: "18", "13000", "18-20".
- pay_type must be exactly one of: hour, day, week, month, year, or "".
- If the answer says "a year", "per year", "yearly", "annual", "annually", or "salary", pay_type must be "year".
- If the answer says "a month", "per month", or "monthly", pay_type must be "month".
- If the answer says "a week", "per week", or "weekly", pay_type must be "week".
- If the answer says "a day", "per day", or "daily", pay_type must be "day".
- If the answer says "an hour", "per hour", "hourly", "hr", or "/hr", pay_type must be "hour".

Date rules:
- Convert dates like "5/2022" to "May 2022" if possible.
- Convert dates like "January 3rd 2024" to "January 3, 2024".
- Convert dates like "February 7th 2026" to "February 7, 2026".
- Keep the day number if the user gives one.
- Remove "st", "nd", "rd", or "th" from day numbers.

User answer:
{answer_text}
"""

    return run_ai_json_extraction(
        prompt,
        default_result={
            "job_title": "",
            "employer": "",
            "dates_from": "",
            "dates_to": "",
            "pay_rate": "",
            "pay_type": "",
        },
    )
    

def extract_details_from_job_duties(answer_text):
    if openai_client is None:
        return {}

    if not str(answer_text).strip():
        return {}

    prompt = f"""
Extract only clearly stated details from this job duties answer.

Return ONLY JSON with these keys:
equipment, exposure_description, medical_conditions

Rules:
- Do not guess.
- If not clearly stated, use "".
- equipment = tools, machines, supplies, or equipment used.
- exposure_description = workplace conditions or exposures like chemicals, fumes, loud noise, heat, cold, dust, heights, moving machinery.
- medical_conditions = how health symptoms or conditions affected the job.
- Do not include explanations.

Job duties answer:
{answer_text}
"""

    return run_ai_json_extraction(
        prompt,
        default_result={
            "equipment": "",
            "exposure_description": "",
            "medical_conditions": "",
        },
    ) 

def extract_with_rules(answer_text, keys, extra_rules=""):
    if openai_client is None:
        return {}

    if not str(answer_text).strip():
        return {}

    key_list = "\n".join(keys)

    prompt = f"""
You are helping complete a Social Security form.

Extract ONLY information that is clearly stated.

Return ONLY valid JSON using these exact keys:

{key_list}

Rules:
- Do not guess.
- If unclear, use "".
- For Yes/No fields, only use "Yes", "No", or "".
- Only fill Yes/No fields when the user clearly says it.
- If a Yes/No answer is only implied or uncertain, use "".
- For No answers, include the reason when clearly stated.
- Do not provide legal advice.
- Do not fill frequency/time questions such as how often, how long, or when.
- affected_abilities must be a JSON list if included.

Additional rules:
{extra_rules}

User answer:
{answer_text}
"""

    return run_ai_json_extraction(prompt, default_result={})


def document_selector():
    st.title("DDS AI App")
    st.subheader("Choose a form")

    st.info("Select the document you want help completing.")

    form_choice = st.selectbox(
        "Which form do you need help with?",
        [
            "Work History Report (SSA-3369)",
            "Function Report (SSA-3373)",
            "Adult Disability Report (SSA-3368) - Coming Soon",
        ],
    )

    if st.button("Start This Form", use_container_width=True):

        if form_choice == "Work History Report (SSA-3369)":
            st.session_state.selected_form = "ssa_3369"

        elif form_choice == "Function Report (SSA-3373)":
            st.session_state.selected_form = "ssa_3373"

        elif "Coming Soon" in form_choice:
            st.warning("This form is not ready yet.")
            return

        st.rerun()

def remember_answer(memory_key, value, source_label=""):
    if is_blank(value):
        return

    if "case_memory" not in st.session_state:
        st.session_state.case_memory = {}

    st.session_state.case_memory[memory_key] = {
        "value": value,
        "source": source_label,
        "updated_at": datetime.now().isoformat(),
    }


def get_memory_answer(memory_key):
    memory = st.session_state.get("case_memory", {})
    item = memory.get(memory_key)

    if not item:
        return None

    return item.get("value")

CROSS_FORM_MEMORY_KEYS = {
    # Work History → concepts
    "standing_walking": "standing_walking",
    "sitting": "sitting",
    "lifting_description": "lifting",
    "medical_conditions": "condition_limits",
    "job_duties": "work_activities",

    # Function Report → same concepts
    "condition_limits_work": "condition_limits",
    "ability_limitations": "condition_limits",
    "assistive_devices": "assistive_devices",
    "medication_side_effects": "medication_side_effects",
    "daily_routine": "daily_routine",
    "before_conditions": "before_conditions",
}

def remember_current_answer(question, value, source_label=""):
    question_key = question.get("key")

    if question_key not in CROSS_FORM_MEMORY_KEYS:
        return

    memory_key = CROSS_FORM_MEMORY_KEYS[question_key]

    remember_answer(
        memory_key,
        value,
        source_label=source_label,
    )
def show_cross_form_memory(question, target_dict):
    question_key = question.get("key")

    if question_key not in CROSS_FORM_MEMORY_KEYS:
        return

    # Don't show memory if the user already answered this question
    current_value = target_dict.get(question_key, "")
    if str(current_value).strip():
        return

    ignore_key = f"ignore_memory_{question_key}"

    if st.session_state.get(ignore_key):
        return

    memory_key = CROSS_FORM_MEMORY_KEYS[question_key]
    previous = get_memory_answer(memory_key)

    if not previous:
        return

    st.info("✨ You may have already answered something similar in another form.")

    st.write(previous)

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Use Previous Answer",
            key=f"use_memory_{question_key}",
        ):
            target_dict[question_key] = previous
            st.rerun()

    with col2:
        if st.button(
            "Keep Current Answer",
            key=f"ignore_memory_{question_key}",
        ):
            st.session_state[ignore_key] = True
            st.rerun()



def extract_function_daily_routine_details(answer_text):
    return extract_with_rules(
        answer_text,
        keys=[
            "sleep_affected",
            "sleep_affected_details",
            "personal_care",
            "prepare_meals",
            "meal_preparation_details",
            "prepare_meals_no_reason",
            "housework",
            "housework_time_frequency",
            "housework_help",
            "travel_alone",
            "travel_alone_no_reason",
            "transportation",
            "drive",
            "drive_no_reason",
            "shopping",
            "shopping_details",
            "shopping_no_reason",
            "time_with_others",
            "time_with_others_details",
            "time_with_others_no_reason",
            "assistive_devices",
            "medication_side_effects",
        ],
    )

def extract_function_condition_limits_details(answer_text):
    return extract_with_rules(
        answer_text,
        keys=[
            "affected_abilities",
            "ability_limitations",
            "assistive_devices",
            "medication_side_effects",
            "sleep_affected",
            "sleep_affected_details",
            "function_report_remarks",
        ],
        extra_rules="""
affected_abilities can ONLY contain these exact values:
"Lifting", "Squatting", "Bending", "Standing", "Reaching", "Walking", "Sitting", "Kneeling", "Stair Climbing", "Seeing", "Using Hands", "Remembering", "Completing Tasks", "Concentrating", "Understanding", "Following Instructions", "Getting Along With Others", "Handling Stress", "Handling Changes In Routine", "None"
""",
    )




def show_extraction_suggestions(
    title,
    extracted_key,
    done_key,
    target_dict,
    completed_flag_key=None,
    apply_label="Apply Suggestions",
    ignore_label="Ignore Suggestions",
):
    extracted = st.session_state.get(extracted_key)

    if not extracted:
        return

    st.info(title)

    for key, value in extracted.items():
        if str(value).strip():
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

    if st.button(apply_label):
        for key, value in extracted.items():
            if key in target_dict and value not in ["", None, []]:

                if key == "affected_abilities":
                    valid_options = [
                        "Lifting",
                        "Squatting",
                        "Bending",
                        "Standing",
                        "Reaching",
                        "Walking",
                        "Sitting",
                        "Kneeling",
                        "Stair Climbing",
                        "Seeing",
                        "Using Hands",
                        "Remembering",
                        "Completing Tasks",
                        "Concentrating",
                        "Understanding",
                        "Following Instructions",
                        "Getting Along With Others",
                        "Handling Stress",
                        "Handling Changes In Routine",
                        "None",
                    ]

                    if isinstance(value, list):
                        target_dict[key] = [v for v in value if v in valid_options]
                    else:
                        target_dict[key] = []

                else:
                    target_dict[key] = value

        st.session_state[extracted_key] = {}
        st.session_state[done_key] = True
        if completed_flag_key:
            st.session_state[completed_flag_key] = True



        st.success("Suggestions applied.")
        st.rerun()

    if st.button(ignore_label):
        st.session_state[extracted_key] = {}
        st.session_state[done_key] = True

        if completed_flag_key:
            st.session_state[completed_flag_key] = True

        st.rerun()

def answer_changed_since_extraction(answer_key, current_answer):
    previous_key = f"{answer_key}_last_extracted_answer"

    previous_answer = st.session_state.get(previous_key, "")

    return str(previous_answer).strip() != str(current_answer).strip()

def answer_changed_since_validation(question_key, current_answer):
    previous_key = f"{question_key}_last_validated_answer"
    previous_answer = st.session_state.get(previous_key, "")

    return str(previous_answer).strip() != str(current_answer).strip()

def show_current_question_contradiction(question):
    job = st.session_state.guided_job
    physical = job["physical_activities"]
    key = question.get("key")

    none_values = ["none", "0", "0 minutes", "0 hours", "zero", "n/a", "na", "no"]

    pairs = {
        "fingers_hand_usage": ("fingers_time", "finger/hand use"),
        "grasping_hand_usage": ("grasping_time", "grasping/holding"),
        "reaching_below_arm_usage": ("reaching_below_time", "reaching at/below shoulder level"),
        "reaching_overhead_arm_usage": ("reaching_overhead_time", "reaching overhead"),
    }

    if key not in pairs:
        return

    time_key, label = pairs[key]

    time_answer = str(physical.get(time_key, "")).strip()
    usage_answer = str(physical.get(key, "")).strip()

    if not time_answer:
        return

    if time_answer.lower() not in none_values and usage_answer.lower() == "none":
        st.warning(
            f"⚠️ You previously said you spent time on {label}: **{time_answer}**.\n\n"
            f"If that is correct, please choose One Hand/One Arm or Both Hands/Both Arms. "
            f"If you did not do this activity, go back and change the previous answer to None."
        )
def extract_function_before_conditions_details(answer_text):
    return extract_with_rules(
        answer_text,
        keys=[
            "affected_abilities",
            "ability_limitations",
            "prepare_meals",
            "prepare_meals_no_reason",
            "drive",
            "drive_no_reason",
            "shopping",
            "shopping_no_reason",
            "time_with_others",
            "time_with_others_no_reason",
            "social_changes",
            "function_report_remarks",
        ],
        extra_rules="""
affected_abilities can ONLY contain these exact values:
"Lifting", "Squatting", "Bending", "Standing", "Reaching", "Walking", "Sitting", "Kneeling", "Stair Climbing", "Seeing", "Using Hands", "Remembering", "Completing Tasks", "Concentrating", "Understanding", "Following Instructions", "Getting Along With Others", "Handling Stress", "Handling Changes In Routine", "None"
""",
    )



AI_EXTRACTION_RULES = {
    "daily_routine": {
        "extracted_key": "function_daily_routine_extracted_details",
        "done_suffix": "daily_routine_extraction_done",
        "target_state_key": "function_report",
        "extractor": extract_function_daily_routine_details,
        "message": "✨ I found some possible details from your daily routine answer.",
        "completed_flag_key": "function_daily_routine_extraction_completed_for_report",
    },

        "condition_limits_work": {
        "extracted_key": "function_condition_limits_extracted_details",
        "done_suffix": "condition_limits_extraction_done",
        "target_state_key": "function_report",
        "extractor": extract_function_condition_limits_details,
        "message": "✨ I found some possible details from your condition answer.",
        "completed_flag_key": "function_condition_limits_extraction_completed_for_report",
    },
        "before_conditions": {
        "extracted_key": "function_before_conditions_extracted_details",
        "done_suffix": "before_conditions_extraction_done",
        "target_state_key": "function_report",
        "extractor": extract_function_before_conditions_details,
        "message": "✨ I found some possible details from what you could do before.",
        "completed_flag_key": "function_before_conditions_extraction_completed_for_report",
    },

    }

def run_ai_extraction_if_needed(question, answer_text, unique_key, state_key):
    rule = AI_EXTRACTION_RULES.get(question.get("key"))

    if not rule:
        return

    if rule.get("target_state_key") != state_key:
        return

    done_key = f"{unique_key}_{rule['done_suffix']}"

    if st.session_state.get(done_key):
        return

    extracted = rule["extractor"](answer_text)

    st.write("DEBUG extracted:", extracted)

    useful_extracted = {
        k: v for k, v in extracted.items()
        if v and k in st.session_state[state_key]
    }

    st.write("DEBUG useful:", useful_extracted)

    if useful_extracted:
        st.session_state[rule["extracted_key"]] = useful_extracted
        st.session_state[done_key] = True
        st.rerun()

def client_guided_mode():


    st.title("DDS AI App")
    st.subheader("Client Guided Work History Interview")
    st.caption(APP_DISCLAIMER)
    st.markdown("---")

    
    if st.button("← Back to Form Selection"):
        st.session_state.selected_form = None
        st.rerun()



    if st.session_state.guided_step == 0:
        job_memory_helper()

    st.session_state.guided_step = next_guided_step(st.session_state.guided_step)
    total_steps = len(GUIDED_QUESTIONS)
    step = st.session_state.guided_step

    if step >= total_steps:
        completed_job = repair_job(st.session_state.guided_job)

        st.success(f"Job {st.session_state.guided_job_number} interview complete.")
        show_client_job_review(completed_job, st.session_state.guided_job_number)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Save This Job", use_container_width=True):
                st.session_state.jobs.append(completed_job)
                st.success(f"Job {st.session_state.guided_job_number} saved.")

        with col2:
            if st.button("Save & Add Another Job", use_container_width=True):
                st.session_state.jobs.append(completed_job)
                st.session_state.guided_job_number += 1
                reset_guided_current_job()
                st.rerun()

        with col3:
            edit_options = [
                f"{i + 1}. {q['question']}"
                for i, q in enumerate(GUIDED_QUESTIONS)
                if should_show_guided_question(q)
            ]

            selected_edit = st.selectbox(
                "Need to edit a different answer?",
                edit_options,
                key="edit_question_select"
            )

            if st.button("Edit Selected Answer", use_container_width=True):
                selected_index = int(selected_edit.split(".")[0]) - 1
                st.session_state.editing_from_review = True
                st.session_state.guided_step = selected_index
                st.rerun()

        st.markdown("---")

        if st.session_state.jobs:
            st.markdown("## Saved Jobs")
            for i, job in enumerate(st.session_state.jobs, start=1):
                with st.expander(f"Saved Job {i}: {job.get('job_title', 'Untitled Job')}", expanded=False):
                    show_job_review(job, i)

            filename, case_data = save_case(st.session_state.jobs, "Client Guided Mode")
            st.download_button("Download Case JSON", data=json.dumps(case_data, indent=2), file_name=filename.name, mime="application/json", use_container_width=True)
            st.info(f"Saved locally in your project folder: {filename}")

        if st.button("Start Over", use_container_width=True):
            reset_everything()
            st.rerun()

        return

    question = GUIDED_QUESTIONS[step]
    current_value = get_guided_value(question)
    unique_key = f"guided_job_{st.session_state.guided_job_number}_step_{step}_{question['key']}"

    st.markdown(f"## Job {st.session_state.guided_job_number}")
    render_big_question(question, step, total_steps)

    questions_left = total_steps - (step + 1)
    percent_done = int(((step + 1) / total_steps) * 100)

    st.caption(
        f"You're making great progress. About {percent_done}% complete "
        f"({questions_left} questions remaining)."
    )

    if step >= 5:
        show_job_memory_summary()

    if st.session_state.get("editing_from_review"):
        st.warning("You are editing this answer. Click Next to return to the review page.")

    speech_text = question["question"] + ". " + question.get("helper", "")

    if st.button("🔊 Read Question Aloud", key=f"read_{unique_key}"):
            audio_path = create_question_audio(
                speech_text,
                filename=f"question_audio_{st.session_state.guided_job_number}_{step}.mp3"
            )

            if audio_path:
                st.audio(audio_path, format="audio/mp3")
            else:
                st.warning("Audio could not be created. Please check your OpenAI API key.")

    voice_text_key = f"{unique_key}_voice_text"

    pending_voice_key = f"{unique_key}_pending_voice"

    if st.session_state.get(pending_voice_key):
        current_value = st.session_state[pending_voice_key]
        st.session_state[unique_key] = current_value
        del st.session_state[pending_voice_key]

    answer = render_answer_input(question, current_value, unique_key)

    show_current_question_contradiction(question)

    saved_voice_answer = st.session_state.get(voice_text_key, "")

    if saved_voice_answer and str(answer).strip() and str(answer).strip() != str(saved_voice_answer).strip():
        st.session_state[voice_text_key] = ""
        saved_voice_answer = ""

    if saved_voice_answer:
        st.info(f"Using voice answer: {saved_voice_answer}")

        if st.button("Use typed answer instead", key=f"use_typed_{unique_key}"):
            st.session_state[voice_text_key] = ""
            set_guided_value(question, answer)
            st.rerun()

        answer_for_storage = saved_voice_answer
    else:
        answer_for_storage = answer

    answer_for_storage = normalize_answer(question, answer_for_storage)

    set_guided_value(question, answer_for_storage)
    apply_guided_autofill(question)

    if question.get("check_type"):
        previous_validation_key = f"{unique_key}_previous_validation_answer"
        previous_validation_answer = st.session_state.get(previous_validation_key, "")

        if str(previous_validation_answer).strip() != str(answer_for_storage).strip():
            st.session_state[f"{question['key']}_last_validated_answer"] = ""
            st.session_state[previous_validation_key] = answer_for_storage

    if question["key"] == "job_duties":
        previous_duties_key = f"{unique_key}_previous_duties_answer"
        previous_duties_answer = st.session_state.get(previous_duties_key, "")

        if str(previous_duties_answer).strip() != str(answer_for_storage).strip():
            st.session_state.duties_extraction_completed_for_job = False
            st.session_state.duties_extracted_details = {}
            st.session_state[f"{unique_key}_duties_extraction_done"] = False
            st.session_state[previous_duties_key] = answer_for_storage


    if st.session_state.get("inline_extracted_details"):
        st.info("✨ I found some details in your answer.")

        for key, value in st.session_state.inline_extracted_details.items():
            st.write(f"**{key.replace('_', ' ').title()}:** {value}")

        extraction_done_key = f"{unique_key}_inline_extraction_done"

        if st.button("Apply These Details"):
            for key, value in st.session_state.inline_extracted_details.items():
                if key == "pay_type":
                    clean_value = str(value).lower().strip().replace(".", "")

                    pay_type_map = {
                        # Hour
                        "hour": "hour",
                        "hourly": "hour",
                        "per hour": "hour",
                        "an hour": "hour",
                        "a hour": "hour",
                        "hr": "hour",
                        "hrs": "hour",
                        "/hr": "hour",

                        # Day
                        "day": "day",
                        "daily": "day",
                        "per day": "day",
                        "a day": "day",

                        # Week
                        "week": "week",
                        "weekly": "week",
                        "per week": "week",
                        "a week": "week",

                        # Month
                        "month": "month",
                        "monthly": "month",
                        "per month": "month",
                        "a month": "month",

                        # Year
                        "year": "year",
                        "yearly": "year",
                        "annual": "year",
                        "annually": "year",
                        "salary": "year",
                        "per year": "year",
                        "a year": "year",
                    }

                    st.session_state.guided_job[key] = pay_type_map.get(clean_value, value)
                else:
                    st.session_state.guided_job[key] = value

            st.session_state.inline_extracted_details = {}
            st.session_state[extraction_done_key] = True
            st.session_state.inline_extraction_completed_for_job = True
            st.success("Details applied.")
            st.rerun()

        if st.button("Ignore These Details"):
            st.session_state.inline_extracted_details = {}
            st.session_state[extraction_done_key] = True
            st.rerun()


    duties_done_key = f"{unique_key}_duties_extraction_done"

    show_extraction_suggestions(
        title="✨ I found some possible details from your workday answer.",
        extracted_key="duties_extracted_details",
        done_key=duties_done_key,
        target_dict=st.session_state.guided_job,
        completed_flag_key="duties_extraction_completed_for_job",
    )


    issues = check_in_flow_review_issues(
        st.session_state.guided_job,
        question["key"]
    )

    for issue in issues:
        show_in_flow_review_banner(
            issue["issue_id"],
            issue["message"],
            issue["target_step"]
        )


    if question["type"] in ["text", "textarea"]:
        with st.expander("🎤 Prefer to speak your answer?"):
            audio_answer = st.audio_input(
                "Record your answer",
                key=f"voice_{unique_key}",
            )

            if audio_answer is not None:
                if st.button("Use Voice Answer", key=f"use_voice_{unique_key}"):

                    try:
                        transcript = transcribe_audio(audio_answer)
                    except Exception as e:
                        st.error("Voice transcription failed.")
                        st.write(str(e))
                        transcript = ""

                    st.write("Transcript:", transcript)

                    if transcript:
                        st.session_state[voice_text_key] = transcript
                        st.session_state[f"{unique_key}_pending_voice"] = transcript
                        set_guided_value(question, transcript)

                        st.success("Voice answer added. Click Next to continue.")
                        st.info(transcript)
                        st.rerun()

                    else:
                        st.warning("No transcript was created. Please try again.")
                        st.write("Debug: transcript value was:", transcript)

    with st.expander("💬 Need help with this question?"):
        help_question = st.text_input(
            "Ask a question about this form question",
            key=f"help_question_{unique_key}",
            placeholder="Example: What does this question mean?",
        )

        if st.button("Ask Assistant", key=f"ask_help_{unique_key}"):
            if help_question.strip():
                assistant_response = ask_help_assistant(
                    help_question,
                    question.get("question", ""),
                    answer_for_storage
                )
                st.info(assistant_response)
            else:
                st.warning("Type a question first.")                   


    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Back", disabled=step == 0, use_container_width=True):
            previous_step = step - 1

            while previous_step >= 0:
                if should_show_guided_question(GUIDED_QUESTIONS[previous_step]):
                    st.session_state.guided_step = previous_step
                    st.rerun()

                previous_step -= 1

            st.session_state.guided_step = 0
            st.rerun()

    with col2:
        next_label = "Finish Job" if step == total_steps - 1 else "Next"

        if st.button(next_label, use_container_width=True):
            
            answer_to_check = get_guided_value(question)

            if question["key"] == "pay_rate":
                pay_text = str(answer_to_check).lower()

                if "year" in pay_text or "annual" in pay_text or "annually" in pay_text:
                    st.session_state.guided_job["pay_type"] = "year"
                elif "month" in pay_text or "monthly" in pay_text:
                    st.session_state.guided_job["pay_type"] = "month"
                elif "week" in pay_text or "weekly" in pay_text:
                    st.session_state.guided_job["pay_type"] = "week"
                elif "day" in pay_text or "daily" in pay_text:
                    st.session_state.guided_job["pay_type"] = "day"
                elif "hour" in pay_text or "hourly" in pay_text:
                    st.session_state.guided_job["pay_type"] = "hour"


            extraction_done_key = f"{unique_key}_inline_extraction_done"

            if (
                question["key"] == "job_title"
                and (
                    not st.session_state.get(extraction_done_key)
                    or answer_changed_since_extraction(question["key"], answer_to_check)
                )
            ):
                extracted = extract_inline_job_details(str(answer_to_check))

                useful_extracted = {
                    k: v for k, v in extracted.items()
                    if v and k in st.session_state.guided_job
                }

                meaningful_extractions = [
                    "job_title",
                    "employer",
                    "dates_from",
                    "dates_to",
                    "pay_rate",
                    "pay_type",
                ]

                if any(useful_extracted.get(key) for key in meaningful_extractions):
                    st.session_state["job_title_last_extracted_answer"] = answer_to_check
                    st.session_state.inline_extracted_details = useful_extracted
                    st.rerun()

            duties_done_key = f"{unique_key}_duties_extraction_done"

            if (
                question["key"] == "job_duties"
                and (
                    not st.session_state.get(duties_done_key)
                    or answer_changed_since_extraction(question["key"], answer_to_check)
                )
            ):
                extracted = extract_details_from_job_duties(str(answer_to_check))

                useful_extracted = {
                    k: v for k, v in extracted.items()
                    if v and k in st.session_state.guided_job
                }

                if useful_extracted:
                    st.session_state["job_duties_last_extracted_answer"] = answer_to_check
                    st.session_state.duties_extracted_details = useful_extracted
                    st.rerun()        

            if not run_validation_for_question(question, answer_to_check, unique_key):
                st.stop()

            if st.session_state.get("editing_from_review"):
                next_step = next_guided_step(step + 1)

                if next_step < len(GUIDED_QUESTIONS):
                    next_question = GUIDED_QUESTIONS[next_step]

                    if next_question.get("depends_on"):
                        st.session_state.guided_step = next_step
                    else:
                        st.session_state.editing_from_review = False
                        st.session_state.guided_step = len(GUIDED_QUESTIONS)
                else:
                    st.session_state.editing_from_review = False
                    st.session_state.guided_step = len(GUIDED_QUESTIONS)

            elif st.session_state.get("editing_from_banner"):
                next_step = next_guided_step(step + 1)

                if next_step < len(GUIDED_QUESTIONS):
                    next_question = GUIDED_QUESTIONS[next_step]

                    if next_question.get("depends_on"):
                        st.session_state.guided_step = next_step
                    else:
                        st.session_state.editing_from_banner = False
                        st.session_state.guided_step = st.session_state.get(
                            "return_step_after_banner_edit",
                            next_guided_step(step + 1)
                        )
                else:
                    st.session_state.editing_from_banner = False
                    st.session_state.guided_step = st.session_state.get(
                        "return_step_after_banner_edit",
                        len(GUIDED_QUESTIONS)
                    )

            else:
                next_step = next_guided_step(step + 1)

                if should_skip_after_autofill(question):
                    next_step = next_guided_step(next_step + 1)

                remember_current_answer(
                    question,
                    answer_to_check,
                    source_label="work_history",
                )

                st.session_state.guided_step = next_step

            st.rerun()

    with col3:
        st.progress((step + 1) / total_steps)

        visible_steps = [
            (i, q)
            for i, q in enumerate(GUIDED_QUESTIONS)
            if should_show_guided_question(q)
        ]

        jump_options = [
            f"{i + 1}. {q['question']}"
            for i, q in visible_steps
        ]

        selected_jump = st.selectbox(
            "Review an earlier question",
            ["Stay here"] + jump_options,
            key=f"jump_question_{st.session_state.guided_job_number}_{step}"
        )

        if selected_jump != "Stay here":
            selected_index = int(selected_jump.split(".")[0]) - 1

            if selected_index <= step:
                st.session_state.guided_step = selected_index
                st.rerun()
            else:
                st.warning("You can only jump to questions you already reached.")

def previous_guided_step(start):
    current_question = GUIDED_QUESTIONS[start]

    if current_question.get("key") == "exposure_description":
        return find_question_step("exposure_checkboxes")

    step = start - 1

    while step >= 0:
        if should_show_guided_question(GUIDED_QUESTIONS[step]):
            return step
        step -= 1

    return 0

def format_date_for_pdf_table(date_text):
    date_text = str(date_text or "").strip()

    if not date_text:
        return ""

    if date_text.lower() == "present":
        return "Present"

    for fmt in ["%B %d, %Y", "%B %Y"]:
        try:
            parsed = datetime.strptime(date_text, fmt)
            return parsed.strftime("%m/%Y")
        except:
            pass

    return date_text

def run_validation_for_question(question, answer, unique_key):
    answer_to_validate = str(answer or "").strip()

    if needs_time_unit(question, answer_to_validate):
        st.warning(
            "Please include a time type, such as hours or minutes. "
            "Example: 6 hours, 30 minutes, none, or unknown."
        )
        return False

    if not question.get("check_type"):
        return True

    answer_to_validate = str(answer or "").strip()

    if needs_time_unit(question, answer_to_validate):
        st.warning(
            "Please include a time type, such as hours or minutes. "
            "Example: 6 hours, 30 minutes, none, or unknown."
        )
        return False

    none_like_answers = ["none", "no", "n/a", "na", "not applicable"]

    if answer_to_validate.lower() in none_like_answers:
        return True

    if not answer_to_validate:
        return True

    validation_warning_key = f"{unique_key}_validation_warning_shown"

    if answer_changed_since_validation(question["key"], answer_to_validate):
        st.session_state[validation_warning_key] = False

    validation_text = validate_answer(
        answer_to_validate,
        question["check_type"]
    )

    try:
        validation = json.loads(validation_text)

        status = validation.get("status", "")
        follow_up = validation.get("follow_up_question", "")

        st.session_state[f"{question['key']}_last_validated_answer"] = answer_to_validate

        if status == "Needs Follow-Up":
            if not st.session_state.get(validation_warning_key):
                st.session_state[validation_warning_key] = True
                show_validation_warning(validation, follow_up)
                return False

        elif status == "Usable but Light":
            st.info(f"Optional improvement: {follow_up}")

    except Exception:
        st.warning("AI review could not read the response, but you can continue.")

    return True



def normalize_job_for_pdf(job):
    clean_job = repair_job(job).copy()

    title_text = str(clean_job.get("job_title", "")).strip()
    title_lower = title_text.lower()

    if "house cleaner" in title_lower:
        clean_job["job_title"] = "House Cleaner"
    elif "cleaner" in title_lower:
        clean_job["job_title"] = "Cleaner"
    elif "cook" in title_lower:
        clean_job["job_title"] = "Cook"
    elif "cashier" in title_lower:
        clean_job["job_title"] = "Cashier"

    # Clean pay rate
    pay_text = str(clean_job.get("pay_rate", "")).strip()
    pay_text_lower = pay_text.lower()

    number_match = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", pay_text)

    if number_match:
        clean_job["pay_rate"] = number_match.group(1).replace(",", "")

    # Clean pay type
    combined_pay_text = f"{pay_text_lower} {str(clean_job.get('pay_type', '')).lower()}"

    if "year" in combined_pay_text or "annual" in combined_pay_text or "annually" in combined_pay_text:
        clean_job["pay_type"] = "year"
    elif "month" in combined_pay_text or "monthly" in combined_pay_text:
        clean_job["pay_type"] = "month"
    elif "week" in combined_pay_text or "weekly" in combined_pay_text:
        clean_job["pay_type"] = "week"
    elif "day" in combined_pay_text or "daily" in combined_pay_text:
        clean_job["pay_type"] = "day"
    elif "hour" in combined_pay_text or "hourly" in combined_pay_text:
        clean_job["pay_type"] = "hour"

    # Clean hours per day
    hours_text = str(clean_job.get("hours_per_day", "")).lower().strip()

    number_words = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
        "eleven": "11", "twelve": "12",
    }

    hour_number = re.search(r"(\d+)", hours_text)
    if hour_number:
        clean_job["hours_per_day"] = hour_number.group(1)
    else:
        for word, number in number_words.items():
            if word in hours_text:
                clean_job["hours_per_day"] = number
                break

    # Clean days per week
    days_text = str(clean_job.get("days_per_week", "")).lower().strip()

    day_number = re.search(r"(\d+)", days_text)
    if day_number:
        clean_job["days_per_week"] = day_number.group(1)
    else:
        for word, number in number_words.items():
            if word in days_text:
                clean_job["days_per_week"] = number
                break
        
    clean_job["dates_from"] = format_date_for_pdf_table(clean_job.get("dates_from", ""))
    clean_job["dates_to"] = format_date_for_pdf_table(clean_job.get("dates_to", ""))

    return clean_job 


def guided_interview_mode(questions, state_key, title):
    st.title("DDS AI App")
    st.subheader(title)
    st.caption(APP_DISCLAIMER)
    st.markdown("---")

    if st.button("← Back to Form Selection"):
        st.session_state.selected_form = None
        st.rerun()

    step_key = f"{state_key}_step"

    if step_key not in st.session_state:
        st.session_state[step_key] = 0

    if state_key not in st.session_state:
        st.session_state[state_key] = {}

    def should_show_question(q):
        depends_on = q.get("depends_on")
        if not depends_on:
            return True

        parent_key = depends_on.get("key")
        required_value = depends_on.get("value")
        required_contains = depends_on.get("contains")

        current_value = st.session_state[state_key].get(parent_key, "")

        if required_contains:
            if isinstance(current_value, list):
                return required_contains in current_value
            return required_contains in str(current_value)

        return str(current_value).strip() == str(required_value).strip()

    def next_visible_step(start):
        while start < len(questions):
            if should_show_question(questions[start]):
                return start
            start += 1
        return len(questions)

    st.session_state[step_key] = next_visible_step(st.session_state[step_key])

    total_steps = len(questions)
    step = st.session_state[step_key]

    if step >= total_steps:
        st.success("Interview complete.")

        if state_key == "function_report":
            show_function_report_review(st.session_state[state_key])

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("✏️ Back to Edit", use_container_width=True):
                    st.session_state[step_key] = 0
                    st.rerun()

            with col2:
                if st.button("💾 Save Function Report", use_container_width=True):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = CASES_FOLDER / f"function_report_{timestamp}.json"

                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(st.session_state[state_key], f, indent=2)

                    st.success(f"Function Report saved: {filename}")

            with col3:
                if st.button("Start Over", use_container_width=True):
                    st.session_state[step_key] = 0
                    st.session_state[state_key] = empty_function_report()
                    st.rerun()

        else:
            st.json(st.session_state[state_key])

            if st.button("Start Over", use_container_width=True):
                st.session_state[step_key] = 0
                st.session_state[state_key] = {}
                st.rerun()

        return

    question = questions[step]
    current_value = st.session_state[state_key].get(question["key"], "")
    unique_key = f"{state_key}_{step}_{question['key']}"

    render_big_question(question, step, total_steps)

    questions_left = total_steps - (step + 1)
    percent_done = int(((step + 1) / total_steps) * 100)

    st.caption(
        f"You're making great progress. About {percent_done}% complete "
        f"({questions_left} questions remaining)."
    )

    speech_text = question["question"] + ". " + question.get("helper", "")

    if st.button("🔊 Read Question Aloud", key=f"read_{unique_key}"):
        audio_path = create_question_audio(
            speech_text,
            filename=f"question_audio_{state_key}_{step}_{question['key']}.mp3"
        )

        if audio_path:
            with open(audio_path, "rb") as audio_file:
                st.audio(audio_file.read(), format="audio/mp3")
        else:
            st.warning("Audio could not be created. Please check your OpenAI API key.")

    voice_text_key = f"{unique_key}_voice_text"
    pending_voice_key = f"{unique_key}_pending_voice"

    if st.session_state.get(pending_voice_key):
        current_value = st.session_state[pending_voice_key]
        st.session_state[unique_key] = current_value
        del st.session_state[pending_voice_key]

    answer = render_answer_input(question, current_value, unique_key)

    saved_voice_answer = st.session_state.get(voice_text_key, "")

    if saved_voice_answer and str(answer).strip() and str(answer).strip() != str(saved_voice_answer).strip():
        st.session_state[voice_text_key] = ""
        saved_voice_answer = ""

    if saved_voice_answer:
        st.info(f"Using voice answer: {saved_voice_answer}")

        if st.button("Use typed answer instead", key=f"use_typed_{unique_key}"):
            st.session_state[voice_text_key] = ""
            st.session_state[state_key][question["key"]] = answer
            st.rerun()

        answer_for_storage = saved_voice_answer
    else:
        answer_for_storage = answer

    st.session_state[state_key][question["key"]] = answer_for_storage

    show_cross_form_memory(
        question,
        st.session_state[state_key],
    )


    rule = AI_EXTRACTION_RULES.get(question.get("key"))

    if rule and rule.get("target_state_key") == state_key:
        done_key = f"{unique_key}_{rule['done_suffix']}"

        show_extraction_suggestions(
            title=rule["message"],
            extracted_key=rule["extracted_key"],
            done_key=done_key,
            target_dict=st.session_state[state_key],
            completed_flag_key=rule.get("completed_flag_key"),
        )

    if question["type"] in ["text", "textarea"]:
        with st.expander("🎤 Prefer to speak your answer?"):
            audio_answer = st.audio_input(
                "Record your answer",
                key=f"voice_{unique_key}",
            )

            if audio_answer is not None:
                if st.button("Use Voice Answer", key=f"use_voice_{unique_key}"):

                    try:
                        transcript = transcribe_audio(audio_answer)
                    except Exception as e:
                        st.error("Voice transcription failed.")
                        st.write(str(e))
                        transcript = ""

                    if transcript:
                        st.session_state[voice_text_key] = transcript
                        st.session_state[pending_voice_key] = transcript
                        st.session_state[state_key][question["key"]] = transcript

                        st.success("Voice answer added. Click Next to continue.")
                        st.info(transcript)
                        st.rerun()
                    else:
                        st.warning("No transcript was created. Please try again.") 

    with st.expander("💬 Need help with this question?"):
        help_question = st.text_input(
            "Ask the assistant",
            key=f"help_question_{unique_key}"
        )

        if st.button("Ask Assistant", key=f"ask_help_{unique_key}"):
            if help_question.strip():
                assistant_response = ask_help_assistant(
                    help_question,
                    question.get("question", ""),
                    answer_for_storage
                )
                st.info(assistant_response)
            else:
                st.warning("Type a question first.")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Back", disabled=step == 0, use_container_width=True):
            previous_step = step - 1

            while previous_step >= 0:
                if should_show_question(questions[previous_step]):
                    st.session_state[step_key] = previous_step
                    st.rerun()

                previous_step -= 1

            st.session_state[step_key] = 0
            st.rerun()

    with col2:
        next_label = "Finish" if step == total_steps - 1 else "Next"

        if st.button(next_label, use_container_width=True):

            answer_to_check = st.session_state[state_key].get(
                question["key"], ""
            )

            run_ai_extraction_if_needed(
                question,
                answer_to_check,
                unique_key,
                state_key,
            )

            if st.session_state.get("function_daily_routine_extracted_details"):
                st.warning("Please review the AI suggestions above. Click Apply Suggestions or Ignore Suggestions before continuing.")
                st.stop() 

            if question.get("check_type"):
                answer_to_validate = str(answer_to_check).strip()

                

                none_like_answers = [
                    "none",
                    "no",
                    "n/a",
                    "na",
                    "not applicable",
                ]

                if answer_to_validate.lower() in none_like_answers:
                    pass

                elif answer_to_validate:

                    validation_warning_key = f"{unique_key}_validation_warning_shown"

                    if answer_changed_since_validation(question["key"], answer_to_validate):
                        st.session_state[validation_warning_key] = False

                    validation_text = validate_answer(
                        answer_to_validate,
                        question["check_type"]
                    )

                    try:
                        validation = json.loads(validation_text)

                        status = validation.get("status", "")
                        follow_up = validation.get("follow_up_question", "")
                        st.session_state[f"{question['key']}_last_validated_answer"] = answer_to_validate

                        if status == "Needs Follow-Up":

                            if not st.session_state.get(validation_warning_key):
                                st.session_state[validation_warning_key] = True

                                st.warning(
                                    "⚠️ Please add more detail before moving forward.\n\n"
                                    + (
                                        follow_up
                                        or "This answer needs a little more detail."
                                    )
                                )

                                st.info("You can revise your answer, or click Next again to continue.")
                                st.stop()

                        elif status == "Usable but Light":
                            st.info(f"Optional improvement: {follow_up}")

                    except Exception:
                        st.warning(
                            "AI review could not read the response, but you can continue."
                        )
          
            remember_current_answer(
                question,
                answer_to_check,
                source_label=state_key,

                
            )
            
            st.session_state[step_key] = next_visible_step(step + 1)
            st.rerun()

    with col3:
        st.progress((step + 1) / total_steps)

        visible_steps = [
            (i, q)
            for i, q in enumerate(questions)
            if should_show_question(q) and i <= step
        ]

        jump_options = [
            f"{i + 1}. {q['question']}"
            for i, q in visible_steps
        ]

        selected_jump = st.selectbox(
            "Review an earlier question",
            ["Stay here"] + jump_options,
            key=f"jump_question_{state_key}_{step}"
        )

        if selected_jump != "Stay here":
            selected_index = int(selected_jump.split(".")[0]) - 1
            st.session_state[step_key] = selected_index
            st.rerun()



def generate_case_pdf(jobs, output_path="work_history_report.pdf"):
    clean_jobs = [normalize_job_for_pdf(job) for job in jobs]

    case_data = {
        "jobs": clean_jobs,
        "client_name": "",
        "ssn": "",
        "primary_phone": "",
        "secondary_phone": "",
        "remarks": "",
        "date_completed": datetime.now().strftime("%m/%d/%Y"),
        "who_completed": "The person listed in Section 1.A.",
        "preparer_name": "",
        "preparer_relationship": "",
        "preparer_address": "",
        "preparer_city": "",
        "preparer_state": "",
        "preparer_zip": "",
        "preparer_country": "",
        "preparer_phone": "",
    }

    fill_work_history_pdf(case_data, output_path)
    return output_path

def generate_case_manager_summary(job):
    if openai_client is None:
        return "OpenAI API key is missing. Summary cannot be generated."

    job = repair_job(job)

    prompt = f"""
You are helping a disability case manager quickly understand a client's work history.

Create a concise case-manager summary from the job data below.

Rules:
- Do not give legal advice.
- Do not decide disability or eligibility.
- Do not add facts.
- Only summarize what is provided.
- If something is unclear or missing, list it under "Review Items."
- Use plain English.
- Keep it organized and easy to scan.
- Help users determine whether their answer may need more detail.

Job data:
{json.dumps(job, indent=2)}

Format:

Job Overview:
...

Main Duties:
...

Physical Demands:
...

People Interaction:
...

Lifting/Carrying:
...

Environmental Exposures:
...

Medical Condition Impact:
...

Review Items:
...
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content













def case_manager_mode():
    st.title("DDS AI App")
    st.subheader("Case Manager Work History Entry")
    st.caption(APP_DISCLAIMER)
    st.markdown("---")

    if not st.session_state.jobs:
        st.session_state.jobs = [empty_job()]

    top_col1, top_col2 = st.columns([1, 3])

    with top_col1:
        if st.button("Add Another Job"):
            st.session_state.jobs.append(empty_job())
            st.rerun()

    with top_col2:
        st.info("Client Guided Mode and Case Manager Mode now use the same job structure.")

    pay_options = ["hour", "day", "week", "month", "year"]
    yes_no_options = ["No", "Yes"]
    hand_options = ["None", "One Hand", "Both Hands"]
    arm_options = ["None", "One Arm", "Both Arms"]
    heaviest_options = ["", "less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"]
    frequent_options = ["", "less_than_1", "less_than_10", "10", "25", "50_or_more", "other"]

    for i, job in enumerate(st.session_state.jobs):
        job = repair_job(job)
        st.session_state.jobs[i] = job
        physical = job["physical_activities"]
        exposures = job["exposures"]

        with st.expander(f"Job {i + 1}: {job.get('job_title') or 'Untitled Job'}", expanded=True):
            st.markdown(f"## Job {i + 1}")
            col1, col2 = st.columns(2)

            with col1:
                job["job_title"] = st.text_input("Job title", value=job["job_title"], key=f"cm_job_title_{i}")
                job["employer"] = st.text_input("Employer/business", value=job["employer"], key=f"cm_employer_{i}")
                job["dates_from"] = st.text_input("Date started", value=job["dates_from"], key=f"cm_dates_from_{i}")
                job["dates_to"] = st.text_input("Date ended", value=job["dates_to"], key=f"cm_dates_to_{i}")

            with col2:
                job["pay_rate"] = st.text_input("Rate of pay", value=job["pay_rate"], key=f"cm_pay_rate_{i}")
                job["pay_type"] = st.selectbox("Pay type", pay_options, index=safe_index(pay_options, job["pay_type"]), key=f"cm_pay_type_{i}")
                job["hours_per_day"] = st.text_input("Hours per day", value=job["hours_per_day"], key=f"cm_hours_per_day_{i}")
                job["days_per_week"] = st.text_input("Days per week", value=job["days_per_week"], key=f"cm_days_per_week_{i}")

            st.markdown("### Duties and Work Details")
            job["job_duties"] = st.text_area("Typical workday duties", value=job["job_duties"], key=f"cm_job_duties_{i}", height=120)
            job["reports"] = st.text_area("Writing, reports, forms, or computer work", value=job["reports"], key=f"cm_reports_{i}", height=90)
            job["supervise"] = st.text_area("Supervision duties", value=job["supervise"], key=f"cm_supervise_{i}", height=90)
            job["equipment"] = st.text_area("Tools, machines, or equipment used", value=job["equipment"], key=f"cm_equipment_{i}", height=90)

            job["interacted_with_people"] = st.radio("Did this job require interaction with people?", yes_no_options, index=safe_index(yes_no_options, job["interacted_with_people"]), key=f"cm_interacted_with_people_{i}", horizontal=True)

            if job["interacted_with_people"] == "Yes":
                job["interaction_details"] = st.text_area("Describe who they interacted with, why, how often, and how much time per day/week.", value=job["interaction_details"], key=f"cm_interaction_details_{i}", height=100)
            else:
                job["interaction_details"] = ""

            st.markdown("### Physical Activities")
            col1, col2 = st.columns(2)

            with col1:
                for field, label in [
                    ("standing_walking", "Standing/walking per workday"),
                    ("sitting", "Sitting per workday"),
                    ("stooping", "Stooping/bending per workday"),
                    ("kneeling", "Kneeling per workday"),
                    ("crouching", "Crouching per workday"),
                    ("crawling", "Crawling per workday"),
                    ("stairs", "Climbing stairs or ramps"),
                    ("ladders", "Climbing ladders, ropes, or scaffolds"),
                ]:
                    physical[field] = st.text_input(label, value=physical[field], key=f"cm_{field}_{i}")

            with col2:
                physical["fingers_time"] = st.text_input("Using fingers for small objects/typing", value=physical["fingers_time"], key=f"cm_fingers_time_{i}")
                physical["fingers_hand_usage"] = st.radio("Finger use involved:", hand_options, index=safe_index(hand_options, physical["fingers_hand_usage"]), key=f"cm_fingers_hand_usage_{i}", horizontal=True)

                physical["grasping_time"] = st.text_input("Grasping/holding/turning objects", value=physical["grasping_time"], key=f"cm_grasping_time_{i}")
                physical["grasping_hand_usage"] = st.radio("Grasping involved:", hand_options, index=safe_index(hand_options, physical["grasping_hand_usage"]), key=f"cm_grasping_hand_usage_{i}", horizontal=True)

                physical["reaching_below_time"] = st.text_input("Reaching at/below shoulder level", value=physical["reaching_below_time"], key=f"cm_reaching_below_time_{i}")
                physical["reaching_below_arm_usage"] = st.radio("At/below shoulder reaching involved:", arm_options, index=safe_index(arm_options, physical["reaching_below_arm_usage"]), key=f"cm_reaching_below_arm_usage_{i}", horizontal=True)

                physical["reaching_overhead_time"] = st.text_input("Reaching overhead", value=physical["reaching_overhead_time"], key=f"cm_reaching_overhead_time_{i}")
                physical["reaching_overhead_arm_usage"] = st.radio("Overhead reaching involved:", arm_options, index=safe_index(arm_options, physical["reaching_overhead_arm_usage"]), key=f"cm_reaching_overhead_arm_usage_{i}", horizontal=True)

            st.markdown("### Lifting and Carrying")
            job["lifting_description"] = st.text_area("Explain what they lifted/carried, how far, and how often", value=job["lifting_description"], key=f"cm_lifting_description_{i}", height=100)

            col_a, col_b = st.columns(2)
            with col_a:
                job["heaviest_lift"] = st.selectbox("Heaviest weight lifted", heaviest_options, index=safe_index(heaviest_options, job["heaviest_lift"]), key=f"cm_heaviest_lift_{i}")
                if job["heaviest_lift"] == "other":
                    job["other_lift_text"] = st.text_input("What was the heaviest weight?", value=job["other_lift_text"], key=f"cm_other_lift_text_{i}")
                else:
                    job["other_lift_text"] = ""

            with col_b:
                job["frequent_lift"] = st.selectbox("Weight frequently lifted", frequent_options, index=safe_index(frequent_options, job["frequent_lift"]), key=f"cm_frequent_lift_{i}")
                if job["frequent_lift"] == "other":
                    job["other_frequent_lift_text"] = st.text_input("What weight did they frequently lift?", value=job["other_frequent_lift_text"], key=f"cm_other_frequent_lift_text_{i}")
                else:
                    job["other_frequent_lift_text"] = ""

            st.markdown("### Environmental Exposures")
            col1, col2, col3 = st.columns(3)

            with col1:
                exposures["outdoors"] = st.checkbox("Outdoors", value=exposures["outdoors"], key=f"cm_outdoors_{i}")
                exposures["heat"] = st.checkbox("Extreme heat", value=exposures["heat"], key=f"cm_heat_{i}")
                exposures["cold"] = st.checkbox("Extreme cold", value=exposures["cold"], key=f"cm_cold_{i}")
                exposures["wetness"] = st.checkbox("Wetness", value=exposures["wetness"], key=f"cm_wetness_{i}")

            with col2:
                exposures["humidity"] = st.checkbox("Humidity", value=exposures["humidity"], key=f"cm_humidity_{i}")
                exposures["hazardous_substances"] = st.checkbox("Hazardous substances", value=exposures["hazardous_substances"], key=f"cm_hazardous_substances_{i}")
                exposures["moving_parts"] = st.checkbox("Moving mechanical parts", value=exposures["moving_parts"], key=f"cm_moving_parts_{i}")
                exposures["heights"] = st.checkbox("High exposed places", value=exposures["heights"], key=f"cm_heights_{i}")

            with col3:
                exposures["vibrations"] = st.checkbox("Heavy vibrations", value=exposures["vibrations"], key=f"cm_vibrations_{i}")
                exposures["loud_noise"] = st.checkbox("Loud noises", value=exposures["loud_noise"], key=f"cm_loud_noise_{i}")
                exposures["other"] = st.checkbox("Other exposure", value=exposures["other"], key=f"cm_other_exposure_{i}")

            job["other_exposure_text"] = st.text_input("If Other exposure, explain", value=job["other_exposure_text"], key=f"cm_other_exposure_text_{i}")
            job["exposure_description"] = st.text_area("Explain exposures and how often", value=job["exposure_description"], key=f"cm_exposure_description_{i}", height=90)
            job["medical_conditions"] = st.text_area("Explain how medical conditions affect ability to do this job", value=job["medical_conditions"], key=f"cm_medical_conditions_{i}", height=100)
            job["extra_notes"] = st.text_area("Extra notes", value=job["extra_notes"], key=f"cm_extra_notes_{i}", height=80)

            if st.button(f"Remove Job {i + 1}", key=f"remove_job_{i}"):
                if len(st.session_state.jobs) > 1:
                    st.session_state.jobs.pop(i)
                    st.rerun()
                else:
                    st.warning("At least one job must remain.")

    st.markdown("---")
    st.markdown("## Review")
   
    for idx, job in enumerate(st.session_state.jobs, start=1):
        with st.expander(
            f"Review Job {idx}: {job.get('job_title') or 'Untitled Job'}",
            expanded=False
        ):
            if st.button(f"Generate AI Summary for Job {idx}", key=f"summary_job_{idx}"):
                st.session_state[f"ai_summary_job_{idx}"] = generate_case_manager_summary(job)

            if st.session_state.get(f"ai_summary_job_{idx}"):
                st.markdown("### AI Case Manager Summary")
                st.info(st.session_state[f"ai_summary_job_{idx}"])

            st.markdown("### Full Job Answers")
            show_job_review(job, idx)


    if st.button("Save Case", use_container_width=True):
        filename, case_data = save_case(
            st.session_state.jobs,
            "Case Manager Mode"
        )

        st.success(f"Case saved locally: {filename}")

    if st.button("Generate PDF", use_container_width=True):
        st.session_state.generated_pdf_path = generate_case_pdf(
            st.session_state.jobs
        )

    if "generated_pdf_path" in st.session_state:
        pdf_path = st.session_state.generated_pdf_path

        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="Download Work History PDF",
                data=pdf_file,
                file_name="work_history_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
mode = st.sidebar.radio("Choose App Mode", ["Client Guided Mode", "Function Report", "Case Manager Mode"])
st.sidebar.markdown("---")
st.sidebar.caption(APP_DISCLAIMER)

if st.sidebar.button("Reset App"):
    reset_everything()
    st.rerun()

if mode == "Client Guided Mode":
    if st.session_state.selected_form is None:
        document_selector()
    elif st.session_state.selected_form == "ssa_3369":
        client_guided_mode()
    elif st.session_state.selected_form == "ssa_3373":
        guided_interview_mode(
            FUNCTION_REPORT_QUESTIONS,
            "function_report",
            "Client Guided Function Report"
        )
else:
    case_manager_mode()