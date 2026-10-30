from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    add_activity,
    add_or_update_goal,
    create_user,
    get_activity,
    get_active_goal,
    get_dashboard_stats,
    get_user_by_email,
    get_user_by_id,
    list_activities,
    update_profile,
    get_achievements_for_user,
    get_daily_challenges,
    get_progress_data,
    get_recent_point_events,
    claim_challenge_reward,
    motivation_for_user,
    seed_system_data,
    sync_user_rewards,
)
from ml_model import classify_session, recommend_activity
from adaptive_fitness import ACTIVITY_LEVELS, age_category, generate_adaptive_session
from activity_explanation import build_activity_breakdown
from behavior_adapter import adapt_session, analyze_behavior
from explainable_recommendation import explain_recommendation

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "fitx.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FITX_SECRET_KEY", "change-this-secret-key")
app.config["DATABASE"] = str(DB_PATH)

ALLOWED_ACTIVITY_TYPES = {
    "Walking",
    "Running",
    "Cycling",
    "Strength",
    "Yoga",
    "Mobility",
    "Sports",
    "Dance",
}

GOALS = {"Consistency", "Endurance", "Strength", "Wellness"}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            goal TEXT NOT NULL DEFAULT 'Consistency',
            age INTEGER,
            activity_level TEXT NOT NULL DEFAULT 'Beginner',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0 AND duration_minutes <= 600),
            activity_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            points INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weekly_minutes INTEGER NOT NULL DEFAULT 150,
            weekly_days INTEGER NOT NULL DEFAULT 5,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT NOT NULL,
            requirement_type TEXT NOT NULL,
            requirement_value INTEGER NOT NULL,
            reward_points INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_id INTEGER NOT NULL,
            unlocked_at TEXT NOT NULL,
            UNIQUE(user_id, achievement_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(achievement_id) REFERENCES achievements(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            challenge_type TEXT NOT NULL,
            target_value INTEGER NOT NULL,
            reward_points INTEGER NOT NULL DEFAULT 0,
            difficulty TEXT NOT NULL,
            icon TEXT NOT NULL,
            challenge_date TEXT NOT NULL,
            UNIQUE(code, challenge_date)
        );

        CREATE TABLE IF NOT EXISTS user_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, challenge_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS point_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_key TEXT NOT NULL,
            label TEXT NOT NULL,
            points INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, event_key),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS adaptive_session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('completed', 'partial', 'skipped')),
            recommended_minutes INTEGER NOT NULL,
            completed_minutes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(user_challenges)").fetchall()}
    user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "age" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN age INTEGER")
    if "activity_level" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN activity_level TEXT NOT NULL DEFAULT 'Beginner'")
    if "reward_claimed" not in columns:
        conn.execute("ALTER TABLE user_challenges ADD COLUMN reward_claimed INTEGER NOT NULL DEFAULT 0")
    seed_system_data(conn)
    conn.commit()
    conn.close()


@app.context_processor
def inject_globals():
    user = get_user_by_id(session.get("user_id")) if session.get("user_id") else None
    return {"current_user": user, "game_user": get_game_state(session["user_id"]) if user else None}


def level_from_xp(xp: int) -> tuple[int, int, int, int]:
    level = max(1, (xp // 500) + 1)
    current_floor = (level - 1) * 500
    next_floor = level * 500
    return level, xp - current_floor, next_floor - current_floor, max(0, next_floor - xp)


def get_game_state(user_id: int) -> dict:
    sync_user_rewards(user_id)
    conn = get_db()
    user = conn.execute("SELECT name, goal FROM users WHERE id = ?", (user_id,)).fetchone()
    activities = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY activity_date DESC, id DESC", (user_id,)
    ).fetchall()
    totals = conn.execute(
        "SELECT COALESCE(SUM(points), 0) AS xp, COUNT(*) AS activity_count, "
        "COALESCE(SUM(duration_minutes), 0) AS minutes FROM activities WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    event_points = conn.execute("SELECT COALESCE(SUM(points), 0) AS points FROM point_events WHERE user_id = ?", (user_id,)).fetchone()["points"]
    conn.close()
    xp = int(totals["xp"] or 0) + int(event_points or 0)
    level, level_xp, level_span, next_xp = level_from_xp(xp)
    stats = get_dashboard_stats(user_id)
    return {
        "name": user["name"], "goal": user["goal"], "xp": xp, "coins": xp // 10,
        "level": level, "level_xp": level_xp, "level_span": level_span, "next_xp": next_xp,
        "level_progress": round(level_xp / level_span * 100) if level_span else 0,
        "streak": stats["streak"], "activity_count": int(totals["activity_count"]),
        "minutes": int(totals["minutes"]), "weekly_minutes": stats["weekly_minutes"],
        "active_days": stats["active_days_7"], "activities": activities,
    }


def get_behavior(user_id: int) -> dict:
    conn = get_db()
    rows = conn.execute(
        "SELECT status, recommended_minutes, completed_minutes, created_at FROM adaptive_session_events "
        "WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,),
    ).fetchall()
    conn.close()
    return analyze_behavior([dict(row) for row in reversed(rows)])


def get_challenges(game: dict) -> list[dict]:
    return [{**item, "reward": item["reward_points"], "complete": bool(item["completed"]), "target": item["target_value"], "unit": item["challenge_type"]} for item in get_daily_challenges(game["activities"][0]["user_id"] if game["activities"] else session["user_id"])]


def get_achievements(game: dict) -> list[dict]:
    user_id = session.get("user_id")
    return get_achievements_for_user(user_id) if user_id else []


@app.route("/")
def index():
    return redirect(url_for("dashboard")) if "user_id" in session else render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        goal = request.form.get("goal", "Consistency")
        activity_level = request.form.get("activity_level", "Beginner")
        try:
            age = int(request.form.get("age", "0"))
        except (TypeError, ValueError):
            age = 0

        if len(name) < 2:
            return render_template("register.html", error="Please enter a valid name.")
        if "@" not in email or "." not in email.split("@")[-1]:
            return render_template("register.html", error="Please enter a valid email.")
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters.")
        if goal not in GOALS:
            goal = "Consistency"
        if not 13 <= age <= 120:
            return render_template("register.html", error="Please enter an age between 13 and 120.")
        if activity_level not in ACTIVITY_LEVELS:
            activity_level = "Beginner"

        try:
            user_id = create_user(name, email, generate_password_hash(password), goal, age, activity_level)
            add_or_update_goal(user_id, 150, 5)
        except sqlite3.IntegrityError:
            return render_template("register.html", error="An account with that email already exists.")

        session.clear()
        session["user_id"] = user_id
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")
        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats(session["user_id"])
    game = get_game_state(session["user_id"])
    challenges = get_daily_challenges(session["user_id"])
    user = get_user_by_id(session["user_id"])
    activities = [dict(item) for item in list_activities(session["user_id"], limit=100)]
    adaptive = generate_adaptive_session(age=user["age"], activity_level=user["activity_level"], goal=user["goal"], activities=activities, streak=stats["streak"])
    adaptive = adapt_session(adaptive, get_behavior(session["user_id"]))
    adaptive["explanation"] = explain_recommendation(user=user, session=adaptive, behavior=adaptive["behavior"])
    adaptive["breakdown"] = build_activity_breakdown(adaptive["activities"][0]["type"], adaptive["duration"], age_category=adaptive["category"], activity_level=adaptive["activity_level"], goal=adaptive["goal"], reason=adaptive["reason"], components=adaptive["activities"])
    return render_template("dashboard.html", stats=stats, game=game, challenges=challenges, adaptive=adaptive, achievements=get_achievements(game), motivation=motivation_for_user(session["user_id"], challenges[0] if challenges else None), point_events=get_recent_point_events(session["user_id"]), today=date.today().isoformat())


@app.route("/activities")
@login_required
def activities_page():
    activities = list_activities(session["user_id"], limit=50)
    return render_template("activities.html", activities=activities, today=date.today().isoformat())


@app.route("/goals")
@login_required
def goals_page():
    goal = get_active_goal(session["user_id"])
    user = get_user_by_id(session["user_id"])
    return render_template("goals.html", goal=goal, user=user)


@app.get("/game")
@login_required
def game_page():
    return render_template("game.html", game=get_game_state(session["user_id"]))


@app.get("/challenges")
@login_required
def challenges_page():
    game = get_game_state(session["user_id"])
    return render_template("challenges.html", game=game, challenges=get_daily_challenges(session["user_id"]))


@app.get("/progress", endpoint="progress_page")
@login_required
def progress_page():
    today = date.today()
    return render_template("progress.html", progress=get_progress_data(session["user_id"]), motivation=motivation_for_user(session["user_id"]), today_year=today.year, today_month=today.month)


@app.get("/leaderboard")
@login_required
def leaderboard_page():
    conn = get_db()
    rows = conn.execute(
        "SELECT u.id, u.name, COALESCE(SUM(a.points), 0) AS xp "
        "FROM users u LEFT JOIN activities a ON a.user_id = u.id GROUP BY u.id ORDER BY xp DESC, u.name LIMIT 20"
    ).fetchall()
    conn.close()
    leaderboard = [{"rank": i + 1, "name": row["name"], "xp": int(row["xp"]), "level": level_from_xp(int(row["xp"]))[0], "you": row["id"] == session["user_id"]} for i, row in enumerate(rows)]
    demo = [("Nova", 2450), ("Pulse", 2120), ("Stride", 1980), ("Orbit", 1750), ("Kinetic", 1540)]
    for name, xp in demo:
        leaderboard.append({"rank": len(leaderboard) + 1, "name": name, "xp": xp, "level": level_from_xp(xp)[0], "you": False})
    return render_template("leaderboard.html", game=get_game_state(session["user_id"]), leaderboard=leaderboard[:8])


@app.get("/achievements")
@login_required
def achievements_page():
    game = get_game_state(session["user_id"])
    return render_template("achievements.html", game=game, achievements=get_achievements(game))


@app.get("/profile")
@login_required
def profile_page():
    game = get_game_state(session["user_id"])
    return render_template("profile.html", game=game, user=get_user_by_id(session["user_id"]), achievements=get_achievements(game))


@app.get("/rewards")
@login_required
def rewards_page():
    return render_template("rewards.html", game=get_game_state(session["user_id"]))


@app.post("/api/activities")
@login_required
def api_add_activity():
    data = request.get_json(silent=True) or request.form
    activity_type = str(data.get("activity_type", "")).strip()
    date_text = str(data.get("activity_date", "")).strip()
    notes = str(data.get("notes", "")).strip()[:500]

    try:
        duration = int(data.get("duration_minutes", 0))
    except (TypeError, ValueError):
        duration = 0

    if activity_type not in ALLOWED_ACTIVITY_TYPES:
        return jsonify({"error": "Choose a valid activity type."}), 400
    if duration < 1 or duration > 600:
        return jsonify({"error": "Duration must be between 1 and 600 minutes."}), 400
    try:
        activity_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Use a valid date."}), 400
    if activity_date > date.today():
        return jsonify({"error": "Future activity dates are not allowed."}), 400

    points = min(100, duration + 10)
    activity_id = add_activity(
        session["user_id"], activity_type, duration, activity_date.isoformat(), notes, points
    )
    sync_user_rewards(session["user_id"])
    return jsonify({"message": "Activity saved.", "activity_id": activity_id, "points": points}), 201


@app.post("/api/ai-session")
@login_required
def api_ai_session():
    data = request.get_json(silent=True) or {}
    try:
        duration_seconds = int(data.get("duration_seconds", 0))
        steps = int(data.get("steps", 0))
        movement_score = float(data.get("movement_score", 0))
        pace = float(data.get("pace", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "The session signals were invalid."}), 400

    if duration_seconds < 10 or duration_seconds > 7200:
        return jsonify({"error": "An AI session must last between 10 seconds and 2 hours."}), 400
    result = classify_session(duration_seconds, steps, movement_score, pace)
    activity_id = add_activity(
        session["user_id"], result["activity"], result["minutes"], date.today().isoformat(),
        f"AI detected session. {result['reason']}", result["points"]
    )
    sync_user_rewards(session["user_id"])
    result.update({"activity_id": activity_id, "next_reminder": "Tomorrow at 6:00 PM"})
    return jsonify(result), 201


@app.post("/api/game-session")
@login_required
def api_game_session():
    data = request.get_json(silent=True) or {}
    try:
        score = max(0, min(10000, int(data.get("score", 0))))
        distance = max(0, min(10000, int(data.get("distance", 0))))
        duration = max(1, min(600, int(data.get("duration_minutes", 1))))
    except (TypeError, ValueError):
        return jsonify({"error": "The run result was invalid."}), 400
    xp = min(250, max(25, score // 8 + distance // 20))
    coins = xp // 10
    activity_id = add_activity(
        session["user_id"], "Running", duration, date.today().isoformat(),
        f"FITX Run complete: {distance}m distance, {score} score, {coins} coins.", xp
    )
    sync_user_rewards(session["user_id"])
    return jsonify({"activity_id": activity_id, "xp": xp, "coins": coins, "score": score, "distance": distance}), 201


@app.delete("/api/activities/<int:activity_id>")
@login_required
def api_delete_activity(activity_id: int):
    activity = get_activity(activity_id, session["user_id"])
    if not activity:
        return jsonify({"error": "Activity not found."}), 404
    conn = get_db()
    conn.execute("DELETE FROM activities WHERE id = ? AND user_id = ?", (activity_id, session["user_id"]))
    conn.commit()
    conn.close()
    sync_user_rewards(session["user_id"])
    return jsonify({"message": "Activity deleted."})


@app.post("/api/goals")
@login_required
def api_save_goal():
    data = request.get_json(silent=True) or request.form
    try:
        weekly_minutes = int(data.get("weekly_minutes", 150))
        weekly_days = int(data.get("weekly_days", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "Goals must be numeric."}), 400

    if not (30 <= weekly_minutes <= 1000):
        return jsonify({"error": "Weekly minutes should be between 30 and 1000."}), 400
    if not (1 <= weekly_days <= 7):
        return jsonify({"error": "Weekly active days should be between 1 and 7."}), 400

    add_or_update_goal(session["user_id"], weekly_minutes, weekly_days)
    sync_user_rewards(session["user_id"])
    return jsonify({"message": "Goal updated."})


@app.post("/api/profile")
@login_required
def api_profile():
    data = request.get_json(silent=True) or request.form
    name = str(data.get("name", "")).strip()
    goal = str(data.get("goal", "Consistency"))
    activity_level = str(data.get("activity_level", "Beginner"))
    try:
        age = int(data.get("age", 0))
    except (TypeError, ValueError):
        age = 0
    if len(name) < 2 or goal not in GOALS or not 13 <= age <= 120 or activity_level not in ACTIVITY_LEVELS:
        return jsonify({"error": "Enter a valid name, age, goal, and activity level."}), 400
    update_profile(session["user_id"], name, goal, age, activity_level)
    return jsonify({"message": "Profile updated."})


@app.get("/api/dashboard")
@login_required
def api_dashboard():
    return jsonify(get_dashboard_stats(session["user_id"]))


@app.get("/api/progress")
@login_required
def api_progress():
    return jsonify(get_progress_data(session["user_id"]))


@app.get("/api/achievements")
@login_required
def api_achievements():
    return jsonify(get_achievements_for_user(session["user_id"]))


@app.get("/api/challenges")
@login_required
def api_challenges():
    return jsonify(get_daily_challenges(session["user_id"]))


@app.post("/api/challenges/<int:challenge_id>/claim")
@login_required
def api_claim_challenge(challenge_id: int):
    result = claim_challenge_reward(session["user_id"], challenge_id)
    status = result.pop("status")
    return jsonify(result), status


@app.get("/api/recommendation")
@login_required
def api_recommendation():
    stats = get_dashboard_stats(session["user_id"])
    user = get_user_by_id(session["user_id"])
    result = recommend_activity(
        goal=user["goal"],
        avg_duration=stats["avg_duration"],
        active_days=stats["active_days_7"],
        recent_count=stats["recent_count"],
    )
    result["breakdown"] = build_activity_breakdown(
        result["activity"],
        max(5, int(stats["avg_duration"] or 10)),
        age_category=age_category(user["age"]),
        activity_level=user["activity_level"],
        goal=user["goal"],
        reason=result["reason"],
    )
    behavior = get_behavior(session["user_id"])
    explanation_session = {
        "category": age_category(user["age"]),
        "activity_level": user["activity_level"],
        "reason": result["reason"],
        "signals": {"recent_count": stats["recent_count"]},
    }
    result["explanation"] = explain_recommendation(user=user, session=explanation_session, behavior=behavior)
    return jsonify(result)


@app.get("/api/adaptive-session")
@login_required
def api_adaptive_session():
    user = get_user_by_id(session["user_id"])
    stats = get_dashboard_stats(session["user_id"])
    result = generate_adaptive_session(age=user["age"], activity_level=user["activity_level"], goal=user["goal"], activities=[dict(item) for item in list_activities(session["user_id"], limit=100)], streak=stats["streak"])
    result = adapt_session(result, get_behavior(session["user_id"]))
    result["explanation"] = explain_recommendation(user=user, session=result, behavior=result["behavior"])
    result["breakdown"] = build_activity_breakdown(result["activities"][0]["type"], result["duration"], age_category=result["category"], activity_level=result["activity_level"], goal=result["goal"], reason=result["reason"], components=result["activities"])
    return jsonify(result)


@app.post("/api/adaptive-session/complete")
@login_required
def api_complete_adaptive_session():
    data = request.get_json(silent=True) or {}
    try:
        duration = int(data.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    if duration < 1 or duration > 600:
        return jsonify({"error": "The adaptive session duration is invalid."}), 400
    status = str(data.get("status", "completed"))
    if status not in {"completed", "partial", "skipped"}:
        return jsonify({"error": "The session result is invalid."}), 400
    try:
        completed_minutes = max(0, min(duration, int(data.get("completed_minutes", duration if status == "completed" else 0))))
    except (TypeError, ValueError):
        completed_minutes = duration if status == "completed" else 0
    conn = get_db()
    conn.execute("INSERT INTO adaptive_session_events (user_id, status, recommended_minutes, completed_minutes) VALUES (?, ?, ?, ?)", (session["user_id"], status, duration, completed_minutes))
    conn.commit()
    conn.close()
    if status == "skipped":
        return jsonify({"message": "Session skipped. FITX will offer a smaller restart session next time."}), 201
    activity = str(data.get("activity", "Walking"))
    if activity not in ALLOWED_ACTIVITY_TYPES:
        activity = "Walking"
    title = str(data.get("title", "Adaptive FITX session"))[:100]
    if status == "partial" and completed_minutes < 1:
        return jsonify({"message": "Partial session saved. No activity points were added."}), 201
    recorded_minutes = completed_minutes if status == "partial" else duration
    activity_id = add_activity(session["user_id"], activity, recorded_minutes, date.today().isoformat(), f"{status.title()} {title}.", min(100, recorded_minutes + 10))
    sync_user_rewards(session["user_id"])
    return jsonify({"message": "Adaptive session completed." if status == "completed" else "Partial session saved.", "activity_id": activity_id, "points": min(100, recorded_minutes + 10)}), 201


@app.get("/api/activities")
@login_required
def api_activities():
    return jsonify([dict(row) for row in list_activities(session["user_id"], limit=100)])


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
