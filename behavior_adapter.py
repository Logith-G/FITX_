from __future__ import annotations

from datetime import date, timedelta


def _resize_activities(activities: list[dict], duration: int) -> list[dict]:
    if not activities:
        return []
    original = sum(item["minutes"] for item in activities) or 1
    resized = [{**item, "minutes": max(1, duration * item["minutes"] // original)} for item in activities]
    resized[-1]["minutes"] += duration - sum(item["minutes"] for item in resized)
    return resized


def analyze_behavior(events: list[dict]) -> dict:
    recent = events[-5:]
    if not recent:
        return {"state": "new", "label": "Normal personalized session", "completed": 0, "completion_rate": None, "reason": "There is not enough session history yet, so FITX is using your profile and current activity data."}

    completed = sum(event["status"] == "completed" for event in recent)
    partial = sum(event["status"] == "partial" for event in recent)
    completion_rate = round(completed / len(recent) * 100)
    last_date = date.fromisoformat(recent[-1]["created_at"][:10])
    inactive = (date.today() - last_date).days >= 7

    if inactive:
        return {"state": "returning", "label": "Consistency rescue", "completed": completed, "completion_rate": completion_rate, "reason": "Your recent activity has decreased, so FITX created a shorter session to help you restart your routine."}
    if partial >= 2 or (len(recent) >= 3 and completion_rate < 50):
        return {"state": "struggling", "label": "Adapted session", "completed": completed, "completion_rate": completion_rate, "reason": "Your recent sessions were partially completed, so FITX adjusted the next session to make it more manageable."}
    if len(recent) >= 3 and completed >= 3:
        return {"state": "consistent", "label": "Progressive session", "completed": completed, "completion_rate": completion_rate, "reason": "Your recent sessions show consistent participation, so FITX has slightly increased the challenge."}
    return {"state": "normal", "label": "Normal personalized session", "completed": completed, "completion_rate": completion_rate, "reason": "FITX is continuing with a manageable session while it learns more from your participation."}


def adapt_session(session: dict, behavior: dict) -> dict:
    result = {**session, "behavior": behavior}
    if behavior["state"] == "returning":
        result["duration"] = 6
        result["difficulty"] = "Consistency Rescue"
        result["title"] = "6-Minute Consistency Rescue Session"
        result["activities"] = [{"type": "Walking", "minutes": 2}, {"type": "Mobility", "minutes": 2}, {"type": "Strength", "minutes": 2}]
    elif behavior["state"] == "struggling":
        result["duration"] = max(8, min(session["duration"], session["duration"] - 5))
        result["difficulty"] = "Adapted"
        result["title"] = f"{result['duration']}-Minute Adapted Session"
    elif behavior["state"] == "consistent":
        result["duration"] = min(session["duration"] + 2, session["duration"] + 5)
        result["difficulty"] = "Progressive"
        result["title"] = f"{result['duration']}-Minute Progressive Session"
    if behavior["state"] in {"returning", "struggling", "consistent"}:
        result["activities"] = _resize_activities(result["activities"], result["duration"])
    result["reason"] = behavior["reason"]
    return result