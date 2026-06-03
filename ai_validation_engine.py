import os
from openai import OpenAI
from validation_rubrics import VALIDATION_RUBRICS

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is missing.")

client = OpenAI(api_key=api_key)


def get_rubric(check_type):
    return VALIDATION_RUBRICS.get(check_type, {
        "label": check_type,
        "required_details": [],
        "good_enough_rule": "Accept only if the answer gives clear, useful detail for this question.",
        "follow_up_rule": "Ask one short follow-up if the answer is vague, incomplete, or unclear."
    })


def validate_answer(client_answer, check_type="general"):
    answer = str(client_answer or "").strip()
    rubric = get_rubric(check_type)

    prompt = f"""
You are an AI quality reviewer for an SSA/DDS Work History Report app.

Return ONLY valid JSON in this exact format:

{{
  "status": "Good" or "Needs Follow-Up",
  "reason": "short reason",
  "missing_details": ["detail1", "detail2"],
  "follow_up_question": "one short question or empty string"
}}

Do NOT give legal advice.
Do NOT tell the user what to say.
Do NOT exaggerate or add facts.

Question type:
{rubric["label"]}

Details this answer should usually include:
{rubric.get("required_details", [])}

Good enough standard:
{rubric.get("good_enough_rule", "")}

Follow-up rule:
{rubric.get("follow_up_rule", "")}

User answer:
"{answer}"

Rules:
- This is not a perfection test.
- Mark "Good" if a reasonable case manager would generally understand the work activity.
- Mark "Needs Follow-Up" only if the answer is unclear, extremely vague, contradictory, or missing the core activity.
- Ask only ONE short follow-up question.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content