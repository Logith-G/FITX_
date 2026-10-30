# FITX — Fitness Activity Motivation Platform

FITX is a full-stack department-level project built around the problem statement:
**Develop technology-enabled tools that motivate users to participate regularly in fitness activities.**

## What this version already does

- User registration and secure password hashing
- Session-based login/logout
- Personal dashboard
- Activity logging and history
- Weekly minutes + active-day goals
- Progress bars, weekly chart, and activity-mix chart
- Streak and FITX points for motivation
- ML-powered next-activity category recommendation
- Profile focus selection
- Responsive UI for laptop and mobile
- SQLite database, so no database server is required
- Game-style player levels, XP, coins, missions, achievements, leaderboard, and reward shop
- FITX Run arcade prototype with keyboard controls and persisted completion rewards
- AI motion-session classifier for automatic Walking, Running, or Mobility detection
- Persisted achievements and one-time achievement rewards
- Date-based daily challenges with progress recalculated from real activities
- Dedicated Progress page with weekly summaries, monthly metrics, and an activity calendar
- Contextual motivation messages based on streaks, goals, recent activity, and challenges
- Adaptive personal fitness sessions using age category, activity level, goal, and recent behavior
- Beginner-friendly recommendation breakdowns with ordered exercises, timing, instructions, and total duration

## Tech stack

Frontend: HTML5, CSS3, JavaScript, Chart.js
Backend: Python + Flask
Database: SQLite
ML: scikit-learn Random Forest + joblib

## Run in VS Code / Windows

### 1. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

### 2. Activate it

```powershell
.venv\Scripts\activate
```

If PowerShell blocks activation, open Command Prompt and run:

```cmd
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start FITX

```powershell
python app.py
```

Then open the local address printed by Flask, normally `http://127.0.0.1:5000`.

The first launch creates `instance/fitx.db` and trains the tiny demo ML model in `models/`.

## Main pages

- `/` — FITX landing page
- `/register` — create an account
- `/login` — sign in
- `/dashboard` — game command center with XP, missions, streak, and coach
- `/game` — playable FITX Run with A/D or arrow-key lane controls
- `/activities` — AI motion capture and activity timeline
- `/progress` — weekly/monthly progress and fitness calendar
- `/challenges` — daily mission board
- `/leaderboard` — demo community rankings
- `/achievements` — player badge cabinet
- `/profile` — player journey and stats
- `/rewards` — virtual coin reward shop
- `/goals` — goals and profile focus settings

## REST API

- `POST /api/activities`
- `GET /api/activities`
- `DELETE /api/activities/<id>`
- `POST /api/goals`
- `POST /api/profile`
- `GET /api/dashboard`
- `GET /api/recommendation`
- `GET /api/adaptive-session`
- `POST /api/adaptive-session/complete`

Recommendations returned by `/api/recommendation` and `/api/adaptive-session` now include a `breakdown` object. This is a presentation layer around the existing recommendation and adaptive engines; it does not change their decisions or add database tables.
- `GET /api/progress`
- `GET /api/achievements`
- `GET /api/challenges`
- `POST /api/ai-session`
- `POST /api/game-session`

### Hackathon demo flow

1. Open `/` and show the FITX power loop: move → XP → level up → rewards.
2. Register a player and open the command center.
3. Start **FITX Run**, use A/D or arrow keys, then press **Finish**.
4. Show the completion card, updated XP/coins, level progress, missions, and streak.
5. Open Missions, Leaderboard, Achievements, Profile, and Reward shop to demonstrate the connected game layer.

The run and AI-session features are intentionally lightweight browser prototypes. Motion detection is more reliable on a phone with motion sensors; desktop browsers use timing and keyboard/game signals. Reward-shop purchases are currently presentation interactions and do not deduct coins from SQLite.

## Database schema

### users
`id, name, email, password_hash, goal, age, activity_level, created_at`

The adaptive engine categorizes ages as Youth, Young Adult, Adult, or Older Adult, then combines that category with activity level, goal, recent activity, and streak history. Existing databases are migrated in place at startup; existing activities remain the session history and adaptive completion uses the normal activity/reward pipeline.

### activities
`id, user_id, activity_type, duration_minutes, activity_date, notes, points, created_at`

### goals
`id, user_id, weekly_minutes, weekly_days, active, created_at`

### achievements and rewards
FITX seeds a small achievement catalog on startup. `user_achievements` stores each user's unlock date, while `point_events` stores one-time achievement and challenge rewards with a unique event key. This prevents refreshes from duplicating rewards and keeps existing activity data intact.

### challenges
Daily challenge definitions are stored in `challenges`; each user's calculated progress and completion date are stored in `user_challenges`. Progress is synchronized after activity, goal, and deletion changes.

## Demo flow

1. Register a user.
2. Open Dashboard and show the empty progress state.
3. Go to Activities and log 3–5 activities across different days.
4. Return to Dashboard and show minutes, active days, points, streak, charts, and recommendation.
5. Change goals and show progress recalculation.
6. Open the recommendation endpoint in DevTools or present the recommendation card as the ML feature.

## Important academic note

The included ML model is intentionally small and uses synthetic training data so the project is runnable without collecting sensitive user datasets. For a final-year/research extension, replace the synthetic dataset with an appropriately governed, anonymized dataset and evaluate the model with train/test splits and metrics.

FITX recommendations are generic activity suggestions and should not be presented as medical or clinical advice.

## Optional demo data

Register `demo@example.com`, then run:

```powershell
python demo_data.py
```

This creates four sample activity records for the presentation dashboard.

## Suggested presentation narrative

**Problem:** People may know that fitness is important but lack a simple way to track consistency and stay motivated.

**Solution:** FITX combines activity logging, goals, visual progress, personal points/streaks, and an ML-based activity-category suggestion in one lightweight application.

The full motivation loop is **Track → Analyze → Motivate → Challenge → Reward → Build consistency**. Achievements, daily challenges, progress summaries, calendar intensity, and contextual motivation all use the authenticated user's SQLite records.

**Innovation angle:** Instead of only counting workouts, the system focuses on continuity and personalized activity suggestions from recent patterns.

**Future scope:** wearable/device integrations, notifications, richer datasets, model evaluation, institution-level analytics with appropriate privacy controls, and explainable recommendation models.
