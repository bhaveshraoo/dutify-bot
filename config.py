"""
Configuration for DutyBot
"""

import os

# ── Bot Token ──────────────────────────────────────────────────
# Set via environment variable or replace the placeholder below
BOT_TOKEN = os.environ.get("8637737970:AAEwi1Lg2hj18o1AxxzsyQFXHEUWQR19BAI", "8637737970:AAEwi1Lg2hj18o1AxxzsyQFXHEUWQR19BAI")

# ── Reminder Lead Time Options ─────────────────────────────────
# Predefined reminder options shown to users (in minutes)
REMINDER_LEAD_TIMES = [5, 10, 15, 30, 60, 120, 1440]  # last = 1 day before

# ── Default Timezone ───────────────────────────────────────────
DEFAULT_TIMEZONE = "Asia/Kolkata"

# ── Daily Summary ──────────────────────────────────────────────
DAILY_SUMMARY_HOUR = 8      # 8 AM
DAILY_SUMMARY_MINUTE = 0

# ── Database ───────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "dutybot.db")
