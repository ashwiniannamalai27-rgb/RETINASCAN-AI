import math
import re
from typing import Any, Dict, Optional, Tuple


# PROJECT-DEFINED RULES
# These values are intentionally simple, transparent, and easy to revise later.
DR_STAGE_SCORES = {
    "No_DR": 0,
    "Mild": 2,
    "Moderate": 5,
    "Severe": 8,
    "Proliferate_DR": 9,
}

AGE_RULES = (
    (0, 17, 0),
    (18, 29, 1),
    (30, 44, 2),
    (45, 59, 3),
    (60, 130, 4),
)

BLOOD_SUGAR_RULES = (
    (0, 99, 0),
    (100, 125, 1),
    (126, 180, 2),
    (181, 250, 3),
    (251, float("inf"), 4),
)

# PROJECT-DEFINED RULES for blood pressure in mmHg.
# This is not a medical threshold table; it is a transparent project scoring rule.
BLOOD_PRESSURE_RULES = (
    (0, 119, 0, "Normal range"),
    (120, 129, 1, "Elevated range"),
    (130, 139, 2, "Moderately elevated"),
    (140, 159, 3, "High range"),
    (160, 250, 4, "Very high range"),
)

RISK_LEVEL_THRESHOLDS = {
    "Low": 5,
    "Moderate": 10,
}

FOLLOW_UP_RECOMMENDATIONS = {
    "Low": (
        "Continue routine eye-care follow-up and consult an eye-care professional if you have concerns."
    ),
    "Moderate": (
        "Consider discussing this screening result with an eye-care professional for further evaluation."
    ),
    "High": (
        "Prompt consultation with an eye-care professional is recommended for further evaluation."
    ),
}


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(parsed):
        return None

    return parsed


def _coerce_int(value: Any) -> Optional[int]:
    parsed = _coerce_float(value)
    if parsed is None:
        return None

    return int(parsed)


def _parse_blood_pressure(value: Any) -> Optional[Tuple[int, int, str]]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = re.fullmatch(r"\s*(\d{2,3})\s*/\s*(\d{2,3})\s*", text)
    if not match:
        return None

    systolic = int(match.group(1))
    diastolic = int(match.group(2))

    if systolic <= 0 or diastolic <= 0:
        return None

    if systolic > 250 or diastolic > 180:
        return None

    if systolic < diastolic:
        return None

    return systolic, diastolic, f"{systolic}/{diastolic}"


def _score_age(age: Optional[float]) -> int:
    if age is None:
        return 0

    age_int = int(age)
    if age_int <= 0 or age_int > 130:
        return 0

    for lower, upper, score in AGE_RULES:
        if lower <= age_int <= upper:
            return score

    return 0


def _score_blood_sugar(value: Optional[float]) -> int:
    if value is None:
        return 0

    sugar = float(value)
    if sugar <= 0:
        return 0

    for lower, upper, score in BLOOD_SUGAR_RULES:
        if lower <= sugar <= upper:
            return score

    return 0


def _score_blood_pressure(value: Any) -> int:
    parsed = _parse_blood_pressure(value)
    if parsed is None:
        return 0

    systolic, diastolic, _ = parsed

    for lower, upper, score, _ in BLOOD_PRESSURE_RULES:
        if systolic >= lower and systolic <= upper:
            return score

    return 0


def _risk_level_from_score(score: int) -> str:
    if score <= RISK_LEVEL_THRESHOLDS["Low"]:
        return "Low"
    if score <= RISK_LEVEL_THRESHOLDS["Moderate"]:
        return "Moderate"
    return "High"


def calculate_risk_indication(
    predicted_class,
    age,
    blood_sugar,
    blood_pressure
) -> Dict[str, Any]:
    """
    Calculate a project-defined rule-based risk indication using:
    - the CNN DR stage as the main driver
    - age, blood sugar, and blood pressure as supporting factors

    This is intentionally not a clinical risk model and should be described
    as a project-defined rule-based indication in the UI and logs.
    """
    stage_name = str(predicted_class or "No_DR").strip()
    stage_name = stage_name if stage_name in DR_STAGE_SCORES else "No_DR"

    age_value = _coerce_int(age)
    sugar_value = _coerce_float(blood_sugar)
    bp_value = _parse_blood_pressure(blood_pressure)

    stage_score = DR_STAGE_SCORES[stage_name]
    age_score = _score_age(age_value)
    sugar_score = _score_blood_sugar(sugar_value)
    bp_score = _score_blood_pressure(blood_pressure)

    total_score = stage_score + age_score + sugar_score + bp_score
    risk_level = _risk_level_from_score(total_score)

    age_display = f"{age_value} years" if age_value is not None else "Not provided"
    sugar_display = f"{sugar_value} mg/dL" if sugar_value is not None else "Not provided"
    bp_display = f"{bp_value[2]} mmHg" if bp_value is not None else "Not provided or invalid"

    factors = [
        f"DR screening stage: {stage_name} ({stage_score} project-defined points)",
        f"Age: {age_display} ({age_score} project-defined points)",
        f"Blood Sugar: {sugar_display} ({sugar_score} project-defined points)",
        f"Blood Pressure: {bp_display} ({bp_score} project-defined points)",
    ]

    if risk_level == "Low":
        explanation = (
            "The project-defined score is low because the AI screening result is not severe "
            "and the supporting information does not add much additional risk. "
            "This is a project-defined rule-based risk indication and not a medical diagnosis."
        )
    elif risk_level == "Moderate":
        explanation = (
            "The project-defined score is moderate because the AI screening result and/or the "
            "supporting health factors increase risk. This indicates a need for closer review, "
            "but it is still a project-defined rule-based risk indication rather than a medical diagnosis."
        )
    else:
        explanation = (
            "The project-defined score is high because the AI screening result and the supporting "
            "information together indicate elevated risk. This is a project-defined rule-based risk "
            "indication and not a medical diagnosis or clinically validated risk prediction."
        )

    recommendation = FOLLOW_UP_RECOMMENDATIONS.get(risk_level, FOLLOW_UP_RECOMMENDATIONS["Low"])

    return {
        "risk_level": risk_level,
        "risk_score": total_score,
        "explanation": explanation,
        "factors": factors,
        "recommendation": recommendation,
    }


def get_follow_up_recommendation(risk_level: str) -> str:
    """Return general project guidance based on the risk indication."""
    return FOLLOW_UP_RECOMMENDATIONS.get(str(risk_level or "Low").title(), FOLLOW_UP_RECOMMENDATIONS["Low"])


__all__ = [
    "calculate_risk_indication",
    "get_follow_up_recommendation",
    "DR_STAGE_SCORES",
    "AGE_RULES",
    "BLOOD_SUGAR_RULES",
    "BLOOD_PRESSURE_RULES",
    "RISK_LEVEL_THRESHOLDS",
    "FOLLOW_UP_RECOMMENDATIONS",
]
