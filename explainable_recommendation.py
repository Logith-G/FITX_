from __future__ import annotations


def explain_recommendation(*, user: dict, session: dict, behavior: dict) -> dict:
    signals = session.get("signals", {})
    recent_count = signals.get("recent_count", 0)
    recent_level = "low" if recent_count <= 1 else "regular" if recent_count >= 4 else "moderate"
    factors = [
        f"Age group: {session['category']}",
        f"Activity level: {session['activity_level']}",
        f"Fitness goal: {user['goal']}",
        f"Recent activity: {recent_level}",
    ]
    if behavior.get("completion_rate") is not None:
        factors.append(f"Recent session completion: {behavior['completion_rate']}%")
    return {
        "title": "Why this session?",
        "factors": factors,
        "reason": session["reason"],
        "behavior_state": behavior["state"],
        "behavior_label": behavior["label"],
    }