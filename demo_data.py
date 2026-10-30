"""Optional demo-data loader. Run after creating a FITX account."""
from datetime import date, timedelta

from db import add_activity, get_user_by_email

EMAIL = "demo@example.com"

user = get_user_by_email(EMAIL)
if not user:
    raise SystemExit("Create demo@example.com through the Register page first.")

patterns = [
    (0, "Walking", 20),
    (1, "Cycling", 35),
    (2, "Yoga", 25),
    (4, "Sports", 45),
]
for offset, kind, minutes in patterns:
    day = date.today() - timedelta(days=offset)
    add_activity(user["id"], kind, minutes, day.isoformat(), "Demo activity", min(100, minutes + 10))

print("Demo activities added. Open the FITX dashboard.")
