
import json
from datetime import datetime
from pathlib import Path
import streamlit as st
from fill_pdf import fill_work_history_pdf
import os 
from openai import OpenAI
import json
from ai_validation_engine import validate_answer




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
    months = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    days = [""] + [str(i) for i in range(1, 32)]
    years = ["", "Present"] + [str(y) for y in range(2026, 1950, -1)]

    col1, col2, col3 = st.columns(3)

    with col1:
        month = st.selectbox("Month", months, key=f"{key_prefix}_month")
    with col2:
        day = st.selectbox("Day", days, key=f"{key_prefix}_day")
    with col3:
        year = st.selectbox("Year", years, key=f"{key_prefix}_year")

    if year == "Present":
        return "Present"
    if month and year:
        return f"{month} {day + ', ' if day else ''}{year}"
    return current_value


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
        "jobs": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


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


def reset_guided_current_job():
    st.session_state.guided_step = 0
    st.session_state.guided_job = empty_job()


def reset_everything():
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
    {"key": "pay_type", "target": "job", "icon": "💵", "question": "Was that pay by hour, day, week, month, or year?", "helper": "Choose the closest option.", "type": "select", "options": ["hour", "day", "week", "month", "year"]},
    {"key": "hours_per_day", "target": "job", "icon": "⏰", "question": "How many hours did you usually work per day?", "helper": "Example: 8 hours, 4 hours, varied, or unknown.", "type": "text"},
    {"key": "days_per_week", "target": "job", "icon": "🗓️", "question": "How many days did you usually work per week?", "helper": "Example: 5 days, 3 days, varied, or unknown.", "type": "text"},
    {"key": "job_duties", "target": "job", "icon": "📝", "question": "What did you do during a typical workday?", "helper": "Describe the main tasks you did.", "type": "textarea", "check_type": "job_duties"},
    {"key": "reports", "target": "job", "icon": "📄", "question": "Did this job involve writing, reports, forms, or computer work?", "helper": "Write No if it did not. If yes, describe what you completed and about how often.", "type": "textarea", "check_type": "reports"},
    {"key": "supervise", "target": "job", "icon": "👥", "question": "Did you supervise other people?", "helper": "Write No if not. If yes, describe who/how many and what you did.", "type": "textarea"},
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
    {"key": "exposure_checkboxes","target": "exposures","icon": "⚠️","question": "Which environmental exposures did this job have?","helper": "Select all that apply. If none apply, leave this blank and explain None on the next question.", "type": "multiselect","options": ["outdoors","heat","cold","wetness","humidity","hazardous_substances","moving_parts","heights","vibrations","loud_noise","other",],
     },
    {"key": "exposure_description", "target": "job", "icon": "⚠️", "question": "Were you exposed to heat, cold, wetness, fumes, noise, heights, moving machinery, or other hazards?", "helper": "If none, write None. If yes, describe what you were exposed to and how often.", "type": "textarea"},
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
    return st.session_state.guided_job.get(dep["key"]) == dep["value"]


def next_guided_step(start):
    step = start
    while step < len(GUIDED_QUESTIONS):
        if should_show_guided_question(GUIDED_QUESTIONS[step]):
            return step
        step += 1
    return len(GUIDED_QUESTIONS)


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

    for key in physical_required:
        if is_blank(physical.get(key)):
            warnings.append(f"Job {job_number}: Missing physical activity field: {key}.")

    if job.get("interacted_with_people") == "Yes" and is_blank(job.get("interaction_details")):
        warnings.append(f"Job {job_number}: Interaction details are required because interaction is marked Yes.")

    unit_words = ["hour", "hours", "hr", "hrs", "minute", "minutes", "min", "mins", "none", "n/a", "na", "unknown", "don't know", "dont know", "varied", "rarely"]
    for key, value in physical.items():
        if key.endswith("_usage"):
            continue
        clean = str(value or "").strip().lower()
        if clean and clean.isdigit():
            warnings.append(f"Job {job_number}: '{key}' says only '{value}'. Add a unit like hours/minutes or write None.")
        elif clean and not any(unit in clean for unit in unit_words):
            warnings.append(f"Job {job_number}: '{key}' may need a unit like hours/minutes or write None.")

       # -----------------------------
    # Review checks / contradiction checks
    # -----------------------------

    duties_text = str(job.get("job_duties", "")).lower()
    lifting_text = str(job.get("lifting_description", "")).lower()
    interaction_text = str(job.get("interaction_details", "")).lower()

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

    if hours_worked is not None and total_physical_hours > hours_worked + 2:
        warnings.append(
            f"Job {job_number}: Please review — some activity times may be longer than the hours worked per day."
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
    if warnings:
        with st.expander(f"Please Review Job {job_number}", expanded=True):
            for warning in warnings:
                st.warning(warning)
    else:
        st.success(f"Job {job_number} looks complete enough for review.")

def ask_help_assistant(user_question, current_form_question=""):
    if openai_client is None:
        return "OpenAI API key is missing. Please set OPENAI_API_KEY before using the help assistant."

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

Current form question:
{current_form_question}

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
            "This is a voice answer for a DDS Work History Report. "
            "The speaker may mention job duties, employers, dates, hours, days per week, "
            "standing, walking, sitting, stooping, kneeling, crouching, crawling, lifting, "
            "carrying, reaching, handling, grasping, tools, equipment, customers, coworkers, "
            "supervisors, symptoms, pain, fatigue, and environmental exposures. "
            "Transcribe clearly and keep the user's words as spoken."
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

def client_guided_mode():
    st.title("DDS AI App")
    st.subheader("Client Guided Work History Interview")
    st.caption(APP_DISCLAIMER)
    st.markdown("---")

    st.session_state.guided_step = next_guided_step(st.session_state.guided_step)
    total_steps = len(GUIDED_QUESTIONS)
    step = st.session_state.guided_step

    if step >= total_steps:
        completed_job = repair_job(st.session_state.guided_job)

        st.success(f"Job {st.session_state.guided_job_number} interview complete.")
        st.markdown("## Review This Job")
        show_job_review(completed_job, st.session_state.guided_job_number)

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
            if st.button("Edit This Job", use_container_width=True):
                st.session_state.guided_step = 0
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

    answer = render_answer_input(question, current_value, unique_key)

    saved_voice_answer = st.session_state.get(voice_text_key, "")
    answer_for_storage = saved_voice_answer if saved_voice_answer else answer

    set_guided_value(question, answer_for_storage)

    if saved_voice_answer:
        st.info(f"Using voice answer: {saved_voice_answer}")

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
                        set_guided_value(question, transcript)

                        st.success("Voice answer added. Click Next to continue.")
                        st.info(transcript)

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
                        question.get("question", "")
                    )
                    st.info(assistant_response)
                else:
                    st.warning("Type a question first.")         




    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Back", disabled=step == 0, use_container_width=True):
            st.session_state.guided_step = max(0, step - 1)
            st.rerun()

    with col2:
        next_label = "Finish Job" if step == total_steps - 1 else "Next"

        if st.button(next_label, use_container_width=True):

            if question.get("check_type"):
                answer_to_validate = str(get_guided_value(question)).strip()

                if answer_to_validate:
                    validation_text = validate_answer(
                        answer_to_validate,
                        question["check_type"]
                    )

                    try:
                        validation = json.loads(validation_text)

                        status = validation.get("status", "")
                        follow_up = validation.get("follow_up_question", "")

                        if status == "Needs Follow-Up":
                            st.warning(follow_up or "This answer needs a little more detail.")
                            st.stop()

                        
                        elif status == "Usable but Light":
                            st.info(f"Optional improvement: {follow_up}")

                    except Exception:
                        st.warning("AI review could not read the response, but you can continue.")
        
            st.session_state.guided_step = next_guided_step(step + 1)
            st.rerun()

    with col3:
        st.progress((step + 1) / total_steps)

def generate_case_pdf(jobs, output_path="work_history_report.pdf"):
    case_data = {
        "jobs": jobs,
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
mode = st.sidebar.radio("Choose App Mode", ["Client Guided Mode", "Case Manager Mode"])
st.sidebar.markdown("---")
st.sidebar.caption(APP_DISCLAIMER)

if st.sidebar.button("Reset App"):
    reset_everything()
    st.rerun()

if mode == "Client Guided Mode":
    client_guided_mode()
else:
    case_manager_mode()