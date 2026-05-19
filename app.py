import streamlit as st
import json
import os
from datetime import datetime

from fill_pdf import fill_work_history_pdf

CASES_FOLDER = "cases"
os.makedirs(CASES_FOLDER, exist_ok=True)

st.set_page_config(page_title="DDS AI App", layout="wide")

st.title("DDS AI App")
st.subheader("Work History Report Generator")


# -----------------------------
# Helper Functions
# -----------------------------

def clean_filename(name):
    return name.lower().strip().replace(" ", "_")


def save_case(case_data):
    client_name = case_data.get("client_name", "untitled_case")
    filename = clean_filename(client_name) + "_work_history.json"
    filepath = os.path.join(CASES_FOLDER, filename)

    with open(filepath, "w") as f:
        json.dump(case_data, f, indent=4)

    return filepath


def load_case(filename):
    filepath = os.path.join(CASES_FOLDER, filename)

    with open(filepath, "r") as f:
        return json.load(f)


def list_saved_cases():
    return [file for file in os.listdir(CASES_FOLDER) if file.endswith(".json")]


# -----------------------------
# Session State Setup
# -----------------------------

if "jobs" not in st.session_state:
    st.session_state.jobs = [{}]

if "client_name" not in st.session_state:
    st.session_state.client_name = ""


# -----------------------------
# Sidebar Load Case
# -----------------------------

st.sidebar.header("Saved Cases")

saved_cases = list_saved_cases()

if saved_cases:
    selected_case = st.sidebar.selectbox("Load a saved case", saved_cases)

    if st.sidebar.button("Load Case"):
        loaded_data = load_case(selected_case)

        st.session_state.client_name = loaded_data.get("client_name", "")
        st.session_state.jobs = loaded_data.get("jobs", [{}])

        st.sidebar.success("Case loaded successfully.")
        st.rerun()
else:
    st.sidebar.info("No saved cases yet.")


# -----------------------------
# Client Information
# -----------------------------

st.header("Client Information")

st.session_state.client_name = st.text_input(
    "Client Name",
    value=st.session_state.client_name,
    placeholder="Example: John Smith"
)

ssn = st.text_input(
    "Social Security Number",
    placeholder="Example: 123-45-6789"
)

primary_phone = st.text_input(
    "Primary Phone",
    placeholder="Example: 555-123-4567"
)

secondary_phone = st.text_input(
    "Secondary Phone",
    placeholder="Optional"
)


# -----------------------------
# Job Entry Section
# -----------------------------

st.header("Work History Jobs")

if st.button("Add Another Job"):
    st.session_state.jobs.append({})
    st.rerun()


for i, job in enumerate(st.session_state.jobs):
    st.divider()
    st.markdown(f"## Job {i + 1}")

    col1, col2 = st.columns(2)

    with col1:
        job["job_title"] = st.text_input(
            "Job Title",
            value=job.get("job_title", ""),
            placeholder="Example: Cook",
            key=f"job_title_{i}"
        )

        job["employer"] = st.text_input(
            "Type of Business / Employer",
            value=job.get("employer", ""),
            placeholder="Example: Fast food restaurant",
            key=f"employer_{i}"
        )

        date_col1, date_col2 = st.columns(2)

        with date_col1:
            job["dates_from"] = st.text_input(
                "Date Started",
                value=job.get("dates_from", ""),
                placeholder="MM/YYYY",
                key=f"dates_from_{i}"
            )

        with date_col2:
            job["dates_to"] = st.text_input(
                "Date Ended",
                value=job.get("dates_to", ""),
                placeholder="MM/YYYY or Present",
                key=f"dates_to_{i}"
            )

    with col2:
        job["pay_rate"] = st.text_input(
            "Rate of Pay",
            value=job.get("pay_rate", ""),
            placeholder="Example: 15"
            ,
            key=f"pay_rate_{i}"
        )

        job["pay_type"] = st.selectbox(
            "Pay Type",
            ["hour", "day", "week", "month", "year"],
            index=["hour", "day", "week", "month", "year"].index(
                job.get("pay_type", "hour")
            ) if job.get("pay_type", "hour") in ["hour", "day", "week", "month", "year"] else 0,
            key=f"pay_type_{i}"
        )

        job["hours_per_day"] = st.text_input(
            "Hours Per Day",
            value=job.get("hours_per_day", ""),
            placeholder="Example: 8",
            key=f"hours_per_day_{i}"
        )

        job["days_per_week"] = st.text_input(
            "Days Per Week",
            value=job.get("days_per_week", ""),
            placeholder="Example: 5",
            key=f"days_per_week_{i}"
        )


    # -----------------------------
    # Phase 2: Job Duties
    # -----------------------------

    st.markdown("#### Job Duties and Work Details")

    job["job_duties"] = st.text_area(
        "Describe the tasks performed in a typical workday",
        value=job.get("job_duties", ""),
        placeholder="Example: Cooked food, cleaned work stations, prepared orders, stocked supplies.",
        key=f"job_duties_{i}"
    )

    job["reports"] = st.text_area(
        "Did the job involve writing or completing reports?",
        value=job.get("reports", ""),
        placeholder="Example: No reports. OR Completed daily food safety logs for 15 minutes per shift.",
        key=f"reports_{i}"
    )

    job["supervise"] = st.text_area(
        "Did the job involve supervising other people?",
        value=job.get("supervise", ""),
        placeholder="Example: No supervisory duties. OR Supervised 3 employees and made schedules.",
        key=f"supervise_{i}"
    )

    job["equipment"] = st.text_area(
        "List machines, tools, or equipment used regularly",
        value=job.get("equipment", ""),
        placeholder="Example: Grill, fryer, oven, mop, cash register, headset.",
        key=f"equipment_{i}"
    )

    interaction_value = st.radio(
        "Did this job require interaction with coworkers, the public, or anyone else?",
        ["Yes", "No"],
        index=0 if job.get("interacted_with_people", "No") == "Yes" else 1,
        key=f"interacted_with_people_{i}"
    )

    job["interacted_with_people"] = interaction_value

    if interaction_value == "Yes":
        job["interact"] = st.text_area(
            "Describe who they interacted with, why, how, and how often",
            value=job.get("interact", ""),
            placeholder="Example: Interacted with coworkers and customers in person throughout the shift.",
            key=f"interact_{i}"
        )
    else:
        job["interact"] = ""


    # -----------------------------
    # Phase 1: Physical Activities
    # -----------------------------

    st.markdown("#### Physical Activities")
    st.caption("Enter time amounts only. Examples: 6 hours, 30 minutes, None, Don't know.")

    if "physical_activities" not in job:
        job["physical_activities"] = {}

    physical = job["physical_activities"]

    col1, col2 = st.columns(2)

    with col1:
        physical["standing_walking"] = st.text_input(
            "How much time standing/walking per workday?",
            value=physical.get("standing_walking", ""),
            placeholder="Example: 6 hours",
            key=f"standing_walking_detail_{i}"
        )

        physical["sitting"] = st.text_input(
            "How much time sitting per workday?",
            value=physical.get("sitting", ""),
            placeholder="Example: 2 hours",
            key=f"sitting_{i}"
        )

        physical["stooping"] = st.text_input(
            "How much time stooping/bending per workday?",
            value=physical.get("stooping", ""),
            placeholder="Example: 30 minutes or None",
            key=f"stooping_{i}"
        )

        physical["kneeling"] = st.text_input(
            "How much time kneeling per workday?",
            value=physical.get("kneeling", ""),
            placeholder="Example: 15 minutes or None",
            key=f"kneeling_{i}"
        )

        physical["crouching"] = st.text_input(
            "How much time crouching per workday?",
            value=physical.get("crouching", ""),
            placeholder="Example: 15 minutes or None",
            key=f"crouching_{i}"
        )

        physical["crawling"] = st.text_input(
            "How much time crawling per workday?",
            value=physical.get("crawling", ""),
            placeholder="Example: None",
            key=f"crawling_{i}"
        )

    with col2:
        physical["fingers_time"] = st.text_input(
            "How much time using fingers to touch, pick, pinch, type, or button?",
            value=physical.get("fingers_time", ""),
            placeholder="Example: 2 hours",
            key=f"fingers_time_{i}"
        )

        fingers_usage = st.radio(
            "Finger use involved:",
            ["None", "One Hand", "Both Hands"],
            index=["None", "One Hand", "Both Hands"].index(
                physical.get("fingers_hand_usage", "None")
            ) if physical.get("fingers_hand_usage", "None") in ["None", "One Hand", "Both Hands"] else 0,
            key=f"fingers_hand_usage_{i}"
        )

        physical["fingers_hand_usage"] = fingers_usage
        physical["fingers_one_hand"] = fingers_usage == "One Hand"
        physical["fingers_both_hands"] = fingers_usage == "Both Hands"

        physical["grasping_time"] = st.text_input(
            "How much time grasping, holding, or turning objects?",
            value=physical.get("grasping_time", ""),
            placeholder="Example: 4 hours",
            key=f"grasping_time_{i}"
        )

        grasping_usage = st.radio(
            "Grasping involved:",
            ["None", "One Hand", "Both Hands"],
            index=["None", "One Hand", "Both Hands"].index(
                physical.get("grasping_hand_usage", "None")
            ) if physical.get("grasping_hand_usage", "None") in ["None", "One Hand", "Both Hands"] else 0,
            key=f"grasping_hand_usage_{i}"
        )

        physical["grasping_hand_usage"] = grasping_usage
        physical["grasping_one_hand"] = grasping_usage == "One Hand"
        physical["grasping_both_hands"] = grasping_usage == "Both Hands"

        physical["reaching_below_time"] = st.text_input(
            "How much time reaching at or below shoulder level?",
            value=physical.get("reaching_below_time", ""),
            placeholder="Example: 1 hour",
            key=f"reaching_below_time_{i}"
        )

        reaching_below_usage = st.radio(
            "Reaching at/below shoulder involved:",
            ["None", "One Arm", "Both Arms"],
            index=["None", "One Arm", "Both Arms"].index(
                physical.get("reaching_below_arm_usage", "None")
            ) if physical.get("reaching_below_arm_usage", "None") in ["None", "One Arm", "Both Arms"] else 0,
            key=f"reaching_below_arm_usage_{i}"
        )

        physical["reaching_below_arm_usage"] = reaching_below_usage
        physical["reaching_below_one_arm"] = reaching_below_usage == "One Arm"
        physical["reaching_below_both_arms"] = reaching_below_usage == "Both Arms"

        physical["reaching_overhead_time"] = st.text_input(
            "How much time reaching overhead?",
            value=physical.get("reaching_overhead_time", ""),
            placeholder="Example: None or 30 minutes",
            key=f"reaching_overhead_time_{i}"
        )

        reaching_overhead_usage = st.radio(
            "Overhead reaching involved:",
            ["None", "One Arm", "Both Arms"],
            index=["None", "One Arm", "Both Arms"].index(
                physical.get("reaching_overhead_arm_usage", "None")
            ) if physical.get("reaching_overhead_arm_usage", "None") in ["None", "One Arm", "Both Arms"] else 0,
            key=f"reaching_overhead_arm_usage_{i}"
        )

        physical["reaching_overhead_arm_usage"] = reaching_overhead_usage
        physical["reaching_overhead_one_arm"] = reaching_overhead_usage == "One Arm"
        physical["reaching_overhead_both_arms"] = reaching_overhead_usage == "Both Arms"

    physical["stairs"] = st.text_input(
        "How much time climbing stairs or ramps?",
        value=physical.get("stairs", ""),
        placeholder="Example: 30 minutes or None",
        key=f"stairs_{i}"
    )

    physical["ladders"] = st.text_input(
        "How much time climbing ladders, ropes, or scaffolds?",
        value=physical.get("ladders", ""),
        placeholder="Example: None",
        key=f"ladders_{i}"
    )


    # -----------------------------
    # Lifting and Carrying
    # -----------------------------

    st.markdown("#### Lifting and Carrying")

    job["lifting_description"] = st.text_area(
        "Explain what they lifted/carried, how far, and how often",
        value=job.get("lifting_description", ""),
        placeholder="Example: Lifted boxes of food supplies about 10 feet several times per shift.",
        key=f"lifting_description_{i}"
    )

    job["heaviest_lift"] = st.selectbox(
        "Heaviest weight lifted",
        ["", "less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"],
        index=["", "less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"].index(
            job.get("heaviest_lift", "")
        ) if job.get("heaviest_lift", "") in ["", "less_than_1", "less_than_10", "10", "20", "50", "100_or_more", "other"] else 0,
        key=f"heaviest_lift_{i}"
    )

    job["frequent_lift"] = st.selectbox(
        "Weight frequently lifted",
        ["", "less_than_1", "less_than_10", "10", "25", "50_or_more", "other"],
        index=["", "less_than_1", "less_than_10", "10", "25", "50_or_more", "other"].index(
            job.get("frequent_lift", "")
        ) if job.get("frequent_lift", "") in ["", "less_than_1", "less_than_10", "10", "25", "50_or_more", "other"] else 0,
        key=f"frequent_lift_{i}"
    )

    job["other_lift_text"] = st.text_input(
        "If heaviest lift is Other, explain",
        value=job.get("other_lift_text", ""),
        key=f"other_lift_text_{i}"
    )

    job["other_frequent_lift_text"] = st.text_input(
        "If frequent lift is Other, explain",
        value=job.get("other_frequent_lift_text", ""),
        key=f"other_frequent_lift_text_{i}"
    )


    # -----------------------------
    # Environmental Exposures
    # -----------------------------

    st.markdown("#### Environmental Exposures")

    if "exposures" not in job:
        job["exposures"] = {}

    exposures = job["exposures"]

    col1, col2, col3 = st.columns(3)

    with col1:
        exposures["outdoors"] = st.checkbox("Outdoors", value=exposures.get("outdoors", False), key=f"outdoors_{i}")
        exposures["heat"] = st.checkbox("Extreme heat", value=exposures.get("heat", False), key=f"heat_{i}")
        exposures["cold"] = st.checkbox("Extreme cold", value=exposures.get("cold", False), key=f"cold_{i}")
        exposures["wetness"] = st.checkbox("Wetness", value=exposures.get("wetness", False), key=f"wetness_{i}")

    with col2:
        exposures["humidity"] = st.checkbox("Humidity", value=exposures.get("humidity", False), key=f"humidity_{i}")
        exposures["hazardous_substances"] = st.checkbox("Hazardous substances", value=exposures.get("hazardous_substances", False), key=f"hazardous_substances_{i}")
        exposures["moving_parts"] = st.checkbox("Moving mechanical parts", value=exposures.get("moving_parts", False), key=f"moving_parts_{i}")
        exposures["heights"] = st.checkbox("High exposed places", value=exposures.get("heights", False), key=f"heights_{i}")

    with col3:
        exposures["vibrations"] = st.checkbox("Heavy vibrations", value=exposures.get("vibrations", False), key=f"vibrations_{i}")
        exposures["loud_noise"] = st.checkbox("Loud noises", value=exposures.get("loud_noise", False), key=f"loud_noise_{i}")
        exposures["other"] = st.checkbox("Other exposure", value=exposures.get("other", False), key=f"other_exposure_{i}")

    job["other_exposure_text"] = st.text_input(
        "If Other exposure, explain",
        value=job.get("other_exposure_text", ""),
        key=f"other_exposure_text_{i}"
    )

    job["exposure_description"] = st.text_area(
        "Explain exposures and how often",
        value=job.get("exposure_description", ""),
        placeholder="Example: Exposed to loud kitchen noise daily.",
        key=f"exposure_description_{i}"
    )

    job["medical_conditions"] = st.text_area(
        "Explain how medical conditions affect ability to do this job",
        value=job.get("medical_conditions", ""),
        placeholder="Example: Back pain makes standing and lifting difficult.",
        key=f"medical_conditions_{i}"
    )

    if st.button(f"Remove Job {i + 1}", key=f"remove_job_{i}"):
        st.session_state.jobs.pop(i)
        st.rerun()


# -----------------------------
# Save / Generate
# -----------------------------

case_data = {
    "client_name": st.session_state.client_name,
    "ssn": ssn,
    "primary_phone": primary_phone,
    "secondary_phone": secondary_phone,
    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "jobs": st.session_state.jobs
}

col1, col2 = st.columns(2)

with col1:
    if st.button("Save Case"):
        if not st.session_state.client_name.strip():
            st.error("Please enter a client name before saving.")
        else:
            saved_path = save_case(case_data)
            st.success(f"Case saved to: {saved_path}")

with col2:
    if st.button("Generate Work History PDF"):
        if not st.session_state.client_name.strip():
            st.error("Please enter a client name first.")
        else:
            output_pdf = clean_filename(st.session_state.client_name) + "_work_history_completed.pdf"

            try:
                fill_work_history_pdf(case_data, output_pdf)
                st.success("PDF generated successfully.")

                with open(output_pdf, "rb") as pdf_file:
                    st.download_button(
                        label="Download Completed Work History PDF",
                        data=pdf_file,
                        file_name=output_pdf,
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error("PDF generation failed.")
                st.exception(e)