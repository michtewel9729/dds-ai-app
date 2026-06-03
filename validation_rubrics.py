VALIDATION_RUBRICS = {
    "job_duties": {
        "label": "Typical workday duties",
        "required_details": [
            "main tasks performed",
            "tools/equipment or setting if relevant",
            "how often tasks were performed"
        ],
        "good_enough_rule": "Accept if the answer describes at least two specific work tasks.",
        "follow_up_rule": "Ask one follow-up only if the answer is too vague."
    },

    "reports": {
        "label": "Reports, writing, forms, or computer work",
        "required_details": [
            "whether reports/forms/computer work were done",
            "type of report or computer task if yes",
            "how often or how much time if known"
        ],
        "good_enough_rule": "Accept 'none' or 'no reports' as good enough.",
        "follow_up_rule": "If the answer says yes but gives no detail, ask what type of report, form, or computer task."
    },

    "supervise": {
        "label": "Supervision duties",
        "required_details": [
            "whether they supervised others",
            "who/how many people if yes",
            "what supervision duties were done"
        ],
        "good_enough_rule": "Accept 'no supervision' as good enough.",
        "follow_up_rule": "If the answer only says yes, ask who they supervised or what duties they had."
    },

    "equipment": {
        "label": "Machines, tools, and equipment",
        "required_details": [
            "specific tools, machines, or equipment used",
            "what they were used for if not obvious"
        ],
        "good_enough_rule": "Accept if the answer lists at least one specific tool, machine, or equipment item.",
        "follow_up_rule": "If the answer only says tools or equipment, ask what specific tools were used."
    },

    "interaction_details": {
        "label": "Interaction with people",
        "required_details": [
            "who they interacted with",
            "purpose of the interaction",
            "how often or how much time if known"
        ],
        "good_enough_rule": "Accept if the answer says who they interacted with and gives a basic reason.",
        "follow_up_rule": "Ask one follow-up if the answer does not say who they interacted with."
    },

    "time_amount_default": {
        "label": "Time amount fields",
        "applies_to": [
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
            "ladders"
        ],
        "required_details": [
            "time estimate with unit",
            "or none/don't know/does not apply"
        ],
        "good_enough_rule": "Accept if the answer includes hours/minutes or says none/don't know.",
        "follow_up_rule": "If the answer is only a number, ask whether it means hours or minutes."
    },

    "lifting_description": {
        "label": "Lifting and carrying explanation",
        "required_details": [
            "what was lifted or carried",
            "approximate weight if known",
            "how often or how far carried"
        ],
        "good_enough_rule": "Accept if the answer includes what was lifted and at least one of: weight, frequency, or distance.",
        "follow_up_rule": "Ask one follow-up for the most important missing detail."
    },

    "heaviest_lift": {
        "label": "Heaviest weight lifted",
        "required_details": [
            "selected weight category or don't know"
        ],
        "good_enough_rule": "Accept if a weight category is selected.",
        "follow_up_rule": "If blank, ask for the closest estimate from the listed choices."
    },

    "frequent_lift": {
        "label": "Weight frequently lifted",
        "required_details": [
            "selected weight category or don't know"
        ],
        "good_enough_rule": "Accept if a weight category is selected.",
        "follow_up_rule": "If blank, ask for the closest estimate from the listed choices."
    },

    "exposure_description": {
        "label": "Environmental exposures",
        "required_details": [
            "whether exposures happened",
            "type of exposure if yes",
            "how often if known"
        ],
        "good_enough_rule": "Accept 'none' as good enough. If exposures happened, accept if the answer names the exposure.",
        "follow_up_rule": "If the answer says yes but gives no exposure type, ask what they were exposed to."
    },

    "medical_conditions": {
        "label": "Medical condition impact on job",
        "required_details": [
            "symptom or limitation",
            "specific work task affected",
            "basic frequency or limitation if known"
        ],
        "good_enough_rule": "Accept if the answer connects a symptom or limitation to at least one work task.",
        "follow_up_rule": "Ask one follow-up if the answer does not explain how work tasks were affected."
    }
}