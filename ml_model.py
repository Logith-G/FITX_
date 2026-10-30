from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "activity_recommender.joblib"

FEATURES = ["goal_code", "avg_duration", "active_days", "recent_count"]

GOAL_MAP = {
    "Consistency": 0,
    "Endurance": 1,
    "Strength": 2,
    "Wellness": 3,
}

ACTIVITIES = ["Walking", "Cycling", "Strength", "Yoga", "Mobility", "Sports", "Dance", "Running"]


def classify_session(duration_seconds: int, steps: int, movement_score: float, pace: float) -> dict:
    """Classify a captured phone session from time, cadence, motion, and pace signals."""
    minutes = max(1, round(duration_seconds / 60))
    cadence = steps / max(duration_seconds / 60, 1)
    if pace >= 8.5 or cadence >= 145:
        activity = "Running"
        confidence = 0.94
        reason = "Your pace and step cadence match a running pattern."
    elif pace >= 3.0 or cadence >= 70 or movement_score >= 0.35:
        activity = "Walking"
        confidence = 0.89
        reason = "Your movement rhythm matches a steady walking pattern."
    else:
        activity = "Mobility"
        confidence = 0.74
        reason = "The motion signal looks like a light movement session."

    intensity = 20 if activity == "Running" else 10 if activity == "Walking" else 5
    points = min(100, minutes + intensity)
    return {
        "activity": activity,
        "minutes": minutes,
        "steps": max(0, steps),
        "points": points,
        "confidence": confidence,
        "reason": reason,
        "coach_message": f"Nice work. Your {minutes}-minute session counts as {activity.lower()} and earned {points} FITX points.",
    }


def train_model() -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    # Small synthetic training set is used so the demo works without collecting personal data.
    samples = []
    labels = []
    for goal, goal_code in GOAL_MAP.items():
        for avg in [10, 20, 30, 45, 60]:
            for active_days in [0, 1, 3, 5, 7]:
                for recent_count in [0, 2, 4, 8]:
                    if goal == "Strength":
                        label = "Strength"
                    elif goal == "Endurance":
                        label = "Cycling" if avg < 40 else "Running"
                    elif goal == "Wellness":
                        label = "Yoga" if active_days < 4 else "Mobility"
                    else:
                        label = "Walking" if active_days < 4 or avg < 25 else "Sports"
                    samples.append([goal_code, avg, active_days, recent_count])
                    labels.append(label)

    X = np.array(samples, dtype=float)
    encoder = LabelEncoder()
    y = encoder.fit_transform(labels)
    model = RandomForestClassifier(n_estimators=80, random_state=42, max_depth=8)
    model.fit(X, y)
    joblib.dump({"model": model, "encoder": encoder}, MODEL_PATH)


def _ensure_model():
    if not MODEL_PATH.exists():
        train_model()
    return joblib.load(MODEL_PATH)


def recommend_activity(goal: str, avg_duration: float, active_days: int, recent_count: int) -> dict:
    bundle = _ensure_model()
    model = bundle["model"]
    encoder = bundle["encoder"]
    goal_code = GOAL_MAP.get(goal, 0)
    row = np.array([[goal_code, avg_duration, active_days, recent_count]], dtype=float)
    prediction = model.predict(row)[0]
    label = encoder.inverse_transform([prediction])[0]

    explanation = {
        "Consistency": "The model is prioritizing an easy-to-repeat activity based on recent consistency.",
        "Endurance": "The model is prioritizing an endurance-oriented activity from recent activity patterns.",
        "Strength": "The model is prioritizing a strength-oriented activity based on the selected goal.",
        "Wellness": "The model is prioritizing a lower-complexity wellness activity based on recent patterns.",
    }.get(goal, "The model used your selected goal and recent activity pattern.")

    return {
        "activity": label,
        "reason": explanation,
        "note": "FITX recommendations are general activity suggestions, not medical advice. Choose activities appropriate for you and follow your school, coach, or healthcare guidance when relevant.",
    }
