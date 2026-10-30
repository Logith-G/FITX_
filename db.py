from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "fitx.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_user(name: str, email: str, password_hash: str, goal: str, age: int, activity_level: str) -> int:
    conn = connect()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, goal, age, activity_level) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password_hash, goal, age, activity_level),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return int(user_id)


def get_user_by_email(email: str):
    conn = connect()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = connect()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def update_profile(user_id: int, name: str, goal: str, age: int, activity_level: str) -> None:
    conn = connect()
    conn.execute("UPDATE users SET name = ?, goal = ?, age = ?, activity_level = ? WHERE id = ?", (name, goal, age, activity_level, user_id))
    conn.commit()
    conn.close()


def add_activity(user_id: int, activity_type: str, duration: int, activity_date: str, notes: str, points: int) -> int:
    conn = connect()
    cur = conn.execute(
        """
        INSERT INTO activities (user_id, activity_type, duration_minutes, activity_date, notes, points)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, activity_type, duration, activity_date, notes, points),
    )
    conn.commit()
    activity_id = cur.lastrowid
    conn.close()
    return int(activity_id)


def get_activity(activity_id: int, user_id: int):
    conn = connect()
    row = conn.execute(
        "SELECT * FROM activities WHERE id = ? AND user_id = ?", (activity_id, user_id)
    ).fetchone()
    conn.close()
    return row


def list_activities(user_id: int, limit: int = 50):
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY activity_date DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def add_or_update_goal(user_id: int, weekly_minutes: int, weekly_days: int) -> None:
    conn = connect()
    conn.execute("UPDATE goals SET active = 0 WHERE user_id = ?", (user_id,))
    conn.execute(
        "INSERT INTO goals (user_id, weekly_minutes, weekly_days, active) VALUES (?, ?, ?, 1)",
        (user_id, weekly_minutes, weekly_days),
    )
    conn.commit()
    conn.close()


def get_active_goal(user_id: int):
    conn = connect()
    row = conn.execute(
        "SELECT * FROM goals WHERE user_id = ? AND active = 1 ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()
    return row


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _calculate_streak(rows) -> int:
    dates = {date.fromisoformat(row["activity_date"]) for row in rows}
    if not dates:
        return 0
    cursor = date.today()
    if cursor not in dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def get_dashboard_stats(user_id: int) -> dict:
    conn = connect()
    goal = conn.execute(
        "SELECT weekly_minutes, weekly_days FROM goals WHERE user_id = ? AND active = 1 ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    all_rows = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY activity_date DESC, id DESC", (user_id,)
    ).fetchall()
    week_start = _current_week_start().isoformat()
    week_rows = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? AND activity_date >= ?", (user_id, week_start)
    ).fetchall()
    last_30 = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? AND activity_date >= ?",
        (user_id, (date.today() - timedelta(days=29)).isoformat()),
    ).fetchall()
    conn.close()

    total_minutes = sum(row["duration_minutes"] for row in week_rows)
    active_days = len({row["activity_date"] for row in week_rows})
    total_points = sum(row["points"] for row in all_rows)
    avg_duration = round(sum(row["duration_minutes"] for row in last_30) / len(last_30), 1) if last_30 else 0
    recent_count = len(last_30)
    streak = _calculate_streak(all_rows)

    weekly_minutes_goal = goal["weekly_minutes"] if goal else 150
    weekly_days_goal = goal["weekly_days"] if goal else 5

    daily_minutes = []
    start = _current_week_start()
    for i in range(7):
        day = start + timedelta(days=i)
        daily_minutes.append(
            {
                "day": day.strftime("%a"),
                "date": day.isoformat(),
                "minutes": sum(r["duration_minutes"] for r in week_rows if r["activity_date"] == day.isoformat()),
            }
        )

    activity_breakdown = {}
    for row in all_rows:
        activity_breakdown[row["activity_type"]] = activity_breakdown.get(row["activity_type"], 0) + row["duration_minutes"]

    return {
        "weekly_minutes": total_minutes,
        "active_days_7": active_days,
        "total_points": total_points,
        "streak": streak,
        "avg_duration": avg_duration,
        "recent_count": recent_count,
        "weekly_minutes_goal": weekly_minutes_goal,
        "weekly_days_goal": weekly_days_goal,
        "minutes_progress": min(100, round(total_minutes / weekly_minutes_goal * 100)) if weekly_minutes_goal else 0,
        "days_progress": min(100, round(active_days / weekly_days_goal * 100)) if weekly_days_goal else 0,
        "daily_minutes": daily_minutes,
        "activity_breakdown": activity_breakdown,
    }


ACHIEVEMENT_SEED = [
    ("first-step", "First Step", "Complete your first activity.", "◉", "activities", 1, 25),
    ("three-day-streak", "3-Day Streak", "Stay active for three consecutive days.", "🔥", "streak", 3, 40),
    ("seven-day-streak", "7-Day Streak", "Stay active for seven consecutive days.", "⚡", "streak", 7, 75),
    ("fourteen-day-streak", "14-Day Streak", "Stay active for fourteen consecutive days.", "✦", "streak", 14, 150),
    ("hundred-minutes", "100 Minutes", "Complete 100 total fitness minutes.", "◈", "minutes", 100, 50),
    ("five-hundred-minutes", "500 Minutes", "Complete 500 total fitness minutes.", "◆", "minutes", 500, 100),
    ("thousand-minutes", "1000 Minutes", "Complete 1000 total fitness minutes.", "★", "minutes", 1000, 250),
    ("goal-crusher", "Goal Crusher", "Complete a weekly fitness goal.", "🎯", "weekly_goal", 1, 75),
    ("consistency-champion", "Consistency Champion", "Complete weekly goals in four different weeks.", "🏆", "goal_weeks", 4, 200),
    ("point-master", "Point Master", "Earn 1000 FITX points.", "⭐", "points", 1000, 150),
]

CHALLENGE_SEED = [
    ("daily-minutes", "20-Minute Activity", "Complete at least 20 minutes of activity today.", "Minutes", 20, 30, "medium", "◈"),
    ("daily-session", "Show Up Today", "Complete any physical activity today.", "Session", 1, 25, "easy", "✓"),
    ("daily-variety", "Try Something Different", "Log an activity type you have not done recently.", "Variety", 1, 40, "medium", "✦"),
]


def seed_system_data(conn: sqlite3.Connection) -> None:
    for seed in ACHIEVEMENT_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO achievements (code, name, description, icon, requirement_type, requirement_value, reward_points) VALUES (?, ?, ?, ?, ?, ?, ?)",
            seed,
        )
    today = date.today().isoformat()
    if not conn.execute("SELECT id FROM challenges WHERE challenge_date = ?", (today,)).fetchone():
        day_index = date.today().toordinal() % len(CHALLENGE_SEED)
        code, title, description, kind, target, reward, difficulty, icon = CHALLENGE_SEED[day_index]
        conn.execute(
            "INSERT INTO challenges (code, title, description, challenge_type, target_value, reward_points, difficulty, icon, challenge_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (code, title, description, kind, target, reward, difficulty, icon, today),
        )
    conn.commit()


def _user_totals(conn: sqlite3.Connection, user_id: int) -> dict:
    row = conn.execute("SELECT COUNT(*) AS activities, COALESCE(SUM(duration_minutes), 0) AS minutes, COALESCE(SUM(points), 0) AS activity_points FROM activities WHERE user_id = ?", (user_id,)).fetchone()
    events = conn.execute("SELECT COALESCE(SUM(points), 0) AS event_points FROM point_events WHERE user_id = ?", (user_id,)).fetchone()
    rows = conn.execute("SELECT activity_date FROM activities WHERE user_id = ?", (user_id,)).fetchall()
    return {"activities": row["activities"], "minutes": row["minutes"], "points": row["activity_points"] + events["event_points"], "streak": _calculate_streak(rows)}


def _weekly_goal_complete(conn: sqlite3.Connection, user_id: int) -> bool:
    goal = conn.execute("SELECT weekly_minutes, weekly_days FROM goals WHERE user_id = ? AND active = 1 ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    if not goal:
        return False
    rows = conn.execute("SELECT duration_minutes, activity_date FROM activities WHERE user_id = ? AND activity_date >= ?", (user_id, _current_week_start().isoformat())).fetchall()
    return sum(row["duration_minutes"] for row in rows) >= goal["weekly_minutes"] and len({row["activity_date"] for row in rows}) >= goal["weekly_days"]


def sync_user_rewards(user_id: int) -> list[dict]:
    conn = connect()
    seed_system_data(conn)
    totals = _user_totals(conn, user_id)
    values = {**totals, "weekly_goal": int(_weekly_goal_complete(conn, user_id)), "goal_weeks": conn.execute("SELECT COUNT(*) AS count FROM goals WHERE user_id = ? AND active = 0", (user_id,)).fetchone()["count"]}
    unlocked = []
    for achievement in conn.execute("SELECT * FROM achievements ORDER BY id").fetchall():
        if values.get(achievement["requirement_type"], 0) < achievement["requirement_value"]:
            continue
        if not conn.execute("SELECT id FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user_id, achievement["id"])).fetchone():
            now = datetime.utcnow().isoformat(timespec="seconds")
            conn.execute("INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)", (user_id, achievement["id"], now))
            conn.execute("INSERT OR IGNORE INTO point_events (user_id, event_key, label, points, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, f"achievement:{achievement['code']}", f"Achievement: {achievement['name']}", achievement["reward_points"], now))
            unlocked.append(dict(achievement))
    challenge = conn.execute("SELECT * FROM challenges WHERE challenge_date = ?", (date.today().isoformat(),)).fetchone()
    if challenge:
        today_rows = conn.execute("SELECT activity_type, duration_minutes FROM activities WHERE user_id = ? AND activity_date = ?", (user_id, date.today().isoformat())).fetchall()
        if challenge["challenge_type"] == "Minutes":
            progress = sum(row["duration_minutes"] for row in today_rows)
        elif challenge["challenge_type"] == "Variety":
            progress = int(bool(today_rows) and len({row["activity_type"] for row in today_rows}) > 0 and len(conn.execute("SELECT DISTINCT activity_type FROM activities WHERE user_id = ? AND activity_date >= ?", (user_id, (date.today() - timedelta(days=14)).isoformat())).fetchall()) > 1)
        else:
            progress = int(bool(today_rows))
        completed = progress >= challenge["target_value"]
        now = datetime.utcnow().isoformat(timespec="seconds") if completed else None
        conn.execute("INSERT OR IGNORE INTO user_challenges (user_id, challenge_id, progress, completed, completed_at) VALUES (?, ?, ?, ?, ?)", (user_id, challenge["id"], progress, int(completed), now))
        conn.execute("UPDATE user_challenges SET progress = ?, completed = ?, completed_at = COALESCE(completed_at, ?) WHERE user_id = ? AND challenge_id = ?", (progress, int(completed), now, user_id, challenge["id"]))
    conn.commit()
    conn.close()
    return unlocked


def achievement_progress(user_id: int, achievement: dict) -> int:
    conn = connect()
    values = _user_totals(conn, user_id)
    values["weekly_goal"] = int(_weekly_goal_complete(conn, user_id))
    values["goal_weeks"] = conn.execute("SELECT COUNT(*) AS count FROM goals WHERE user_id = ? AND active = 0", (user_id,)).fetchone()["count"]
    conn.close()
    return min(achievement["requirement_value"], int(values.get(achievement["requirement_type"], 0)))


def get_achievements_for_user(user_id: int) -> list[dict]:
    sync_user_rewards(user_id)
    conn = connect()
    rows = conn.execute("SELECT a.*, ua.unlocked_at FROM achievements a LEFT JOIN user_achievements ua ON ua.achievement_id = a.id AND ua.user_id = ? ORDER BY a.id", (user_id,)).fetchall()
    conn.close()
    return [dict(row) | {"unlocked": bool(row["unlocked_at"]), "progress": achievement_progress(user_id, dict(row))} for row in rows]


def get_daily_challenges(user_id: int) -> list[dict]:
    sync_user_rewards(user_id)
    conn = connect()
    rows = conn.execute("SELECT c.*, COALESCE(uc.progress, 0) AS progress, COALESCE(uc.completed, 0) AS completed, COALESCE(uc.reward_claimed, 0) AS reward_claimed, uc.completed_at FROM challenges c LEFT JOIN user_challenges uc ON uc.challenge_id = c.id AND uc.user_id = ? WHERE c.challenge_date >= ? ORDER BY c.challenge_date DESC", (user_id, (date.today() - timedelta(days=6)).isoformat())).fetchall()
    conn.close()
    return [dict(row) | {"target": row["target_value"], "reward": row["reward_points"], "complete": bool(row["completed"]), "claimed": bool(row["reward_claimed"]), "unit": row["challenge_type"]} for row in rows]


def claim_challenge_reward(user_id: int, challenge_id: int) -> dict:
    conn = connect()
    challenge = conn.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
    progress = conn.execute("SELECT * FROM user_challenges WHERE user_id = ? AND challenge_id = ?", (user_id, challenge_id)).fetchone()
    if not challenge or not progress:
        conn.close()
        return {"success": False, "status": 404, "message": "Challenge not found."}
    if not progress["completed"]:
        conn.close()
        return {"success": False, "status": 400, "message": "Complete the mission before claiming the reward."}
    claimed = progress["reward_claimed"] if "reward_claimed" in progress.keys() else 0
    legacy_event = conn.execute("SELECT id FROM point_events WHERE user_id = ? AND event_key = ?", (user_id, f"challenge:{challenge_id}")).fetchone()
    if claimed or legacy_event:
        conn.close()
        return {"success": False, "status": 200, "already_claimed": True, "message": "Reward already claimed."}
    now = datetime.utcnow().isoformat(timespec="seconds")
    updated = conn.execute("UPDATE user_challenges SET reward_claimed = 1 WHERE user_id = ? AND challenge_id = ? AND completed = 1 AND reward_claimed = 0", (user_id, challenge_id))
    if updated.rowcount != 1:
        conn.close()
        return {"success": False, "status": 200, "already_claimed": True, "message": "Reward already claimed."}
    conn.execute("INSERT INTO point_events (user_id, event_key, label, points, created_at) VALUES (?, ?, ?, ?, ?)", (user_id, f"challenge:{challenge_id}", f"Daily challenge: {challenge['title']}", challenge["reward_points"], now))
    total = conn.execute("SELECT COALESCE(SUM(points), 0) AS points FROM activities WHERE user_id = ?", (user_id,)).fetchone()["points"]
    total += conn.execute("SELECT COALESCE(SUM(points), 0) AS points FROM point_events WHERE user_id = ?", (user_id,)).fetchone()["points"]
    conn.commit()
    conn.close()
    return {"success": True, "status": 200, "message": "Reward claimed successfully.", "points": challenge["reward_points"], "total_points": total}


def get_recent_point_events(user_id: int, limit: int = 8) -> list[dict]:
    conn = connect()
    rows = conn.execute("SELECT * FROM point_events WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_progress_data(user_id: int) -> dict:
    conn = connect()
    all_rows = conn.execute("SELECT * FROM activities WHERE user_id = ? ORDER BY activity_date", (user_id,)).fetchall()
    goal = conn.execute("SELECT * FROM goals WHERE user_id = ? AND active = 1 ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    stats = get_dashboard_stats(user_id)
    dates = {row["activity_date"] for row in all_rows}
    longest = 0
    run = 0
    cursor = None
    for value in sorted(dates):
        current = date.fromisoformat(value)
        run = run + 1 if cursor and current == cursor + timedelta(days=1) else 1
        longest = max(longest, run)
        cursor = current
    month_start = date.today().replace(day=1).isoformat()
    month_rows = [row for row in all_rows if row["activity_date"] >= month_start]
    breakdown = {}
    for row in all_rows:
        breakdown[row["activity_type"]] = breakdown.get(row["activity_type"], 0) + row["duration_minutes"]
    calendar = {}
    for row in all_rows:
        calendar[row["activity_date"]] = calendar.get(row["activity_date"], 0) + row["duration_minutes"]
    return {"total_activities": len(all_rows), "total_minutes": sum(row["duration_minutes"] for row in all_rows), "active_days": len(dates), "longest_streak": longest, "monthly_count": len(month_rows), "monthly_minutes": sum(row["duration_minutes"] for row in month_rows), "average_duration": round(sum(row["duration_minutes"] for row in all_rows) / len(all_rows), 1) if all_rows else 0, "most_performed": max(breakdown, key=breakdown.get) if breakdown else "None yet", "calendar": calendar, "weekly": stats, "goal": dict(goal) if goal else {"weekly_minutes": 150, "weekly_days": 5}}


def motivation_for_user(user_id: int, challenge: dict | None = None) -> str:
    stats = get_dashboard_stats(user_id)
    if stats["streak"] >= 2:
        return f"🔥 You're on a {stats['streak']}-day streak. Keep it going."
    remaining = max(0, stats["weekly_minutes_goal"] - stats["weekly_minutes"])
    if remaining and remaining <= 30:
        return f"🎯 You're only {remaining} minutes away from your weekly goal."
    if stats["minutes_progress"] >= 100:
        return "🎉 Weekly goal completed. Great consistency."
    if challenge and not challenge.get("completed"):
        return "🎯 Your daily challenge is still waiting for you."
    return "A short 15-minute session is enough to get your momentum moving again."
