from __future__ import annotations

from datetime import date, timedelta


AGE_CATEGORIES = {
    "Youth": (13, 17),
    "Young Adult": (18, 39),
    "Adult": (40, 59),
    "Older Adult": (60, 150),
}

ACTIVITY_LEVELS = ("Beginner", "Intermediate", "Regular")


def age_category(age: int | None) -> str:
    if age is None:
        return "Unspecified"
    for category, (minimum, maximum) in AGE_CATEGORIES.items():
        if minimum <= age <= maximum:
            return category
    return "Unspecified"


def _recent_signals(activities: list[dict]) -> dict:
    today = date.today()
    recent = [
        item for item in activities
        if item["activity_date"] >= (today - timedelta(days=29)).isoformat()
    ]
    last_date = max((item["activity_date"] for item in activities), default=None)
    inactive_days = (today - date.fromisoformat(last_date)).days if last_date else 999
    return {
        "recent_count": len(recent),
        "recent_minutes": sum(item["duration_minutes"] for item in recent),
        "average_duration": round(sum(item["duration_minutes"] for item in recent) / len(recent)) if recent else 0,
        "inactive_days": inactive_days,
    }


def generate_adaptive_session(
    *,
    age: int | None,
    activity_level: str,
    goal: str,
    activities: list[dict],
    streak: int,
) -> dict:
    level = activity_level if activity_level in ACTIVITY_LEVELS else "Beginner"
    category = age_category(age)
    signals = _recent_signals(activities)
    returning = signals["inactive_days"] >= 7
    struggling = signals["recent_count"] <= 1 or returning
    progressing = signals["recent_count"] >= 4 and streak >= 3

    if struggling:
        duration = 12 if level == "Beginner" else 15
        difficulty = "Re-engagement"
    else:
        duration = {"Beginner": 18, "Intermediate": 25, "Regular": 30}[level]
        difficulty = {"Beginner": "Beginner", "Intermediate": "Intermediate", "Regular": "Progressive"}[level]
        if progressing:
            duration += 3
            difficulty = "Progressive"

    if goal == "Strength":
        activities_plan = [("Strength", max(5, duration - 6)), ("Mobility", 6)]
    elif goal == "Endurance":
        activities_plan = [("Walking", max(8, duration - 5)), ("Mobility", 5)]
    elif goal == "Wellness":
        activities_plan = [("Yoga", max(7, duration - 5)), ("Mobility", 5)]
    else:
        activities_plan = [("Walking", max(7, duration - 6)), ("Mobility", 6)]

    if category in {"Older Adult", "Youth"} and level == "Beginner":
        activities_plan = [("Walking", max(6, duration - 8)), ("Mobility", 5), ("Yoga", 3)]

    total_duration = sum(minutes for _, minutes in activities_plan)
    if returning:
        reason = "FITX kept this session smaller because your recent activity shows a return after time away."
    elif progressing:
        reason = "Your recent activity and streak show consistency, so FITX added a small progressive step."
    else:
        reason = "FITX used your age group, activity level, goal, and recent activity to shape this session."

    return {
        "category": category,
        "activity_level": level,
        "goal": goal,
        "title": f"{total_duration}-Minute {difficulty} Session",
        "activities": [{"type": kind, "minutes": minutes} for kind, minutes in activities_plan],
        "duration": total_duration,
        "difficulty": difficulty,
        "reason": reason,
        "signals": signals,
        "note": "FITX provides general fitness recommendations and is not a substitute for professional medical advice.",
    }